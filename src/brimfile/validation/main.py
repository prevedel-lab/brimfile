import json
from dataclasses import dataclass
from enum import Enum
import re
from math import prod

from ..metadata.types import MetadataItem, MetadataItemValidity
from ..metadata.validation import validate_single_field
from ..metadata.schema import Type as MetadataType
from ..metadata.schema import METADATA_SCHEMA

from ..constants import brim_obj_names
from ..utils import concatenate_paths
from .utils import get_node_type, get_attributes, get_array_shape_and_dtype, \
                    is_numeric_dtype, generate_attr_path, _NodeType, broadcast_shapes

class ValidationLevel(Enum):
    """Severity for validation issues."""
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'

class ValidationType(Enum):
    UNKNOWN_ERROR = 'unknown error'
    MISSING_GROUP = 'missing group'
    MISSING_ARRAY = 'missing array'
    MISSING_ATTRIBUTE = 'missing attribute'
    MISSING_UNITS = 'missing units'
    MISSING_METADATA = 'missing metadata'
    INVALID_NAME = 'invalid name'
    INVALID_VALUE = 'invalid value'
    INVALID_TYPE = 'invalid type'
    INVALID_SHAPE = 'invalid shape'

@dataclass(frozen=True, slots=True)
class ValidationError:
    level: ValidationLevel
    type: ValidationType
    path: str = None # The full path of the object (group or array) where the error occurred. None if the error is not specific to a particular path.
    message: str = ""


def validate_metadata(metadata_type: MetadataType, metadata_dict: dict[str]) -> list[ValidationError]:
    errs: list[ValidationError] = []

    def generate_metadata_path(field_name: str) -> str:
        path = generate_attr_path('Brillouin_data', 'Metadata')
        return f"{path}.{metadata_type.value}.{field_name}"
    
    def map_MetadataItemValidity_to_ValidationError(validity: MetadataItemValidity, *,
                                                    canonical_field_name: str,  path: str) -> ValidationError | None:
        if validity != MetadataItemValidity.VALID and validity != MetadataItemValidity.NOT_CHECKED:                
            match validity :
                case MetadataItemValidity.LIKELY_TYPO:
                    level = ValidationLevel.ERROR
                    error_type  = ValidationType.INVALID_NAME
                    message = f"Metadata field '{field_name}' is likely a typo. Did you mean '{canonical_field_name}'?"
                case MetadataItemValidity.UNKNOWN_FIELD:
                    level = ValidationLevel.WARNING
                    error_type  = ValidationType.INVALID_NAME
                    message = f"Metadata field '{field_name}' is not recognized by the schema but may be a valid field outside the schema. The closest match within the schema is '{canonical_field_name}'."
                case MetadataItemValidity.MISSING_UNITS:
                    level = ValidationLevel.ERROR
                    error_type  = ValidationType.MISSING_UNITS
                    message = f"Metadata field '{field_name}' is missing units, but units are required."
                case MetadataItemValidity.INVALID_TYPE:
                    level = ValidationLevel.ERROR
                    error_type  = ValidationType.INVALID_TYPE
                    message = f"Metadata field '{field_name}' has an invalid type. Expected type is {METADATA_SCHEMA[metadata_type].get_field(canonical_field_name).python_type.__name__}."
                case MetadataItemValidity.INVALID_VALUE:
                    level = ValidationLevel.ERROR
                    error_type  = ValidationType.INVALID_VALUE
                    message = f"Metadata field '{field_name}' has an invalid value."
                case _:
                    level = ValidationLevel.ERROR
                    error_type  = ValidationType.UNKNOWN_ERROR
                    message = f"An unknown error occurred while validating the metadata field '{field_name}'"
            return ValidationError(
                    level=level,
                    type=error_type,
                    path=path,
                    message=message
                )
        return None
    
    # validate fields in the file
    for field_name in metadata_dict:
        if field_name.endswith('_units'):
            continue # skip the units fields, they will be checked together with the corresponding value fields
        value = metadata_dict[field_name]
        units = None
        if f"{field_name}_units" in metadata_dict:
            units = metadata_dict[f"{field_name}_units"]
        canonical_field_name, value = validate_single_field(metadata_type, field_name, MetadataItem(value, units))
        validity = value.get_validity()
        err = map_MetadataItemValidity_to_ValidationError(validity, canonical_field_name=canonical_field_name, 
                                                                path = generate_metadata_path(field_name))
        if err is not None:
            errs.append(err)
    # check for missing required fields
    for field in METADATA_SCHEMA[metadata_type]:
        if not field.required:
            # only check for required fields, optional fields can be missing without causing an error
            continue
        field_name = field.name
        if field_name not in metadata_dict:
            errs.append(ValidationError(
                level=ValidationLevel.ERROR,
                type=ValidationType.MISSING_METADATA,
                path=generate_metadata_path(field_name),
                message=f"The required field '{field_name}' is missing for metadata type '{metadata_type.value}'."
            ))
    return errs

