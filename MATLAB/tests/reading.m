%% open the .brim file
% Set up file path
filename = 'https://s3.embl.de/brim-example-files/drosophila_LSBM.brim.zarr';
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