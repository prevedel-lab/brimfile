function out = py2mat(pyObj)
% py2mat Convert common Python containers/values to MATLAB types
%   out = brimfile.py2mat(pyObj)
%
% This helper converts Python str, int, float, bool, list, tuple and dict
% into MATLAB char, double, logical, cell and struct respectively. Other
% objects (e.g. numpy.ndarray) are returned as the original Python object
% for the caller to handle.

    if nargin == 0 || isempty(pyObj)
        out = [];
        return
    end

    % Scalars
    if isa(pyObj, 'py.str')
        out = char(pyObj);
        return
    end
    if isa(pyObj, 'py.bytes')
        out = char(pyObj);
        return
    end
    if isa(pyObj, 'py.int') || isa(pyObj, 'py.long') || isa(pyObj, 'py.float')
        out = double(pyObj);
        return
    end
    if isa(pyObj, 'py.bool')
        out = logical(pyObj);
        return
    end

    % List or tuple
    if isa(pyObj, 'py.list') || isa(pyObj, 'py.tuple')
        n = int64(py.len(pyObj));
        out = cell(1, double(n));
        for k = 1:double(n)
            out{k} = brimfile.py2mat(pyObj{k});
        end
        return
    end

    % Dict
    if isa(pyObj, 'py.dict')
        keys = py.list(pyObj.keys());
        out = struct();
        for k = 1:length(keys)
            key = keys{k};
            try
                val = pyObj.get(key);
            catch
                val = [];
            end
            field = matlab.lang.makeValidName(char(key));
            out.(field) = brimfile.py2mat(val);
        end
        return
    end

    % Fallback: return Python object
    out = pyObj;
end