def validate_analysis_group(node: dict, path: str, *, sparse=False, PSD_shape=None) -> list[ValidationError]:
    errs: list[ValidationError] = []
    attrs = get_attributes(node)
    if attrs is None or 'Fit_model' not in attrs:
        errs.append(ValidationError(
            level=ValidationLevel.ERROR,
            type=ValidationType.MISSING_ATTRIBUTE,
            path=generate_attr_path(path, 'Fit_model'),
            message=f"The analysis group '{path}' is missing the required 'Fit_model' attribute."
        ))
    def _check_quantity(name: str) -> bool:
        """Validate all arrays for a given analysis quantity.

        A quantity is considered valid if at least one corresponding peak type
        exists and passes validation checks. Any validation issues are appended
        to ``errs``.

        Args:
            name: Quantity prefix to validate (for example, ``'Shift'``).

        Returns:
            ``True`` if at least one matching and valid peak array is found,
            otherwise ``False``.
        """
        _any_match_found = False
        for qt in node.keys():
            match = re.match(name + r'_(AS|S)_(\d+)$', qt)
            if match:
                if get_node_type(node[qt]) != _NodeType.ARRAY:
                    errs.append(ValidationError(
                        level=ValidationLevel.ERROR,
                        type=ValidationType.INVALID_TYPE,
                        path=concatenate_paths(path, qt),
                        message=f"The '{qt}' node in the analysis group '{path}' must be an array, found '{get_node_type(node[qt])}'."
                    ))
                else:
                    _any_match_found = True
                    qt_shape, qt_dtype = get_array_shape_and_dtype(node[qt])
                    if qt_shape is None or qt_dtype is None:
                        errs.append(ValidationError(
                            level=ValidationLevel.CRITICAL,
                            type=ValidationType.MISSING_ATTRIBUTE,
                            path=concatenate_paths(path, qt),
                            message=f"The '{qt}' array in the analysis group '{path}' must have 'shape' and 'dtype' attributes."
                        ))
                    elif not is_numeric_dtype(qt_dtype):
                        errs.append(ValidationError(
                            level=ValidationLevel.ERROR,
                            type=ValidationType.INVALID_TYPE,
                            path=concatenate_paths(path, qt),
                            message=f"The '{qt}' array in the analysis group '{path}' must have a numeric dtype, found '{qt_dtype}'."
                        ))
                    if qt_shape is not None and PSD_shape is not None:
                        if qt_shape != PSD_shape[:-1]:
                            errs.append(ValidationError(
                                level=ValidationLevel.CRITICAL,
                                type=ValidationType.INVALID_SHAPE,
                                path=concatenate_paths(path, qt),
                                message=f"The '{qt}' array in the analysis group '{path}' has an incompatible shape {qt_shape} with the shape of the 'PSD' array {PSD_shape}."
                            ))
        return _any_match_found
    _check_quantity('Shift')
    _check_quantity('Width')
    _check_quantity('Amplitude')
    _check_quantity('Offset')
    # TODO: check the Fit_error group
    return errs

