"""
Utility classes and functions for PyPack
"""

from header_imports import *

class Logger:
    """Simple logging utility"""
    
    def __init__(self, debug=False):
        self.debug_mode = debug
    
    def info(self, message):
        print(f"[INFO] {message}")
    
    def warning(self, message):
        print(f"[WARNING] {message}")
    
    def error(self, message):
        print(f"[ERROR] {message}")
    
    def debug(self, message):
        if self.debug_mode:
            print(f"[DEBUG] {message}")

@dataclass
class ConfigManager:
    """Configuration manager for build settings"""
    script_path: Path
    output_name: str
    onefile: bool = True
    windowed: bool = False
    debug: bool = False
    exclude_modules: List[str] = None
    include_modules: List[str] = None
    add_data: List[str] = None
    
    def __post_init__(self):
        if self.exclude_modules is None:
            self.exclude_modules = []
        if self.include_modules is None:
            self.include_modules = []
        if self.add_data is None:
            self.add_data = []
        
        # Create work directory
        self.work_dir = Path(f"build_{self.output_name}_{int(time.time())}")
        self.work_dir.mkdir(exist_ok=True)
        
        # Output directory
        self.output_dir = Path("dist")
        self.output_dir.mkdir(exist_ok=True)
    
    def get_work_path(self, *args):
        """Get path relative to work directory"""
        return self.work_dir / Path(*args)
    
    def get_output_path(self, *args):
        """Get path relative to output directory"""
        return self.output_dir / Path(*args)

def get_python_paths():
    """Get Python installation paths"""
    import sysconfig
    
    paths = {
        'executable': sys.executable,
        'stdlib': sysconfig.get_path('stdlib'),
        'platstdlib': sysconfig.get_path('platstdlib'),
        'purelib': sysconfig.get_path('purelib'),
        'platlib': sysconfig.get_path('platlib'),
        'include': sysconfig.get_path('include'),
        'data': sysconfig.get_path('data'),
    }
    
    return paths

def get_platform_info():
    """Get platform-specific information"""
    import platform
    
    return {
        'system': platform.system().lower(),
        'machine': platform.machine().lower(),
        'architecture': platform.architecture()[0],
        'python_version': platform.python_version(),
    }

def find_python_dll():
    """Find Python DLL/SO file"""
    import sysconfig
    
    platform_info = get_platform_info()
    
    if platform_info['system'] == 'windows':
        # Windows: look for pythonXX.dll
        version = sys.version_info
        dll_name = f"python{version.major}{version.minor}.dll"
        
        # Check common locations
        locations = [
            Path(sys.executable).parent / dll_name,
            Path(sys.executable).parent / "DLLs" / dll_name,
            Path(sysconfig.get_path('stdlib')) / dll_name,
        ]
        
        for location in locations:
            if location.exists():
                return location
    
    elif platform_info['system'] == 'linux':
        # Linux: look for libpythonX.Y.so
        version = sys.version_info
        so_name = f"libpython{version.major}.{version.minor}.so"
        
        # Check common locations
        locations = [
            Path(f"/usr/lib/x86_64-linux-gnu/{so_name}"),
            Path(f"/usr/lib/{so_name}"),
            Path(f"/usr/local/lib/{so_name}"),
            Path(sysconfig.get_path('stdlib')) / ".." / "lib" / so_name,
        ]
        
        for location in locations:
            if location.exists():
                return location
                
        # Try to find any libpython*.so
        import glob
        for pattern in ["/usr/lib/*/libpython*.so*", "/usr/local/lib/libpython*.so*"]:
            matches = glob.glob(pattern)
            if matches:
                return Path(matches[0])
    
    elif platform_info['system'] == 'darwin':
        # macOS: look for libpythonX.Y.dylib
        version = sys.version_info
        dylib_name = f"libpython{version.major}.{version.minor}.dylib"
        
        locations = [
            Path(f"/usr/local/lib/{dylib_name}"),
            Path(f"/opt/homebrew/lib/{dylib_name}"),
            Path(sysconfig.get_path('stdlib')) / ".." / "lib" / dylib_name,
        ]
        
        for location in locations:
            if location.exists():
                return location
    
    return None

def is_builtin_module(module_name):
    """Check if a module is a built-in module"""
    return module_name in sys.builtin_module_names

def is_stdlib_module(module_name):
    """Check if a module is part of the standard library"""
    import importlib.util
    
    if is_builtin_module(module_name):
        return True
    
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False
        
        if spec.origin is None:
            return True  # namespace package, likely stdlib
        
        # Check if the module is in the standard library path
        stdlib_path = Path(get_python_paths()['stdlib'])
        platstdlib_path = Path(get_python_paths()['platstdlib'])
        
        module_path = Path(spec.origin)
        
        try:
            module_path.relative_to(stdlib_path)
            return True
        except ValueError:
            pass
        
        try:
            module_path.relative_to(platstdlib_path)
            return True
        except ValueError:
            pass
        
        return False
    except ImportError:
        return False

def create_temp_file(content, suffix=".c"):
    """Create a temporary file with content"""
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
        f.write(content)
        return f.name
