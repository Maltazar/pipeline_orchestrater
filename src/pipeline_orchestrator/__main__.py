"""Pulumi Orchestrator Main Entry Point

Responsible for:
1. Setting up logging
2. Loading configuration
3. Initializing pipeline
4. Running pipeline
"""
import json
from pipeline_orchestrator.core.bootstrap import PipelineBootstrap
from pipeline_orchestrator.core.logging import setup_logger

def main():
    """Main entry point"""
    # Initialize logging
    logger = setup_logger(log_level="DEBUG")
    logger.info("Starting pipeline")
    try:
        # Create and initialize pipeline
        bootstrap = PipelineBootstrap()
        bootstrap.load_configuration()
        
        # Create and run orchestrator
        orchestrator = bootstrap.create_orchestrator()
        orchestrator.execute()
        
        # Output extension data when running directly (not through Pulumi)
        if bootstrap.is_mock_mode():
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