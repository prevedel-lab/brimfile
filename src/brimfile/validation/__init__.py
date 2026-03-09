import zarr
from .json_descriptor import generate_json_descriptor
from .main import validate_json, ValidationError, ValidationLevel, ValidationType

def validate(root: zarr.Group) -> list[ValidationError]:
    """Validate a brim file.

    Args:
        root: Root Zarr group to validate.

    Returns:
        A list of ValidationError instances describing any issues found.
        An empty list indicates that no issues were found.
    """
    json_descriptor = generate_json_descriptor(root)
    validation_errors = validate_json(json_descriptor)
    return validation_errors