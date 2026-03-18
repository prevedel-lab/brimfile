from ..constants import running_from_pyodide
from ..file_abstraction import sync, _AbstractFile
from typing import Any, TypeAlias

if not running_from_pyodide:
    import zarr
    import json

    Node: TypeAlias = zarr.Group | zarr.Array | zarr.AsyncGroup | zarr.AsyncArray | None

    def list_keys(group: zarr.Group | zarr.AsyncGroup) -> list[str]:
        if isinstance(group, zarr.AsyncGroup):
            async def list_keys_async() -> list[str]:
                return [key async for key in group.keys()]
            return sync(list_keys_async())
        else:
            return list(group.keys())
        
    def get_child(group: zarr.Group | zarr.AsyncGroup, key: str) -> Node:
        if isinstance(group, zarr.AsyncGroup):
            async def get_child_async() -> Node:
                return await group.get(key)
            return sync(get_child_async())
        else:
            return group[key]

    def recurse_nodes(node: Node) -> dict[str, Any]:
        if node is None:
            raise ValueError("Unexpected None node while traversing Zarr hierarchy")
        node_dict: dict[str, Any] = {}
        attrs_obj: Any = node.attrs
        if hasattr(attrs_obj, 'asdict'):
            attrs_obj = attrs_obj.asdict()
        node_dict['attributes'] = attrs_obj
        if isinstance(node, zarr.Group) or isinstance(node, zarr.AsyncGroup):
            node_dict['node_type'] = 'group'
            # Recursively process children
            for key in list_keys(node):
                child_dict = recurse_nodes(get_child(node, key))
                node_dict[key] = child_dict
        else:
            node_dict['node_type'] = 'array'
            node_dict['shape'] = node.shape
            node_dict['dtype'] = str(node.dtype)        
        
        return node_dict

    def generate_json_descriptor(file: _AbstractFile) -> str:
        """Generate a JSON descriptor for a Zarr hierarchy.

        The descriptor recursively captures each node's attributes and type.
        Group nodes include their children, while array nodes include shape and
        data type information.

        Args:
            file: The _AbstractFile instance containing the Zarr hierarchy.

        Returns:
            A pretty-printed JSON string describing the full hierarchy.
        """

        root_obj = getattr(file, '_root', None)
        if root_obj is None:
            raise ValueError("File root group is not available")
        root: Node = root_obj
        out_dict = recurse_nodes(root)

        json_output = json.dumps(out_dict, indent=4)
        return json_output
else:
    def generate_json_descriptor(file: _AbstractFile) -> str:
        """Generate a JSON descriptor for a Zarr hierarchy.

        The descriptor recursively captures each node's attributes and type.
        Group nodes include their children, while array nodes include shape and
        data type information.

        Args:
            file: The _AbstractFile instance containing the Zarr hierarchy.

        Returns:
            A pretty-printed JSON string describing the full hierarchy.
        """

        zarr_js = file._zarr_js
        assert zarr_js is not None
        return sync(zarr_js.generateJsonDescriptor())