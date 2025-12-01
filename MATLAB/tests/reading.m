%% Initialize the brimfile module
% It is highly reccomanded to set up a virtual environment
% To know how to do, see https://github.com/prevedel-lab/brimfile?tab=readme-ov-file#how-to-install-it

% specify the path of the python executable in the virtual environment
% see documentation at https://www.mathworks.com/help/matlab/matlab_external/install-supported-python-implementation.html#buialof-39
venv_path = '../../.venv/bin/python';

% add the path containing the brimfile module
addpath('../')

% if you want to use the default environment (no venv) you can just call
% brimfile.init()
brim = brimfile.init(venv_path);

%% open the .brim file
% Set up file path
filename = '/path/to/file.brim.zarr';
f = brimfile.File(filename);

f.list_data_groups();
f.is_read_only();

d = f.get_data();
spectrum = d.get_spectrum_in_image([0,0,0]);
spectra = d.get_PSD_as_spatial_map();

md = d.get_metadata();
md_list = md.all_to_dict();

ar = d.list_AnalysisResults();
ar = d.get_analysis_results();

Quantity = brimfile.const().AnalysisResults.Quantity;
img = ar.get_image(Quantity.Shift);
ar.get_quantity_at_pixel([0,0,0], Quantity.Shift);

ar.get_name();
ar.get_units(Quantity.Shift);

ar.list_existing_peak_types();
ar.fit_model()

f.close()