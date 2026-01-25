# Contributing to BrimFile ImageJ Plugin

Thank you for your interest in contributing to the BrimFile ImageJ plugin! This document provides guidelines for contributing to the plugin.

## Ways to Contribute

- **Report bugs**: Open an issue describing the problem
- **Suggest features**: Open an issue with your feature request
- **Fix bugs**: Submit a pull request with your fix
- **Add features**: Submit a pull request with new functionality
- **Improve documentation**: Help make our docs better
- **Test**: Try the plugin and report your experience

## Development Setup

### Prerequisites

1. Java 11 or later
2. Maven 3.6.0 or later
3. GraalVM with Python support
4. ImageJ 1.54j or later (for testing)
5. Git

### Clone and Build

```bash
git clone https://github.com/prevedel-lab/brimfile.git
cd brimfile/imagej-plugin
mvn clean package
```

### Development Workflow

1. **Create a branch**: `git checkout -b feature/your-feature-name`
2. **Make changes**: Edit the code
3. **Test**: Build and test your changes
4. **Commit**: `git commit -m "Description of changes"`
5. **Push**: `git push origin feature/your-feature-name`
6. **Pull Request**: Open a PR on GitHub

## Code Style

### Java

- Follow standard Java naming conventions
- Use 4 spaces for indentation
- Add Javadoc comments for public methods
- Keep methods focused and concise
- Use meaningful variable names

Example:
```java
/**
 * Load a brim file and convert it to an ImageJ ImagePlus.
 * 
 * @param filePath Path to the brim file
 * @return ImagePlus containing the data
 */
private ImagePlus loadBrimFile(String filePath) {
    // Implementation
}
```

### Documentation

- Use clear, concise language
- Include examples where helpful
- Keep documentation up-to-date with code changes
- Use Markdown formatting consistently

## Testing

### Manual Testing

1. Build the plugin: `mvn package`
2. Copy to ImageJ: `cp target/*.jar ~/ImageJ/plugins/`
3. Copy dependencies: `cp target/dependencies/*.jar ~/ImageJ/jars/`
4. Restart ImageJ
5. Test functionality:
   - Open brim files
   - Test configuration dialog
   - Verify error handling
   - Check different file formats

### Test Checklist

- [ ] Plugin appears in correct menu
- [ ] File dialog opens correctly
- [ ] Files load successfully
- [ ] Images display correctly
- [ ] Calibration is preserved
- [ ] Configuration dialog works
- [ ] Error messages are helpful
- [ ] No memory leaks

## Submitting Issues

### Bug Reports

Include:
- Plugin version
- ImageJ version
- Java version
- GraalVM version
- Operating system
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages or logs
- Sample file (if possible)

### Feature Requests

Include:
- Clear description of the feature
- Use cases for the feature
- Expected behavior
- Mockups or examples (if applicable)

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** from `main`
3. **Make your changes**
4. **Test thoroughly**
5. **Update documentation** if needed
6. **Update CHANGELOG.md**
7. **Submit pull request**

### PR Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated
- [ ] Commit messages are clear
- [ ] No unnecessary files are included

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring

## Testing
How was this tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests pass
- [ ] Documentation updated
- [ ] CHANGELOG updated
```

## Project Structure

```
imagej-plugin/
├── src/
│   └── main/
│       ├── java/com/prevedel/brimfile/
│       │   ├── BrimFile_Reader.java      # Main plugin
│       │   └── BrimFile_Configure.java   # Configuration
│       └── resources/
│           └── plugins.config            # Plugin registration
├── pom.xml                               # Maven configuration
├── build.sh                              # Unix build script
├── build.bat                             # Windows build script
├── README.md                             # Main documentation
├── INSTALL.md                            # Installation guide
├── USAGE.md                              # Usage examples
├── QUICKSTART.md                         # Quick start guide
├── ARCHITECTURE.md                       # Architecture docs
├── CHANGELOG.md                          # Version history
└── CONTRIBUTING.md                       # This file
```

## Feature Development Guidelines

### Adding a New Feature

1. **Check existing issues**: Avoid duplicate work
2. **Open an issue**: Discuss the feature first
3. **Get feedback**: Make sure it fits the project goals
4. **Implement**: Follow coding standards
5. **Test**: Ensure it works as expected
6. **Document**: Update relevant docs
7. **Submit PR**: Include thorough description

### Example Features to Consider

- Support for selecting specific data groups
- Loading different quantities (linewidth, intensity)
- Displaying metadata in ImageJ
- Spectral plotting for selected pixels
- Batch processing multiple files
- Time-series support
- Multi-channel support

## Code Review Process

All contributions will be reviewed by maintainers. We look for:

- **Correctness**: Does it work as intended?
- **Quality**: Is the code well-written?
- **Testing**: Is it adequately tested?
- **Documentation**: Is it properly documented?
- **Style**: Does it follow conventions?
- **Impact**: Does it break existing functionality?

## Getting Help

- **Questions**: Open a discussion on GitHub
- **Bugs**: Open an issue with details
- **Features**: Open an issue with your proposal
- **Chat**: Contact the maintainers

## Recognition

Contributors will be acknowledged in:
- CHANGELOG.md
- Git commit history
- README.md (for significant contributions)

## License

By contributing, you agree that your contributions will be licensed under the LGPL-3.0-or-later license, the same as the brimfile package.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Help others learn
- Assume good intentions

## Thank You!

Every contribution, no matter how small, helps make this project better. Thank you for taking the time to contribute! 🙏
