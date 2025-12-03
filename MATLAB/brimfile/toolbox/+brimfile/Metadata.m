classdef Metadata
    % Metadata MATLAB wrapper for Python brimfile.metadata.Metadata
    properties (Access = private)
        pyObj
    end

    methods
        function obj = Metadata(pyObjArg)
            if nargin < 1
                error('Python Metadata object required');
            end
            obj.pyObj = pyObjArg;
        end

        function s = all_to_dict(obj)
            pyDict = obj.pyObj.all_to_dict();
            s = brimfile.py2mat(pyDict);
        end

        function val = get(obj, key)
            % get a single metadata item by string key 'Group.Key'
            val = obj.pyObj.get(key);
        end

        function add(obj, type, metadata, local)
            if nargin < 4
                local = false;
            end
            obj.pyObj.add(type, metadata, local);
        end
    end
end
