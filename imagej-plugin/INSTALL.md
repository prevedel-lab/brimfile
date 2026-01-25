# Installation Guide - BrimFile ImageJ Plugin

This guide provides detailed instructions for installing the BrimFile ImageJ plugin on different platforms.

## System Requirements

### Required Software
- **ImageJ**: Version 1.54j or later ([Download](https://imagej.net/downloads))
- **Java**: Version 11 or later ([Download](https://adoptium.net/))
- **GraalVM**: Community Edition 24.1.1 or later with Python support ([Download](https://www.graalvm.org/downloads/))

### Operating Systems
- Windows 10/11
- macOS 10.14 or later
- Linux (Ubuntu 20.04+, Fedora 34+, or equivalent)

### Hardware Requirements
- Minimum 4 GB RAM (8 GB recommended)
- 500 MB free disk space for dependencies
- Additional space for brim files

## Installation Steps

### Step 1: Install Prerequisites

#### Install Java 11+

**Windows:**
```bash
# Download and run the installer from https://adoptium.net/
# Verify installation:
java -version
```

**macOS:**
```bash
brew install openjdk@11
# Verify installation:
java -version
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install openjdk-11-jdk
# Verify installation:
java -version
```

#### Install GraalVM

**Windows:**
1. Download GraalVM from https://www.graalvm.org/downloads/
2. Extract to `C:\Program Files\GraalVM\`
3. Set environment variables:
   ```
   GRAALVM_HOME=C:\Program Files\GraalVM\graalvm-ce-java11-24.1.1
   PATH=%PATH%;%GRAALVM_HOME%\bin
   ```
4. Install Python component:
   ```bash
   gu install python
   ```

**macOS:**
```bash
# Download and extract GraalVM
cd ~/Downloads
tar -xzf graalvm-ce-java11-darwin-amd64-24.1.1.tar.gz
sudo mv graalvm-ce-java11-24.1.1 /Library/Java/JavaVirtualMachines/

# Set JAVA_HOME in ~/.zshrc or ~/.bash_profile
export GRAALVM_HOME=/Library/Java/JavaVirtualMachines/graalvm-ce-java11-24.1.1/Contents/Home
export PATH=$GRAALVM_HOME/bin:$PATH

# Install Python component
gu install python
```

**Linux:**
```bash
# Download and extract GraalVM
cd ~/Downloads
tar -xzf graalvm-ce-java11-linux-amd64-24.1.1.tar.gz
sudo mv graalvm-ce-java11-24.1.1 /usr/lib/jvm/

# Set JAVA_HOME in ~/.bashrc
export GRAALVM_HOME=/usr/lib/jvm/graalvm-ce-java11-24.1.1
export PATH=$GRAALVM_HOME/bin:$PATH

# Install Python component
gu install python
```

#### Install ImageJ

1. Download ImageJ from https://imagej.net/downloads
2. Extract/install to your preferred location
3. Launch ImageJ to verify installation

### Step 2: Build the Plugin

Clone the brimfile repository and build the plugin:

```bash
# Clone the repository
git clone https://github.com/prevedel-lab/brimfile.git
cd brimfile/imagej-plugin

# Build the plugin (Unix/Linux/macOS)
./build.sh

# Or on Windows
build.bat
```

The build process will:
1. Download all required dependencies
2. Compile the Java code
3. Package the plugin JAR
4. Copy dependencies to `target/dependencies/`

### Step 3: Install the Plugin in ImageJ

#### Option A: Manual Installation (Recommended)

**Windows:**
```bash
# Copy plugin JAR
copy target\brimfile-imagej-plugin-1.0.0.jar "%USERPROFILE%\ImageJ\plugins\"

# Copy dependencies
xcopy /E target\dependencies\*.jar "%USERPROFILE%\ImageJ\jars\"
```

**macOS/Linux:**
```bash
# Copy plugin JAR
cp target/brimfile-imagej-plugin-1.0.0.jar ~/ImageJ/plugins/

# Copy dependencies
cp target/dependencies/*.jar ~/ImageJ/jars/
```

#### Option B: Using ImageJ's Plugin Installer

1. In ImageJ, go to `Plugins > Install...`
2. Navigate to `brimfile/imagej-plugin/target/`
3. Select `brimfile-imagej-plugin-1.0.0.jar`
4. Click "Open"
5. **Important**: Manually copy dependencies:
   ```bash
   cp target/dependencies/*.jar ~/ImageJ/jars/
   ```

#### Option C: Development Installation (Symbolic Link)

For developers who want to test changes without copying files:

**Unix/Linux/macOS:**
```bash
ln -s $(pwd)/target/brimfile-imagej-plugin-1.0.0.jar ~/ImageJ/plugins/
ln -s $(pwd)/target/dependencies ~/ImageJ/jars/graalpy-deps
```

**Windows (as Administrator):**
```bash
mklink "%USERPROFILE%\ImageJ\plugins\brimfile-imagej-plugin-1.0.0.jar" "%CD%\target\brimfile-imagej-plugin-1.0.0.jar"
```

### Step 4: Configure Python Environment

The plugin needs access to the brimfile Python package. You have two options:

#### Option A: Use brimfile from Repository

If you're working from the cloned repository:

```bash
# No additional configuration needed!
# The plugin will automatically find the package in ../src/
```

#### Option B: Install brimfile via pip

If you want to use an installed version:

```bash
# Install brimfile in GraalPy environment
graalpy -m pip install brimfile

# Set PYTHONPATH (if needed)
export PYTHONPATH=/path/to/graalpy/site-packages
```

### Step 5: Verify Installation

1. **Restart ImageJ**
2. Check the menu: `File > Open...` should show "Brim File..." option
3. Open ImageJ's plugin list: `Plugins > Utilities > List PlugIns`
4. Look for "BrimFile_Reader" in the list

If the plugin appears, installation was successful!

## Troubleshooting Installation

### Plugin Not Appearing in Menu

**Problem**: Plugin menu item doesn't appear after installation.

**Solutions**:
1. Verify JAR is in correct location: `ImageJ/plugins/`
2. Check file permissions (should be readable)
3. Restart ImageJ completely
4. Check ImageJ console for error messages

### "Class not found" Error

**Problem**: ImageJ reports class not found when trying to load plugin.

**Solutions**:
1. Verify all dependency JARs are in `ImageJ/jars/`
2. Check that you copied all 25 dependency JARs
3. Re-run the build and copy process

### "Cannot initialize Python" Error

**Problem**: Plugin loads but fails to initialize GraalPy.

**Solutions**:
1. Verify GraalVM is properly installed: `java -version` should show GraalVM
2. Verify Python component is installed: `gu list` should show "python"
3. Check GRAALVM_HOME environment variable
4. Try reinstalling Python component: `gu install python --force`

### "Module brimfile not found" Error

**Problem**: Python initializes but cannot find brimfile package.

**Solutions**:
1. Install brimfile: `graalpy -m pip install brimfile`
2. Or ensure repository structure is correct (plugin should be in `brimfile/imagej-plugin/`)
3. Set PYTHONPATH if needed
4. Check Python can import brimfile: `graalpy -c "import brimfile; print(brimfile.__version__)"`

### Maven Build Fails

**Problem**: Build script fails with Maven errors.

**Solutions**:
1. Verify Maven is installed: `mvn -version`
2. Check internet connection (Maven downloads dependencies)
3. Clear Maven cache: `mvn clean` then retry
4. Try updating Maven: https://maven.apache.org/download.cgi

### Out of Memory During Build

**Problem**: Maven runs out of memory during compilation.

**Solutions**:
```bash
# Set Maven memory options
export MAVEN_OPTS="-Xmx2048m"
mvn clean package
```

## Platform-Specific Notes

### Windows

- Use Command Prompt or PowerShell as Administrator for installation
- Antivirus may interfere with JAR files - add exception if needed
- Path separators use backslash `\`

### macOS

- May need to allow JARs in System Preferences > Security & Privacy
- Use Terminal for command-line operations
- GraalVM may require manual security approval

### Linux

- Ensure ImageJ has proper permissions to load plugins
- Some distributions require `sudo` for installing to system directories
- Consider using AppImage or Flatpak version of ImageJ

## Uninstallation

To remove the plugin:

1. Delete plugin JAR: `rm ~/ImageJ/plugins/brimfile-imagej-plugin-1.0.0.jar`
2. Delete dependencies: `rm ~/ImageJ/jars/{graalpy-related-jars}`
3. Restart ImageJ

## Updating the Plugin

To update to a newer version:

1. Pull latest changes: `git pull origin main`
2. Rebuild: `./build.sh` or `build.bat`
3. Replace old JAR in ImageJ plugins directory
4. Update dependencies if they changed
5. Restart ImageJ

## Getting Help

If installation issues persist:

1. Check the [main README](README.md) troubleshooting section
2. Review [ImageJ documentation](https://imagej.net/learn/)
3. Check [GraalVM documentation](https://www.graalvm.org/docs/)
4. Open an issue on [GitHub](https://github.com/prevedel-lab/brimfile/issues)

When reporting issues, include:
- Your operating system and version
- Java version (`java -version`)
- ImageJ version
- GraalVM version
- Complete error messages
- Steps you've already tried
