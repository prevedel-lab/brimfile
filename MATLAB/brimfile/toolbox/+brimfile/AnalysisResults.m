classdef AnalysisResults
    % AnalysisResults MATLAB wrapper for Python
    % brimfile.data.AnalysisResults

    properties (Access = private)
        pyObj
    end

    methods
        function obj = AnalysisResults(pyObjArg)
            if nargin < 1
                error('Python AnalysisResults object required');
            end
            obj.pyObj = pyObjArg;
        end

        function name = get_name(obj)
            name = char(obj.pyObj.get_name());
        end

        function add_data(obj, data_AntiStokes, data_Stokes, varargin)
            % add_data Pass-through to Python add_data
            % Usage: add_data(data_AntiStokes, data_Stokes, 'fit_model', fit_model)
            % The MATLAB caller is expected to provide Python-compatible
            % arguments (numpy arrays, py.dict, enums). This wrapper does
            % not attempt complex MATLAB->Python conversions.
            if nargin < 2
                error('At least one argument required for add_data');
            end
            % forward all provided args to the python object
            try
                if nargin == 2
                    obj.pyObj.add_data(data_AntiStokes);
                elseif nargin == 3
                    obj.pyObj.add_data(data_AntiStokes, data_Stokes);
                else
                    % handle additional name-value pairs via pyargs
                    obj.pyObj.add_data(data_AntiStokes, data_Stokes, varargin{:});
                end
            catch ME
                rethrow(ME)
            end
        end

        function u = get_units(obj, quantity, peak_type, index)
            if nargin < 3
                peak_type = brimfile.const().AnalysisResults.PeakType.AntiStokes;
            end
            if nargin < 4
                index = int32(0);
            end
            u = char(obj.pyObj.get_units(quantity, peak_type, int32(index)));
        end

        function [img, px_size] = get_image(obj, quantity, peak_type, index)
            if nargin < 3 || isempty(peak_type)
                peak_type = brimfile.const().AnalysisResults.PeakType.average;
            end
            if nargin < 4 || isempty(index)
                index = int32(0);
            end
            
            spec = obj.pyObj.get_image(quantity, peak_type, int32(index));          
            spec = brimfile.py2mat(spec);
            % spec{1} -> numpy array, spec{2} -> pixel sizes (tuple)
            try
                img = double(spec{1}.astype(py.numpy.float64));
            catch
                img = spec{1};
            end
            px_size = spec{2};
        end

        function val = get_quantity_at_pixel(obj, coord, quantity, peak_type, index)
            if nargin < 4 || isempty(peak_type)
                peak_type = brimfile.const().AnalysisResults.PeakType.average;
            end
            if nargin < 5 || isempty(index)
                index = int32(0);
            end

            % convert MATLAB numeric vector to py.tuple if necessary
            if ~isa(coord, 'py.tuple')
                coord_py = py.tuple(cellfun(@(x) py.int(int32(x)), num2cell(coord), 'UniformOutput', false));
            else
                coord_py = coord;
            end

            res = obj.pyObj.get_quantity_at_pixel(coord_py, quantity, peak_type, int32(index));
           
            % try to convert common Python scalars/arrays to MATLAB types
            val = brimfile.py2mat(res);
            if isa(val, 'py.int') || isa(val, 'py.float')
                val = double(val);
            end
        end

        function ls = list_existing_peak_types(obj, index)
            if nargin < 2 || isempty(index)
                index = int32(0);
            end
            pyList = obj.pyObj.list_existing_peak_types(int32(index));
            ls = brimfile.py2mat(pyList);
        end

        function ls = list_existing_quantities(obj, peak_type, index)
            if nargin < 2 || isempty(peak_type)
                peak_type = brimfile.const().AnalysisResults.PeakType.average;
            end
            if nargin < 3 || isempty(index)
                index = int32(0);
            end
            pyList = obj.pyObj.list_existing_quantities(peak_type, int32(index));
           
            ls = brimfile.py2mat(pyList);
        end

        function fm = fit_model(obj)
            try
                fm_py = obj.pyObj.fit_model;
                fm = fm_py;
            catch
                fm = [];
            end
        end
    end
end