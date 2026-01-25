@echo off
REM Build script for BrimFile ImageJ Plugin (Windows)

echo ================================
echo BrimFile ImageJ Plugin Builder
echo ================================
echo.

REM Check if Maven is installed
where mvn >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Maven is not installed. Please install Maven 3.6.0 or later.
    exit /b 1
)

echo Maven version:
mvn -version | findstr "Apache Maven"
echo.

REM Navigate to the plugin directory
cd /d "%~dp0"

REM Clean and build
echo Cleaning previous builds...
call mvn clean

echo.
echo Building plugin...
call mvn package

echo.
echo ================================
echo Build completed successfully!
echo ================================
echo.
echo Plugin JAR: target\brimfile-imagej-plugin-1.0.0.jar
echo Dependencies: target\dependencies\
echo.
echo To install in ImageJ:
echo 1. Copy target\brimfile-imagej-plugin-1.0.0.jar to ^<ImageJ^>\plugins\
echo 2. Copy target\dependencies\*.jar to ^<ImageJ^>\jars\
echo 3. Restart ImageJ
echo.

pause
