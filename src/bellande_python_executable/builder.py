"""
Executable builder for PyPack
Creates the final executable with embedded Python runtime
"""

from header_imports import *

class ExecutableBuilder:
    """Builds the final executable"""
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.platform_info = get_platform_info()
    
    def build(self, compiled_files: Dict[str, Path]) -> Path:
        """Build the final executable"""
        self.logger.debug("Starting executable build")
        
        # Create the bootstrap C code
        bootstrap_c = self._create_bootstrap_code(compiled_files)
        
        # Write bootstrap code to temporary file
        bootstrap_path = create_temp_file(bootstrap_c, '.c')
        
        try:
            # Compile the executable
            executable_path = self._compile_executable(bootstrap_path, compiled_files)
            
            # Make executable on Unix-like systems
            if self.platform_info['system'] in ['linux', 'darwin']:
                os.chmod(executable_path, 0o755)
            
            self.logger.debug(f"Built executable: {executable_path}")
            return executable_path
        
        finally:
            # Clean up temporary files
            try:
                os.unlink(bootstrap_path)
            except:
                pass
    
    def _create_bootstrap_code(self, compiled_files: Dict[str, Path]) -> str:
        """Create the C bootstrap code"""
        template = self._get_bootstrap_template()
        
        # Read main script bytecode
        main_script_data = ""
        if compiled_files.get('main_script'):
            with open(compiled_files['main_script'], 'rb') as f:
                bytecode = f.read()
                main_script_data = self._bytes_to_c_array(bytecode)
        
        # Read archive data
        archives_data = {}
        for category in ['stdlib_modules', 'third_party_modules', 'local_modules', 'data_files']:
            if compiled_files.get(category):
                with open(compiled_files[category], 'rb') as f:
                    archive_data = f.read()
                    archives_data[category] = self._bytes_to_c_array(archive_data)
        
        # Fill in template
        code = template.format(
            main_script_data=main_script_data,
            main_script_size=len(main_script_data.split(',')) if main_script_data else 0,
            stdlib_data=archives_data.get('stdlib_modules', ''),
            stdlib_size=len(archives_data.get('stdlib_modules', '').split(',')) if archives_data.get('stdlib_modules') else 0,
            third_party_data=archives_data.get('third_party_modules', ''),
            third_party_size=len(archives_data.get('third_party_modules', '').split(',')) if archives_data.get('third_party_modules') else 0,
            local_data=archives_data.get('local_modules', ''),
            local_size=len(archives_data.get('local_modules', '').split(',')) if archives_data.get('local_modules') else 0,
            data_files_data=archives_data.get('data_files', ''),
            data_files_size=len(archives_data.get('data_files', '').split(',')) if archives_data.get('data_files') else 0,
        )
        
        return code
    
    def _get_bootstrap_template(self) -> str:
        """Get the C bootstrap template"""
        return '''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#ifdef _WIN32
#include <windows.h>
#include <direct.h>
#define PATH_SEP "\\\\"
#else
#include <dlfcn.h>
#define PATH_SEP "/"
#endif

#define PY_SSIZE_T_CLEAN
#include <Python.h>

// Embedded data
static unsigned char main_script_data[] = {{{main_script_data}}};
static size_t main_script_size = {main_script_size};

static unsigned char stdlib_data[] = {{{stdlib_data}}};
static size_t stdlib_size = {stdlib_size};

static unsigned char third_party_data[] = {{{third_party_data}}};
static size_t third_party_size = {third_party_size};

static unsigned char local_data[] = {{{local_data}}};
static size_t local_size = {local_size};

static unsigned char data_files_data[] = {{{data_files_data}}};
static size_t data_files_size = {data_files_size};

// Extract embedded data to temporary directory
static char* extract_data(unsigned char* data, size_t size, const char* filename) {{
    if (size == 0) return NULL;
    
    char* temp_dir = getenv("TMPDIR");
    if (!temp_dir) temp_dir = "/tmp";
    
    char* filepath = malloc(strlen(temp_dir) + strlen(filename) + 20);
    sprintf(filepath, "%s/pypacker_%d_%s", temp_dir, getpid(), filename);
    
    FILE* f = fopen(filepath, "wb");
    if (!f) {{
        free(filepath);
        return NULL;
    }}
    
    fwrite(data, 1, size, f);
    fclose(f);
    
    return filepath;
}}

// Custom import hook
static PyObject* custom_import(PyObject* self, PyObject* args) {{
    // This would implement custom import logic
    // For now, use default import
    return PyObject_CallMethod(PyImport_GetModuleDict(), "get", "s", "__import__");
}}

int main(int argc, char* argv[]) {{
    // Initialize Python
    Py_Initialize();
    
    if (!Py_IsInitialized()) {{
        fprintf(stderr, "Failed to initialize Python\\n");
        return 1;
    }}
    
    // Set up sys.argv
    PySys_SetArgv(argc, argv);
    
    // Extract and run main script
    if (main_script_size > 0) {{
        // Load bytecode from embedded data
        PyObject* code = PyMarshal_ReadObjectFromString((char*)main_script_data + 12, main_script_size - 12);
        if (!code) {{
            PyErr_Print();
            Py_Finalize();
            return 1;
        }}
        
        // Create main module
        PyObject* main_module = PyImport_AddModule("__main__");
        if (!main_module) {{
            Py_DECREF(code);
            Py_Finalize();
            return 1;
        }}
        
        PyObject* main_dict = PyModule_GetDict(main_module);
        
        // Execute the code
        PyObject* result = PyEval_EvalCode(code, main_dict, main_dict);
        
        Py_DECREF(code);
        
        if (!result) {{
            PyErr_Print();
            Py_Finalize();
            return 1;
        }}
        
        Py_DECREF(result);
    }}
    
    // Clean up
    Py_Finalize();
    return 0;
}}
'''
    
    def _bytes_to_c_array(self, data: bytes) -> str:
        """Convert bytes to C array format"""
        if not data:
            return ""
        return ','.join(f'0x{b:02x}' for b in data)
    
    def _compile_executable(self, bootstrap_path: str, compiled_files: Dict[str, Path]) -> Path:
        """Compile the C bootstrap into an executable"""
        output_path = self.config.get_output_path(self.config.output_name)
        
        if self.platform_info['system'] == 'windows':
            output_path = output_path.with_suffix('.exe')
        
        # Find Python includes and libraries
        python_includes = self._get_python_includes()
        python_libs = self._get_python_libs()
        
        # Build compiler command
        if self.platform_info['system'] == 'windows':
            # Windows with MSVC
            cmd = [
                'cl',
                '/nologo',
                f'/I{python_includes}',
                bootstrap_path,
                f'/Fe{output_path}',
                f'/link', f'/LIBPATH:{python_libs}',
                'python3.lib'
            ]
        else:
            # Unix-like systems with GCC
            cmd = [
                'gcc',
                '-o', str(output_path),
                f'-I{python_includes}',
                bootstrap_path,
                f'-L{python_libs}',
                '-lpython3.11',  # Adjust version as needed
                '-ldl', '-lm'
            ]
        
        self.logger.debug(f"Compiler command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.debug("Compilation successful")
            return output_path
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Compilation failed: {e}")
            self.logger.error(f"Stdout: {e.stdout}")
            self.logger.error(f"Stderr: {e.stderr}")
            raise
    
    def _get_python_includes(self) -> str:
        """Get Python include directory"""
        import sysconfig
        return sysconfig.get_path('include')
    
    def _get_python_libs(self) -> str:
        """Get Python library directory"""
        import sysconfig
        
        if self.platform_info['system'] == 'windows':
            return sysconfig.get_path('stdlib')
        else:
            # For Unix-like systems
            return sysconfig.get_config_var('LIBDIR') or '/usr/lib'
    
    def _find_compiler(self) -> Optional[str]:
        """Find a suitable C compiler"""
        compilers = []
        
        if self.platform_info['system'] == 'windows':
            compilers = ['cl', 'gcc', 'clang']
        else:
            compilers = ['gcc', 'clang', 'cc']
        
        for compiler in compilers:
            if shutil.which(compiler):
                return compiler
        
        return None
