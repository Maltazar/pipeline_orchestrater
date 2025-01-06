# install pulumi

```
brew install pulumi
```

or

```
curl -fsSL https://get.pulumi.com | sh
```

## setup local pulumi

```
pulumi login -l
```

## create new project

```
pulumi new python
```

## run the pipeline

```
export PULUMI_CONFIG_PASSPHRASE=""
pulumi up
```

## run the pipeline in mock mode without pulumi

```
export PULUMI_PIPELINE_CONFIG="../example_pipeline.yaml"
source ./.venv/bin/activate
cd src
python __main__.py
```

## add pulumi config

```
pulumi config set core:pipeline_config example_pipeline.yaml
```

## Extension Development

Install the pulumi-orchestrator package into the virtual environment.

```
uv pip install -e .
```

and make the exteions depend upon the pulumi-orchestrator package

```
dependencies = [
    "pulumi-orchestrator>=0.1.0",
]
```

## test with test file

```
export PULUMI_PIPELINE_CONFIG="../test/test_pipeline.yaml"
cd src
uv sync
uv pip install -e .
source ./.venv/bin/activate
cd pipeline_orchestrator
python __main__.py
```

## debug pulumi logs

```
pulumi up --logtostderr -v=9 2>pulumi.log
```
