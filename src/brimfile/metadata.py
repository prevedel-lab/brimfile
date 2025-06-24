from .file_abstraction import FileAbstraction
from .utils import concatenate_paths

from . import units
from .constants import brim_obj_names, reserved_attr_names

import warnings
from enum import Enum

__docformat__ = "google"


class Metadata:

    class Item:
        # units should be a str. If None, no units is defined
        def __init__(self, value, units: str = None):
            self.value = value
            self.units = units

        def __str__(self):
            res = str(self.value)
            if self.units is not None:
                res += str(self.units)
            return res

    class Type(Enum):
        Experiment = 'Experiment'
        Optics = 'Optics'
        Brillouin = 'Brillouin'
        Acquisition = 'Acquisition'
        Spectrometer = 'Spectrometer'

    def __init__(self, file: FileAbstraction, data_full_path: str = None):
        """
        Initialize the Metadata object.
        Args:
            file (FileAbstraction).
            data_full_path (str): The full path to the data group in the file. If None, only the metadata in the file are exposed.
        """
        self._file = file
        self._path = concatenate_paths(
            brim_obj_names.Brillouin_base_path, brim_obj_names.metadata.base_group)
        self._data_path = data_full_path

    @classmethod
    def _create_group_in_file(cls, file: FileAbstraction):
        """
        Create the metadata group in the file.
        This method creates the necessary metadata groups in the file.
        Args:
            file (FileAbstraction): The file object where the groups will be created.
        """
        # Create the metadata groups
        for t in Metadata.Type:
            group = concatenate_paths(
                brim_obj_names.Brillouin_base_path, brim_obj_names.metadata.base_group, t.value)
            if not file.object_exists(group):
                file.create_group(group)

    def _get_single_item(self, type: Type, name: str) -> Item:
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
            Exception: If the metadata attribute cannot be retrieved from either the specific
                       data group or the general metadata group.
        """

        # if 'self' is linked to a specific data group, we first check if the metadata is defined in that group
        if self._data_path is not None:
            attr_name = f"{type.value}.{name}"
            try:
                return Metadata.Item(self._file.get_attr(self._data_path, attr_name),
                                     units.of_attribute(self._file, self._data_path, attr_name))
            except Exception:
                pass
        # otherwise we load the metadata from the metadata group
        group = concatenate_paths(self._path, type.value)
        return Metadata.Item(self._file.get_attr(group, name),
                             units.of_attribute(self._file, group, name))

    def __getitem__(self, key: str) -> Item:
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
        return self._get_single_item(Metadata.Type[group], obj)

    def to_dict(self, type: Type) -> dict:
        """
        Returns the metadata of a specific type as a dictionary.
        Returns:
            dict: A dictionary containing all metadata attributes, where each element is of the type Item.
        """

        out_dict = {}

        # if 'self' is linked to a specific data group, we first check if the metadata is defined in that group
        local_attrs = []
        if self._data_path is not None:
            attrs = self._file.list_attributes(self._data_path)
            group = f"{type.value}."
            attrs = [attr for attr in attrs if attr.startswith(
                group) and not attr.endswith('_units')]
            for attr in attrs:
                val = self._file.get_attr(self._data_path, attr)
                u = units.of_attribute(self._file, self._data_path, attr)
                out_dict[attr[len(group):]] = Metadata.Item(val, u)
            local_attrs = [attr[len(group):] for attr in attrs]

        # otherwise we load the metadata from the metadata group
        group = concatenate_paths(self._path, type.value)
        attrs = self._file.list_attributes(group)
        for attr in attrs:
            if attr in local_attrs or attr.endswith('_units') or attr in reserved_attr_names:
                # we already loaded this attribute from the data group
                # or it is the units attribute
                continue
            val = self._file.get_attr(group, attr)
            u = units.of_attribute(self._file, group, attr)
            out_dict[attr] = Metadata.Item(val, u)

        return out_dict

    def add(self, type: Type, metadata: dict, local: bool = False):
        """
        Add metadata to the file.
        Args:
            type (Type): The type of the metadata to add.
            metadata (dict): A dictionary containing the metadata attributes to add.
                              Each element must be of the type Item.
            local (bool): If True, the metadata will be added to the data group. Otherwise, it will be added to the general metadata group.
        """
        for key, value in metadata.items():
            if not isinstance(value, Metadata.Item):
                warnings.warn(f"No units provided for {key}; None is assumed.")
                # if no units are provided, we assume None
                value = Metadata.Item(value, None)
            if local:
                if self._data_path is None:
                    raise ValueError(
                        "The current metadata object is not linked to a data group. Set local to False to add the metadata to the general metadata group.")
                group = self._data_path
                name = f"{type.value}.{key}"
            else:
                group = concatenate_paths(self._path, type.value)
                name = key
            val = value.value
            if isinstance(value.value, Enum):
                val = value.value.value
            self._file.create_attr(group, name, val)
            if value.units is not None:
                units.add_to_attribute(self._file, group, name, value.units)

    def all_to_dict(self) -> dict:
        """
        Returns all the metadata as a dictionary.
        Returns:
            dict: A dictionary containing all the elements in Metadata.Type as a key.
                    Each of the key is defining a dictionary, as returned by Metadata.to_dict()
        """
        full_metadata = {}
        for type in Metadata.Type:
            full_metadata[type.name] = self.to_dict(type)
        return full_metadata

    # -------------------- Enums definition --------------------
    class ImmersionMedium(Enum):
        other = 'other'
        air = 'air'
        water = 'water'
        oil = 'oil'

    class SignalType(Enum):
        other = 'other'
        spontaneous = 'spontaneous'
        stimulated = 'stimulated'
        time_resolved = 'time_resolved'

    class PhononsMeasured(Enum):
        other = 'other'
        longitudinal = 'longitudinal-like'
        transverse = 'transverse-like'
        longitudinal_Transverse = 'longitudinal-transverse-like'

    class PolarizationProbedAnalyzed(Enum):
        other = 'other'
        VH = 'VH'
        HV = 'HV'
        HH = 'HH'
        VV = 'VV'
        V_Unpolarized = 'V-unpolarized'
        Circular_Circular = 'circular-circular'

    class ScanningStrategy(Enum):
        other = 'other'
        point_scanning = 'point_scanning'
        line_scanning = 'line_scanning'
        light_sheet = 'light_sheet'
        time_resolved = 'time_resolved'

    class SpectrometerType(Enum):
        other = 'other'
        VIPA = 'VIPA'
        FP = 'Fabry_Perot'
        stimulated = 'stimulated'
        heterodyne = 'heterodyne'
        time_domain = 'time_domain'
        impulsive = 'impulsive'

    class DetectorType(Enum):
        other = 'other'
        EMCCD = 'EMCCD'
        CCD = 'CCD'
        sCMOS = 'sCMOS'
        PMT = 'PMT'
        balanced = 'balanced'
        single_PD = 'single_PD'
        single_APD = 'single_APD'
