"""
Configuration Management for E-Commerce Website Evaluator.

This module manages application configuration, providing a centralized
location for all configuration settings and validation.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, List, Union, TypeVar, Set
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
T = TypeVar('T')  # Generic type for config values

# Default locations for configuration files
DEFAULT_CONFIG_PATHS = [
    "./config.yaml",
    "./config.json",
    "./config/config.yaml",
    "./config/config.json",
]

# Configuration schema with types and default values
CONFIG_SCHEMA = {
    "api": {
        "openai": {
            "api_key": {"type": str, "default": None, "env_var": "OPENAI_API_KEY"},
            "model": {"type": str, "default": "gpt-3.5-turbo"},
            "timeout": {"type": int, "default": 30},
            "max_tokens": {"type": int, "default": 500}
        },
        "anthropic": {
            "api_key": {"type": str, "default": None, "env_var": "ANTHROPIC_API_KEY"},
            "model": {"type": str, "default": "claude-3-opus-20240229"},
            "timeout": {"type": int, "default": 30},
            "max_tokens": {"type": int, "default": 500}
        }
    },
    "app": {
        "debug": {"type": bool, "default": False, "env_var": "DEBUG"},
        "log_level": {"type": str, "default": "INFO", "env_var": "LOG_LEVEL"},
        "temp_dir": {"type": str, "default": "./temp"},
        "output_dir": {"type": str, "default": "./output"},
        "screenshots_dir": {"type": str, "default": "./screenshots"},
        "host": {"type": str, "default": "127.0.0.1", "env_var": "HOST"},
        "port": {"type": int, "default": 5000, "env_var": "PORT"}
    },
    "simulation": {
        "browser": {
            "headless": {"type": bool, "default": True},
            "browser_type": {"type": str, "default": "chromium"},
            "timeout": {"type": int, "default": 60000},
            "max_browsers": {"type": int, "default": 5},
            "idle_timeout": {"type": int, "default": 300},
            "viewport": {
                "desktop": {
                    "width": {"type": int, "default": 1280},
                    "height": {"type": int, "default": 800}
                },
                "tablet": {
                    "width": {"type": int, "default": 768},
                    "height": {"type": int, "default": 1024}
                },
                "mobile": {
                    "width": {"type": int, "default": 375},
                    "height": {"type": int, "default": 667}
                }
            }
        },
        "personas": {
            "count": {"type": int, "default": 3}
        },
        "jobs": {
            "max_retries": {"type": int, "default": 2},
            "concurrent_jobs": {"type": int, "default": 3},
            "default_job": {"type": str, "default": "product_discovery"}
        },
        "selectors": {
            "cache_file": {"type": str, "default": "./data/selectors.yaml"}
        }
    },
    "analysis": {
        "min_data_points": {"type": int, "default": 2},
        "chart_dpi": {"type": int, "default": 100},
        "chart_style": {"type": str, "default": "ggplot"},
        "chart_colors": {"type": list, "default": ["#4285F4", "#34A853", "#FBBC05", "#EA4335"]}
    },
    "security": {
        "token_required": {"type": bool, "default": False, "env_var": "TOKEN_REQUIRED"},
        "api_token": {"type": str, "default": None, "env_var": "API_TOKEN"}
    }
}


class ConfigurationManager:
    """Manages application configuration with validation and defaults."""
    
    def __init__(self, config_paths: Optional[List[str]] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_paths: List of paths to configuration files to load
        """
        self.config_paths = config_paths or DEFAULT_CONFIG_PATHS
        self.config = {}
        self.loaded_files = []
        
        # Load configuration
        self._load_config()
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"Configuration loaded from: {', '.join(self.loaded_files) or 'defaults'}")
    
    def _load_config(self):
        """Load configuration from files and environment variables."""
        # Initialize with defaults
        self.config = self._get_defaults(CONFIG_SCHEMA)
        
        # Load from configuration files
        for path in self.config_paths:
            if os.path.exists(path):
                file_config = self._load_config_file(path)
                if file_config:
                    self._merge_configs(self.config, file_config)
                    self.loaded_files.append(path)
        
        # Load from environment variables
        self._load_from_env(CONFIG_SCHEMA, self.config)
    
    def _load_config_file(self, path: str) -> Dict[str, Any]:
        """Load configuration from a file."""
        try:
            with open(path, 'r') as f:
                if path.endswith('.yaml') or path.endswith('.yml'):
                    return yaml.safe_load(f)
                elif path.endswith('.json'):
                    return json.load(f)
                else:
                    logger.warning(f"Unsupported configuration file format: {path}")
                    return {}
        except Exception as e:
            logger.error(f"Error loading configuration file {path}: {e}")
            return {}
    
    def _get_defaults(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Extract default values from schema."""
        defaults = {}
        for key, value in schema.items():
            if isinstance(value, dict) and "type" in value:
                # This is a leaf node
                defaults[key] = value.get("default")
            elif isinstance(value, dict):
                # This is a nested dictionary
                defaults[key] = self._get_defaults(value)
        return defaults
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]):
        """Recursively merge configuration dictionaries."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value
    
    def _load_from_env(self, schema: Dict[str, Any], config: Dict[str, Any], prefix: str = ""):
        """Load configuration from environment variables based on schema."""
        for key, value in schema.items():
            env_key = f"{prefix}_{key}" if prefix else key
            if isinstance(value, dict) and "type" in value:
                # This is a leaf node
                if "env_var" in value:
                    env_value = os.getenv(value["env_var"])
                    if env_value is not None:
                        # Convert to appropriate type
                        if value["type"] is bool:
                            config[key] = env_value.lower() in ("true", "yes", "1", "t")
                        else:
                            config[key] = value["type"](env_value)
            elif isinstance(value, dict):
                # This is a nested dictionary
                if key not in config:
                    config[key] = {}
                self._load_from_env(value, config[key], env_key)
    
    def _validate_config(self):
        """Validate configuration against schema."""
        errors = self._validate_against_schema(CONFIG_SCHEMA, self.config)
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _validate_against_schema(self, schema: Dict[str, Any], config: Dict[str, Any], 
                                path: str = "") -> List[str]:
        """Validate configuration values against schema."""
        errors = []
        
        for key, schema_value in schema.items():
            if isinstance(schema_value, dict) and "type" in schema_value:
                # This is a leaf node
                if key in config and config[key] is not None:
                    value = config[key]
                    # Type checking
                    if not isinstance(value, schema_value["type"]):
                        curr_path = f"{path}.{key}" if path else key
                        errors.append(
                            f"{curr_path} should be of type {schema_value['type'].__name__}, "
                            f"got {type(value).__name__}"
                        )
            elif isinstance(schema_value, dict):
                # This is a nested dictionary
                curr_path = f"{path}.{key}" if path else key
                if key in config and isinstance(config[key], dict):
                    # Recursive validation
                    errors.extend(self._validate_against_schema(
                        schema_value, config[key], curr_path
                    ))
        
        return errors
    
    def get(self, path: str, default: Optional[T] = None) -> T:
        """
        Get a configuration value using dot notation.
        
        Args:
            path: Configuration path using dot notation (e.g., 'app.debug')
            default: Default value to return if path is not found
            
        Returns:
            Configuration value or default
        """
        parts = path.split('.')
        value = self.config
        
        try:
            for part in parts:
                value = value[part]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, path: str, value: Any):
        """
        Set a configuration value using dot notation.
        
        Args:
            path: Configuration path using dot notation (e.g., 'app.debug')
            value: Value to set
        """
        parts = path.split('.')
        config = self.config
        
        # Navigate to the parent of the target key
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        
        # Set the value
        config[parts[-1]] = value
    
    def save(self, path: Optional[str] = None):
        """
        Save configuration to a file.
        
        Args:
            path: Path to save configuration to (defaults to first loaded file or first in config_paths)
        """
        if not path:
            path = self.loaded_files[0] if self.loaded_files else self.config_paths[0]
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        try:
            with open(path, 'w') as f:
                if path.endswith('.yaml') or path.endswith('.yml'):
                    yaml.dump(self.config, f, default_flow_style=False)
                elif path.endswith('.json'):
                    json.dump(self.config, f, indent=2)
                else:
                    raise ValueError(f"Unsupported file format: {path}")
            
            logger.info(f"Configuration saved to {path}")
        except Exception as e:
            logger.error(f"Error saving configuration to {path}: {e}")
            raise


# Global configuration instance
_config_manager = None

def get_config(config_paths: Optional[List[str]] = None) -> ConfigurationManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(config_paths)
    return _config_manager 