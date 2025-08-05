//////////////////////////////////////////////////////////////////
// Helper function
function reviveError(obj) {
    const err = new Error(obj.message);
    err.name = obj.name || 'Error';
    err.stack = obj.stack || '';

    for (const key in obj) {
        if (!['name', 'message', 'stack'].includes(key)) {
            err[key] = obj[key];
        }
    }

    return err;
}

/******* definition of constants shared between the two workers *******/
/*
The SharedArrayBuffer sab contains a header of size 'sab_payload_offset' and a payload of size 'sab_payload_size' (sizes in bytes)
The header contains two int32 numbers at RESULT_READY and DATA_SIZE
 */

//starting of the payload in bytes
const sab_payload_offset = 2 * 4

//indices of the header elements (type int32)
const RESULT_READY = 0;
const DATA_SIZE = 1;

//in case of an array the payload consists of:
//    1   uint32: contains the size of the dimensions (n_dims)
// n_dims uint32: cotains the size of each dimensions
//    N   float64: the array containing the actual data; IMPORTANT: the offset is ceiled to a multiple of 8
function read_array_from_sab() {
    //get the shape of the array
    const n_dims = (new Uint32Array(sab, sab_payload_offset, 1))[0];
    const shape = new Uint32Array(sab, sab_payload_offset + 4, n_dims);
    let tot_size = 1;
    for (let i = 0; i < shape.length; i++) { tot_size *= shape[i] }
    //calculate the offset of the array
    const array_payload_offset = 8 * Math.ceil((sab_payload_offset + 4 * (1 + n_dims)) / 8)
    const array_payload = new Float64Array(sab, array_payload_offset, tot_size);
    const res = { shape: shape, data: array_payload };
    return res;
}

function read_json_from_sab() {
    if (data_size[0] > sab.byteLength - sab_payload_offset) {
        throw new Error("The worker set a payload larger than the buffer size")
    }
    const worker_data = payload_unit8array.slice(0, data_size[0])
    const json = decoder.decode(worker_data)
    const obj = JSON.parse(json)
    return obj;
}

////////////////////////////////////////////////////////////////

const growable_sab_supported = (() => {
    try { new SharedArrayBuffer(1, { maxByteLength: 1 }); return true; } catch { return false; }
})();
// If SharedArrayBuffer is growable set a small size to start with 
const initial_sab_payload_size = growable_sab_supported ? 10e6 : 200e6;

if (!isSecureContext) {
    throw new Error("No secure context!")
}
if (!crossOriginIsolated) {
    throw new Error("No cross origin isolation!")
}

//sab_payload_offset bytes for flags + initial_sab_payload_size for the actual data 
const sab = (() => { const size = sab_payload_offset + initial_sab_payload_size; return growable_sab_supported ? new SharedArrayBuffer(size, { maxByteLength: 1e9 }) : new SharedArrayBuffer(size) })();
const sync_flags = new Int32Array(sab, 4 * RESULT_READY, 1);
const data_size = new Int32Array(sab, 4 * DATA_SIZE, 1);
const payload_unit8array = new Uint8Array(sab, sab_payload_offset);

//Initialize the worker
let zarrWorker_initialized = false
const zarrWorker = new Worker('./zarr_file.js', { type: 'module' });
zarrWorker.postMessage({
    type: "init",
    sab: sab
});

zarrWorker.onmessage = (e) => {
    switch (e.data.type) {
        case 'initialized':
            zarrWorker_initialized = true
            break;
    }
};

const decoder = new TextDecoder();
//variable that keeps track of whether a previous call to a worker returned
let previous_called_returned = true;
// Function to call a function in the worker in a synchronous way (i.e. waiting for the result)
function callWorkerFunc(func, args, result_is_array = false) {
    /**
     * Call a function in the zarr worker
     * @param  {String} func the name of the function to call 
     * @param  {Object} args the arguments to pass to the function as a dictionary
     */
    if (!zarrWorker_initialized) {
        throw new Error("The zarr worker didn't finish initializing");
    }

    if (!previous_called_returned) {
        throw new Error("The previous call hasn't finished yet")
    }
    else { //prepare the state variable for calling the zarr worker
        previous_called_returned = false;
        // Reset the result ready flag, in case it is in the wrong state due to a previous failed call
        Atomics.store(sync_flags, RESULT_READY, 0);
    }

    let pyproxies = [];
    let args_proxy = null;
    if (args instanceof pyodide.ffi.PyProxy) {
        args_proxy = args
        args = args.toJs({ dict_converter: Object.fromEntries, pyproxies: pyproxies })
    }

    zarrWorker.postMessage({
        type: "call_func",
        func: func,
        args: args
    });

    //clean the js proxies that were possibly created during the function call
    //see https://pyodide.org/en/stable/usage/type-conversions.html
    if (args_proxy !== null) {
        for (let px of pyproxies) {
            px.destroy();
        }
        args_proxy.destroy();
    }
    const timeout_ms = 2000;
    const r = Atomics.wait(sync_flags, RESULT_READY, 0, timeout_ms); // Wait for the result to be set
    Atomics.store(sync_flags, RESULT_READY, 0); // Reset the result ready flag
    previous_called_returned = true;
    if (r === "timed-out") {
        throw new Error(`The operation didn't complete within the timeout period of ${timeout_ms}ms!`);
    }
    if (r === "not-equal") {
        //the zarr worker had already processed the results before we reached Atomics.wait
    }

    if (result_is_array) {
        const obj = read_array_from_sab();
        return obj;
    }
    else {
        const obj = read_json_from_sab();
        if (typeof obj.isError !== 'undefined' && typeof obj.Err !== 'undefined') { if (obj.isError) throw new Error(reviveError(obj.Err)); }
        return obj;
    }
};

