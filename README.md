# pipeline_orchestrater
Fully bootstrap and orchestrate your infrastructure though a single yaml pipeline

## Initital idea

The idea is to create a single yaml file that can be used to bootstrap and orchestrate your infrastructure.

The yaml file will be used to define the infrastructure you want to create and the order in which you want to create it.

For now the pipeline is using pulumi to orchestrate the infrastructure. but the idea is to be able to use other tools like dagger or stuff like that.

