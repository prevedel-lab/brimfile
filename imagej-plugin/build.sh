#!/bin/bash
# Build script for BrimFile ImageJ Plugin

set -e

echo "================================"
echo "BrimFile ImageJ Plugin Builder"
echo "================================"
echo ""

# Check if Maven is installed
if ! command -v mvn &> /dev/null; then
    echo "Error: Maven is not installed. Please install Maven 3.6.0 or later."
    exit 1
fi

echo "Maven version:"
mvn -version | head -1
echo ""

# Navigate to the plugin directory
cd "$(dirname "$0")"

# Clean and build
echo "Cleaning previous builds..."
mvn clean

echo ""
echo "Building plugin..."
mvn package

echo ""
echo "================================"
echo "Build completed successfully!"
echo "================================"
echo ""
echo "Plugin JAR: target/brimfile-imagej-plugin-1.0.0.jar"
echo "Dependencies: target/dependencies/"
echo ""
echo "To install in ImageJ:"
echo "1. Copy target/brimfile-imagej-plugin-1.0.0.jar to <ImageJ>/plugins/"
echo "2. Copy target/dependencies/*.jar to <ImageJ>/jars/"
echo "3. Restart ImageJ"
echo ""