def validate_data_group(node: dict, path: str) -> list[ValidationError]:
    errs: list[ValidationError] = []
    node_type = get_node_type(node)
    if node_type != _NodeType.GROUP:
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.INVALID_TYPE,
            path=path,
            message=f"The data group '{path}' must be a group, found '{node_type}'."
        ))
    # Validate the attributes of the data group
    attrs = get_attributes(node)
    if attrs is None:
        errs.append(ValidationError(
            level=ValidationLevel.ERROR,
            type=ValidationType.MISSING_ATTRIBUTE,
            path=path,
            message=f"The data group '{path}' must define at least the 'Sparse' or the 'element_size' attribute."
        ))
    sparse: bool = False
    if attrs is not None:
        if 'Sparse' in attrs:
            sparse = attrs['Sparse']
        if not isinstance(sparse, bool):
            errs.append(ValidationError(
                level=ValidationLevel.ERROR,
                type=ValidationType.INVALID_TYPE,
                path=generate_attr_path(path, 'Sparse'),
                message=f"The 'Sparse' attribute of the data group '{path}' must be a boolean, found '{type(sparse).__name__}'."
            ))
        if sparse is False and 'element_size' not in attrs:
            errs.append(ValidationError(
                level=ValidationLevel.ERROR,
                type=ValidationType.MISSING_ATTRIBUTE,
                path=path,
                message=f"The data group '{path}' must have an 'element_size' attribute when 'Sparse' is False."
            ))
        if 'element_size' in attrs:
            element_size = attrs['element_size']
            if not (isinstance(element_size, list) and len(element_size) == 3):
                errs.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.INVALID_VALUE,
                    path=generate_attr_path(path, 'element_size'),
                    message=f"The 'element_size' attribute of the data group '{path}' must be a list of three numbers (in the order z, y, x), found '{element_size}'. Unused dimensions can be set to None."
                ))
            if 'element_size_units' not in attrs:
                errs.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.MISSING_ATTRIBUTE,
                    path=generate_attr_path(path, 'element_size_units'),
                    message=f"The 'element_size_units' attribute of the data group '{path}' is required when 'element_size' is provided, but it is missing."
                ))

    # Validate the arrays in the data group

    # Validate the PSD array
    PSD_shape = None
    if 'PSD' not in node:
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.MISSING_ARRAY,
            path=path,
            message=f"The data group '{path}' must contain a 'PSD' array."
        ))
    else:
        PSD_shape, PSD_dtype = get_array_shape_and_dtype(node['PSD'])
        if PSD_shape is None or PSD_dtype is None:
            errs.append(ValidationError(
                level=ValidationLevel.CRITICAL,
                type=ValidationType.MISSING_ATTRIBUTE,
                path=concatenate_paths(path, 'PSD'),
                message=f"The 'PSD' array in the data group '{path}' must have 'shape' and 'dtype' attributes."
            ))
        elif not is_numeric_dtype(PSD_dtype):
            errs.append(ValidationError(
                level=ValidationLevel.ERROR,
                type=ValidationType.INVALID_TYPE,
                path=concatenate_paths(path, 'PSD'),
                message=f"The 'PSD' array in the data group '{path}' must have a numeric dtype, found '{PSD_dtype}'."
            ))
        if PSD_shape is not None:
            if not sparse and len(PSD_shape) < 4:
                errs.append(ValidationError(
                    level=ValidationLevel.CRITICAL,
                    type=ValidationType.INVALID_SHAPE,
                    path=concatenate_paths(path, 'PSD'),
                    message=f"The 'PSD' array in the data group '{path}' must be at least 4-dimensional for non-sparse data, found shape {PSD_shape}."
                ))
            elif sparse and len(PSD_shape) < 2:
                errs.append(ValidationError(
                    level=ValidationLevel.CRITICAL,
                    type=ValidationType.INVALID_SHAPE,
                    path=concatenate_paths(path, 'PSD'),
                    message=f"The 'PSD' array in the data group '{path}' must be at least 2-dimensional for sparse data, found shape {PSD_shape}."
                ))

    # Validate the frequency array         
    if 'Frequency' not in node:
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.MISSING_ARRAY,
            path=path,
            message=f"The data group '{path}' must contain a 'Frequency' array."
        ))
    else:
        Frequency_shape, Frequency_dtype = get_array_shape_and_dtype(node['Frequency'])
        if Frequency_shape is None or Frequency_dtype is None:
            errs.append(ValidationError(
                level=ValidationLevel.CRITICAL,
                type=ValidationType.MISSING_ATTRIBUTE,
                path=concatenate_paths(path, 'Frequency'),
                message=f"The 'Frequency' array in the data group '{path}' must have 'shape' and 'dtype' attributes."
            ))
        elif not is_numeric_dtype(Frequency_dtype):
            errs.append(ValidationError(
                level=ValidationLevel.ERROR,
                type=ValidationType.INVALID_TYPE,
                path=concatenate_paths(path, 'Frequency'),
                message=f"The 'Frequency' array in the data group '{path}' must have a numeric dtype, found '{Frequency_dtype}'."
            ))
        if PSD_shape is not None and Frequency_shape is not None:
            try:
                broadcast_shapes(PSD_shape, Frequency_shape)
            except ValueError as e:
                errs.append(ValidationError(
                    level=ValidationLevel.CRITICAL,
                    type=ValidationType.INVALID_SHAPE,
                    path=concatenate_paths(path, 'Frequency'),
                    message=f"The 'Frequency' array in the data group '{path}' has an incompatible shape {Frequency_shape} that cannot be broadcast to the shape of the 'PSD' array {PSD_shape}. Error details: {e}"
                ))
        attrs = get_attributes(node['Frequency'])
        if attrs is None or "Units" not in attrs:
            errs.append(ValidationError(
                level=ValidationLevel.ERROR,
                type=ValidationType.MISSING_UNITS,
                path=concatenate_paths(path, 'Frequency'),
                message=f"The 'Frequency' array in the data group '{path}' is missing the required 'Units' attribute."
            ))

    # Validate the Scanning group
    if not sparse and "Scanning" in node:
        errs.append(ValidationError(
            level=ValidationLevel.WARNING,
            type=ValidationType.INVALID_VALUE,
            path=concatenate_paths(path, "Scanning"),
            message=f"The 'Scanning' group in '{path}' is not supported for non-sparse data. It will probably be ignored by most software."
        ))
    if sparse and ("Scanning" not in node or get_node_type(node["Scanning"]) != _NodeType.GROUP):
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.MISSING_ARRAY,
            path=path,
            message=f"The data group '{path}' must contain a 'Scanning' group when 'Sparse' is True."
        ))
    elif "Scanning" in node:
        if get_node_type(node["Scanning"]) != _NodeType.GROUP:
            errs.append(ValidationError(
                level=ValidationLevel.CRITICAL,
                type=ValidationType.INVALID_TYPE,
                path=concatenate_paths(path, "Scanning"),
                message=f"The 'Scanning' node in the data group '{path}' must be a group, found '{get_node_type(node['Scanning'])}'."
            ))
        scanning_group = node["Scanning"]
        if sparse and not ("Spatial_map" in scanning_group or "Cartesian_visualisation" in scanning_group):
            errs.append(ValidationError(
                level=ValidationLevel.CRITICAL,
                type=ValidationType.MISSING_ARRAY,
                path=concatenate_paths(path, "Scanning"),
                message=f"The 'Scanning' group in the data group '{path}' must contain at least a 'Spatial_map' group or a 'Cartesian_visualisation' array when 'Sparse' is True."
            ))
        # Validate the Spatial_map group if it exists
        if "Spatial_map" in scanning_group:
            spatial_map_group = scanning_group["Spatial_map"]
            def _get_coord_len(coor: str) -> int | None:
                if coor in spatial_map_group:
                    coor_shape, coor_dtype = get_array_shape_and_dtype(spatial_map_group[coor])
                    if coor_shape is not None and coor_dtype is not None:
                        if not is_numeric_dtype(coor_dtype):
                            errs.append(ValidationError(
                                level=ValidationLevel.ERROR,
                                type=ValidationType.INVALID_TYPE,
                                path=concatenate_paths(path, f"Scanning/Spatial_map/{coor}"),
                                message=f"The '{coor}' array in the 'Spatial_map' group of the data group '{path}' must have a numeric dtype, found '{coor_dtype}'."
                            ))
                            return None
                        if len(coor_shape) != 1:
                            errs.append(ValidationError(
                                level=ValidationLevel.ERROR,
                                type=ValidationType.INVALID_SHAPE,
                                path=concatenate_paths(path, f"Scanning/Spatial_map/{coor}"),
                                message=f"The '{coor}' array in the 'Spatial_map' group of the data group '{path}' must be 1-dimensional, found shape {coor_shape}."
                            ))
                            return None
                        return coor_shape[0]
                    else:
                        errs.append(ValidationError(
                            level=ValidationLevel.CRITICAL,
                            type=ValidationType.MISSING_ATTRIBUTE,
                            path=concatenate_paths(path, f"Scanning/Spatial_map/{coor}"),
                            message=f"The '{coor}' array in the 'Spatial_map' group of the data group '{path}' must have 'shape' and 'dtype' attributes."
                        ))
                        return None
                else:
                    return None
            x_len = _get_coord_len('x')
            y_len = _get_coord_len('y')
            z_len = _get_coord_len('z')
            coor_len = x_len or y_len or z_len
            if coor_len is None:
                errs.append(ValidationError(
                    level=ValidationLevel.CRITICAL,
                    type=ValidationType.MISSING_ARRAY,
                    path=concatenate_paths(path, "Scanning/Spatial_map"),
                    message=f"The 'Spatial_map' group in the data group '{path}' must contain at least one of the coordinate arrays 'x', 'y' or 'z'."
                ))
            is_valid_len = lambda coor: coor is None or coor == coor_len
            if not is_valid_len(x_len) or not is_valid_len(y_len) or not is_valid_len(z_len):
                errs.append(ValidationError(
                    level=ValidationLevel.CRITICAL,
                    type=ValidationType.INVALID_SHAPE,
                    path=concatenate_paths(path, "Scanning/Spatial_map"),
                    message=f"All the coordinate arrays in the 'Spatial_map' group of the data group '{path}' must have the same length. Found lengths x: {x_len}, y: {y_len}, z: {z_len}."
                ))
            if PSD_shape is not None and coor_len is not None:
                if PSD_shape[0] != coor_len:
                    errs.append(ValidationError(
                        level=ValidationLevel.CRITICAL,
                        type=ValidationType.INVALID_SHAPE,
                        path=concatenate_paths(path, "Scanning/Spatial_map"),
                        message=f"The length of the coordinate arrays in the 'Spatial_map' group of the data group '{path}' must match the size of the first dimension of the 'PSD' array. Found coordinate length: {coor_len}, 'PSD' shape: {PSD_shape}."
                    ))
        # Validate the Cartesian_visualisation array if it exists
        if "Cartesian_visualisation" in scanning_group:
            cart_vis_shape, cart_vis_dtype = get_array_shape_and_dtype(scanning_group["Cartesian_visualisation"])
            if cart_vis_shape is None or cart_vis_dtype is None:
                errs.append(ValidationError(
                    level=ValidationLevel.CRITICAL,
                    type=ValidationType.MISSING_ATTRIBUTE,
                    path=concatenate_paths(path, "Scanning/Cartesian_visualisation"),
                    message=f"The 'Cartesian_visualisation' array in the 'Scanning' group of the data group '{path}' must have 'shape' and 'dtype' attributes."
                ))
            elif not is_numeric_dtype(cart_vis_dtype):
                errs.append(ValidationError(
                    level=ValidationLevel.CRITICAL,
                    type=ValidationType.INVALID_TYPE,
                    path=concatenate_paths(path, "Scanning/Cartesian_visualisation"),
                    message=f"The 'Cartesian_visualisation' array in the 'Scanning' group of the data group '{path}' must have a numeric dtype, found '{cart_vis_dtype}'."
                ))
            elif len(cart_vis_shape) != 3:
                errs.append(ValidationError(
                    level=ValidationLevel.CRITICAL,
                    type=ValidationType.INVALID_SHAPE,
                    path=concatenate_paths(path, "Scanning/Cartesian_visualisation"),
                    message=f"The 'Cartesian_visualisation' array in the 'Scanning' group of the data group '{path}' must be 3-dimensional, found shape {cart_vis_shape}."
                ))
            elif PSD_shape is not None and cart_vis_shape is not None:
                if sparse and prod(cart_vis_shape) != PSD_shape[0]:
                    errs.append(ValidationError(
                        level=ValidationLevel.WARNING,
                        type=ValidationType.INVALID_SHAPE,
                        path=concatenate_paths(path, "Scanning/Cartesian_visualisation"),
                        message=f"The total number of elements in the 'Cartesian_visualisation' array (shape {cart_vis_shape}) is not matching the spatial positions of the 'PSD' array (shape {PSD_shape}). This is valid - e.g. when some spatial positions are missing (which is often the case for sparse data) - but a warning is issued nevertheless."
                    ))
            
    # Validate the Parameters array
    if PSD_shape is not None and \
        ((sparse and len(PSD_shape) > 2) or (not sparse and len(PSD_shape) > 4)):
        if "Parameters" not in node:
            errs.append(ValidationError(
                level=ValidationLevel.ERROR,
                type=ValidationType.MISSING_ARRAY,
                path=path,
                message=f"The data group '{path}' must have a 'Parameters' array when the 'PSD' array has more than 2 dimensions for sparse data or more than 4 dimensions for non-sparse data."
            ))
        else:
            Parameters_shape, Parameters_dtype = get_array_shape_and_dtype(node['Parameters'])
            if Parameters_shape is None or Parameters_dtype is None:
                errs.append(ValidationError(
                    level=ValidationLevel.CRITICAL,
                    type=ValidationType.MISSING_ATTRIBUTE,
                    path=concatenate_paths(path, 'Parameters'),
                    message=f"The 'Parameters' array in the data group '{path}' must have 'shape' and 'dtype' attributes."
                ))
            num_pars = len(PSD_shape) - (2 if sparse else 4)
            if Parameters_shape is not None and len(Parameters_shape) != num_pars+1:
                errs.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.INVALID_SHAPE,
                    path=concatenate_paths(path, 'Parameters'),
                    message=f"The 'Parameters' array in the data group '{path}' must have {num_pars+1} dimensions, found shape {Parameters_shape}."
                ))
            if Parameters_shape is not None and Parameters_shape[-1] != num_pars:
                errs.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.INVALID_SHAPE,
                    path=concatenate_paths(path, 'Parameters'),
                    message=f"The 'Parameters' array in the data group '{path}' must have {num_pars} elements in the last dimension, found {Parameters_shape[-1]} instead."
                ))
    
    # list the analysis groups in the current data group and validate them
    analysis_groups: list[tuple[str, int]] = []
    for key in node.keys():
        match = re.match(brim_obj_names.data.analysis_results + r"_(\d+)$", key)
        if match:
            analysis_groups.append((key, int(match.group(1))))
    # check that there is at least one analysis group
    if len(analysis_groups) == 0:
        errs.append(ValidationError(
            level=ValidationLevel.WARNING,
            type=ValidationType.MISSING_GROUP,
            path=path,
            message=f"No analysis group was found in {path}. The file is still valid but no image could be extracted from it."
        ))
    else:
        # validate each analysis group
        for dg_name, dg_index in analysis_groups:
            errs.extend(validate_analysis_group(node[dg_name], path=concatenate_paths(path, dg_name),
                                                sparse=sparse, PSD_shape=PSD_shape))

    return errs

