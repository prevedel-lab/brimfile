import re
import numpy as np

from .file_abstraction import FileAbstraction

__docformat__ = "google"


def concatenate_paths(*paths):
    """
    Concatenate multiple paths into a single path.

    Args:
        *paths: Paths to concatenate.

    Returns:
        str: The concatenated path. The concatenated path will have a leading '/' but no trailing '/'.
    """
    con_path = ''
    for path in paths:
        if path.endswith('/'):
            path = path[:-1]
        if path.startswith('/'):
            path = path[1:]
        con_path += '/' + path
    return con_path


def list_objects_matching_pattern(file: FileAbstraction, parent_obj, regexp: str) -> list:
    """
    Lists objects within a parent object that match a given regular expression pattern.
    Args:
        file (FileAbstraction): An abstraction representing the file system or storage 
            where objects are listed.
        parent_obj: The parent object containing the objects to be matched.
        regexp (str): A regular expression pattern to match object names.
    Returns:
        list: A list of tuples containing the matched object names and their corresponding capturing groups as string.
    """

    pattern = re.compile(regexp)
    # n_par = pattern.groups

    matched_objects = []
    for obj_name in file.list_objects(parent_obj):
        match = pattern.match(obj_name)
        if match:
            matched_objects.append((obj_name,) + match.groups())
    return matched_objects


def get_object_name(file: FileAbstraction, obj_path: str) -> str:
    """
    Returns the name of the object.

    The name is retrieved from the 'Name' attribute attached to the object.
    If the attribute is not found, the last part of the path is returned instead.
    """
    try:
        name = file.get_attr(obj_path, 'Name')
    except Exception as e:
        name = obj_path.split('/')[-1]
    return name


def set_object_name(file: FileAbstraction, obj, name: str):
    """
    Set the name of the object.

    The name is set by attaching a 'Name' attribute to the object.
    """
    file.create_attr(obj, 'Name', name)

def var_to_singleton(var):
    """
    If `var` is not a list or a tuple, convert it to a single-ton (list with one element).

    Args:
        var: The variable to convert.

    Returns:
        list: A single-ton containing the variable.
    """    
    if (not isinstance(var, list)) and (not isinstance(var, tuple)):
        var = [var,]
    return var

def np_array_to_smallest_int_type(arr):
    """
    Convert a numpy array containing integers to the smallest integer type that can hold its values.

    Args:
        arr (numpy.ndarray): The input numpy array.

    Returns:
        numpy.ndarray: The converted array with the smallest integer type.
    """
    def type_bug_fix (dt):
        # explicitely pass an object of type np.dtype
        # as what is returned by `min_scalar_type seems``
        # to break type matching in the zarr library
        match dt:
            case np.int8:
                return np.int8
            case np.uint8:
                return np.uint8
            case np.int16:
                return np.int16
            case np.uint16:
                return np.uint16
            case np.int32:
                return np.int32
            case np.uint32:
                return np.uint32
            case np.int64:
                return np.int64
            case np.uint64:
                return np.uint64
            case _:
                return dt
    if not isinstance(arr, np.ndarray):
        raise TypeError("Input must be a numpy array.")
    if not np.issubdtype(arr.dtype, np.integer):
        raise TypeError("Input array must contain integer values.")
    if np.any(arr < 0):
        # set mx to a negative number so that the smallest integer type is signed
        mx = -np.max(np.abs(arr)).astype(np.int64)
    else:
        mx = arr.max().astype(np.uint64)    
    # convert arr to the smallest integer type that can hold the values
    return arr.astype(type_bug_fix(np.min_scalar_type(mx)))
