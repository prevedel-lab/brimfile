classdef Data
    % Data MATLAB wrapper for Python brimfile.data.Data
    properties (Access = private)
        pyObj
    end

    methods
        function obj = Data(pyObjArg)
            if nargin < 1
                error('Python Data object required');
            end
            obj.pyObj = pyObjArg;
        end

        function name = get_name(obj)
            name = char(obj.pyObj.get_name());
        end

        function n = get_num_parameters(obj)
            n = double(obj.pyObj.get_num_parameters());
        end

        function md = get_metadata(obj)
            pyMd = obj.pyObj.get_metadata();
            md = brimfile.Metadata(pyMd);
        end

        function ar = get_analysis_results(obj, index)
            if nargin < 2
                index = int32(0);
            end
            pyAr = obj.pyObj.get_analysis_results(index);   
            ar = brimfile.AnalysisResults(pyAr);
        end

        function list = list_AnalysisResults(obj, retrieve_custom_name)
            % list_AnalysisResults List analysis results in the data group
            if nargin<2 
                retrieve_custom_name = false;
            end
            pyList = obj.pyObj.list_AnalysisResults(retrieve_custom_name);
            list = brimfile.py2mat(pyList);
        end

        function [PSD, frequency, PSD_units, frequency_units] = get_spectrum_in_image(obj, coord)
            % coord can be MATLAB vector or py.tuple
            if ~isa(coord, 'py.tuple')
                % convert numeric vector to py.tuple of py.int
                coord_py = py.tuple(cellfun(@(x) py.int(int32(x)), num2cell(coord), 'UniformOutput', false));
            else
                coord_py = coord;
            end
            spec = obj.pyObj.get_spectrum_in_image(coord_py);
            spec = brimfile.py2mat(spec);
            PSD = double(spec{1}.astype(py.numpy.float64));
            frequency = double(spec{2}.astype(py.numpy.float64));
            PSD_units = spec{3};
            frequency_units = spec{4};
        end

        function [PSD, frequency, PSD_units, frequency_units] = get_PSD_as_spatial_map(obj)
            spec = obj.pyObj.get_PSD_as_spatial_map();
            spec = brimfile.py2mat(spec);
            PSD = double(spec{1}.astype(py.numpy.float64));
            frequency = double(spec{2}.astype(py.numpy.float64));
            PSD_units = spec{3};
            frequency_units = spec{4};
        end
    end
end
