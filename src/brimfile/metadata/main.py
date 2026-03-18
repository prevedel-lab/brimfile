from ..file_abstraction import FileAbstraction, sync, _gather_sync
from ..utils import concatenate_paths
from . import schema, validation
from .types import MetadataItem, MetadataValue

from .. import units
from ..constants import brim_obj_names, reserved_attr_names

import warnings

import asyncio
from typing import Any
from enum import Enum

__docformat__ = "google"


class Metadata:
    Item = MetadataItem
    Type = schema.Type

    @staticmethod
    def print_schema(
        include_description: bool = True, *, 
        description_width: int | None = None,
        attr_width: int = 30,
        type_width: int | None = None,
        mandatory_width: int = 10
    ) -> None:
        """Print all metadata attributes defined in ``METADATA_SCHEMA``.
        Args:
            include_description: Whether to include the description column.
            For other arguments, see `brimfile.metadata.schema.schema_as_string()`. They are passed to this function to allow configuring the output format when printing the metadata schema.
        """
        
        print(
            schema.schema_as_string(
                include_description=include_description,
                description_width=description_width,
                attr_width=attr_width,
                type_width=type_width,
                mandatory_width=mandatory_width
            )
        )

    def __init__(self, file: FileAbstraction, data_full_path: str | None = None) -> None:
        """
        Initialize the Metadata object.
        Args:
            file (FileAbstraction).
            data_full_path (str): The full path to the data group in the file. If None, only the metadata in the file are exposed.
        """
        self._file = file
        self._path = brim_obj_names.Brillouin_base_path
        self._general_metadata: dict[str, dict[str, MetadataValue]] | None = None
        self._data_path = data_full_path
    
    async def _load_local_metadata(self, metadata_type: schema.Type) -> dict[str, MetadataItem]:
        out_dict: dict[str, MetadataItem] = {}
        if self._data_path is not None:
            attrs = await self._file.list_attributes(self._data_path)
            group = f"{metadata_type.value}."
            attrs = [attr for attr in attrs if attr.startswith(
                group) and not attr.endswith('_units')]
            coros_attrs = [self._file.get_attr(self._data_path, attr) for attr in attrs]
            coros_units = [units.of_attribute(self._file, self._data_path, attr) for attr in attrs]
            res = await asyncio.gather(*coros_attrs, *coros_units)
            for i, attr in enumerate(attrs):
                val = res[i]
                u = res[i + len(attrs)]
                out_dict[attr[len(group):]] = Metadata.Item(val, u)
        return out_dict

    async def _load_general_metadata(self) -> dict[str, dict[str, MetadataValue]]:
        if self._general_metadata is not None:
            return self._general_metadata   
        metadata_dict: dict[str, dict[str, MetadataValue]] = {}
        try:
            loaded_metadata = await self._file.get_attr(self._path, 'Metadata')
            if isinstance(loaded_metadata, dict):
                normalized_metadata: dict[str, dict[str, MetadataValue]] = {}
                for section_name, section_value in loaded_metadata.items():
                    if not isinstance(section_name, str) or not isinstance(section_value, dict):
                        continue
                    normalized_section: dict[str, MetadataValue] = {}
                    for k, v in section_value.items():
                        if isinstance(k, str):
                            normalized_section[k] = v
                    normalized_metadata[section_name] = normalized_section
                metadata_dict = normalized_metadata
        except Exception:
            # if the metadata group does not exist, create it
            for metadata_type in Metadata.Type:
                metadata_dict[metadata_type.value] = {}
            await self._file.create_attr(self._path, 'Metadata', metadata_dict)
        for metadata_type in Metadata.Type:
            if metadata_type.value not in metadata_dict or not isinstance(metadata_dict[metadata_type.value], dict):
                metadata_dict[metadata_type.value] = {}
        self._general_metadata = metadata_dict
        return metadata_dict

    async def _get_single_item(self, metadata_type: schema.Type, name: str) -> MetadataItem:
        """
        Retrieve a single metadata.
        This method attempts to fetch a metadata attribute based on the specified type and name.
        If the instance is linked to a specific data group, it first checks if the metadata is
        defined within that group. If not, it retrieves the metadata from the general metadata group.
        Args:
            type (Type): The type of the metadata to retrieve.
            name (str): The name of the metadata attribute.
        Returns:
            The value of the requested metadata attribute and its units.
        Raises:
            KeyError: If the metadata attribute cannot be retrieved from either the specific
                       data group or the general metadata group.
        """

        metadata_dict = await self.to_dict_async(metadata_type)
        if name not in metadata_dict:
            raise KeyError(
            f"Metadata attribute {metadata_type.value}.{name} not found.")
        return metadata_dict[name]

    def __getitem__(self, key: str) -> MetadataItem:
        """
        Get the metadata for a specific key.
        Args:
            key (str): The key for the metadata. It has the format 'group.object', e.g. 'Experiment.Datetime'.
        """
        parts = key.split('.', 1)
        if len(parts) != 2:
            raise KeyError(
                f"Invalid key format: {key}. Expected 'group.object'.")
        group = parts[0]
        obj = parts[1]
        if group not in Metadata.Type.__members__:
            raise KeyError(
                f"Group {group} not valid. It must be one of {list(Metadata.Type.__members__)}")
        return sync(self._get_single_item(Metadata.Type[group], obj))

    def to_dict(self, metadata_type: schema.Type, *,
                validate: bool = False, include_missing: bool = False) -> dict[str, MetadataItem]:
        """
        Returns the metadata of a specific type as a dictionary. See doc of `to_dict_async`.
        """
        return sync(self.to_dict_async(metadata_type, validate=validate, include_missing=include_missing))

    async def to_dict_async(self, metadata_type: schema.Type, *,
                            validate: bool = False, include_missing: bool = False) -> dict[str, MetadataItem]:
        """
        Returns the metadata of a specific type as a dictionary.
        This method attempts to fetch a metadata attribute based on the specified type and name.
        If the instance is linked to a specific data group, it first checks if some metadata are
        defined within that group. If not, it retrieves the metadata from the general metadata group.
        Args:
            type (Type): The type of the metadata to retrieve.
            validate (bool): If True, validate the metadata against the schema.
            include_missing (bool): If True and validate is True, include missing metadata attributes in the result. Missing attributes will have the value None. If validate is False, this argument is ignored and missing attributes are not included in the result.
        Returns:
            dict: A dictionary containing all metadata attributes, where each element is of the type Item.
        """

        # load first the metadata defined locally in the data group (if the Metadata object is linked to a data group), as they take precedence over the general metadata
        out_dict = await self._load_local_metadata(metadata_type)
        local_attrs = tuple(out_dict.keys())
        if validate:
            # validate the local metadata first.
            for key, value in out_dict.items():
                _, out_dict[key] = validation.validate_single_field(metadata_type, key, value)

        # then load the general metadata from the metadata group
        full_global_metadata_dict = await self._load_general_metadata()
        global_metadata_dict_for_type = full_global_metadata_dict.get(metadata_type.value, {})
        # remove the attributes that are already loaded from the data group or that are units attributes
        attrs = [attr for attr in global_metadata_dict_for_type.keys() if not (attr in local_attrs or attr.endswith('_units') or attr in reserved_attr_names)]
        for attr in attrs:
            val = global_metadata_dict_for_type.get(attr)
            units_value = global_metadata_dict_for_type.get(f"{attr}_units", None)
            u = units_value if isinstance(units_value, str) else None
            res = Metadata.Item(val, u)
            if validate:
                _, res = validation.validate_single_field(metadata_type, attr, res)
            out_dict[attr] = res

        if validate and include_missing:
            # include missing required attributes with value None
            schema_attrs = [field.name for field in schema.METADATA_SCHEMA[metadata_type] if field.required]
            for attr in schema_attrs:
                if attr not in out_dict:
                    out_dict[attr] = Metadata.Item(None, None, validity=validation.MetadataItemValidity.MISSING_FIELD)

        return out_dict

    def add(self, metadata_type: schema.Type, metadata: dict[str, MetadataItem], local: bool = False) -> None:
        """
        Add metadata to the file.
        Call `brimfile.Metadata.metadata_class.print_schema()` to see the list of available metadata attributes and their description.
        Args:
            type (Type): The type of the metadata to add.
            metadata (dict[str, Item]): A dictionary containing the metadata attributes to add.
                            Each element must be of type Metadata.Item.
                            The keys of the dictionary are the names of the attributes.
            local (bool): If True, the metadata will be added to the data group. Otherwise, it will be added to the general metadata group.
        """
        # to save local metadata, the Metadata object must be linked to a data group
        if local and self._data_path is None:
            raise ValueError(
                "The current metadata object is not linked to a data group. Set local to False to add the metadata to the general metadata group.")
        if not local:
            general_metadata = sync(self._load_general_metadata())        
        # iterate over the metadata dictionary and add each attribute
        for key, value in metadata.items():
            if not isinstance(value, Metadata.Item):
                # if no units are provided, we assume None
                value = Metadata.Item(value, None)
            key, value = validation.validate_single_field(metadata_type, key, value, report_on_invalid=True)
            val = value.value
            if local:
                group = self._data_path
                name = f"{metadata_type.value}.{key}"
                sync(self._file.create_attr(group, name, val))
                if value.units is not None:
                    units.add_to_attribute(self._file, group, name, value.units)
            else:
                general_metadata[metadata_type.value][key] = val
                if value.units is not None:
                    general_metadata[metadata_type.value][f"{key}_units"] = value.units
        if not local:
            self._general_metadata = general_metadata
            sync(self._file.create_attr(self._path, 'Metadata', general_metadata))

    def all_to_dict(self, *,
                    validate: bool = False, include_missing: bool = False) -> dict[str, dict[str, MetadataItem]]:
        """
        Returns all the metadata as a dictionary.
        Returns:
            dict: A dictionary containing all the elements in Metadata.Type as a key.
                    Each of the key is defining a dictionary, as returned by Metadata.to_dict()
            For `validate and `include_missing` arguments, see `Metadata.to_dict_async()`.
        """
        metadata_types = [metadata_type for metadata_type in Metadata.Type]
        coros = [self.to_dict_async(metadata_type, validate=validate, include_missing=include_missing) for metadata_type in metadata_types]

        #retrieve all metadata asynchronously
        res = _gather_sync(*coros)
        #assign them to a dictionary
        full_metadata = {metadata_type.name: dic for metadata_type, dic in zip(metadata_types, res)}
        return full_metadata

    @staticmethod
    def _coerce_numeric_metadata_value(value: MetadataValue, *, field_name: str) -> float:
        if isinstance(value, Enum):
            raise TypeError(f"Metadata field '{field_name}' has enum value, expected a numeric value.")
        if isinstance(value, (int, float, str)):
            return float(value)
        raise TypeError(f"Metadata field '{field_name}' value '{value}' is not numeric.")
    

