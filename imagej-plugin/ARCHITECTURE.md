# Architecture Overview - BrimFile ImageJ Plugin

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Layer                           │
│  ┌──────────┐                                               │
│  │ ImageJ   │  File > Open > Brim File...                   │
│  │   UI     │  Plugins > BrimFile > Configure...            │
│  └────┬─────┘                                               │
└───────┼─────────────────────────────────────────────────────┘
        │
        │ User Actions
        ▼
┌─────────────────────────────────────────────────────────────┐
│                     Plugin Layer (Java)                      │
│  ┌──────────────────┐         ┌────────────────────┐        │
│  │ BrimFile_Reader  │         │ BrimFile_Configure │        │
│  │                  │         │                    │        │
│  │ - Open dialog    │         │ - Set paths        │        │
│  │ - Load file      │         │ - Save preferences │        │
│  │ - Convert data   │         └────────────────────┘        │
│  │ - Display image  │                                        │
│  └────┬─────────────┘                                        │
└───────┼─────────────────────────────────────────────────────┘
        │
        │ GraalPy Bridge
        ▼
┌─────────────────────────────────────────────────────────────┐
│              GraalVM Python (GraalPy)                        │
│  ┌──────────────────────────────────────────┐               │
│  │ Python Context                           │               │
│  │ - Initialize Python environment          │               │
│  │ - Import brimfile package                │               │
│  │ - Execute Python code from Java          │               │
│  └────┬─────────────────────────────────────┘               │
└───────┼─────────────────────────────────────────────────────┘
        │
        │ Python API Calls
        ▼
┌─────────────────────────────────────────────────────────────┐
│              brimfile Python Package                         │
│  ┌──────────────────────────────────────────┐               │
│  │ File.open(path)                          │               │
│  │ Data.get_data()                          │               │
│  │ AnalysisResults.get_image()              │               │
│  └────┬─────────────────────────────────────┘               │
└───────┼─────────────────────────────────────────────────────┘
        │
        │ Zarr API
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                             │
│  ┌──────────────┐          ┌──────────────┐                 │
│  │ .brim.zarr   │          │ .brim.zip    │                 │
│  │ (Directory)  │          │ (Archive)    │                 │
│  └──────────────┘          └──────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

## Component Diagram

```
ImageJ Application
├── Plugins
│   ├── BrimFile_Reader.class
│   │   ├── run()                    # Entry point
│   │   ├── loadBrimFile()           # Main loading logic
│   │   ├── convertToImagePlus()     # Data conversion
│   │   └── getBrimfilePackagePath() # Path detection
│   └── BrimFile_Configure.class
│       └── run()                    # Configuration dialog
├── Dependencies (jars/)
│   ├── polyglot-24.1.1.jar
│   ├── python-language-24.1.1.jar
│   ├── python-resources-24.1.1.jar
│   └── ... (22 more JARs)
└── Configuration
    └── IJ_Prefs.txt
        └── brimfile.path            # Stored path
```

## Data Flow

### Opening a Brim File

```
1. User Action
   └─> File > Open > Brim File...
       └─> OpenDialog shown
           └─> User selects file

2. Plugin Initialization
   └─> BrimFile_Reader.run()
       └─> Get file path
           └─> Initialize GraalPy Context

3. Python Setup
   └─> Create Python context
       └─> Configure sys.path
           └─> Import brimfile package

4. File Loading
   └─> Call Python: f = File(path)
       └─> Call Python: d = f.get_data()
           └─> Call Python: ar = d.get_analysis_results()
               └─> Call Python: img, px_size = ar.get_image()

5. Data Conversion
   └─> Extract numpy array shape
       └─> Loop through Z, Y, X dimensions
           └─> Convert to float[][]
               └─> Create FloatProcessor
                   └─> Add to ImageStack

6. Display
   └─> Create ImagePlus
       └─> Set calibration
           └─> Show in ImageJ
               └─> Close Python context
```

