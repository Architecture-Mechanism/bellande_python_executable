"""
Dependency analyzer for PyPack
Analyzes Python files to find all imports and dependencies
"""

from header_imports import *

class DependencyAnalyzer:
    """Analyzes Python files to find dependencies"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.analyzed_files = set()
        self.dependencies = set()
        self.import_graph = {}
    
    def analyze(self) -> Dict[str, Set[str]]:
        """Analyze the main script and return all dependencies"""
        self.logger.debug("Starting dependency analysis")
        
        # Start with the main script
        self._analyze_file(self.config.script_path)
        
        # Add explicitly included modules
        for module in self.config.include_modules:
            self._add_module_dependency(module)
        
        # Remove excluded modules
        for module in self.config.exclude_modules:
            self.dependencies.discard(module)
        
        # Categorize dependencies
        result = {
            'builtin': set(),
            'stdlib': set(),
            'third_party': set(),
            'local': set()
        }
        
        for dep in self.dependencies:
            if is_builtin_module(dep):
                result['builtin'].add(dep)
            elif is_stdlib_module(dep):
                result['stdlib'].add(dep)
            elif self._is_local_module(dep):
                result['local'].add(dep)
            else:
                result['third_party'].add(dep)
        
        self.logger.debug(f"Found {len(self.dependencies)} dependencies")
        self.logger.debug(f"Builtin: {len(result['builtin'])}")
        self.logger.debug(f"Stdlib: {len(result['stdlib'])}")
        self.logger.debug(f"Third-party: {len(result['third_party'])}")
        self.logger.debug(f"Local: {len(result['local'])}")
        
        return result
    
    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file"""
        if file_path in self.analyzed_files:
            return
        
        self.analyzed_files.add(file_path)
        self.logger.debug(f"Analyzing {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                self.logger.warning(f"Could not read {file_path}: {e}")
                return
        
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            self.logger.warning(f"Syntax error in {file_path}: {e}")
            return
        
        # Find all imports
        imports = self._extract_imports(tree)
        
        # Add to dependencies
        for imp in imports:
            self.dependencies.add(imp)
            self._add_module_dependency(imp)
        
        # Find local imports and analyze them
        for imp in imports:
            if self._is_local_module(imp):
                local_path = self._find_local_module_path(imp, file_path.parent)
                if local_path:
                    self._analyze_file(local_path)
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements from AST"""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split('.')[0])
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split('.')[0])
                else:
                    # Relative import
                    imports.append('.')
        
        return imports
    
    def _add_module_dependency(self, module_name: str):
        """Add a module and its dependencies"""
        if module_name in ['', '.']:
            return
        
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                self.logger.warning(f"Module not found: {module_name}")
                return
            
            # If it's a package, try to find submodules
            if spec.submodule_search_locations:
                self._find_package_modules(module_name, spec.submodule_search_locations)
            
        except ImportError as e:
            self.logger.warning(f"Could not import {module_name}: {e}")
    
    def _find_package_modules(self, package_name: str, search_paths: List[str]):
        """Find modules in a package"""
        for search_path in search_paths:
            path = Path(search_path)
            if path.exists():
                for py_file in path.glob('*.py'):
                    if py_file.name != '__init__.py':
                        module_name = f"{package_name}.{py_file.stem}"
                        self.dependencies.add(module_name)
    
    def _is_local_module(self, module_name: str) -> bool:
        """Check if a module is local to the project"""
        if module_name in ['', '.']:
            return False
        
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None or spec.origin is None:
                return False
            
            # Check if the module is in the project directory
            project_dir = self.config.script_path.parent
            module_path = Path(spec.origin)
            
            try:
                module_path.relative_to(project_dir)
                return True
            except ValueError:
                return False
        
        except ImportError:
            return False
    
    def _find_local_module_path(self, module_name: str, base_path: Path) -> Optional[Path]:
        """Find the path to a local module"""
        # Try direct .py file
        py_file = base_path / f"{module_name}.py"
        if py_file.exists():
            return py_file
        
        # Try package directory
        package_dir = base_path / module_name
        if package_dir.is_dir():
            init_file = package_dir / "__init__.py"
            if init_file.exists():
                return init_file
        
        # Try searching in parent directories
        parent = base_path.parent
        if parent != base_path:  # Not at root
            return self._find_local_module_path(module_name, parent)
        
        return None

class ImportVisitor(ast.NodeVisitor):
    """AST visitor to find imports"""
    
    def __init__(self):
        self.imports = []
    
    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)
