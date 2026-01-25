package com.prevedel.brimfile;

import ij.IJ;
import ij.ImagePlus;
import ij.ImageStack;
import ij.io.OpenDialog;
import ij.plugin.PlugIn;
import ij.process.FloatProcessor;
import org.graalvm.polyglot.Context;
import org.graalvm.polyglot.Value;

import java.io.File;
import java.util.HashMap;
import java.util.Map;

/**
 * ImageJ plugin to read brim files using the brimfile Python package via GraalPy.
 * 
 * This plugin allows ImageJ to open and display Brillouin microscopy data stored
 * in the brim file format (.brim.zarr or .brim.zip).
 * 
 * @author Carlo Bevilacqua, Sebastian Hambura
 * @version 1.0.0
 */
public class BrimFile_Reader implements PlugIn {

    private Context pythonContext;

    @Override
    public void run(String arg) {
        // Show file open dialog
        OpenDialog od = new OpenDialog("Open Brim File", arg);
        String directory = od.getDirectory();
        String fileName = od.getFileName();
        
        if (fileName == null) {
            return; // User cancelled
        }
        
        String filePath = directory + fileName;
        
        IJ.showStatus("Loading brim file: " + fileName);
        IJ.showProgress(0.1);
        
        try {
            // Load the brim file
            ImagePlus imp = loadBrimFile(filePath);
            
            if (imp != null) {
                imp.show();
                IJ.showStatus("Brim file loaded successfully");
                IJ.showProgress(1.0);
            } else {
                IJ.error("BrimFile Reader", "Failed to load the brim file.");
            }
        } catch (Exception e) {
            IJ.error("BrimFile Reader", "Error loading brim file:\n" + e.getMessage());
            e.printStackTrace();
        } finally {
            if (pythonContext != null) {
                pythonContext.close();
            }
        }
    }