def validate_root_attrs(attrs: dict) -> list[ValidationError]:
    errs: list[ValidationError] = []
    path = 'Brillouin_data'
    # check the version attribute
    attr_name = 'brim_version'
    version = attrs.get(attr_name, None)
    if version is None:
        errs.append(ValidationError(
            level=ValidationLevel.ERROR,
            type=ValidationType.MISSING_ATTRIBUTE,
            path=generate_attr_path(path, attr_name),
            message=f"The root group must have a '{attr_name}' attribute."
        ))
    elif version != '0.1':
        errs.append(ValidationError(
            level=ValidationLevel.ERROR,
            type=ValidationType.INVALID_VALUE,
            path=generate_attr_path(path, attr_name),
            message=f"The only current supported version is '0.1', found {version}."
        ))
    attr_name = 'Subtype'
    subtype = attrs.get(attr_name, None)
    if subtype is not None:
        # TODO validate the subtype value when the allowed subtypes are defined
        attr_name = 'Subtype_features'
        subtype_features = attrs.get(attr_name, None)
        if subtype_features is None:
            errs.append(ValidationError(
                level=ValidationLevel.WARNING,
                type=ValidationType.MISSING_ATTRIBUTE,
                path=generate_attr_path(path, attr_name),
                message=f"When 'Subtype' is specified, it is recommended to provide the '{attr_name}' attribute as well."
            ))
    return errs

