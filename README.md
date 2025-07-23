# Bellande Python Executable

bellande_python_executable is a Python tool that converts Python scripts into standalone executables, similar to PyInstaller but with a simpler architecture and focus on multi-platform operations.

## Features

- Convert Python scripts to native executables
- Automatic dependency analysis
- Support for standard library, third-party, and local modules
- Single-file executable output
- Cross-platform support (Linux, Windows, macOS)
- No external dependencies required
- Debug mode for troubleshooting

## Installation

```bash
git clone <repository-url>
cd bellande_python_executable
pip install -e .
```

## Requirements

- Python 3.7 or higher
- C compiler (GCC on Linux/macOS, MSVC or GCC on Windows)
- Python development headers

### Installing Requirements on Linux

```bash
# Ubuntu/Debian
sudo apt-get install python3-dev gcc

# CentOS/RHEL/Fedora
sudo dnf install python3-devel gcc

# Or for older versions
sudo yum install python3-devel gcc
```

### Installing Requirements on Windows

- Install Visual Studio Build Tools or Visual Studio Community
- Or install GCC via MinGW-w64

### Installing Requirements on macOS

```bash
xcode-select --install
```

## Usage

### Basic Usage

```bash
bellande_python_executable script.py
```

This will create an executable named `script` (or `script.exe` on Windows) in the `dist/` directory.

### Advanced Usage

```bash
bellande_python_executable script.py \
    --output myapp \
    --onefile \
    --exclude tkinter \
    --include requests \
    --add-data "data.txt:." \
    --debug
```

### Command Line Options

- `--script` - Python script to convert (required)
- `--output` - Output executable name
- `--name` - Name of the executable
- `--onefile` - Create a single executable file (default)
- `--windowed` - Create windowed application (no console)
- `--debug` - Enable debug mode
- `--exclude` - Exclude modules (can be used multiple times)
- `--include` - Include additional modules (can be used multiple times)
- `--add-data` - Add data files in format `src:dest` (can be used multiple times)

## Examples

### Simple Script

```python
# hello.py
print("Hello, World!")
```

```bash
bellande_python_executable hello.py
./dist/hello
```

### Script with Dependencies

```python
# web_scraper.py
import requests
from bs4 import BeautifulSoup

def main():
    response = requests.get("https://httpbin.org/json")
    print(response.json())

if __name__ == "__main__":
    main()
```

```bash
bellande_python_executable --script web_scraper.py --include requests --include bs4
./dist/web_scraper
```

### Script with Data Files

```python
# config_app.py
import json

def main():
    with open("config.json", "r") as f:
        config = json.load(f)
    print(f"App name: {config['name']}")

if __name__ == "__main__":
    main()
```

```bash
bellande_python_executable --script-file config_app.py --add-data "config.json:."
./dist/config_app
```

## Architecture

bellande_python_executable consists of several modules:

1. **main.py** - Entry point and command-line interface
2. **analyzer.py** - Dependency analysis using AST parsing
3. **collector.py** - Code and resource collection
4. **compiler.py** - Bytecode compilation and archiving
5. **builder.py** - Executable generation with C bootstrap
6. **utils.py** - Utility functions and configuration management

### Build Process

1. **Analysis Phase** - Analyze the main script and discover all dependencies
2. **Collection Phase** - Gather all required Python files and resources
3. **Compilation Phase** - Compile Python source to bytecode and create archives
4. **Building Phase** - Generate C bootstrap code and compile to executable

## How It Works

bellande_python_executable creates a C executable that:

1. Embeds Python bytecode and resources as binary data
2. Initializes the Python interpreter at runtime
3. Loads and executes the embedded bytecode
4. Provides a custom import system for bundled modules

The generated executable is completely self-contained and doesn't require Python to be installed on the target system.

## Troubleshooting

### Common Issues

1. **Missing Python headers**
   ```
   error: Python.h: No such file or directory
   ```
   Solution: Install Python development packages (python3-dev on Ubuntu)

2. **Compiler not found**
   ```
   gcc: command not found
   ```
   Solution: Install GCC or appropriate C compiler

3. **Import errors in generated executable**
   ```
   ModuleNotFoundError: No module named 'xyz'
   ```
   Solution: Use `--include xyz` to explicitly include the module

### Debug Mode

Use `--debug` flag to enable verbose logging:

```bash
bellande_python_executable script.py --debug
```

This will show detailed information about:
- Discovered dependencies
- Collected files
- Compilation process
- Build steps

## Limitations

- Requires C compiler on build system
- Some dynamic imports may not be detected automatically
- Binary size may be large due to embedded Python runtime
- Limited support for Python extensions that require specific loading mechanisms

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Comparison with PyInstaller

| Feature | bellande_python_executable | PyInstaller |
|---------|----------|-------------|
| Dependencies | None | Multiple |
| Build system | Simple C bootstrap | Complex bundling |
| Size | Moderate | Smaller |
| Compatibility | Good | Excellent |
| Customization | High | Moderate |
| Learning curve | Low | Moderate |

bellande_python_executable is designed to be a simpler, more transparent alternative to PyInstaller with fewer dependencies and easier customization.
