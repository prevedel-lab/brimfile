# Quick Start Guide - BrimFile ImageJ Plugin

This is a 5-minute quick start guide to get the BrimFile ImageJ plugin up and running.

## Prerequisites Check

Before starting, verify you have:

```bash
# Check Java version (need 11+)
java -version

# Check Maven (for building)
mvn -version

# Check GraalVM with Python
gu list | grep python
```

If any are missing, see the full [Installation Guide](INSTALL.md).

## Quick Installation

### 1. Build the Plugin

```bash
# Clone the repository
git clone https://github.com/prevedel-lab/brimfile.git
cd brimfile/imagej-plugin

# Build (choose your platform)
./build.sh      # Unix/Linux/macOS
build.bat       # Windows
```

### 2. Install in ImageJ

```bash
# Copy plugin and dependencies to ImageJ
cp target/brimfile-imagej-plugin-1.0.0.jar ~/ImageJ/plugins/
cp target/dependencies/*.jar ~/ImageJ/jars/

# On Windows:
# copy target\brimfile-imagej-plugin-1.0.0.jar %USERPROFILE%\ImageJ\plugins\
# xcopy /E target\dependencies\*.jar %USERPROFILE%\ImageJ\jars\
```

### 3. Configure (if needed)

If brimfile is not installed via pip, configure the path:

**Option A: Using Environment Variable**
```bash
export BRIMFILE_PATH=/path/to/brimfile/src
ImageJ
```

**Option B: Using Configuration Dialog**
1. Launch ImageJ
2. Go to `Plugins > BrimFile > Configure...`
3. Enter path to brimfile package
4. Click OK

## Quick Usage

1. **Launch ImageJ** (restart if it was already running)
2. **Open a brim file**: `File > Open... > Brim File...`
3. **Select your file**: Choose a `.brim.zarr` directory or `.brim.zip` file
4. **View the results**: The Brillouin shift image will open in ImageJ

## What's Next?

- Read the [detailed documentation](README.md)
- Check out [usage examples](USAGE.md)
- See [troubleshooting tips](README.md#troubleshooting)

## Common Issues

### "Plugin not found"
→ Restart ImageJ after copying the JAR files

### "Cannot find brimfile module"
→ Configure the path using `Plugins > BrimFile > Configure...`

### Build fails
→ Check Maven and Java versions, ensure internet connection

## Getting Help

- Full documentation: [README.md](README.md)
- Installation guide: [INSTALL.md](INSTALL.md)
- Usage examples: [USAGE.md](USAGE.md)
- Report issues: [GitHub Issues](https://github.com/prevedel-lab/brimfile/issues)

## Summary

That's it! In just a few commands:
1. ✓ Built the plugin with Maven
2. ✓ Copied files to ImageJ
3. ✓ Configured Python path (if needed)
4. ✓ Ready to open brim files in ImageJ

Enjoy using the BrimFile ImageJ plugin! 🎉
