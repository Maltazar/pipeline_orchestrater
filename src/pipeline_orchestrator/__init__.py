"""Pulumi Orchestrator Core Package

This package provides the core functionality for the Pulumi Orchestrator.
"""
# Import core components to make them available at package level
from pipeline_orchestrator.handlers.extension import ExtensionHandler
from pipeline_orchestrator.interfaces.pulumi import PulumiInterface

__all__ = [
    'ExtensionHandler',
    'PulumiInterface'
] 