"""Plugin system for Skillberry Store.

This module provides the infrastructure for discovering and loading plugins
that extend the store's functionality.
"""

from .base import PluginBase, PluginMetadata, PluginType

__all__ = ["PluginBase", "PluginMetadata", "PluginType"]

# Made with Bob
