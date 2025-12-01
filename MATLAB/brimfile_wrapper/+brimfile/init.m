function brimfile_module = init(venv_path)
    %init Initialize the Python environment and load the brimfile package
    %   it returns the loaded brimfile module
    persistent bf_module
    % the python module was not initialized yet
    % import it and call the initialization functions
    if isempty(bf_module)
        if nargin >= 1
            pyenv('Version',venv_path);
        end
        try 
            bf_module = py.importlib.import_module('brimfile');
        catch
            error('Could not load the brimfile module. Check that it is correctly installed in the current Python environment')
        end
        brimfile.const(bf_module);
    end
    brimfile_module = bf_module;
end