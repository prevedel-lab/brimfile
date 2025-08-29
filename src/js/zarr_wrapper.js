import { ZarrFile, init_file } from './zarr_file.js';
//import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v0.28.2/full/pyodide.mjs";

// Loads the Zarr and create a bls_file in the globals of pyodide
function loadZarrFile(file) {
    const zarr_file_js = init_file(file)

    const locals = pyodide.toPy({ zarr_file_js: zarr_file_js, zarr_filename: file.name });
    pyodide.runPython(`
        import brimfile as bls
        from brimfile.file_abstraction import _zarrFile

        zf = _zarrFile(zarr_file_js, filename=zarr_filename)
        global bls_file
        bls_file = bls.File(zf)
    `, { locals });
    return true;
}

//TEST
/*
async function init_pyodide() {
    self.pyodide = await loadPyodide();
    await pyodide.loadPackage("micropip");
    await pyodide.loadPackage("numpy")
    await pyodide.loadPackage("./brimfile-1.1.3-py2.py3-none-any.whl")
}
init_pyodide().then (
    () => {
        loadZarrFile('https://storage.googleapis.com/brim-example-files/zebrafish_eye_confocal.brim.zarr');
        pyodide.runPythonAsync(`
            from js import console
            dg = bls_file.list_data_groups(retrieve_custom_name=True)
            console.log(str(dg[0]))

            d = bls_file.get_data()

            # get the metadata 
            md = d.get_metadata()
            all_metadata = md.all_to_dict()
            console.log(str(all_metadata['Experiment']))`)
    }
)
*/
