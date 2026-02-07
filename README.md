<div align="center">
    <img src="https://raw.githubusercontent.com/prevedel-lab/brimfile/refs/heads/main//brimfile_logo.png"/>
</div>

# brimfile package

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://prevedel-lab.github.io/brimfile/brimfile.html)

## What is it?

*brimfile* is a package to read and write to brim (**Br**illouin **im**aging) files, containing spectral data and metadata from Brillouin microscopy.

The detailed specs of the brim file format can be found [here](https://github.com/prevedel-lab/Brillouin-standard-file/blob/main/docs/brim_file_specs.md).

## How to install it

We recommend installing *brimfile* in a [virtual environment](https://docs.python.org/3/library/venv.html).

After activating the environment, *brimfile* can be installed from PyPI using `pip`:
```bash
pip install brimfile
```

## How to use it

The full documentation of the package can be found [here](https://prevedel-lab.github.io/brimfile/).

To quickly start reading an existing .brim file, the following code shows how to:
- open a .brim file 
- get an image for the Brillouin shift 
- get the spectrum at a specific pixel
- get the metadata.

```Python
from brimfile import File, Data, Metadata
Quantity = Data.AnalysisResults.Quantity
PeakType = Data.AnalysisResults.PeakType

filename = 'path/to/your/file.brim.zarr' 
f = File(filename)

# get the first data group in the file
d = f.get_data()

# get the first analysis results in the data group
ar = d.get_analysis_results()

# get the image for the shift
img, px_size = ar.get_image(Quantity.Shift, PeakType.average)

# get the spectrum at the pixel (pz,py,px)
(pz,py,px) = (0,0,0)
PSD, frequency, PSD_units, frequency_units = d.get_spectrum_in_image((pz,py,px))

# get the metadata 
md = d.get_metadata()
all_metadata = md.all_to_dict()

# close the file
f.close()
```
More examples could be found in the [examples folder](examples)

## Matlab support

You can download the [Matlab toolbox](https://github.com/prevedel-lab/brimfile/releases/tag/matlab_toolbox_main), which is basically a wrapper around the Python brimfile package, so you can refer to the [same documentation](https://prevedel-lab.github.io/brimfile/). We only support Matlab >= R2023b, as brimfile needs Python 3.11.

Note that the current version of the Matlab toolbox is not supporting all the functions defined in brimfile and it has not been tested extensively yet.