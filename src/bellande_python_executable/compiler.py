"""
Bytecode compiler for PyPack
Compiles Python source files to bytecode for distribution
"""

from header_imports import *

class BytecodeCompiler:
    """Compiles Python source files to bytecode"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
    
    def compile(self, collected_files: Dict[str, List[Path]]) -> Dict[str, Path]:
        """Compile all Python files to bytecode and create archives"""
        self.logger.debug("Starting bytecode compilation")
        
        result = {}
        
        # Compile main script
        if collected_files['main_script']:
            main_script = collected_files['main_script'][0]
            compiled_main = self._compile_single_file(main_script)
            result['main_script'] = compiled_main
        
        # Create archives for different categories
        for category in ['stdlib_modules', 'third_party_modules', 'local_modules']:
            if collected_files[category]:
                archive_path = self._create_module_archive(category, collected_files[category])
                result[category] = archive_path
        
        # Handle data files
        if collected_files['data_files']:
            data_archive = self._create_data_archive(collected_files['data_files'])
            result['data_files'] = data_archive
        
        # Copy Python DLL
        if collected_files.get('python_dll'):
            result['python_dll'] = collected_files['python_dll']
        
        return result
    
    def _compile_single_file(self, source_path: Path) -> Path:
        """Compile a single Python file to bytecode"""
        output_path = self.config.get_work_path(f"{source_path.stem}.pyc")
        
        try:
            py_compile.compile(source_path, output_path, doraise=True)
            self.logger.debug(f"Compiled {source_path} to {output_path}")
            return output_path
        except py_compile.PyCompileError as e:
            self.logger.error(f"Failed to compile {source_path}: {e}")
            raise
    
    def _create_module_archive(self, category: str, files: List[Path]) -> Path:
        """Create a ZIP archive containing compiled modules"""
        archive_path = self.config.get_work_path(f"{category}.zip")
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                if file_path.suffix == '.py':
                    # Compile Python file
                    try:
                        compiled_path = self._compile_python_to_bytecode(file_path)
                        arcname = file_path.stem + '.pyc'
                        zipf.write(compiled_path, arcname)
                        # Clean up temporary compiled file
                        compiled_path.unlink()
                    except Exception as e:
                        self.logger.warning(f"Could not compile {file_path}: {e}")
                        # Fall back to source
                        arcname = file_path.name
                        zipf.write(file_path, arcname)
                else:
                    # Copy non-Python files as-is
                    arcname = file_path.name
                    zipf.write(file_path, arcname)
        
        self.logger.debug(f"Created module archive: {archive_path}")
        return archive_path
    
    def _create_data_archive(self, files: List[Path]) -> Path:
        """Create a ZIP archive containing data files"""
        archive_path = self.config.get_work_path("data_files.zip")
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in files:
                if file_path.is_file():
                    # Preserve directory structure
                    arcname = file_path.name
                    zipf.write(file_path, arcname)
        
        self.logger.debug(f"Created data archive: {archive_path}")
        return archive_path
    
    def _compile_python_to_bytecode(self, source_path: Path) -> Path:
        """Compile Python source to bytecode"""
        output_path = source_path.with_suffix('.pyc')
        
        with open(source_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        
        try:
            # Compile to code object
            code_obj = compile(source_code, str(source_path), 'exec')
            
            # Write bytecode file
            with open(output_path, 'wb') as f:
                # Write magic number and timestamp
                f.write(py_compile.MAGIC)
                f.write(b'\x00\x00\x00\x00')  # timestamp
                f.write(b'\x00\x00\x00\x00')  # size
                
                # Write marshalled code
                marshal.dump(code_obj, f)
            
            return output_path
        
        except SyntaxError as e:
            self.logger.error(f"Syntax error in {source_path}: {e}")
            raise
