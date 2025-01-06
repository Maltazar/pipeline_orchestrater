# Development Guide

## Initial Setup

### VSCode Extensions
- Pulumi extension
- Python extension

### Virtual Environment Setup
```bash
uv sync
source .venv/bin/activate
uv pip install -e .
```

## Local Development

### Running the Pipeline (Without Pulumi)
```bash
cd src
export PIPELINE_CONFIG="../../example_pipeline.yaml"
cd pipeline_orchestrator
python __main__.py
```

### Testing
```bash
# Run with test configuration
export PIPELINE_CONFIG="../test/test_pipeline.yaml"
cd src
uv sync
uv pip install -e .
source .venv/bin/activate
cd pipeline_orchestrator
python __main__.py
```

## Pulumi Operations

### Installation
```bash
# Using Homebrew
brew install pulumi

# Or using curl
curl -fsSL https://get.pulumi.com | sh
```

### Initial Pulumi Setup
```bash
# Setup local Pulumi state storage
pulumi login -l

# Create new Pulumi project
pulumi new python
```

### Running Pulumi Operations
```bash
cd src
export PULUMI_CONFIG_PASSPHRASE=""
pulumi up
```

### Pulumi Configuration
```bash
# Set pipeline configuration
pulumi config set core:pipeline_config example_pipeline.yaml
```

### Debugging Pulumi
```bash
# Detailed logging
pulumi up --logtostderr -v=9 2>pulumi.log
```

## Extension Development

### Local Package Installation
Install the pipeline-orchestrator package into the virtual environment:
```bash
uv pip install -e .
```

### Extension Dependencies
Add to extension's pyproject.toml:
```toml
dependencies = [
    "pipeline-orchestrator>=0.1.0",
]
```

### Best Practices
- Extensions should depend on the pipeline-orchestrator package
- Each extension should be modular and self-contained
- Follow proper error handling and state management
- Implement proper cleanup procedures
