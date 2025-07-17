import warnings
from abc import ABC, abstractmethod
from enum import Enum

use_h5 = False

__docformat__ = "google"

class FileAbstraction(ABC):
    """
    Abstract base class that rapresents a general interface to work with brim files.

    This class defines a common interface for file operations, such as creating attributes,
    retrieving attributes, and managing groups and datasets. It is designed to be extended
    by specific file implementations, such as HDF5 or Zarr.

    All the methods which require a path to an exixsting object in the file, will accept
    either the object itself (as defined by the specific implementation) or its path as a string.
    """

    # -------------------- Attribute Management --------------------

    @abstractmethod
    def create_attr(self, obj, name: str, data, **kwargs):
        """
        Create an attribute in the file.

        Args:
            obj: object that supports the creation of an attribute (e.g. group or dataset) or its path as a string.
            name (str): Name of the attribute.
            data: Data for the attribute.
            **kwargs: Additional arguments for attribute creation.
        """
        pass

    @abstractmethod
    def get_attr(self, obj, name: str):
        """
        Return the data of an attribute in the file.

        Args:
            obj: object that supports the creation of an attribute (e.g. group or dataset) or its path as a string.
            name (str): Name of the attribute.
        Raises:
            KeyError: If the attribute does not exist.
        """
        pass

    # -------------------- Group Management --------------------

    @abstractmethod
    def open_group(self, full_path: str, **kwargs):
        """
        Open a group in the file.

        Args:
            full_path (str): Path to the group.
            **kwargs: Additional arguments for opening the group.
        """
        pass

    @abstractmethod
    def create_group(self, full_path: str, **kwargs):
        """
        Create a group in the file.

        Args:
            full_path (str): Path to the group.
            **kwargs: Additional arguments for creating the group.
        """
        pass

    # -------------------- Dataset Management --------------------

    class Compression:
        """
        Compression options for datasets.
        """
        NONE = None
        DEFAULT = 1
        ZLIB = 2
        LZF = 3

        def __init__(self, type=DEFAULT, level=None):
            self.type = type
            self.level = level

    @abstractmethod
    def open_dataset(self, full_path: str):
        """
        Open a dataset in the file.

        Args:
            full_path (str): Path to the dataset.

        Returns:
            Dataset object which must support numpy indexing and slicing.
        """
        pass

    @abstractmethod
    def create_dataset(self, parent_group, name: str, data, chunk_size=None, compression: 'FileAbstraction.Compression' = None):
        """
        Create a dataset in the file.

        Args:
            parent_group: Group in which to create the dataset or its path as a string.
            name (str): Name of the dataset.
            data: Data for the dataset.
            chunk_size (tuple, optional): Chunk size for the dataset. If None the automatically computed size will be used.
            compression (FileAbstraction.Compression, optional): Compression options for the dataset.
        """
        pass

    # -------------------- Listing --------------------

    @abstractmethod
    def list_objects(self, obj) -> list:
        """
        Lists the objects (groups or datasets) contained within one hierarchical level below the given object.

        Args:
            obj: parent object or its path as a string.

        Returns:
            list: List of strings representing the names of the objects.
        """
        pass

    @abstractmethod
    def object_exists(self, full_path) -> bool:
        """
        Check if an object exists in the file.

        Args:
            full_path (str): Path to the object.

        Returns:
            bool: True if the object exists, False otherwise.
        """
        pass

    @abstractmethod
    def list_attributes(self, obj) -> list:
        """
        Lists the attributes attached to the specified object.

        Args:
            obj: object or its path as a string.

        Returns:
            list: List of strings representing the names of the attributes.
        """
        pass

    # -------------------- File Management --------------------

    def close(self):
        """
        Close the file.
        """
        pass

    # -------------------- Properties --------------------

    def is_read_only(self) -> bool:
        """
        Check if the file is read-only.

        Returns:
            bool: True if the file is read-only, False otherwise.
        """
        return True