function init_zarr_wrapper() {
    pyodide.runPython(`
        from js import callWorkerFunc
        import numpy as np
        class _zarrFile:
            class ZarrArray:
                def __init__(self, id, dts):
                    self.id = id
                    self.dts = dts                
                def __str__(self):
                    return str(self.dts)
                def __array__(self, dtype=None, copy=None):
                    #TODO: implement dtype and copy
                    # see https://numpy.org/doc/stable/user/basics.interoperability.html#dunder-array-interface
                    return self[...]
                
                def __getitem__(self, index):
                    def index_to_js_slice(i):
                        if isinstance(i, slice):
                            return [i.start, i.stop]
                        elif isinstance(i, type(Ellipsis)):
                            raise ValueEror("INTERNAL: Ellipsis should have been already substituted")
                        else:
                            return [i, i+1]
                    if type(index) is not tuple:
                        index = (index,)
                    # check that only one Ellipsis is present
                    num_ellipsis = sum(isinstance(i, type(Ellipsis)) for i in index)
                    if num_ellipsis>1:
                        raise ValueError("Only one Ellipsis is allowed!")
                    if num_ellipsis == 1:
                        n_dim = len(self.shape)
                        if len(index)-1>n_dim:
                            raise ValueError(f"Expected at most {n_dim} indices and got {len(index)} instead!")
                        n_null_indices = 1 + n_dim-len(index)
                        new_index = ()
                        for i in index:
                            if isinstance(i, type(Ellipsis)):
                                new_index += (slice(None),)*n_null_indices
                            else:
                                new_index += (i,)
                        index = new_index     
                    js_indices = [];
                    for i in index:
                        js_indices.append(index_to_js_slice(i))
                        
                    res = callWorkerFunc('get_array_slice', {'id': self.id, 'full_path': self.dts, 'indices':js_indices}, True)
                    data = _zarrFile.JsProxy_to_py(res.data)
                    shape = _zarrFile.JsProxy_to_py(res.shape)
                    data = np.array(data)
                    data = np.reshape(data, shape).flatten()
                    return data
                @property
                def shape(self):
                    res = callWorkerFunc('get_array_shape', {'id': self.id, 'full_path': self.dts})
                    return _zarrFile.JsProxy_to_py(res)
                @property
                def size(self):
                    return np.prod(self.shape)

                @property
                def ndim(self):
                    return len(self.shape)
                

            def __init__(self, id:int, filename:str="filename"):
                # The id is used to identify the specific file in case multiple are opened
                self.id = id
                self.filename = filename

            @staticmethod
            def JsProxy_to_py(jsproxy):
                #alternatively one ca use isinstance(jsproxy, pyodide.ffi.JsProxy)
                if hasattr(jsproxy, "to_py"):
                    return jsproxy.to_py()
                return jsproxy
            
            # -------------------- Attribute Management --------------------
            def get_attr(self, full_path, attr_name):  
                res = callWorkerFunc('get_attribute', {'id': self.id, 'full_path': str(full_path), 'attr_name':attr_name})
                return _zarrFile.JsProxy_to_py(res)
            
            # -------------------- Group Management --------------------
            def open_group(self, full_path: str):
                return callWorkerFunc('open_group', {'id': self.id, 'full_path': full_path})
            
            # -------------------- Dataset Management --------------------
            def open_dataset(self, full_path: str):
                dts = callWorkerFunc('open_dataset', {'id': self.id, 'full_path': full_path})
                return _zarrFile.ZarrArray(self.id, dts)
            
            # -------------------- Listing --------------------
            def list_objects(self, full_path) -> list:
                res = callWorkerFunc('list_objects', {'id': self.id, 'full_path': str(full_path)})
                return _zarrFile.JsProxy_to_py(res)
            def object_exists(self, full_path) -> bool:
                res = callWorkerFunc('object_exists', {'id': self.id, 'full_path': str(full_path)})
                return _zarrFile.JsProxy_to_py(res)
            def list_attributes(self, full_path) -> list:
                res = callWorkerFunc('list_attributes', {'id': self.id, 'full_path': str(full_path)})
                return _zarrFile.JsProxy_to_py(res)
            
            # -------------------- Properties --------------------
            def is_read_only(self) -> bool:
                return True
    `);
}

// Loads the Zarr and create a bls_file in the globals of pyodide
function loadZarrFile(file) {
    const file_id = callWorkerFunc("init_file", { file: file })
    if (file_id == 0) { return false; }
    pyodide.globals.set("_bls_file_id_temp", file_id);
    pyodide.globals.set("_bls_file_filename_temp", file.name);

    pyodide.runPython(`
        import brimfile as bls
        global _bls_file_id_temp
        global bls_file
        zf = _zarrFile(_bls_file_id_temp, filename=_bls_file_filename_temp)
        bls_file = bls.File(zf)
        del _bls_file_id_temp
        del _bls_file_filename_temp
    `);
    return true;
}