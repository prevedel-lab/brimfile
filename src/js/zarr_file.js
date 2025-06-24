import ZipStore from "https://cdn.jsdelivr.net/npm/@zarrita/storage/zip/+esm";
import * as zarr from "https://cdn.jsdelivr.net/npm/zarrita/+esm";

//////////////////////////////////////////////////////////////////
/******* definition of constants shared between the two workers *******/
/*
The SharedArrayBuffer sab contains a header of size 'sab_payload_offset' and a payload of size 'sab_payload_size' (sizes in bytes)
The header contains two int32 numbers at RESULT_READY and DATA_SIZE
 */

//starting of the payload in bytes
const sab_payload_offset = 2*4

//indices of the header elements (type int32)
const RESULT_READY = 0;
const DATA_SIZE = 1;

//in case of an array the payload consists of:
//    1   uint32: contains the size of the dimensions (n_dims)
// n_dims uint32: cotains the size of each dimensions
//    N   float64: the array containing the actual data; IMPORTANT: the offset is ceiled to a multiple of 8
function write_array_to_sab(arr, shape) {
  if (!(ArrayBuffer.isView(arr))) {throw new Error("Only arrays can be transferred with this function!")}
  if (!(arr instanceof Float64Array)) {console.warn("The data will be converted to Float64")}
  //set the shape of the array
  const shape_sab = new Uint32Array(sab, sab_payload_offset, 1+shape.length);
  shape_sab[0] = shape.length;
  let tot_size = 1;
  for (let i=0; i<shape.length; i++) {shape_sab[i+1]=shape[i]; tot_size*=shape[i]}
  //check that the sizes match
  if (tot_size!=arr.length) {throw new Error("Something went wrong with setting the array!")}
  //calculate the offset of the array
  const array_payload_offset = 8* Math.ceil( (sab_payload_offset+4*(1+shape.length)) / 8)
  //set the total size of the payload
  const tot_size_bytes = array_payload_offset + 8*arr.length; 
  data_size.set(tot_size_bytes);
  if (tot_size_bytes>sab.byteLength) {
    //try to grow the buffer 
    //if the operation is not supported it will fail 
    sab.grow(tot_size_bytes);
    sab_payload_size = tot_size_bytes-sab_payload_offset;
  }
  //set the array in the sab
  const array_payload = new Float64Array(sab, array_payload_offset, arr.length);
  array_payload.set(arr);
}

function write_json_to_sab(js_obj) {
  //encode the object into a unit8 array
  const json = JSON.stringify(js_obj);
  const encoded = encoder.encode(json);
  if (encoded.length>sab_payload_size) {
    //try to grow the buffer 
    //if the operation is not supported it will fail 
    sab.grow(encoded.length+sab_payload_offset);
    sab_payload_size = encoded.length;
  }
  data_size.set([encoded.length]);
  payload_unit8array.set(encoded);
}

////////////////////////////////////////////////////////////////


//the size of the payload in bytes
let sab_payload_size = 0

console.log("Zarr worker loaded")

let sab = null; // SharedArrayBuffer for synchronization
let sync_flags = null;
let data_size = null;
let payload_unit8array = null

const encoder = new TextEncoder();
function setSerializedResult(result, result_is_array=false) {
  // check if the previous result was read by the caller
  if (Atomics.load(sync_flags,RESULT_READY) !== 0) {
    throw new Error("The previous result was not retrieved!");
  }
  if (result_is_array) {
    write_array_to_sab(result.data, result.shape)}
  else {
    write_json_to_sab(result)}
  //notify the caller worker that the result is set
  Atomics.store(sync_flags, RESULT_READY, 1);
  if (1!==Atomics.notify(sync_flags, RESULT_READY)) {
    throw new Error("The caller worker was not waiting for the result!");
  }
};
function setSerializedResultError(reason, result_is_array=false) {
  if (result_is_array) {
    console.log(reason)
    setSerializedResult(new Float64Array([]), true)
  }
  else {
    setSerializedResult({isError: true, Err:reason})
  }
};