if use_h5:
    import h5py

    class _h5File (h5py.File, FileAbstraction):
        def __init__(self, filename: str, *kargs, **kwargs):
            mode = 'r'
            if 'mode' in kwargs:
                mode = kwargs.pop('mode')
            kwargs.pop('store_type', '')
            super().__init__(filename, mode=mode, *kargs, **kwargs)

        # -------------------- Attribute Management --------------------

        def create_attr(self, obj, name: str, data, **kwargs):
            if isinstance(obj, str):
                obj = self[obj]
            if isinstance(data, str):
                obj.attrs.create(name, data, dtype=h5py.string_dtype(
                    encoding='utf-8'), **kwargs)
            else:
                obj.attrs.create(name, data, **kwargs)

        def get_attr(self, obj, name: str):
            if isinstance(obj, str):
                obj = self[obj]
            return obj.attrs[name]

        # -------------------- Group Management --------------------

        def open_group(self, full_path: str, **kwargs):
            g = self[full_path]
            return g

        def create_group(self, full_path: str):
            g = super().create_group(full_path)
            return g

        # -------------------- Dataset Management --------------------

        def open_dataset(self, full_path: str):
            ds = self[full_path]
            return ds

        def create_dataset(self, parent_group, name: str, data, chunk_size=None, compression: 'FileAbstraction.Compression' = None):
            if isinstance(parent_group, str):
                parent_group = self[parent_group]
            if compression is not None:
                if compression.type == FileAbstraction.Compression.NONE:
                    compression = None
                elif compression.type == FileAbstraction.Compression.ZLIB:
                    compression = 'gzip'
                elif compression.type == FileAbstraction.Compression.LZF:
                    compression = 'lzf'
                else:
                    warnings.warn(
                        f"Compression type '{compression.type}' not supported by h5py. Using no compression.")
                    compression = None
            ds = parent_group.create_dataset(
                name=name, data=data, chunks=chunk_size, compression=compression)
            return ds

        # -------------------- Listing --------------------

        def list_objects(self, obj):
            if isinstance(obj, str):
                obj = self[obj]
            return (str(el) for el in obj.keys())

        def object_exists(self, full_path) -> bool:
            return full_path in self

        def list_attributes(self, obj):
            if isinstance(obj, str):
                obj = self[obj]
            return (str(attr) for attr in obj.attrs.keys())

        # -------------------- Properties --------------------

        def is_read_only(self) -> bool:
            return self.mode == 'r'

    _AbstractFile = _h5File
