"""Pulumi Orchestrator Main Entry Point

Responsible for:
1. Setting up logging
2. Loading configuration
3. Initializing pipeline
4. Running pipeline
"""
import json
import os
from pipeline_orchestrator.core.bootstrap import PipelineBootstrap
from pipeline_orchestrator.core.logging import setup_logger

def is_direct_run() -> bool:
    """
    Determines if the code is running directly through Python (mock/direct mode)
    or through Pulumi's runtime.
    """
    try:
        direct_run = False
        if not os.getenv('PULUMI_RUNTIME_VERSION'):
            direct_run = True
        if not os.getenv('PULUMI_CONFIG'):
            direct_run = True
        if not os.getenv('PULUMI_CONFIG_SECRET_KEYS'):
            direct_run = True
            
        return direct_run
    except (ImportError, Exception):
        return True

def main():
    """Main entry point"""
    # Initialize logging
    _is_direct_run = is_direct_run()
    _mode = "DIRECT/NATIVE" if _is_direct_run else "PULUMI"
    level = os.getenv("LOG_LEVEL", "INFO")
    logger = setup_logger(log_level=level)
    logger.info(f"Starting pipeline in MODE: {_mode}")
    try:
        # Create and initialize pipeline
        bootstrap = PipelineBootstrap(_is_direct_run)
        bootstrap.load_configuration()
        
        # Create and run orchestrator
        orchestrator = bootstrap.create_orchestrator()
        orchestrator.execute()
        
        # Output extension data when running directly (not through Pulumi)
        if _is_direct_run:
            # Get resource tree
            logger.debug("Resource Tree:")
            logger.debug(json.dumps(orchestrator.pulumi.get_resource_tree(), indent=2))
            
            # Get extension data
            all_data = orchestrator.state.get_all_extension_data()
            if all_data:
                print("\nPipeline Output:")
                print(json.dumps(all_data, indent=2))
        
        logger.info("Pipeline completed successfully")
    except Exception as e:
        logger.error("Pipeline failed", exc_info=True)
        logger.debug(f"exception: {e}")
        raise

if __name__ == "__main__":
    main()