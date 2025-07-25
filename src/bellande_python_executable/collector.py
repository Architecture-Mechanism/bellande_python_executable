"""
Code collector for PyPack
Gathers all Python source files and modules needed for the executable
"""

from header_imports import *

class CodeCollector:
    """Collects all necessary Python files and resources"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.collected_files = {}
        self.python_paths = get_python_paths()
    
    def collect(self, dependencies: Dict[str, Set[str]]) -> Dict[str, List[Path]]:
        """Collect all necessary files"""
        self.logger.debug("Starting code collection")
        
        result = {
            'main_script': [],
            'stdlib_modules': [],
            'third_party_modules': [],
            'local_modules': [],
            'data_files': [],
            'python_dll': None
        }
        
        # Collect main script
        result['main_script'] = [self.config.script_path]
        
        # Collect standard library modules
        for module in dependencies['stdlib']:
            files = self._collect_stdlib_module(module)
            result['stdlib_modules'].extend(files)
        
        # Collect third-party modules
        for module in dependencies['third_party']:
            files = self._collect_third_party_module(module)
            result['third_party_modules'].extend(files)
        
        # Collect local modules
        for module in dependencies['local']:
            files = self._collect_local_module(module)
            result['local_modules'].extend(files)
        
        # Collect additional data files
        for data_spec in self.config.add_data:
            files = self._collect_data_files(data_spec)
            result['data_files'].extend(files)
        
        # Find Python DLL/SO
        from utils import find_python_dll
        python_dll = find_python_dll()
        if python_dll:
            result['python_dll'] = python_dll
        else:
            self.logger.warning("Could not find Python DLL/SO - executable may not work")
        
        self.logger.debug(f"Collected {sum(len(v) for v in result.values() if isinstance(v, list))} files")
        
        return result
    
    def _collect_stdlib_module(self, module_name: str) -> List[Path]:
        """Collect standard library module files"""
        files = []
        
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                self.logger.warning(f"Standard library module not found: {module_name}")
                return files
            
            if spec.origin:
                # Single file module
                files.append(Path(spec.origin))
            elif spec.submodule_search_locations:
                # Package
                for location in spec.submodule_search_locations:
                    path = Path(location)
                    if path.exists():
                        files.extend(self._collect_package_files(path))
        
        except ImportError as e:
            self.logger.warning(f"Could not collect stdlib module {module_name}: {e}")
        
        return files
    
    def _collect_third_party_module(self, module_name: str) -> List[Path]:
        """Collect third-party module files"""
        files = []
        
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                self.logger.warning(f"Third-party module not found: {module_name}")
                return files
            
            if spec.origin:
                # Single file module
                files.append(Path(spec.origin))
                
                # Also collect any related files (e.g., .so files)
                module_dir = Path(spec.origin).parent
                module_stem = Path(spec.origin).stem
                
                # Look for compiled extensions
                for ext in ['.so', '.pyd', '.dll']:
                    ext_file = module_dir / f"{module_stem}{ext}"
                    if ext_file.exists():
                        files.append(ext_file)
            
            elif spec.submodule_search_locations:
                # Package
                for location in spec.submodule_search_locations:
                    path = Path(location)
                    if path.exists():
                        files.extend(self._collect_package_files(path))
        
        except ImportError as e:
            self.logger.warning(f"Could not collect third-party module {module_name}: {e}")
        
        return files
    
    def _collect_local_module(self, module_name: str) -> List[Path]:
        """Collect local module files"""
        files = []
        
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                self.logger.warning(f"Local module not found: {module_name}")
                return files
            
            if spec.origin:
                files.append(Path(spec.origin))
            elif spec.submodule_search_locations:
                for location in spec.submodule_search_locations:
                    path = Path(location)
                    if path.exists():
                        files.extend(self._collect_package_files(path))
        
        except ImportError as e:
            self.logger.warning(f"Could not collect local module {module_name}: {e}")
        
        return files
    
    def _collect_package_files(self, package_path: Path) -> List[Path]:
        """Collect all files in a package directory"""
        files = []
        
        for item in package_path.rglob('*'):
            if item.is_file():
                # Include Python files
                if item.suffix in ['.py', '.pyx']:
                    files.append(item)
                # Include compiled extensions
                elif item.suffix in ['.so', '.pyd', '.dll']:
                    files.append(item)
                # Include data files in packages
                elif item.suffix in ['.txt', '.json', '.xml', '.yaml', '.yml', '.cfg', '.ini']:
                    files.append(item)
        
        return files
    
    def _collect_data_files(self, data_spec: str) -> List[Path]:
        """Collect data files specified by user"""
        files = []
        
        if ':' in data_spec:
            src, dest = data_spec.split(':', 1)
        else:
            src = data_spec
            dest = None
        
        src_path = Path(src)
        
        if src_path.is_file():
            files.append(src_path)
        elif src_path.is_dir():
            files.extend(src_path.rglob('*'))
        else:
            self.logger.warning(f"Data file not found: {src}")
        
        return files
    
    def copy_to_work_dir(self, collected_files: Dict[str, List[Path]]) -> Dict[str, List[Path]]:
        """Copy collected files to work directory"""
        self.logger.debug("Copying files to work directory")
        
        result = {}
        
        for category, files in collected_files.items():
            if category == 'python_dll':
                # Special handling for Python DLL
                if files:
                    dll_dest = self.config.get_work_path(files.name)
                    shutil.copy2(files, dll_dest)
                    result[category] = dll_dest
                continue
            
            result[category] = []
            
            for file_path in files:
                if not isinstance(file_path, Path):
                    continue
                
                # Determine destination path
                if category == 'main_script':
                    dest_path = self.config.get_work_path(file_path.name)
                elif category == 'local_modules':
                    # Preserve relative structure for local modules
                    try:
                        rel_path = file_path.relative_to(self.config.script_path.parent)
                        dest_path = self.config.get_work_path('local', rel_path)
                    except ValueError:
                        dest_path = self.config.get_work_path('local', file_path.name)
                else:
                    # For stdlib and third-party, preserve the package structure
                    dest_path = self.config.get_work_path(category, file_path.name)
                
                # Create destination directory
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                try:
                    shutil.copy2(file_path, dest_path)
                    result[category].append(dest_path)
                except Exception as e:
                    self.logger.warning(f"Could not copy {file_path}: {e}")
        
        return result
