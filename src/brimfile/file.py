import numpy as np
import warnings

from .data import Data
from .metadata import Metadata

from .utils import concatenate_paths
from .constants import brim_obj_names
from . import units

from .file_abstraction import FileAbstraction, StoreType, sync

# don't import _AbstractFile if running in pyodide (it is defined in js)
import sys
if "pyodide" not in sys.modules:
    from .file_abstraction import _AbstractFile

__docformat__ = "google"

class File:
    """
    Represents a brim file with Brillouin data, extending h5py.File.
    """

    if "pyodide" in sys.modules:
        def __init__(self, file):
            self._file = file
            if not self.is_valid():
                raise ValueError("The brim file is not valid!")
    else:
        def __init__(self, filename: str, mode: str = 'r', store_type: StoreType = StoreType.AUTO):
            """
            Initialize the File object.

            Args:
                filename (str): Path to the brim file.
                mode: {'r', 'r+', 'a', 'w', 'w-'} the mode for opening the file (default is 'r' for read-only).
                            See the definition of `mode` in `brimfile.file_abstraction._zarrFile.__init__()` for more details.
                            'r' means read only (must exist); 'r+' means read/write (must exist);
                            'a' means read/write (create if doesn't exist); 'w' means create (overwrite if exists); 'w-' means create (fail if exists).
                store_type (StoreType): Type of the store to use, as defined in `brimfile.file_abstraction.StoreType`. Default is 'AUTO'.
            """
            self._file = _AbstractFile(
                filename, mode=mode, store_type=store_type)
            if not self.is_valid():
                raise ValueError("The brim file is not valid!")
            
    def __del__(self):
        try:
            self.close()
        except Exception as e:            
            # don't throw an error if the file cannot be closed
            warnings.warn(f"Cannot close the file: {e}")

    def close(self) -> None:
        self._file.close()

    def is_read_only(self) -> bool:
        return sync(self._file.is_read_only())

    def is_valid(self) -> bool:
        """
        Check if the file is a valid brim file.

        Returns:
            bool: True if the file is valid, False otherwise.
        """
        # TODO validate file against https://github.com/prevedel-lab/Brillouin-standard-file/blob/main/docs/brim_file_specs.md
        return True

    @classmethod
    def create(cls, filename: str, store_type: StoreType = StoreType.AUTO, brim_version: str = '0.1') -> 'File':
        """
        Create a new brim file with the specified filename. If the file exists already it will generate an error.

        Args:
            filename (str): Path to the brim file to be created.
            store_type (StoreType): Type of the store to use, as defined in `brimfile.file_abstraction.StoreType`. Default is 'AUTO'.
            brim_version (str): Version of the brim file format to use. Default is '0.1'.

        Returns:
            File: An instance of the File class representing the newly created brim file.
            store_type (str): Type of the store to use, as defined in `brimfile.file_abstraction.StoreType`. Default is 'AUTO'.
        """
        f = cls(filename, mode='w-', store_type=store_type)

        # File version
        sync(f._file.create_attr('/', 'brim_version', brim_version))

        # Root Brillouin_data group
        fr = sync(f._file.create_group(brim_obj_names.Brillouin_base_path))

        return f

    def create_data_group(self, PSD: np.ndarray, frequency: np.ndarray, px_size_um: tuple, *, index: int = None,
                          name: str = None, compression: FileAbstraction.Compression = FileAbstraction.Compression()) -> 'Data':
        """
        Adds a new data entry to the file.
        Parameters:
            PSD (np.ndarray): The Power Spectral Density (PSD) data to be added. It must be 4D with dimensions z, y, x, spectrum
            frequency (np.ndarray): The frequency data corresponding to the PSD. It must be broadcastable to the PSD shape (the most common case is frequency being 1D, in which case the frequency axis is assumed the same for all the spatial coordinates)
            px_size_um (tuple): A tuple of 3 elements, in the order z,y,x, corresponding to the pixel size in um. Unused dimensions can be set to None.
            index (int, optional): The index for the new data group. If None, the next available index is used. Defaults to None.
            name (str, optional): The name for the new data group. Defaults to None.
            compression (FileAbstraction.Compression, optional): The compression method to use for the data. Defaults to FileAbstraction.Compression.DEFAULT.
        Returns:
            Data: The newly created Data object.
        Raises:
            IndexError: If the specified index already exists in the dataset.
            ValueError: If any of the data provided is not valid or consistent
        """
        if PSD.ndim != 4:
            raise ValueError(
                "'PSD' must have 4 dimensions (z, y, x, spectrum)")
        try:
            np.broadcast_shapes(tuple(frequency.shape), tuple(PSD.shape))
        except ValueError as e:
            raise ValueError(f"frequency (shape: {frequency.shape}) is not broadcastable to PSD (shape: {PSD.shape}): {e}")
        if len(px_size_um) != 3:
            raise ValueError("'px_size_um' must have 3 elements (z,y,x); unused dimensions can be set to nan")

        return self._create_data_group_raw(PSD, frequency, scanning = None, sparse = False, px_size_um=px_size_um, 
                                             index=index, name=name, compression=compression)

    def create_data_group_sparse(self, PSD: np.ndarray, frequency: np.ndarray, scanning: dict, *, timestamp: np.ndarray = None,
                                index: int = None, name: str = None, compression: FileAbstraction.Compression = FileAbstraction.Compression()) -> 'Data':
        """
        Adds a new [sparse data entry](https://github.com/prevedel-lab/Brillouin-standard-file/blob/main/docs/brim_file_specs.md) to the file.
        Check the documentation for `brimfile.data.Data._add_data` for more details on the parameters.
        Parameters:
            PSD (np.ndarray): The Power Spectral Density (PSD) data to be added. The last dimension contains the spectra.
            frequency (np.ndarray): The frequency data corresponding to the PSD. Must be broadcastable to the PSD array.
            scanning (dict): Metadata related to the scanning process. See Data._add_data for more details.
            timestamp (np.ndarray, optional): Timestamps in milliseconds for the data. Defaults to None.
            index (int, optional): The index for the new data group. If None, the next available index is used. Defaults to None.
            name (str, optional): The name for the new data group. Defaults to None.
            compression (FileAbstraction.Compression, optional): The compression method to use for the data. Defaults to FileAbstraction.Compression.DEFAULT.
        Returns:
            Data: The newly created Data object.
        Raises:
            IndexError: If the specified index already exists in the dataset.
            ValueError: If any of the data provided is not valid or consistent
        """
        return self._create_data_group_raw(PSD, frequency, scanning=scanning, timestamp=timestamp, sparse=True, index=index, name=name, compression=compression)   
    
    def _create_data_group_raw(self, PSD: np.ndarray, frequency: np.ndarray, *, scanning: dict = None, px_size_um = None, timestamp: np.ndarray = None, sparse: bool = False,
                                index: int = None, name: str = None, compression: FileAbstraction.Compression = FileAbstraction.Compression()) -> 'Data':
        """
        Adds a new data entry to the file. Check the documentation for `brimfile.data.Data._add_data` for more details on the parameters.
        Parameters:
            PSD (np.ndarray): The Power Spectral Density (PSD) data to be added. The last dimension contains the spectra.
            frequency (np.ndarray): The frequency data corresponding to the PSD. Must be broadcastable to the PSD array.
            scanning (dict): Metadata related to the scanning process. See Data._add_data for more details.
            px_size_um (tuple): A tuple of 3 elements, in the order z,y,x, corresponding to the pixel size in um.
            timestamp (np.ndarray, optional): Timestamps in milliseconds for the data. Defaults to None.
            sparse (bool): Whether the data is sparse. See https://github.com/prevedel-lab/Brillouin-standard-file/blob/main/docs/brim_file_specs.md for details. Defaults to False.
            index (int, optional): The index for the new data group. If None, the next available index is used. Defaults to None.
            name (str, optional): The name for the new data group. Defaults to None.
            compression (FileAbstraction.Compression, optional): The compression method to use for the data. Defaults to FileAbstraction.Compression.DEFAULT.
        Returns:
            Data: The newly created Data object.
        Raises:
            IndexError: If the specified index already exists in the dataset.
            ValueError: If any of the data provided is not valid or consistent
        """
        if index is not None:
            if Data._get_existing_group_name(self._file, index) is not None:
                raise IndexError(
                    f"Data {index} already exists in {self._file.filename}")
        else:
            data_groups = self.list_data_groups()
            indices = [dg['index'] for dg in data_groups]
            indices.sort()
            index = indices[-1] + 1 if indices else 0  # Next available index

        # create the data group
        d = Data._create_new(self._file, index, sparse, name)
        # add the pixel size as an attribute of the data group
        if px_size_um is not None:
            sync(self._file.create_attr(d._group, 'element_size', tuple(px_size_um)))
            units.add_to_attribute(self._file, d._group, 'element_size', 'um')
        elif not sparse:
            warnings.warn("Pixel size is not provided for non-sparse data. It is recommended to provide it for proper data interpretation.")
        # add the data to the data group
        d._add_data(PSD, frequency, scanning,
                   timestamp=timestamp, compression=compression)
        return d

    def list_data_groups(self, retrieve_custom_name=False) -> list:
        """
        List all data groups in the brim file.

        Returns:
            See documentation of brimfile.data.Data.list_data_groups
        """
        return Data.list_data_groups(self._file, retrieve_custom_name)

    def get_data(self, index: int = 0) -> 'Data':
        """
        Retrieve a Data object for the specified index.

        Args:
            index (int): The index of the data group to retrieve.

        Returns:
            Data: The Data object corresponding to the specified index.
        """
        group_name: str = Data._get_existing_group_name(self._file, index)
        if group_name is None:
            raise IndexError(f"Data {index} not found")
        data = Data(self._file, concatenate_paths(
            brim_obj_names.Brillouin_base_path, group_name))
        return data

    @property
    def filename(self) -> str:
        """
        Get the filename of the brim file.

        Returns:
            str: The filename of the brim file.
        """
        return self._file.filename