else:

    class StoreType(Enum):
        """
        Enum to represent the type of store used by the Zarr file.
        """
        ZIP = 'zip'
        ZARR = 'zarr'
        S3 = 'S3'
        AUTO = 'auto'

    import sys
    if "pyodide" in sys.modules:  # using javascript based zarr library
        from __main__ import _zarrFile

    else:
        import zarr
        import numcodecs

        import importlib.util

        
        def _parse_storage_url(url):
            from urllib.parse import urlparse

            parsed = urlparse(url)
            scheme = parsed.scheme
            netloc = parsed.netloc
            path = parsed.path.lstrip('/')

            # Case 1: Amazon S3 (virtual-hosted-style or path-style)
            if "amazonaws.com" in netloc:
                parts = netloc.split('.')
                if parts[0] != 's3':  # virtual-hosted-style
                    bucket = parts[0]
                    endpoint = '.'.join(parts[1:])
                    object_path = path
                else:  # path-style
                    path_parts = path.split('/', 1)
                    bucket = path_parts[0]
                    endpoint = netloc
                    object_path = path_parts[1] if len(path_parts) > 1 else ''
            # Case 2: Google Cloud Storage
            elif "storage.googleapis.com" in netloc:
                if netloc == "storage.googleapis.com":
                    # path-style: https://storage.googleapis.com/bucket-name/object
                    path_parts = path.split('/', 1)
                    bucket = path_parts[0]
                    endpoint = netloc
                    object_path = path_parts[1] if len(path_parts) > 1 else ''
                else:
                    # virtual-hosted-style: https://bucket-name.storage.googleapis.com/object
                    bucket = netloc.split('.')[0]
                    endpoint = '.'.join(netloc.split('.')[1:])
                    object_path = path
            # Case 3: Custom endpoint or S3-compatible storage (MinIO, etc.)
            else:
                path_parts = path.split('/', 1)
                bucket = path_parts[0]
                endpoint = netloc
                object_path = path_parts[1] if len(path_parts) > 1 else ''

            return {
                'protocol': scheme,
                'bucket': bucket,
                'endpoint': endpoint,
                'object_path': object_path
            }
        

        class _zarrFile (FileAbstraction):
            def __init__(self, filename: str, mode: str = 'r', store_type: StoreType = StoreType.AUTO):
                """
                Initialize the Zarr file.

                Args:
                    filename (str): Path to the Zarr file.
                    mode: the mode for opening the file (default is 'r' for read-only).
                    store_type (str): Type of the store to use. Default is 'AUTO'.
                """
                st = StoreType

                if store_type == st.ZIP:
                    if not filename.endswith('.zip'):
                        filename += '.zip'
                elif store_type == st.ZARR:
                    if not filename.endswith('.zarr'):
                        filename += '.zarr'
                elif store_type == st.AUTO:
                    if filename.startswith('http') or filename.startswith('s3'):
                        store_type = st.S3
                    elif filename.endswith('.zip'):
                        store_type = st.ZIP
                    elif filename.endswith('.zarr'):
                        store_type = st.ZARR
                    else:
                        raise ValueError(
                            "When using 'auto' store_type, the filename must end with '.zip' or '.zarr' or start with 'http' or 's3'.")

                match store_type:
                    case st.ZIP:
                        mode_zip = mode
                        if mode_zip == 'w-':
                            mode_zip = 'x'
                        store = zarr.storage.ZipStore(filename, mode=mode_zip)
                    case st.ZARR:
                        store = zarr.storage.LocalStore(filename)
                    case st.S3:
                        if importlib.util.find_spec('fsspec') is None:
                            raise ModuleNotFoundError(
                                "The fsspec module is required for using S3 storage")
                        import fsspec
                        parsed_url = _parse_storage_url(filename)                           

                        fs = fsspec.filesystem('s3', anon=True, asynchronous=True,
                                            client_kwargs={'endpoint_url': f"{parsed_url['protocol']}://{parsed_url['endpoint']}"})

                        store = zarr.storage.FsspecStore(fs, path = f"{parsed_url['bucket']}/{parsed_url['object_path']}",
                                                        read_only=(mode == 'r'))
                    case _:
                        raise ValueError(
                            f"Unsupported store type '{store_type}'. Supported types are 'zip', 'zarr', and 'remote'.")
                self._root = zarr.open_group(store=store, mode=mode)
                self._store = store
                self.filename = filename

            # -------------------- Attribute Management --------------------

            def create_attr(self, obj, name: str, data, **kwargs):
                for k in kwargs.keys():
                    warnings.warn(
                        f"'{k}' argument not supported by 'create_attr' in zarr")
                if isinstance(obj, str):
                    obj = self._root[obj]
                obj.attrs[name] = data

            def get_attr(self, obj, name: str):
                if isinstance(obj, str):
                    obj = self._root[obj]
                return obj.attrs[name]

            # -------------------- Group Management --------------------

            def open_group(self, full_path: str, **kwargs):
                for k in kwargs.keys():
                    warnings.warn(
                        f"'{k}' argument not supported by 'open_group' in zarr")
                g = self._root[full_path]
                return g

            def create_group(self, full_path: str):
                g = self._root.create_group(full_path)
                return g

            # -------------------- Dataset Management --------------------

            def open_dataset(self, full_path: str):
                ds = self._root[full_path]
                return ds

            def create_dataset(self, parent_group, name: str, data, chunk_size=None, compression: 'FileAbstraction.Compression' = FileAbstraction.Compression()):
                if isinstance(parent_group, str):
                    parent_group = self[parent_group]
                compressor = None
                if chunk_size is None:
                    chunk_size = 'auto'
                if compression is not None:
                    if compression.type == FileAbstraction.Compression.DEFAULT:
                        # see https://zarr.readthedocs.io/en/stable/api/zarr/index.html#zarr.create_array
                        compressor = 'auto'
                    elif compression.type == FileAbstraction.Compression.ZLIB:
                        compressor = zarr.codecs.BloscCodec(
                            cname='zlib', clevel=compression.level)
                    elif compression.type == FileAbstraction.Compression.LZF:
                        compressor = numcodecs.LZF()
                    else:
                        compression = None
                        warnings.warn(
                            f"Compression type '{compression.type}' not supported by zarr. Using no compression.")
                ds = parent_group.create_array(
                    name=name, shape=data.shape, dtype=data.dtype, chunks=chunk_size, compressors=compressor)
                ds[:] = data
                return ds

            # -------------------- Listing --------------------

            def list_objects(self, obj):
                if isinstance(obj, str):
                    obj = self._root[obj]
                return (str(el) for el in obj.keys())

            def object_exists(self, full_path) -> bool:
                # return self._store.exists(full_path)
                return full_path in self._root

            def list_attributes(self, obj):
                if isinstance(obj, str):
                    obj = self._root[obj]
                return (str(attr) for attr in obj.attrs.keys())

            # -------------------- File Management --------------------

            def close(self):
                self._store.close()

            # -------------------- Properties --------------------

            def is_read_only(self) -> bool:
                return self._store.read_only

    _AbstractFile = _zarrFile