    /**
     * Load a brim file and convert it to an ImageJ ImagePlus.
     * 
     * @param filePath Path to the brim file
     * @return ImagePlus containing the data
     */
    private ImagePlus loadBrimFile(String filePath) {
        try {
            // Initialize GraalPy context
            IJ.showStatus("Initializing Python environment...");
            pythonContext = Context.newBuilder("python")
                    .allowAllAccess(true)
                    .option("python.ForceImportSite", "false")
                    .option("python.Executable", "graalpy")
                    .build();

            IJ.showProgress(0.2);
            
            // Import brimfile package
            IJ.showStatus("Importing brimfile package...");
            pythonContext.eval("python", "import sys");
            
            // Add brimfile path to sys.path if a specific path was found
            String brimfilePath = getBrimfilePackagePath();
            if (!brimfilePath.isEmpty()) {
                pythonContext.eval("python", "sys.path.insert(0, '" + brimfilePath + "')");
            }
            
            pythonContext.eval("python", "from brimfile import File");
            pythonContext.eval("python", "from brimfile.data import Data");

            IJ.showProgress(0.3);
            
            // Load the brim file
            IJ.showStatus("Opening brim file...");
            Value bindings = pythonContext.getBindings("python");
            bindings.putMember("file_path", filePath);
            
            pythonContext.eval("python", "f = File(file_path)");
            pythonContext.eval("python", "d = f.get_data()");
            pythonContext.eval("python", "ar = d.get_analysis_results()");
            
            IJ.showProgress(0.5);
            
            // Get the Brillouin shift image
            IJ.showStatus("Reading image data...");
            pythonContext.eval("python", 
                "Quantity = Data.AnalysisResults.Quantity\n" +
                "PeakType = Data.AnalysisResults.PeakType\n" +
                "img, px_size = ar.get_image(Quantity.Shift, PeakType.average)");
            
            Value imgValue = bindings.getMember("img");
            Value pxSizeValue = bindings.getMember("px_size");
            
            IJ.showProgress(0.7);
            
            // Convert numpy array to ImageJ ImagePlus
            IJ.showStatus("Converting to ImageJ format...");
            ImagePlus imp = convertToImagePlus(imgValue, pxSizeValue, filePath);
            
            // Close the file
            pythonContext.eval("python", "f.close()");
            
            IJ.showProgress(0.9);
            
            return imp;
            
        } catch (Exception e) {
            IJ.error("BrimFile Reader", "Error in loadBrimFile: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }

    /**
     * Convert Python numpy array to ImageJ ImagePlus.
     * 
     * @param imgValue Python numpy array containing the image
     * @param pxSizeValue Pixel size tuple (dz, dy, dx) in micrometers
     * @param fileName Original file name
     * @return ImagePlus object
     */
    private ImagePlus convertToImagePlus(Value imgValue, Value pxSizeValue, String fileName) {
        try {
            // Get image dimensions from numpy array shape
            Value shape = imgValue.getMember("shape");
            int nz = shape.getArrayElement(0).asInt();
            int ny = shape.getArrayElement(1).asInt();
            int nx = shape.getArrayElement(2).asInt();
            
            // Get pixel sizes
            double dz = pxSizeValue.getArrayElement(0).asDouble();
            double dy = pxSizeValue.getArrayElement(1).asDouble();
            double dx = pxSizeValue.getArrayElement(2).asDouble();
            
            // Create ImageStack
            ImageStack stack = new ImageStack(nx, ny);
            
            // Convert numpy array to Java array and populate stack
            for (int z = 0; z < nz; z++) {
                float[][] slice = new float[ny][nx];
                
                for (int y = 0; y < ny; y++) {
                    for (int x = 0; x < nx; x++) {
                        // Access numpy array element [z, y, x]
                        Value element = imgValue.invokeMember("item", z, y, x);
                        slice[y][x] = element.asFloat();
                    }
                }
                
                // Convert 2D array to 1D for FloatProcessor
                float[] sliceData = new float[nx * ny];
                for (int y = 0; y < ny; y++) {
                    for (int x = 0; x < nx; x++) {
                        sliceData[y * nx + x] = slice[y][x];
                    }
                }
                
                FloatProcessor fp = new FloatProcessor(nx, ny, sliceData);
                stack.addSlice("z=" + (z + 1), fp);
            }
            
            // Create ImagePlus
            ImagePlus imp = new ImagePlus(new File(fileName).getName(), stack);
            
            // Set calibration
            ij.measure.Calibration cal = imp.getCalibration();
            cal.pixelWidth = dx;
            cal.pixelHeight = dy;
            cal.pixelDepth = dz;
            cal.setUnit("um");
            
            // Add metadata
            imp.setProperty("Info", "Brillouin Shift Image\n" +
                    "Pixel size (x,y,z): " + dx + ", " + dy + ", " + dz + " um\n" +
                    "Dimensions (x,y,z): " + nx + ", " + ny + ", " + nz);
            
            return imp;
            
        } catch (Exception e) {
            IJ.error("BrimFile Reader", "Error in convertToImagePlus: " + e.getMessage());
            e.printStackTrace();
            return null;
        }
    }

    /**
     * Get the path to the brimfile Python package.
     * This method attempts to find the brimfile package using multiple strategies:
     * 1. Check BRIMFILE_PATH environment variable
     * 2. Check ImageJ preferences
     * 3. Look for brimfile in standard Python site-packages
     * 4. Look for the repository src/ directory
     * 
     * @return Path to the brimfile package source directory
     */
    private String getBrimfilePackagePath() {
        // Strategy 1: Check environment variable
        String envPath = System.getenv("BRIMFILE_PATH");
        if (envPath != null && new File(envPath).exists()) {
            IJ.log("Using brimfile from BRIMFILE_PATH: " + envPath);
            return envPath;
        }
        
        // Strategy 2: Check ImageJ preferences
        String prefPath = ij.Prefs.get("brimfile.path", null);
        if (prefPath != null && new File(prefPath).exists()) {
            IJ.log("Using brimfile from preferences: " + prefPath);
            return prefPath;
        }
        
        // Strategy 3: Try to use installed brimfile (let Python find it)
        // Return empty string to use default Python path
        try {
            Context testContext = Context.newBuilder("python")
                    .allowAllAccess(true)
                    .option("python.ForceImportSite", "false")
                    .build();
            testContext.eval("python", "import brimfile");
            testContext.close();
            IJ.log("Using brimfile from Python site-packages");
            return ""; // Empty string means use Python's default path
        } catch (Exception e) {
            // brimfile not in site-packages, continue to next strategy
        }
        
        // Strategy 4: Try to find the brimfile package in the repository structure
        String currentDir = System.getProperty("user.dir");
        File srcDir = new File(currentDir, "src");
        
        if (srcDir.exists() && new File(srcDir, "brimfile").exists()) {
            IJ.log("Using brimfile from repository: " + srcDir.getAbsolutePath());
            return srcDir.getAbsolutePath();
        }
        
        // Try parent directories (for when plugin is run from imagej-plugin directory)
        File parentDir = new File(currentDir).getParentFile();
        if (parentDir != null) {
            srcDir = new File(parentDir, "src");
            if (srcDir.exists() && new File(srcDir, "brimfile").exists()) {
                IJ.log("Using brimfile from repository (parent): " + srcDir.getAbsolutePath());
                return srcDir.getAbsolutePath();
            }
        }
        
        // Try two levels up
        if (parentDir != null) {
            File grandparentDir = parentDir.getParentFile();
            if (grandparentDir != null) {
                srcDir = new File(grandparentDir, "src");
                if (srcDir.exists() && new File(srcDir, "brimfile").exists()) {
                    IJ.log("Using brimfile from repository (grandparent): " + srcDir.getAbsolutePath());
                    return srcDir.getAbsolutePath();
                }
            }
        }
        
        // Default: return empty and let Python use its default path
        IJ.log("Using default Python path for brimfile");
        return "";
    }
}
