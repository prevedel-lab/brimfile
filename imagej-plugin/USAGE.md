# Example Usage - BrimFile ImageJ Plugin

This document provides step-by-step examples of how to use the BrimFile ImageJ plugin.

## Prerequisites

Before you begin, make sure you have:
- ImageJ 1.54j or later installed
- GraalVM with Python support (or GraalVM Community Edition 24.1.1+)
- The BrimFile ImageJ plugin installed (see [Installation Guide](README.md#installation))
- A sample `.brim.zarr` or `.brim.zip` file

## Example 1: Opening a Basic Brim File

### Step 1: Launch ImageJ

Start ImageJ from your applications menu or command line.

### Step 2: Open the Brim File

1. In ImageJ, click on `File > Open... > Brim File...`
2. Navigate to your brim file (e.g., `sample_data.brim.zarr`)
3. Select the file or directory and click "Open"

### Step 3: View the Results

The plugin will:
- Display a progress bar showing the loading status
- Open the Brillouin shift image as an ImageJ stack
- Apply proper spatial calibration (pixel sizes in micrometers)

### What You'll See

The loaded image will show:
- **Slices**: Each Z-plane of your Brillouin shift data
- **Calibration**: Proper X, Y, Z pixel sizes in micrometers
- **Metadata**: Information about the image in the Info window

## Example 2: Analyzing the Loaded Data

Once the brim file is loaded, you can use ImageJ's standard tools to analyze the data:

### Measure Intensities

1. Select `Analyze > Histogram` to view the distribution of Brillouin shift values
2. Use `Analyze > Measure` to get statistics (mean, std dev, etc.)

### Create Regions of Interest (ROI)

1. Use the selection tools to define an ROI
2. Click `Analyze > Measure` to get statistics for that region
3. Use `Analyze > Plot Profile` to see intensity profiles

### Adjust Display

1. Use `Image > Adjust > Brightness/Contrast` to optimize the display
2. Apply lookup tables (LUTs) with `Image > Lookup Tables`
3. Create maximum intensity projections with `Image > Stacks > Z Project...`

## Example 3: Working with 3D Data

For 3D visualization of your Brillouin shift data:

### Create a 3D Volume

1. Load your brim file as described above
2. Go to `Plugins > 3D Viewer`
3. Select your image and configure the display options
4. Click OK to generate a 3D rendering

### Navigate Through Slices

1. Use the slice slider at the bottom of the image window
2. Or use `Image > Stacks > Animation > Start Animation` to play through slices

## Example 4: Exporting Data

### Save as TIFF

1. Load your brim file
2. Go to `File > Save As > Tiff...`
3. Choose a filename and location
4. The entire stack will be saved as a multi-page TIFF

### Export Specific Slices

1. Navigate to the slice you want to export
2. Go to `Image > Duplicate...`
3. Select the range of slices
4. Save the duplicated image

## Example 5: Batch Processing Multiple Brim Files

To process multiple brim files:

### Using ImageJ Macros

Create a macro (example):

```javascript
// Example ImageJ macro for batch processing brim files
dir = getDirectory("Choose a Directory containing .brim.zarr folders");
list = getFileList(dir);

for (i = 0; i < list.length; i++) {
    if (endsWith(list[i], ".brim.zarr/") || endsWith(list[i], ".brim.zip")) {
        // Open the brim file using the plugin
        run("Brim File...", "open=" + dir + list[i]);
        
        // Process the image (example: measure mean intensity)
        run("Measure");
        
        // Close the image
        close();
    }
}
```

### Run the Macro

1. Go to `Plugins > Macros > Edit...`
2. Paste the macro code
3. Click `Run`

## Example 6: Comparing Multiple Datasets

To compare Brillouin shift data from different samples:

1. Load the first brim file
2. Rename it: `Image > Rename...` (e.g., "Sample 1")
3. Load the second brim file
4. Rename it: "Sample 2"
5. Use `Image > Color > Merge Channels...` to overlay them
6. Or use `Analyze > Tools > ROI Manager` to compare specific regions

## Common Use Cases

### Visualizing Brillouin Shift Gradients

```
1. Load brim file
2. Image > Adjust > Brightness/Contrast
3. Image > Lookup Tables > Fire (or your preferred LUT)
4. Image > Stacks > Z Project... (if needed)
```

### Measuring Brillouin Shift in Specific Regions

```
1. Load brim file
2. Select ROI tool (rectangle, ellipse, etc.)
3. Draw ROI on image
4. Analyze > Measure
5. Results will show mean, std dev, min, max for the ROI
```

### Creating Publication-Quality Figures

```
1. Load brim file
2. Image > Stacks > Z Project... (Max Intensity)
3. Image > Adjust > Brightness/Contrast (optimize)
4. Image > Lookup Tables > (choose appropriate LUT)
5. Image > Overlay > Add Scale Bar...
6. File > Save As > PNG/TIFF
```

## Troubleshooting Common Issues

### Plugin Menu Item Not Visible

- Make sure the plugin JAR is in the ImageJ `plugins/` directory
- Restart ImageJ
- Check `Plugins > Utilities > List PlugIns` to verify installation

### "Cannot find brimfile module" Error

- Verify that the brimfile Python package is accessible
- Check that GraalPy is properly installed
- Try setting the `PYTHONPATH` environment variable before launching ImageJ

### Slow Loading Times

- Large files may take several minutes to load
- Be patient during the "Initializing Python environment" step (first time only)
- Subsequent loads should be faster

### Out of Memory Errors

- Increase ImageJ's memory: `Edit > Options > Memory & Threads...`
- Or start ImageJ with more memory: `ImageJ -Xmx4096m` (for 4GB)

## Tips and Best Practices

1. **Save Your Work**: ImageJ processes are non-destructive until you save, so experiment freely
2. **Use ROI Manager**: For multiple regions, use the ROI Manager to keep track of your selections
3. **Macro Recording**: Record your analysis workflow using `Plugins > Macros > Record...`
4. **Calibration Matters**: The plugin preserves spatial calibration, use it for accurate measurements
5. **Close Files**: Close images when done to free up memory

## Additional Resources

- [ImageJ User Guide](https://imagej.net/docs/)
- [BrimFile Documentation](https://prevedel-lab.github.io/brimfile/)
- [Brillouin File Format Specification](https://github.com/prevedel-lab/Brillouin-standard-file)

## Getting Help

If you encounter issues:
1. Check the ImageJ console window for error messages
2. Review the [Troubleshooting section](README.md#troubleshooting) in the main README
3. Open an issue on the [GitHub repository](https://github.com/prevedel-lab/brimfile/issues)
