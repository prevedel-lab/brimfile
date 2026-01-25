# BrimFile ImageJ Plugin

This ImageJ plugin allows you to open and visualize Brillouin microscopy data stored in brim files (`.brim.zarr` or `.brim.zip`) directly in ImageJ.

The plugin uses [GraalPy](https://www.graalvm.org/python/) to bridge Java and Python, allowing it to directly call the `brimfile` Python package from this repository.

## Features

- Open brim files directly in ImageJ
- Displays Brillouin shift images as ImageJ stacks
- Preserves spatial calibration (pixel sizes)
- Accessible from ImageJ's File > Open menu

## Requirements

- ImageJ 1.54j or later
- Java 11 or later
- GraalVM with Python support (GraalPy) or GraalVM Community Edition 24.1.1+

## Building the Plugin

### Prerequisites

1. Install Maven (3.6.0 or later)
2. Install GraalVM with Python support

### Build Steps

```bash
cd imagej-plugin
mvn clean package
```

This will create:
- `target/brimfile-imagej-plugin-1.0.0.jar` - The plugin JAR file
- `target/dependencies/` - Directory containing all required dependencies

## Installation

### Method 1: Manual Installation

1. Build the plugin as described above
2. Copy the following files to your ImageJ plugins directory:
   ```bash
   cp target/brimfile-imagej-plugin-1.0.0.jar <ImageJ_Directory>/plugins/
   cp target/dependencies/*.jar <ImageJ_Directory>/jars/
   ```
3. Restart ImageJ

### Method 2: Using ImageJ's Plugin Installer

1. Build the plugin
2. In ImageJ, go to `Plugins > Install...`
3. Select `target/brimfile-imagej-plugin-1.0.0.jar`
4. Restart ImageJ

### Method 3: Development Setup

For development, you can create a symbolic link:
```bash
ln -s $(pwd)/target/brimfile-imagej-plugin-1.0.0.jar <ImageJ_Directory>/plugins/
```

## Usage

### Opening a Brim File

1. Launch ImageJ
2. Go to `File > Open... > Brim File...`
3. Select a `.brim.zarr` directory or `.brim.zip` file
4. The Brillouin shift image will be displayed as an ImageJ stack

### What Gets Loaded

The plugin currently loads:
- The Brillouin shift image from the first data group
- The average of Stokes and anti-Stokes peaks
- Spatial calibration (pixel sizes in micrometers)

## Configuration

### Python Package Path

The plugin automatically tries to locate the `brimfile` Python package by searching:
1. `src/` directory in the current working directory
2. `src/` directory in the parent directory

If your brimfile package is installed in a different location, you may need to modify the `getBrimfilePackagePath()` method in `BrimFile_Reader.java`.

### GraalPy Configuration

The plugin uses the following GraalPy context options:
- `python.ForceImportSite=false` - Faster startup
- `python.Executable=graalpy` - Use GraalPy Python implementation
- `allowAllAccess=true` - Required for file I/O operations

## Architecture

The plugin works by:

1. **Initialization**: Creates a GraalPy context to run Python code
2. **Import**: Imports the `brimfile` Python package
3. **Loading**: Uses `brimfile.File` to open the brim file
4. **Extraction**: Extracts the Brillouin shift image using `get_image()`
5. **Conversion**: Converts the numpy array to ImageJ's ImageStack format
6. **Display**: Creates an ImagePlus and displays it in ImageJ

```
┌──────────────┐
│   ImageJ     │
│  (Java)      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  BrimFile    │
│   Plugin     │
└──────┬───────┘
       │
       │ GraalPy Bridge
       ▼
┌──────────────┐
│  brimfile    │
│  (Python)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  .brim.zarr  │
│    File      │
└──────────────┘
```

## Troubleshooting

### "Module brimfile not found"

- Ensure the brimfile package is accessible from the plugin
- Check that `sys.path` includes the directory containing the brimfile package
- Try setting the `PYTHONPATH` environment variable before starting ImageJ

### "No suitable image found"

- Ensure the brim file contains analysis results
- Check that the file has a Brillouin shift image available

### Performance Issues

- Loading large files may take some time
- The initial GraalPy context creation can take a few seconds
- Consider closing ImageJ and restarting if the plugin becomes unresponsive

## Development

### Project Structure

```
imagej-plugin/
├── pom.xml                                    # Maven build configuration
├── src/
│   └── main/
│       ├── java/
│       │   └── com/prevedel/brimfile/
│       │       └── BrimFile_Reader.java      # Main plugin class
│       └── resources/
│           └── plugins.config                 # Plugin menu configuration
└── README.md                                  # This file
```

### Adding Features

To extend the plugin:

1. **Multiple data groups**: Modify the code to show a dialog for selecting data groups
2. **Different quantities**: Add options to load linewidth, intensity, etc.
3. **Metadata display**: Show brim file metadata in ImageJ's info window
4. **Spectra viewing**: Add ability to display spectra for selected pixels

### Testing

To test the plugin during development:

1. Build the plugin: `mvn package`
2. Copy to ImageJ plugins directory
3. Restart ImageJ
4. Test with sample brim files

## License

This plugin is licensed under the same license as the brimfile package (LGPL-3.0-or-later).

## Contributing

Contributions are welcome! Please submit issues and pull requests to the [brimfile repository](https://github.com/prevedel-lab/brimfile).

## Authors

- Carlo Bevilacqua
- Sebastian Hambura

## See Also

- [BrimFile Python Package Documentation](https://prevedel-lab.github.io/brimfile/)
- [Brim File Format Specification](https://github.com/prevedel-lab/Brillouin-standard-file/blob/main/docs/brim_file_specs.md)
- [ImageJ Plugin Development](https://imagej.net/develop/ij1-plugins)
- [GraalPy Documentation](https://www.graalvm.org/python/)
