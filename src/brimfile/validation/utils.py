import re
from enum import StrEnum

_NUMERIC_DTYPE_ALIASES = {
    'int', 'uint', 'float', 'complex',
    'intp', 'uintp',
    'int8', 'int16', 'int32', 'int64',
    'uint8', 'uint16', 'uint32', 'uint64',
    'float16', 'float32', 'float64', 'float96', 'float128',
    'complex64', 'complex128', 'complex192', 'complex256',
    'byte', 'ubyte', 'short', 'ushort', 'longlong', 'ulonglong',
    'half', 'single', 'double', 'longdouble', 'longfloat',
    'csingle', 'cdouble', 'clongdouble',
}

class _NodeType(StrEnum):
    GROUP = 'group'
    ARRAY = 'array'


def is_numeric_dtype(dtype: str) -> bool:
    """Return whether a dtype string represents a numeric dtype."""
    if not isinstance(dtype, str):
        return False

    normalized = dtype.strip().lower()
    if not normalized:
        return False

    if normalized.startswith("<class '") and normalized.endswith("'>"):
        normalized = normalized[8:-2]

    if normalized.startswith('numpy.'):
        normalized = normalized[6:]

    if normalized and normalized[0] in {'<', '>', '=', '|'}:
        normalized = normalized[1:]

    if normalized in _NUMERIC_DTYPE_ALIASES:
        return True

    if re.fullmatch(r'(?:u?int|float|complex)\d+', normalized):
        return True

    if re.fullmatch(r'[iufc]\d*', normalized):
        return True

    return False


def get_node_type(node: dict) -> _NodeType | None:
    return node.get('node_type', None)
def get_array_shape_and_dtype(node: dict) -> tuple[tuple[int] | None, str | None]:
    return node.get('shape', None), node.get('dtype', None)
def get_attributes(node: dict) -> dict | None:
    return node.get('attributes', None)

def generate_attr_path(parent_path: str, attr_name: str) -> str:
    """
    Generate a path string for an attribute based on the parent path and the attribute name.
    Used to fill the 'path' field of ValidationError when the error is related to a specific attribute of a group or array.
    """
    return f"{parent_path}:{attr_name}"