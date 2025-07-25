"""
PyPack - A Python to executable converter
Main entry point for the application
"""
from header_imports import *

def main():
    parser = argparse.ArgumentParser(description='Convert Python scripts to executables')
    parser.add_argument('--script_file', help='Python script or file to convert')
    parser.add_argument('--output', help='Output executable name')
    parser.add_argument('--name', help='Name of the executable')
    parser.add_argument('--onefile', action='store_true', help='Create a single executable file')
    parser.add_argument('--windowed', action='store_true', help='Create windowed application (no console)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--exclude', action='append', help='Exclude modules')
    parser.add_argument('--include', action='append', help='Include additional modules')
    parser.add_argument('--add-data', action='append', help='Add data files (format: src:dest)')
    
    args = parser.parse_args()
    
    # Initialize logger
    logger = Logger(debug=args.debug)
    
    # Validate input script
    script_path = Path(args.script_file)
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        sys.exit(1)
    
    if not script_path.suffix == '.py':
        logger.error("Input must be a Python script (.py)")
        sys.exit(1)
    
    # Determine output name
    if args.name:
        output_name = args.name
    elif args.output:
        output_name = args.output
    else:
        output_name = script_path.stem
    
    # Initialize configuration
    config = ConfigManager(
        script_path=script_path,
        output_name=output_name,
        onefile=args.onefile,
        windowed=args.windowed,
        debug=args.debug,
        exclude_modules=args.exclude or [],
        include_modules=args.include or [],
        add_data=args.add_data or []
    )
    
    try:
        logger.info(f"Converting Python {script_path} to executable...")
        
        # Step 1: Analyze dependencies
        logger.info("Analyzing dependencies...")
        analyzer = DependencyAnalyzer(config, logger)
        dependencies = analyzer.analyze()
        
        # Step 2: Collect code and resources
        logger.info("Collecting code and resources...")
        collector = CodeCollector(config, logger)
        collected_files = collector.collect(dependencies)
        
        # Step 3: Compile to bytecode
        logger.info("Compiling to bytecode...")
        compiler = BytecodeCompiler(config, logger)
        bytecode_files = compiler.compile(collected_files)
        
        # Step 4: Build executable
        logger.info("Building executable...")
        builder = ExecutableBuilder(config, logger)
        executable_path = builder.build(bytecode_files)
        
        logger.info(f"Executable created: {executable_path}")
        
    except Exception as e:
        logger.error(f"Build failed: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
