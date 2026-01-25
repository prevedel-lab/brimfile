package com.prevedel.brimfile;

import ij.IJ;
import ij.gui.GenericDialog;
import ij.plugin.PlugIn;

import java.io.File;

/**
 * Configuration plugin for setting the brimfile package path.
 * This allows users to specify where the brimfile Python package is located.
 * 
 * @author Carlo Bevilacqua, Sebastian Hambura
 * @version 1.0.0
 */
public class BrimFile_Configure implements PlugIn {

    @Override
    public void run(String arg) {
        // Get current path from preferences
        String currentPath = ij.Prefs.get("brimfile.path", "");
        
        // Create configuration dialog
        GenericDialog gd = new GenericDialog("BrimFile Configuration");
        gd.addMessage("Configure the path to the brimfile Python package.");
        gd.addMessage("Leave empty to use Python's default search path.");
        gd.addMessage(" ");
        gd.addStringField("BrimFile Path:", currentPath, 50);
        gd.addMessage(" ");
        gd.addMessage("You can also set the BRIMFILE_PATH environment variable.");
        gd.addMessage(" ");
        gd.addHelp("https://github.com/prevedel-lab/brimfile/tree/main/imagej-plugin");
        
        gd.showDialog();
        
        if (gd.wasCanceled()) {
            return;
        }
        
        // Get the new path
        String newPath = gd.getNextString().trim();
        
        // Validate the path if not empty
        if (!newPath.isEmpty()) {
            File pathFile = new File(newPath);
            if (!pathFile.exists()) {
                IJ.error("BrimFile Configuration", 
                        "The specified path does not exist:\n" + newPath);
                return;
            }
            
            // Check if brimfile package exists in the path
            File brimfileDir = new File(pathFile, "brimfile");
            if (!brimfileDir.exists()) {
                boolean result = IJ.showMessageWithCancel("BrimFile Configuration",
                        "Warning: The directory 'brimfile' was not found in:\n" + 
                        newPath + "\n\n" +
                        "This path may not contain the brimfile package.\n" +
                        "Do you want to save it anyway?");
                if (!result) {
                    return;
                }
            }
        }
        
        // Save to preferences
        if (newPath.isEmpty()) {
            ij.Prefs.set("brimfile.path", null);
            IJ.showMessage("BrimFile Configuration", 
                    "Configuration cleared.\n" +
                    "The plugin will use Python's default search path.");
        } else {
            ij.Prefs.set("brimfile.path", newPath);
            IJ.showMessage("BrimFile Configuration", 
                    "BrimFile path saved:\n" + newPath + "\n\n" +
                    "The new path will be used the next time you open a brim file.");
        }
    }
}
