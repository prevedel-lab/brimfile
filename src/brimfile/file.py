import numpy as np

from .data import Data
from .metadata import Metadata

from .utils import concatenate_paths
from .constants import brim_obj_names

from .file_abstraction import FileAbstraction, StoreType

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
                store_type (StoreType): Type of the store to use, as defined in `brimfile.file_abstraction.StoreType`. Default is 'auto'.
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
            pass

    def close(self) -> None:
        self._file.close()

    def is_read_only(self) -> bool:
        return self._file.is_read_only()

    def is_valid(self) -> bool:
        """
        Check if the file is a valid brim file.

        Returns:
            bool: True if the file is valid, False otherwise.
        """
        # TODO validate file against https://github.com/prevedel-lab/Brillouin-standard-file/blob/main/docs/brim_file_specs.md
        return True

    @classmethod
    def create(cls, filename: str, store_type: str = 'zip'):
        """
        Create a new brim file with the specified filename. If the file exists already it will generate an error.

        Args:
            filename (str): Path to the brim file to be created.

        Returns:
            File: An instance of the File class representing the newly created brim file.
            store_type (str): Type of the store to use ('zip', 'zarr', 'remote'). Default is 'zip'.
        """
        f = cls(filename, mode='w-', store_type=store_type)

        # File version and SubType
        f._file.create_attr('/', 'brim_version', '0.1')
        f._file.create_attr('/', 'SubTypeID', 0)  # Default subtype

        # Root Brillouin_data group
        fr = f._file.create_group(brim_obj_names.Brillouin_base_path)

        # Create the metadata group
        Metadata._create_group_in_file(f._file)

        return f

    def create_data_group(self, PSD: np.ndarray, frequency: np.ndarray, px_size_um: tuple, index: int = None, name: str = None, compression: FileAbstraction.Compression = FileAbstraction.Compression()) -> 'Data':
        """
        Adds a new data entry to the file.
        Parameters:
            PSD (np.ndarray): The Power Spectral Density (PSD) data to be added. It must be 4D with dimensions z, y, x, spectrum
            frequency (np.ndarray): The frequency data corresponding to the PSD. It must be 4D or 1D (in which case the frequency axis is assumed the same for all the spatial coordinates)
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
        if frequency.ndim != 1 and frequency.ndim != 4:
            raise ValueError(
                "'frequency' must have either 4 dimensions (z, y, x, spectrum) or 1 dimension (spectrum)")
        if len(px_size_um) != 3:
            raise ValueError("'px_size_um' must have 3 elements (z,y,x); unused dimensions can be set to nan")

        PSD_flat = np.reshape(PSD, (-1, PSD.shape[3]))
        if frequency.ndim == 4:
            freq_flat = np.reshape(frequency, (-1, frequency.shape[3]))
        else:
            freq_flat = frequency
        indices = np.arange(PSD_flat.shape[0])
        cartesian_vis = np.reshape(indices, PSD.shape[0:3])
        scanning = {'Cartesian_visualisation': cartesian_vis,
                    'Cartesian_visualisation_pixel': px_size_um, 'Cartesian_visualisation_pixel_unit': 'um'}

        return self.create_data_group_raw(PSD_flat, freq_flat, scanning, index=index, name=name, compression=compression)

    def create_data_group_raw(self, PSD: np.ndarray, frequency: np.ndarray, scanning: dict, timestamp: np.ndarray = None, index: int = None, name: str = None, compression: FileAbstraction.Compression = FileAbstraction.Compression()) -> 'Data':
        """
        Adds a new data entry to the file. Check the documentation for `brimfile.data.Data.add_data` for more details on the parameters.
        Parameters:
            PSD (np.ndarray): The Power Spectral Density (PSD) data to be added. The last dimension contains the spectra.
            frequency (np.ndarray): The frequency data corresponding to the PSD.
            scanning (dict): Metadata related to the scanning process. See Data.add_data for more details.
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
        if index is not None:
            if Data._get_existing_group_name(self._file, index) is not None:
                raise IndexError(
                    f"Data {index} already exists in {self._file.filename}")
        else:
            data_groups = self.list_data_groups()
            indices = [dg['index'] for dg in data_groups]
            indices.sort()
            index = indices[-1] + 1 if indices else 0  # Next available index

        d = Data._create_new(self._file, index, name)
        d.add_data(PSD, frequency, scanning,
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
