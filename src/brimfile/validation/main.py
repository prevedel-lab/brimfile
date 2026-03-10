import json
from dataclasses import dataclass
from enum import Enum
import re

from ..metadata.types import MetadataItem, MetadataItemValidity
from ..metadata.validation import validate_single_field
from ..metadata.schema import Type as MetadataType
from ..metadata.schema import METADATA_SCHEMA

from ..constants import brim_obj_names
from ..utils import concatenate_paths
from .utils import get_node_type, get_attributes, get_array_shape_and_dtype, is_numeric_dtype, generate_attr_path, _NodeType

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
    INCONSISTENT_SHAPE = 'inconsistent shape'

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
        field_name = field.name
        if field_name not in metadata_dict:
            errs.append(ValidationError(
                level=ValidationLevel.ERROR,
                type=ValidationType.MISSING_METADATA,
                path=generate_metadata_path(field_name),
                message=f"The required field '{field_name}' is missing for metadata type '{metadata_type.value}'."
            ))
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
        # The 'Conditions_name' attribute is checked when validating the PSD array.

        # Validate the arrays in the data group
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
                    path=generate_attr_path(concatenate_paths(path, 'PSD'), 'dtype'),
                    message=f"The 'PSD' array in the data group '{path}' must have a numeric dtype, found '{PSD_dtype}'."
                ))

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
        pass
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
    """Validate a JSON descriptor against the expected structure of a brim file (https://github.com/prevedel-lab/Brillouin-standard-file/blob/linkml-schema/docs/brim_file_specs.md).

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