def validate_Brillouin_data_group(node: dict) -> list[ValidationError]:
    errs: list[ValidationError] = []
    path = 'Brillouin_data'
    node_type = get_node_type(node)
    if node_type != _NodeType.GROUP:
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.INVALID_TYPE,
            path=path,
            message=f"The 'Brillouin_data' node must be a group, found '{node_type}'."
        ))
    attrs = get_attributes(node)
    if attrs is None:
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.MISSING_ATTRIBUTE,
            path=path,
            message="The 'Brillouin_data' group must have attributes."
        ))
    else:
        # validate the general metadata
        if 'Metadata' not in attrs:
            errs.append(ValidationError(
                level=ValidationLevel.ERROR,
                type=ValidationType.MISSING_ATTRIBUTE,
                path=path,
                message="The 'Brillouin_data' group must contain a 'Metadata' attribute."
            ))
        else:
            metadata_path = generate_attr_path(path, 'Metadata')
            metadata = attrs['Metadata']
            if not isinstance(metadata, dict):
                errs.append(ValidationError(
                    level=ValidationLevel.ERROR,
                    type=ValidationType.INVALID_TYPE,
                    path=metadata_path,
                    message=f"The 'Metadata' attribute must be a dictionary, found {type(metadata).__name__}."
                ))
            else:
                for md_type in MetadataType:
                    if md_type.value in metadata:
                        md_dict = metadata[md_type.value]
                        if not isinstance(md_dict, dict):
                            errs.append(ValidationError(
                                level=ValidationLevel.ERROR,
                                type=ValidationType.INVALID_TYPE,
                                path=f"{metadata_path}.{md_type.value}",
                                message=f"The '{md_type.value}' field in 'Metadata' must be a dictionary, found {type(md_dict).__name__}."
                            ))
                        else:
                            errs.extend(validate_metadata(md_type, md_dict))
                    else:
                        errs.append(ValidationError(
                            level=ValidationLevel.ERROR,
                            type=ValidationType.MISSING_METADATA,
                            path=f"{metadata_path}.{md_type.value}",
                            message=f"The '{md_type.value}' field is missing in 'Metadata'."
                        ))
    # list the data groups in the Brillouin_data group and validate them
    data_groups: list[tuple[str, int]] = []
    for key in node.keys():
        match = re.match(brim_obj_names.data.base_group + r"_(\d+)$", key)
        if match:
            data_groups.append((key, int(match.group(1))))
    # check that there is at least one data group
    if len(data_groups) == 0:
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.MISSING_GROUP,
            path=path,
            message="At least one data group is required in the 'Brillouin_data' group, but none were found."
        ))
    else:
        # validate each data group
        for dg_name, dg_index in data_groups:
            errs.extend(validate_data_group(node[dg_name], path=concatenate_paths(path, dg_name)))

    return errs