onmessage = (e) => {
  switch (e.data.type) {
    case "init":
      sab = e.data.sab; // Store the SharedArrayBuffer
      sab_payload_size = sab.byteLength-sab_payload_offset

      sync_flags = new Int32Array(sab, 4*RESULT_READY, 1); // Initialize the sync_flags
      data_size = new Int32Array(sab, 4*DATA_SIZE, 1);

      payload_unit8array = new Uint8Array(sab, sab_payload_offset);

      postMessage({type: "initialized"})
      break;
    case "call_func":
      const args = e.data.args;
      let zf = null;
      if (e.data.func!=="init_file") {zf = get_zarr_object(args.id);}
      switch (e.data.func){
        case "init_file":
          init_file(args.file).then((res) => setSerializedResult(res), (reas) => setSerializedResultError(reas))
          break;
        case "get_attribute":
          zf.get_attribute(args.full_path, args.attr_name).then((res) => setSerializedResult(res), (reas) => setSerializedResultError(reas));
          break;
        case "open_group":
          zf.open_group(args.full_path).then((res) => setSerializedResult(res), (reas) => setSerializedResultError(reas));
          break;
        case "open_dataset":
          zf.open_dataset(args.full_path).then((res) => setSerializedResult(res), (reas) => setSerializedResultError(reas));
          break;
        case "get_array_slice":
          zf.get_array_slice(args.full_path, args.indices).then((res) => setSerializedResult(res, true), (reas) => setSerializedResultError(reas, true));
          break;
        case "get_array_shape":
          zf.get_array_shape(args.full_path).then((res) => setSerializedResult(res), (reas) => setSerializedResultError(reas));
          break;
        case "list_objects":
          zf.list_objects(args.full_path).then((res) => setSerializedResult(res), (reas) => setSerializedResultError(reas));
          break;
        case "object_exists":
          zf.object_exists(args.full_path).then((res) => setSerializedResult(res), (reas) => setSerializedResultError(reas));
          break;
        case "list_attributes":
          zf.list_attributes(args.full_path).then((res) => setSerializedResult(res), (reas) => setSerializedResultError(reas));
          break;
      }
      break;
  }
};

// This function is used to standardize the path by ensuring it ends with a '/' and does not start with one.
function standardize_path(path) {
  if (!path.endsWith('/')) {
    path = path + '/';
  }
  if (path.startsWith('/')) {
    path = path.slice(1);
  }
  return path;
}

class ZarrFile {
  constructor() {
  }

  async init(file) {
    this.store = await ZipStore.fromBlob(file);
    this.root = await zarr.open(this.store, { kind: "group" });
  }

  /******** Attribute Management ********/
  async get_attribute(full_path, attr_name) {
    full_path = standardize_path(full_path);
    const obj = await zarr.open(this.root.resolve(full_path));
    return obj.attrs[attr_name];
  }

  /******** Group Management ********/

  async open_group(full_path){
    full_path = standardize_path(full_path);
    if (! await this.object_exists(full_path)) {
      throw new Error(`The object '${full_path}' doesn't exist!`)
    }
    // for now simply return the path since all the functions that accepts a group object require its full path
    return full_path
    //Here is the actual code that would open the group 
    /*
    const group = await zarr.open(this.root.resolve(full_path), { kind: "group" });
    return group
    */
  }

  /******** Dataset Management ********/

  async open_dataset(full_path){
    full_path = standardize_path(full_path);
    // for now simply return the path since the array object itself is not json transferrable
    return full_path
    const arr = await zarr.open(this.root.resolve(full_path), { kind: "array" });
    return arr
  }

  async get_array_slice(full_path, indices){
    const array = await zarr.open(this.root.resolve(full_path), { kind: "array" });
    function undef2null(obj) {return obj===undefined?null:obj;}
    let js_indices = [];
    for (let i of indices) {
      js_indices.push(zarr.slice(undef2null(i[0]), undef2null(i[1])))
    }
    const res = await zarr.get(array, js_indices);
    return res
  }

  async get_array_shape(full_path){
    const array = await zarr.open(this.root.resolve(full_path), { kind: "array" });
    return array.shape;
  }

  /******** Listing ********/
  async list_objects(full_path) {
    const objects = [];

    full_path = standardize_path(full_path);

    const entries = (await this.store.info).entries;
    for (const key of Object.keys(entries)) {
      //console.log(key);
      if (key.startsWith(full_path)) {
        let obj = key.slice(full_path.length);
        obj = obj.split("/")[0];
        if (!obj.endsWith('zarr.json') && !objects.includes(obj)) {
          objects.push(obj);
        }
      } 
    }
    return objects;
  }

  async object_exists(full_path) {
    full_path = standardize_path(full_path);
    try {
      const obj = await zarr.open(this.root.resolve(full_path));
      return true;
    }
    catch (e) {
      return false;
    }
  }

  async list_attributes(full_path) {
    full_path = standardize_path(full_path);
    const obj = await zarr.open(this.root.resolve(full_path));
    return Object.keys(obj.attrs);
  }
}


let zarr_file = null;
function get_zarr_object(id) {
  //TODO: implement possibility of multiple files
  if (typeof zarr_file !== "undefined" && zarr_file !== null) {
      return zarr_file;
    }
  throw new Error("Zarr file not initialized.");
}

//create a zarr object and return an unique id (0 in case of error)
async function init_file(file) {
  zarr_file = new ZarrFile();
  await zarr_file.init(file);
  //returns the id of the file
  //TODO: implement possibility of multiple files
  return 1;
}