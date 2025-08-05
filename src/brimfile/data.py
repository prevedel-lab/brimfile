import numpy as np

import warnings
from enum import Enum

from .file_abstraction import FileAbstraction
from .utils import concatenate_paths, list_objects_matching_pattern, get_object_name, set_object_name, var_to_singleton

from .metadata import Metadata

from . import units
from .constants import brim_obj_names

__docformat__ = "google"


class Data:
    """
    Represents a data group within the brim file.
    """

    def __init__(self, file: FileAbstraction, path: str):
        """
        Initialize the Data object. This constructor should not be called directly.

        Args:
            file (File): The parent File object.
            path (str): The path to the data group within the file.
        """
        self._file = file
        self._path = path
        self._group = file.open_group(path)

        self._spatial_map, self._spatial_map_px_size = self._load_spatial_mapping()

    def get_name(self):
        """
        Returns the name of the data group.
        """
        return get_object_name(self._file, self._path)
    
    def get_index(self):
        """
        Returns the index of the data group.
        """
        return int(self._path.split('/')[-1].split('_')[-1])

    def _load_spatial_mapping(self) -> tuple:
        """
        Load a spatial mapping in the same format as 'Cartesian visualisation',
        irrespectively on whether 'Spatial_map' is defined instead.
        nans are used for "empty" pixels in the image
        Returns:
            The spatial map and the corresponding pixel size as a tuple of 3 Metadata.Item, both in the order z, y, x.
        """
        cv = None
        px_size = 3*(Metadata.Item(value=np.nan, units=None),)
        cv_path = concatenate_paths(
            self._path, brim_obj_names.data.cartesian_visualisation)
        sm_path = concatenate_paths(
            self._path, brim_obj_names.data.spatial_map)
        if self._file.object_exists(cv_path):
            cv = self._file.open_dataset(cv_path)
            px_size_val = 3*(np.nan,)
            px_size_units = None
            try:
                px_size_val = self._file.get_attr(cv, 'element_size')
                px_size_units = units.of_attribute(
                    self._file, cv, 'element_size')
            except Exception:
                warnings.warn(
                    "No pixel size / units defined for Cartesian visualisation")
            finally:
                px_size = tuple(Metadata.Item(
                    px_size_val[i], px_size_units) for i in range(3))

        elif self._file.object_exists(sm_path):
            def load_spatial_map_from_file(self):
                def load_coordinate_from_sm(coord: str):
                    res = np.empty(0)  # empty array
                    try:
                        res = np.array(self._file.open_dataset(
                            concatenate_paths(sm_path, coord)))
                        res = np.squeeze(res)  # remove single-dimensional entries
                    except Exception:
                        pass
                    if len(res.shape) > 1:
                        raise ValueError(
                            f"The 'Spatial_map/{coord}' dataset is not a 1D array as expected")
                    return res

                def check_coord_array(arr, size):
                    if arr.size == 0:
                        return np.zeros(size)
                    elif arr.size != size:
                        raise ValueError(
                            "The 'Spatial_map' dataset is invalid")
                    return arr

                x = load_coordinate_from_sm('x')
                y = load_coordinate_from_sm('y')
                z = load_coordinate_from_sm('z')
                size = max([x.size, y.size, z.size])
                if size == 0:
                    raise ValueError("The 'Spatial_map' dataset is empty")
                x = check_coord_array(x, size)
                y = check_coord_array(y, size)
                z = check_coord_array(z, size)
                return x, y, z

            def calculate_step(x):
                n = len(np.unique(x))
                if n == 1:
                    d = np.nan
                else:
                    d = (np.max(x)-np.min(x))/(n-1)
                return n, d

            x, y, z = load_spatial_map_from_file(self)

            # TODO extend the reconstruction to non-cartesian cases

            nX, dX = calculate_step(x)
            nY, dY = calculate_step(y)
            nZ, dZ = calculate_step(z)

            indices = np.lexsort((x, y, z))
            cv = np.reshape(indices, (nZ, nY, nX))

            px_size_units = units.of_object(self._file, sm_path)
            px_size = tuple(Metadata.Item(px_sz, px_size_units)
                            for px_sz in (dZ, dY, dX))
        return cv, px_size

    def get_PSD(self) -> tuple:
        """
        LOW LEVEL FUNCTION

        Retrieve the Power Spectral Density (PSD) and frequency from the current data group.
        Note: this function exposes the internals of the brim file and thus the interface might change in future versions.
        Use only if more specialized functions are not working for your application!
        Returns:
            tuple: (PSD, frequency, PSD_units, frequency_units)
                - PSD: A 2D (or more) numpy array containing all the spectra (see [specs](https://github.com/prevedel-lab/Brillouin-standard-file/blob/main/docs/brim_file_specs.md) for more details).
                - frequency: A numpy array representing the frequency data (see [specs](https://github.com/prevedel-lab/Brillouin-standard-file/blob/main/docs/brim_file_specs.md) for more details).
                - PSD_units: The units of the PSD.
                - frequency_units: The units of the frequency.
        """
        PSD = self._file.open_dataset(concatenate_paths(
            self._path, brim_obj_names.data.PSD))
        frequency = self._file.open_dataset(concatenate_paths(
            self._path, brim_obj_names.data.frequency))
        # retrieve the units of the PSD and frequency
        PSD_units = units.of_object(self._file, PSD)
        frequency_units = units.of_object(self._file, frequency)

        return PSD, frequency, PSD_units, frequency_units

    def get_spectrum(self, index: int) -> tuple:
        """
        Retrieve a spectrum from the data group.

        Args:
            index (int): The index of the spectrum to retrieve.

        Returns:
            tuple: (PSD, frequency, PSD_units, frequency_units) for the specified index. 
                    PSD can be 1D or more (if there are additional parameters);
                    frequency has the same size as PSD
        Raises:
            IndexError: If the index is out of range for the PSD dataset.
        """
        PSD = self._file.open_dataset(concatenate_paths(
            self._path, brim_obj_names.data.PSD))
        if index >= PSD.shape[0]:
            raise IndexError(
                f"index {index} out of range for PSD with shape {PSD.shape}")        
        frequency = self._file.open_dataset(concatenate_paths(
            self._path, brim_obj_names.data.frequency))
        # retrieve the units of the PSD and frequency
        PSD_units = units.of_object(self._file, PSD)
        frequency_units = units.of_object(self._file, frequency)
        # broadcast frequency to match the shape of PSD
        if frequency.ndim < PSD.ndim:
            frequency = np.broadcast_to(frequency, PSD.shape)
        return PSD[index, ...], frequency[index, ...], PSD_units, frequency_units

    def get_spectrum_in_image(self, coor: tuple) -> tuple:
        """
        Retrieve a spectrum from the data group using spatial coordinates.

        Args:
            coor (tuple): A tuple containing the z, y, x coordinates of the spectrum to retrieve.

        Returns:
            tuple: A tuple containing the PSD, frequency, PSD_units, frequency_units for the specified coordinates. See "get_spectrum" for details.
        """
        if len(coor) != 3:
            raise ValueError("coor must contain 3 values for z, y, x")

        index = int(self._spatial_map[coor])
        return self.get_spectrum(index)

    class AnalysisResults:
        """
        Rapresents the analysis results associated with a Data object.
        """

        class Quantity(Enum):
            """
            Enum representing the type of analysis results.
            """
            Shift = "Shift"
            Width = "Width"
            Amplitude = "Amplitude"
            Offset = "Offset"
            R2 = "R2"
            RMSE = "RMSE"
            Cov_matrix = "Cov_matrix"

        class PeakType(Enum):
            AntiStokes = "AS"
            Stokes = "S"
            average = "avg"

        def __init__(self, file: FileAbstraction, full_path: str, spatial_map, spatial_map_px_size):
            """
            Initialize the AnalysisResults object.

            Args:
                file (File): The parent File object.
                full_path (str): path of the group storing the analysis results
            """
            self._file = file
            self._path = full_path
            # self._group = file.open_group(full_path)
            self._spatial_map = spatial_map
            self._spatial_map_px_size = spatial_map_px_size

        def get_name(self):
            """
            Returns the name of the Analysis group.
            """
            return get_object_name(self._file, self._path)

        @classmethod
        def _create_new(cls, data: 'Data', index: int) -> 'Data.AnalysisResults':
            """
            Create a new AnalysisResults group.

            Args:
                file (FileAbstraction): The file.
                index (int): The index for the new AnalysisResults group.

            Returns:
                AnalysisResults: The newly created AnalysisResults object.
            """
            group_name = f"{brim_obj_names.data.analysis_results}_{index}"
            ar_full_path = concatenate_paths(data._path, group_name)
            group = data._file.create_group(ar_full_path)
            return cls(data._file, ar_full_path, data._spatial_map, data._spatial_map_px_size)

        def add_data(self, data_AntiStokes=None, data_Stokes=None):
            """
            Adds data for the analysis results for AntiStokes and Stokes peaks to the file.
            
            Args:
                data_AntiStokes (dict or list[dict]): A dictionary containing the analysis results for AntiStokes peaks.
                    In case multiple peaks were fitted, it might be a list of dictionaries with each element corresponding to a single peak.
                
                    Each dictionary may include the following keys (plus the corresponding units,  e.g. 'shift_units'):
                        - 'shift': The shift value.
                        - 'width': The width value.
                        - 'amplitude': The amplitude value.
                        - 'offset': The offset value.
                        - 'R2': The R-squared value.
                        - 'RMSE': The root mean square error value.
                        - 'Cov_matrix': The covariance matrix.
                data_Stokes (dict or list[dict]): same as `data_AntiStokes` for the Stokes peaks.

                Both `data_AntiStokes` and `data_Stokes` are optional, but at least one of them must be provided.
            """

            ar_cls = Data.AnalysisResults
            ar_group = self._file.open_group(self._path)

            def add_quantity(qt: Data.AnalysisResults.Quantity, pt: Data.AnalysisResults.PeakType, data, index: int = 0):
                # TODO: check if the data is valid
                self._file.create_dataset(
                    ar_group, ar_cls._get_quantity_name(qt, pt, index), data)

            def add_data_pt(pt: Data.AnalysisResults.PeakType, data, index: int = 0):
                if 'shift' in data:
                    add_quantity(ar_cls.Quantity.Shift,
                                 pt, data['shift'], index)
                    if 'shift_units' in data:
                        self._set_units(data['shift_units'],
                                        ar_cls.Quantity.Shift, pt, index)
                if 'width' in data:
                    add_quantity(ar_cls.Quantity.Width,
                                 pt, data['width'], index)
                    if 'width_units' in data:
                        self._set_units(data['width_units'],
                                        ar_cls.Quantity.Width, pt, index)
                if 'amplitude' in data:
                    add_quantity(ar_cls.Quantity.Amplitude,
                                 pt, data['amplitude'], index)
                    if 'amplitude_units' in data:
                        self._set_units(
                            data['amplitude_units'], ar_cls.Quantity.Amplitude, pt, index)
                if 'offset' in data:
                    add_quantity(ar_cls.Quantity.Offset,
                                 pt, data['offset'], index)
                    if 'offset_units' in data:
                        self._set_units(
                            data['offset_units'], ar_cls.Quantity.Offset, pt, index)
                if 'R2' in data:
                    add_quantity(ar_cls.Quantity.R2, pt, data['R2'], index)
                    if 'R2_units' in data:
                        self._set_units(data['R2_units'],
                                        ar_cls.Quantity.R2, pt, index)
                if 'RMSE' in data:
                    add_quantity(ar_cls.Quantity.RMSE, pt, data['RMSE'], index)
                    if 'RMSE_units' in data:
                        self._set_units(data['RMSE_units'],
                                        ar_cls.Quantity.RMSE, pt, index)
                if 'Cov_matrix' in data:
                    add_quantity(ar_cls.Quantity.Cov_matrix,
                                 pt, data['Cov_matrix'], index)
                    if 'Cov_matrix_units' in data:
                        self._set_units(
                            data['Cov_matrix_units'], ar_cls.Quantity.Cov_matrix, pt, index)

            if data_AntiStokes is not None:
                data_AntiStokes = var_to_singleton(data_AntiStokes)
                for i, d_as in enumerate(data_AntiStokes):
                    add_data_pt(ar_cls.PeakType.AntiStokes, d_as, i)
            if data_Stokes is not None:
                data_Stokes = var_to_singleton(data_Stokes)
                for i, d_s in enumerate(data_Stokes):
                    add_data_pt(ar_cls.PeakType.Stokes, d_s, i)

        def get_units(self, qt: Quantity, pt: PeakType = PeakType.AntiStokes, index: int = 0) -> str:
            """
            Retrieve the units of a specified quantity from the data file.

            Args:
                qt (Quantity): The quantity for which the units are to be retrieved.
                pt (PeakType, optional): The type of peak (e.g., Stokes or AntiStokes). Defaults to PeakType.AntiStokes.
                index (int, optional): The index of the quantity in case multiple quantities exist. Defaults to 0.

            Returns:
                str: The units of the specified quantity as a string.
            """
            dt_name = Data.AnalysisResults._get_quantity_name(qt, pt, index)
            full_path = concatenate_paths(self._path, dt_name)
            return units.of_object(self._file, full_path)

        def _set_units(self, un: str, qt: Quantity, pt: PeakType = PeakType.AntiStokes, index: int = 0) -> str:
            """
            Set the units of a specified quantity.

            Args:
                un (str): The units to be set.
                qt (Quantity): The quantity for which the units are to be set.
                pt (PeakType, optional): The type of peak (e.g., Stokes or AntiStokes). Defaults to PeakType.AntiStokes.
                index (int, optional): The index of the quantity in case multiple quantities exist. Defaults to 0.

            Returns:
                str: The units of the specified quantity as a string.
            """
            dt_name = Data.AnalysisResults._get_quantity_name(qt, pt, index)
            full_path = concatenate_paths(self._path, dt_name)
            return units.add_to_object(self._file, full_path, un)

        def save_image_to_OMETiff(self, qt: Quantity, pt: PeakType = PeakType.AntiStokes, index: int = 0, filename: str = None):
            """
            Saves the image corresponding to the specified quantity and index to an OMETiff file.

            Args:
                qt (Quantity): The quantity to retrieve the image for (e.g. shift).
                pt (PeakType, optional): The type of peak to consider (default is PeakType.AntiStokes).
                index (int, optional): The index of the data to retrieve, if multiple are present (default is 0).
                filename (str, optional): The name of the file to save the image to. If None, a default name will be used.

            Returns:
                str: The path to the saved OMETiff file.
            """
            # TODO: implement the possibility of saving the average between Stokes and AntiStokes
            try:
                import tifffile
            except ImportError:
                raise ModuleNotFoundError(
                    "The tifffile module is required for saving to OME-Tiff. Please install it using 'pip install tifffile'.")
            img, px_size = self.get_image(qt, pt, index)
            if filename is None:
                filename = f"{qt.value}_{pt.value}_{index}.ome.tif"
            if not filename.endswith('.ome.tif'):
                filename += '.ome.tif'
            img, px_size = self.get_image(qt, pt, index)
            if img.ndim > 3:
                raise NotImplementedError(
                    "Saving images with more than 3 dimensions is not supported yet.")
            with tifffile.TiffWriter(filename, bigtiff=True) as tif:
                metadata = {
                    'axes': 'ZYX',
                    'PhysicalSizeX': px_size[2].value,
                    'PhysicalSizeXUnit': px_size[2].units,
                    'PhysicalSizeY': px_size[1].value,
                    'PhysicalSizeYUnit': px_size[1].units,
                    'PhysicalSizeZ': px_size[0].value,
                    'PhysicalSizeZUnit': px_size[0].units,
                }
                tif.write(img, metadata=metadata)

        def get_image(self, qt: Quantity, pt: PeakType = PeakType.AntiStokes, index: int = 0) -> tuple:
            """
            Retrieves an image (spatial map) based on the specified quantity, peak type, and index.

            Args:
                qt (Quantity): The quantity to retrieve the image for (e.g. shift).
                pt (PeakType, optional): The type of peak to consider (default is PeakType.AntiStokes).
                index (int, optional): The index of the data to retrieve, if multiple are present (default is 0).

            Returns:
                A tuple containing the image corresponding to the specified quantity and index and the corresponding pixel size.
                The image is a 3D dataset where the dimensions are z, y, x.
                If there are additional parameters, more dimensions are added in the order z, y, x, par1, par2, ...
                The pixel size is a tuple of 3 Metadata.Item in the order z, y, x.
            """
            pt_type = Data.AnalysisResults.PeakType
            data = None
            if pt == pt_type.average:
                peaks = self.list_existing_peak_types(index)
                match len(peaks):
                    case 0:
                        raise ValueError(
                            "No peaks found for the specified index. Cannot compute average.")
                    case 1:
                        data = np.array(self._get_quantity(qt, peaks[0], index))
                    case 2:
                        data = np.abs(
                            np.array(self._get_quantity(qt, peaks[0], index)))
                        data += np.abs(np.array(self._get_quantity(qt,
                                    peaks[1], index)))
                        data /= 2
            else:
                data = np.array(self._get_quantity(qt, pt, index))
            sm = np.array(self._spatial_map)
            img = data[sm, ...]
            return img, self._spatial_map_px_size

        def get_quantity_at_pixel(self, coord: tuple, qt: Quantity, pt: PeakType = PeakType.AntiStokes, index: int = 0):
            """
            Retrieves the specified quantity in the image at coord, based on the peak type and index.

            Args:
                coord (tuple): A tuple of 3 elements corresponding to the z, y, x coordinate in the image
                qt (Quantity): The quantity to retrieve the image for (e.g. shift).
                pt (PeakType, optional): The type of peak to consider (default is PeakType.AntiStokes).
                index (int, optional): The index of the data to retrieve, if multiple are present (default is 0).

            Returns:
                The requested quantity, which is a scalr or a multidimensional array (depending on whether there are additional parameters in the current Data group)
            """
            if len(coord) != 3:
                raise ValueError(
                    "'coord' must have 3 elements corresponding to z, y, x")
            i = self._spatial_map[*coord]
            assert i.size == 1

            pt_type = Data.AnalysisResults.PeakType
            value = None
            if pt == pt_type.average:
                value = None
                peaks = self.list_existing_peak_types(index)
                match len(peaks):
                    case 0:
                        raise ValueError(
                            "No peaks found for the specified index. Cannot compute average.")
                    case 1:
                        data = self._get_quantity(qt, peaks[0], index)
                        value = data[int(i), ...]
                    case 2:
                        data = self._get_quantity(qt, peaks[0], index)
                        value = np.abs(data[int(i), ...])
                        data = self._get_quantity(qt, peaks[1], index)
                        value += np.abs(data[int(i), ...])
                        value /= 2
            else:
                data = self._get_quantity(qt, pt, index)
                value = data[int(i), ...]
            return value

        @classmethod
        def _get_quantity_name(cls, qt: Quantity, pt: PeakType, index: int) -> str:
            """
            Returns the name of the dataset correponding to the specific Quantity, PeakType and index

            Args:
                qt (Quantity)   
                pt (PeakType)  
                intex (int): in case of multiple peaks fitted, the index of the peak to consider       
            """
            if not pt in (cls.PeakType.AntiStokes, cls.PeakType.Stokes):
                raise ValueError("pt has to be either Stokes or AntiStokes")
            if qt == cls.Quantity.R2 or qt == cls.Quantity.RMSE or qt == cls.Quantity.Cov_matrix:
                name = f"Fit_error_{str(pt.value)}_{index}/{str(qt.value)}"
            else:
                name = f"{str(qt.value)}_{str(pt.value)}_{index}"
            return name

        def _get_quantity(self, qt: Quantity, pt: PeakType = PeakType.AntiStokes, index: int = 0):
            """
            Retrieve a specific quantity dataset from the file.

            Args:
                qt (Quantity): The type of quantity to retrieve.
                pt (PeakType, optional): The peak type to consider (default is PeakType.AntiStokes).
                index (int, optional): The index of the quantity if multiple peaks are available (default is 0).

            Returns:
                The dataset corresponding to the specified quantity, as stored in the file.

            """

            dt_name = Data.AnalysisResults._get_quantity_name(qt, pt, index)
            full_path = concatenate_paths(self._path, dt_name)
            return self._file.open_dataset(full_path)

        def list_existing_peak_types(self, index: int = 0) -> tuple:
            """
            Returns a tuple of existing peak types (Stokes and/or AntiStokes) for the specified index.
            Args:
                index (int, optional): The index of the peak to check (in case of multi-peak fit). Defaults to 0.
            Returns:
                tuple: A tuple containing `PeakType` members (`Stokes`, `AntiStokes`) that exist for the given index.
            """

            as_cls = Data.AnalysisResults
            shift_s_name = as_cls._get_quantity_name(
                as_cls.Quantity.Shift, as_cls.PeakType.Stokes, index)
            shift_as_name = as_cls._get_quantity_name(
                as_cls.Quantity.Shift, as_cls.PeakType.AntiStokes, index)
            ls = ()
            if self._file.object_exists(concatenate_paths(self._path, shift_as_name)):
                ls += (as_cls.PeakType.AntiStokes,)
            if self._file.object_exists(concatenate_paths(self._path, shift_s_name)):
                ls += (as_cls.PeakType.Stokes,)
            return ls

        def list_existing_quantities(self,  pt: PeakType = PeakType.AntiStokes, index: int = 0) -> tuple:
            """
            Returns a tuple of existing quantities for the specified index.
            Args:
                index (int, optional): The index of the peak to check (in case of multi-peak fit). Defaults to 0.
            Returns:
                tuple: A tuple containing `Quantity` members that exist for the given index.
            """
            as_cls = Data.AnalysisResults
            ls = ()
            for qt in as_cls.Quantity:
                if self._file.object_exists(concatenate_paths(self._path, as_cls._get_quantity_name(qt, pt, index))):
                    ls += (qt,)
            return ls

    def get_metadata(self):
        """
        Returns the metadata associated with the current Data group
        Note that this contains both the general metadata stored in the file (which might be redifined by the specific data group)
        and the ones specific for this data group
        """
        return Metadata(self._file, self._path)

    def get_num_parameters(self) -> tuple:
        """
        Retrieves the number of parameters

        Returns:
            tuple: The shape of the parameters if they exist, otherwise an empty tuple.
        """
        pars, _ = self.get_parameters()
        return pars.shape if pars is not None else ()

    def get_parameters(self) -> list:
        """
        Retrieves the parameters  and their associated names.

        If PSD.ndims > 2, the parameters are stored in a separate dataset.

        Returns:
            list: A tuple containing the parameters and their names if there are any, otherwise None.
        """
        pars_full_path = concatenate_paths(
            self._path, brim_obj_names.data.parameters)
        if self._file.object_exists(pars_full_path):
            pars = self._file.open_dataset(pars_full_path)
            pars_names = self._file.get_attr(pars, 'Name')
            return (pars, pars_names)
        return (None, None)

    def create_analysis_results_group(self, data_AntiStokes, data_Stokes=None, index: int = None, name: str = None) -> AnalysisResults:
        """
        Adds a new AnalysisResults entry to the current data group.
        Parameters:
            data_AntiStokes (dict or list[dict]): contains the same elements as the ones in `AnalysisResults.add_data`,
                but all the quantities (i.d. 'shift', 'width', etc.) are 3D, corresponding to the spatial positions (z, y, x).
            data_Stokes (dict or list[dict]): same as data_AntiStokes for the Stokes peaks.
            index (int, optional): The index for the new data entry. If None, the next available index is used. Defaults to None.
            name (str, optional): The name for the new Analysis group. Defaults to None.
        Returns:
            AnalysisResults: The newly created AnalysisResults object.
        Raises:
            IndexError: If the specified index already exists in the dataset.
            ValueError: If any of the data provided is not valid or consistent
        """
        def flatten_data(data: dict):
            if data is None:
                return None
            data = var_to_singleton(data)
            out_data = []
            for dn in data:
                for k in dn.keys():
                    if not k.endswith('_units'):
                        d = dn[k]
                        if d.ndim != 3 or d.shape != self._spatial_map.shape:
                            raise ValueError(
                                f"'{k}' must have 3 dimensions (z, y, x) and same shape as the spatial map ({self._spatial_map.shape})")
                        dn[k] = np.reshape(d, -1)  # flatten the data
                out_data.append(dn)
            return out_data
        data_AntiStokes = flatten_data(data_AntiStokes)
        data_Stokes = flatten_data(data_Stokes)
        return self.create_analysis_results_group_raw(data_AntiStokes, data_Stokes, index, name)

    def create_analysis_results_group_raw(self, data_AntiStokes, data_Stokes=None, index: int = None, name: str = None) -> AnalysisResults:
        """
        Adds a new AnalysisResults entry to the current data group.
        Parameters:
            data_AntiStokes (dict or list[dict]): see documentation for AnalysisResults.add_data
            data_Stokes (dict or list[dict]): same as data_AntiStokes for the Stokes peaks.
            index (int, optional): The index for the new data entry. If None, the next available index is used. Defaults to None.
            name (str, optional): The name for the new Analysis group. Defaults to None.
        Returns:
            AnalysisResults: The newly created AnalysisResults object.
        Raises:
            IndexError: If the specified index already exists in the dataset.
            ValueError: If any of the data provided is not valid or consistent
        """
        if index is not None:
            try:
                self.get_analysis_results(index)
            except IndexError:
                pass
            else:
                # If the group already exists, raise an error
                raise IndexError(
                    f"Analysis {index} already exists in {self._path}")
        else:
            ar_groups = self.list_AnalysisResults()
            indices = [ar['index'] for ar in ar_groups]
            indices.sort()
            index = indices[-1] + 1 if indices else 0  # Next available index

        ar = Data.AnalysisResults._create_new(self, index)
        if name is not None:
            set_object_name(self._file, ar._path, name)
        ar.add_data(data_AntiStokes, data_Stokes)

        return ar

    def list_AnalysisResults(self, retrieve_custom_name=False) -> list:
        """
        List all AnalysisResults groups in the current data group.

        Returns:
            list: A list of dictionaries, each containing:
                - 'name' (str): The name of the AnalysisResults group.
                - 'index' (int): The index extracted from the group name.
                - 'custom_name' (str, optional): if retrieve_custom_name==True, it contains the name of the AnalysisResults group as returned from utils.get_object_name.
        """

        analysis_results_groups = []

        matched_objs = list_objects_matching_pattern(
            self._file, self._group, brim_obj_names.data.analysis_results + r"_(\d+)$")
        for matched_obj in matched_objs:
            name = matched_obj[0]
            index = int(matched_obj[1])
            curr_obj_dict = {'name': name, 'index': index}
            if retrieve_custom_name:
                ar_path = concatenate_paths(self._path, name)
                custom_name = get_object_name(self._file, ar_path)
                curr_obj_dict['custom_name'] = custom_name
            analysis_results_groups.append(curr_obj_dict)

        return analysis_results_groups

    def get_analysis_results(self, index: int = 0) -> AnalysisResults:
        """
        Returns the AnalysisResults at the specified index

        Args:
            index (int)                

        Raises:
            IndexError: If there is no analysis with the corresponding index
        """
        name = None
        ls = self.list_AnalysisResults()
        for el in ls:
            if el['index'] == index:
                name = el['name']
                break
        if name is None:
            raise IndexError(f"Analysis {index} not found")
        path = concatenate_paths(self._path, name)
        return Data.AnalysisResults(self._file, path, self._spatial_map, self._spatial_map_px_size)

    def add_data(self, PSD: np.ndarray, frequency: np.ndarray, scanning: dict, freq_units='GHz', timestamp: np.ndarray = None, compression: FileAbstraction.Compression = FileAbstraction.Compression()):
        """
        Add data to the current data group.

        This method adds the provided PSD, frequency, and scanning data to the HDF5 group 
        associated with this `Data` object. It validates the inputs to ensure they meet 
        the required specifications before adding them.

        Args:
            PSD (np.ndarray): A 2D numpy array representing the Power Spectral Density (PSD) data. The last dimension contains the spectra.
            frequency (np.ndarray): A 1D or 2D numpy array representing the frequency data. 
                It must be broadcastable to the shape of the PSD array.
            scanning (dict): A dictionary containing scanning-related data. It may include:
                - 'Spatial_map' (optional): A dictionary containing (up to) 3 arrays (x, y, z) and a string (units)
                - 'Cartesian_visualisation' (optional): A 3D numpy array containing the association between spatial position and spectra.
                   It must have integer values between 0 and PSD.shape[0]-1, or -1 for invalid entries.
                - 'Cartesian_visualisation_pixel' (optional): A list or array of 3 float values 
                  representing the pixel size in the z, y, and x dimensions (unused dimensions can be set to None).
                - 'Cartesian_visualisation_pixel_unit' (optional): A string representing the unit of the pixel size (e.g. 'um').
            timestamp (np.ndarray): the timestamp associated with each spectrum.
                It must be a 1D array with the same length as the PSD array.


        Raises:
            ValueError: If any of the data provided is not valid or consistent
        """

        # Check if frequency is broadcastable to PSD
        try:
            np.broadcast(PSD, frequency)
        except ValueError as e:
            raise ValueError(f"frequency is not broadcastable to PSD: {e}")

        # define the scanning_is_valid variable to check if at least one of 'Spatial_map' or 'Cartesian_visualisation'
        # is present in the scanning dictionary
        scanning_is_valid = False
        if 'Spatial_map' in scanning:
            sm = scanning['Spatial_map']
            size = 0

            def check_coor(coor: str):
                if coor in sm:
                    sm[coor] = np.array(sm[coor])
                    size1 = sm[coor].size
                    if size1 != size and size != 0:
                        raise ValueError(
                            f"'{coor}' in 'Spatial_map' is invalid!")
                    return size1
            size = check_coor('x')
            size = check_coor('y')
            size = check_coor('z')
            if size == 0:
                raise ValueError(
                    "'Spatial_map' should contain at least one x, y or z")
            scanning_is_valid = True
        if 'Cartesian_visualisation' in scanning:
            cv = scanning['Cartesian_visualisation']
            if not isinstance(cv, np.ndarray) or cv.ndim != 3:
                raise ValueError(
                    "Cartesian_visualisation must be a 3D numpy array")
            if not np.issubdtype(cv.dtype, np.integer) or np.min(cv) < -1 or np.max(cv) >= PSD.shape[0]:
                raise ValueError(
                    "Cartesian_visualisation values must be between 0 and 1")
            if 'Cartesian_visualisation_pixel' in scanning:
                if len(scanning['Cartesian_visualisation_pixel']) != 3:
                    raise ValueError(
                        "Cartesian_visualisation_pixel must always contain 3 values for z, y, x (set to nan if not used)")
            else:
                warnings.warn(
                    "It is recommended to add 'Cartesian_visualisation_pixel' to the scanning dictionary, to define the pixel size")
            scanning_is_valid = True
        if not scanning_is_valid:
            raise ValueError("scanning is not valid")

        if timestamp is not None:
            if not isinstance(timestamp, np.ndarray) or timestamp.ndim != 1 or len(timestamp) != PSD.shape[0]:
                raise ValueError("timestamp is not compatible with PSD")

        # TODO: add and validate additional datasets (i.e. 'Parameters', 'Calibration_index', etc.)

        # Add datasets to the group
        self._file.create_dataset(
            self._group, brim_obj_names.data.PSD, data=PSD, compression=compression)
        freq_ds = self._file.create_dataset(
            self._group,  brim_obj_names.data.frequency, data=frequency, compression=compression)
        units.add_to_object(self._file, freq_ds, freq_units)
        if 'Spatial_map' in scanning:
            sm = scanning['Spatial_map']
            sm_group = self._file.create_group(concatenate_paths(
                self._path, brim_obj_names.data.spatial_map))
            if 'units' in sm:
                units.add_to_object(self._file, sm_group, sm['units'])

            def add_sm_dataset(coord: str):
                if coord in sm:
                    coord_dts = self._file.create_dataset(
                        sm_group, coord, data=sm[coord], compression=compression)

            add_sm_dataset('x')
            add_sm_dataset('y')
            add_sm_dataset('z')
        if 'Cartesian_visualisation' in scanning:
            cv = self._file.create_dataset(self._group, brim_obj_names.data.cartesian_visualisation,
                                           data=scanning['Cartesian_visualisation'], compression=compression)
            if 'Cartesian_visualisation_pixel' in scanning:
                self._file.create_attr(
                    cv, 'element_size', scanning['Cartesian_visualisation_pixel'])
                if 'Cartesian_visualisation_pixel_unit' in scanning:
                    px_unit = scanning['Cartesian_visualisation_pixel_unit']
                else:
                    warnings.warn(
                        "No unit provided for Cartesian_visualisation_pixel, defaulting to 'um'")
                    px_unit = 'um'
                units.add_to_attribute(self._file, cv, 'element_size', px_unit)

        self._spatial_map, self._spatial_map_px_size = self._load_spatial_mapping()

        if timestamp is not None:
            self._file.create_dataset(
                self._group, 'Timestamp', data=timestamp, compression=compression)

    @staticmethod
    def list_data_groups(file: FileAbstraction, retrieve_custom_name=False) -> list:
        """
        List all data groups in the brim file. The list is ordered by index.

        Returns:
            list: A list of dictionaries, each containing:
                - 'name' (str): The name of the data group in the file.
                - 'index' (int): The index extracted from the group name.
                - 'custom_name' (str, optional): if retrieve_custom_name==True, it contains the name of the data group as returned from utils.get_object_name.
        """

        data_groups = []

        matched_objs = list_objects_matching_pattern(
            file, brim_obj_names.Brillouin_base_path, brim_obj_names.data.base_group + r"_(\d+)$")
        for matched_obj in matched_objs:
            name = matched_obj[0]
            index = int(matched_obj[1])
            curr_obj_dict = {'name': name, 'index': index}
            if retrieve_custom_name:
                path = concatenate_paths(
                    brim_obj_names.Brillouin_base_path, name)
                custom_name = get_object_name(file, path)
                curr_obj_dict['custom_name'] = custom_name
            data_groups.append(curr_obj_dict)
        
        # Sort the data groups by index
        data_groups.sort(key=lambda x: x['index'])

        return data_groups

    @staticmethod
    def _get_existing_group_name(file: FileAbstraction, index: int) -> str:
        """
        Get the name of an existing data group by index.

        Args:
            file (File): The parent File object.
            index (int): The index of the data group.

        Returns:
            str: The name of the data group, or None if not found.
        """
        group_name: str = None
        data_groups = Data.list_data_groups(file)
        for dg in data_groups:
            if dg['index'] == index:
                group_name = dg['name']
                break
        return group_name

    @classmethod
    def _create_new(cls, file: FileAbstraction, index: int, name: str = None) -> 'Data':
        """
        Create a new data group with the specified index.

        Args:
            file (File): The parent File object.
            index (int): The index for the new data group.
            name (str, optional): The name for the new data group. Defaults to None.

        Returns:
            Data: The newly created Data object.
        """
        group_name = Data._generate_group_name(index)
        group = file.create_group(concatenate_paths(
            brim_obj_names.Brillouin_base_path, group_name))
        if name is not None:
            set_object_name(file, group, name)
        return cls(file, concatenate_paths(brim_obj_names.Brillouin_base_path, group_name))

    @staticmethod
    def _generate_group_name(index: int, n_digits: int = None) -> str:
        """
        Generate a name for a data group based on the index.

        Args:
            index (int): The index for the data group.
            n_digits (int, optional): The number of digits to pad the index with. If None no padding is applied. Defaults to None.

        Returns:
            str: The generated group name.

        Raises:
            ValueError: If the index is negative.
        """
        if index < 0:
            raise ValueError("index must be positive")
        num = str(index)
        if n_digits is not None:
            num = num.zfill(n_digits)
        return f"{brim_obj_names.data.base_group}_{num}"
