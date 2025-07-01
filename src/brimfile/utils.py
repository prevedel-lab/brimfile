import re

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
