%% This is an internal function
function brimfile_module = init()
    %init Initialize the Python environment and load the brimfile package
    %   it returns the loaded brimfile module
    persistent bf_module
    % the python module was not initialized yet
    % import it and call the initialization functions
    if isempty(bf_module)
        venv_path = get_python_env_path();
        pyenv('Version', venv_path);
        disp(pyenv)
        try
            bf_module = py.importlib.import_module('brimfile');
        catch
            error('Could not load the brimfile module. Check that it is correctly installed in the current Python environment')
        end
        % initialize the constants
        brimfile.const(bf_module);
    end
    brimfile_module = bf_module;
end

function path = get_python_env_path()
    path = brimfile.getInstallationLocation('brimfile Python env');
    if ismac
        path = fullfile(path, 'bin', 'python');
    elseif ispc
        path = fullfile(path,'python');
    end           
end