def validate_json(json_descriptor: str) -> list[ValidationError]:
    """Validate a JSON descriptor against the expected structure of a brim file (https://github.com/brillouin-imaging/Brillouin-standard-file/blob/linkml-schema/docs/brim_file_specs.md).

    This function checks that the JSON descriptor contains all required fields
    and that they have the correct types. It raises a ValueError if any
    validation checks fail.

    Args:
        json_descriptor: A JSON string representing the Zarr hierarchy descriptor.
    """
    try:
        descriptor_dict = json.loads(json_descriptor)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format: {e}")

    # Perform validation checks on the descriptor_dict structure
    if not isinstance(descriptor_dict, dict):
        raise ValueError("Descriptor must be a JSON object at the top level.")
        
    errs: list[ValidationError] = []

    # check the root
    path = ''
    node_type = get_node_type(descriptor_dict)
    if node_type != _NodeType.GROUP:
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.MISSING_GROUP,
            path=path,
            message=f"There must be a group at the root level, found '{node_type}'."
        ))
    attrs = get_attributes(descriptor_dict)
    if attrs is None:
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.MISSING_ATTRIBUTE,
            path=path,
            message="The root group must have attributes."
        ))
    else:
        errs.extend(validate_root_attrs(attrs))
    
    # check the Brillouin_data group
    path = 'Brillouin_data'
    brillouin_data_group = descriptor_dict.get('Brillouin_data', None)
    if brillouin_data_group is not None:
        errs.extend(validate_Brillouin_data_group(brillouin_data_group))
    else:
        errs.append(ValidationError(
            level=ValidationLevel.CRITICAL,
            type=ValidationType.MISSING_GROUP,
            path=path,
            message="The 'Brillouin_data' group is required but missing."
        ))

    return errs