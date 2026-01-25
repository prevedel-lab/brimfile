# Changelog - BrimFile ImageJ Plugin

All notable changes to the BrimFile ImageJ plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-25

### Added
- Initial release of BrimFile ImageJ plugin
- Support for reading `.brim.zarr` and `.brim.zip` files
- Integration with GraalPy for Python-Java bridge
- Direct calling of brimfile Python package from Java
- Automatic loading of Brillouin shift images
- Preservation of spatial calibration (pixel sizes)
- Support for 3D image stacks
- File menu integration (`File > Open... > Brim File...`)
- Progress indicators during file loading
- Comprehensive documentation (README, USAGE examples)
- Build scripts for Unix/Linux (build.sh) and Windows (build.bat)
- Maven-based build system
- Dependency management with automatic JAR copying

### Technical Details
- Java 11 compatibility
- GraalVM 24.1.1 integration
- ImageJ 1.54j API compatibility
- Support for first data group in brim files
- Loads average of Stokes and anti-Stokes peaks
- Converts numpy arrays to ImageJ ImageStack format

### Known Limitations
- Only loads the first data group in multi-group files
- Only loads Brillouin shift (not linewidth, intensity, etc.)
- Only loads average peak type (not individual Stokes/anti-Stokes)
- Requires GraalVM Python environment to be properly configured
- Initial context creation can take a few seconds

## Future Enhancements

### Planned for 1.1.0
- [ ] Support for selecting specific data groups
- [ ] Option to load different quantities (linewidth, intensity)
- [ ] Option to select peak type (Stokes, anti-Stokes, average)
- [ ] Display of metadata in ImageJ info window
- [ ] Improved error messages and diagnostics

### Planned for 1.2.0
- [ ] Support for viewing spectra at selected pixels
- [ ] Interactive spectral plotting
- [ ] Batch processing improvements
- [ ] Performance optimizations for large files

### Planned for 2.0.0
- [ ] Support for writing/modifying brim files from ImageJ
- [ ] Integration with ImageJ2/Fiji
- [ ] Custom analysis tools for Brillouin data
- [ ] Multi-channel support
- [ ] Time-series support

## Changelog Notes

### Version Numbering
- Major version: Breaking changes or significant new features
- Minor version: New features, backwards compatible
- Patch version: Bug fixes, backwards compatible

### Contributing
To contribute to the plugin:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request
6. Update this changelog with your changes

### Reporting Issues
Please report bugs and feature requests on the [GitHub Issues page](https://github.com/prevedel-lab/brimfile/issues).

When reporting issues, please include:
- Plugin version
- ImageJ version
- Java version
- GraalVM version
- Operating system
- Sample brim file (if possible)
- Steps to reproduce
- Error messages or logs