# utility functions to retrieve specific metadata attributes, with unit conversion if necessary. 

    async def _get_wavelength_nm_async(self) -> float:
        """
            Retrieve the wavelength metadata and convert it to nm if necessary. If the wavelength metadata is not found, an exception is raised.
            If the wavelength metadata has no units defined, a warning is issued and the value is assumed to be in nm.
            Returns:
                float: The wavelength in nm.
            Raises:
                Exception: If the wavelength metadata cannot be retrieved or if the unit is not recognized.
        """
        wl = await self._get_single_item(Metadata.Type.Optics, 'Wavelength')
        if wl.units is None:
            warnings.warn(f"Wavelength metadata has no units defined. Assuming the value is in nm.")
            return self._coerce_numeric_metadata_value(wl.value, field_name='Wavelength')
        unit = str(wl.units).lower()
        value = self._coerce_numeric_metadata_value(wl.value, field_name='Wavelength')
        if unit in ('nm', 'nanometer', 'nanometers'):
            return value
        if unit in ('um', 'µm', 'micrometer', 'micrometers'):
            return value * 1e3
        if unit in ('m', 'meter', 'meters'):
            return value * 1e9
        raise ValueError(f"Unsupported wavelength unit '{wl.units}'.")

    async def _get_temperature_c_async(self) -> float:
        """
            Retrieve the temperature metadata and convert it to Celsius if necessary. If the temperature metadata is not found, an exception is raised.
            If the temperature metadata has no units defined, a warning is issued and the value is assumed to be in Celsius.
            Returns:
                float: The temperature in Celsius.
            Raises:
                Exception: If the temperature metadata cannot be retrieved or if the unit is not recognized.
        """    
        t = await self._get_single_item(Metadata.Type.Experiment, 'Temperature')       
        if t.units is None:
            warnings.warn(f"Temperature metadata has no units defined. Assuming the value is in Celsius.")
            return self._coerce_numeric_metadata_value(t.value, field_name='Temperature')
        unit = str(t.units).lower()
        value = self._coerce_numeric_metadata_value(t.value, field_name='Temperature')
        if unit in ('c', '°c', 'celsius'):
            return value
        if unit in ('k', 'kelvin'):
            return value - 273.15
        raise ValueError(f"Unsupported temperature unit '{t.units}'.")

    async def _get_scattering_angle_deg_async(self) -> float:
        """
            Retrieve the scattering angle metadata and convert it to degrees if necessary. If the scattering angle metadata is not found, an exception is raised.
            If the scattering angle metadata has no units defined, a warning is issued and the value is assumed to be in degrees.
            Returns:
                float: The scattering angle in degrees.
            Raises:
                Exception: If the scattering angle metadata cannot be retrieved or if the unit is not recognized.
        """
        sa = await self._get_single_item(Metadata.Type.Brillouin, 'Scattering_angle')
        if sa.units is None:
            warnings.warn(f"Scattering angle metadata has no units defined. Assuming the value is in degrees.")
            return self._coerce_numeric_metadata_value(sa.value, field_name='Scattering_angle')
        unit = str(sa.units).lower()
        value = self._coerce_numeric_metadata_value(sa.value, field_name='Scattering_angle')
        if unit in ('deg', '°', 'degree', 'degrees'):
            return value
        if unit in ('rad', 'radian', 'radians'):
            return value * 180 / 3.141592653589793
        raise ValueError(f"Unsupported scattering angle unit '{sa.units}'.")
      