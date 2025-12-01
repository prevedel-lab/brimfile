classdef File < handle
    % File MATLAB wrapper for Python brimfile.File
    properties (Access = private)
        pyFile
    end

    methods (Static)
        function obj = create(filename)
            brim = brimfile.init();
            obj = brimfile.File();
            obj.pyFile = brim.File.create(filename);
        end
    end

    methods
        function obj = File(filename)
            % File Construct a brimfile.File wrapper.
            % Usage:
            %   f = brimfile.File(filename)      % open existing file

            if nargin < 1
                % create an empty object; it is only used internally by
                % other functions of this class
                return
            end

            brim = brimfile.init();

            obj.pyFile = brim.File(filename);           
        end

        function dataObj = get_data(obj, index)
            % get_data Get a Data wrapper for the first (or indexed) data group
            if nargin < 2
               index = int32(0);
            end
            pyData = obj.pyFile.get_data(index);
            dataObj = brimfile.Data(pyData);
        end

        function list = list_data_groups(obj, retrieve_custom_name)
            if nargin < 2
                retrieve_custom_name = false;
            end
            pyList = obj.pyFile.list_data_groups(retrieve_custom_name);
            list = brimfile.py2mat(pyList);
        end

        function tf = is_read_only(obj)
            tf = logical(obj.pyFile.is_read_only());
        end

        function close(obj)
            obj.pyFile.close();
        end

        function delete(obj)
            try
                obj.close();
            catch
            end
        end
    end
end