## Configuration Flow

```
1. Configuration Request
   └─> Plugins > BrimFile > Configure...
       └─> BrimFile_Configure.run()

2. Current Settings
   └─> Load from IJ_Prefs
       └─> Get current path

3. User Input
   └─> Show GenericDialog
       └─> User enters path

4. Validation
   └─> Check path exists
       └─> Check brimfile/ subdirectory
           └─> Warn if not found

5. Save
   └─> Store in IJ_Prefs
       └─> Confirm to user
```

## Path Detection Strategy

```
Priority 1: BRIMFILE_PATH environment variable
    └─> Check System.getenv("BRIMFILE_PATH")
        └─> If exists and valid → Use it

Priority 2: ImageJ Preferences
    └─> Check IJ_Prefs.get("brimfile.path")
        └─> If exists and valid → Use it

Priority 3: Python site-packages
    └─> Try: import brimfile
        └─> If successful → Use default Python path

Priority 4: Repository structure
    └─> Search current directory for src/
        └─> Search parent directory for src/
            └─> Search grandparent directory for src/
                └─> If found → Use it

Priority 5: Default
    └─> Return empty string
        └─> Let Python use its default path
```

## Technology Stack

```
┌─────────────────┐
│ ImageJ 1.54j+   │  UI and Image Processing
└────────┬────────┘
         │
┌────────▼────────┐
│  Java 11+       │  Plugin Implementation
└────────┬────────┘
         │
┌────────▼────────┐
│ GraalVM 24.1.1  │  Polyglot Runtime
└────────┬────────┘
         │
┌────────▼────────┐
│ GraalPy         │  Python Interpreter
└────────┬────────┘
         │
┌────────▼────────┐
│ brimfile 1.3.2+ │  Python Package
└────────┬────────┘
         │
┌────────▼────────┐
│ Zarr 3.1.1+     │  Storage Format
└─────────────────┘
```

## Key Design Decisions

### Why GraalPy?

1. **Native Integration**: Runs on JVM, no external Python required
2. **Performance**: JIT compilation for Python code
3. **Interoperability**: Seamless Java ↔ Python data exchange
4. **Deployment**: Single distribution includes Python runtime

### Why Direct brimfile Calls?

1. **Reusability**: Uses existing, well-tested Python code
2. **Maintenance**: Single codebase for Python and Java users
3. **Features**: Automatically get all brimfile updates
4. **Consistency**: Same behavior across platforms

### Why Multiple Path Strategies?

1. **Flexibility**: Works in various deployment scenarios
2. **User-Friendly**: Auto-detection reduces configuration
3. **Development**: Easy for developers to test
4. **Production**: Enterprise users can set system-wide paths

## Build System

```
Maven Project
├── pom.xml
│   ├── Dependencies
│   │   ├── ImageJ (provided)
│   │   └── GraalPy (runtime)
│   └── Plugins
│       ├── maven-compiler-plugin
│       ├── maven-jar-plugin
│       └── maven-dependency-plugin
└── Target Output
    ├── brimfile-imagej-plugin-1.0.0.jar
    └── dependencies/
        └── 25 JAR files
```

## Extension Points

Future enhancements could add:

1. **Multiple Data Groups**: Dialog to select which group to load
2. **Quantity Selection**: Choose shift, linewidth, intensity, etc.
3. **Peak Type Selection**: Stokes, anti-Stokes, or average
4. **Metadata Display**: Show brim file metadata in ImageJ
5. **Spectral Viewer**: Interactive spectral plotting
6. **Batch Processing**: Load multiple files at once
7. **Write Support**: Save modified data back to brim format

## Performance Considerations

- **Initial Load**: GraalPy context creation takes 2-5 seconds
- **Subsequent Loads**: Could reuse context for better performance
- **Memory**: Large files may require increasing ImageJ memory
- **Optimization**: Could implement lazy loading for large datasets
