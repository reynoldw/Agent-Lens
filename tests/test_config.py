"""
Tests for the configuration management system.
"""

import os
import pytest
import tempfile
import yaml
from src.utils.config import ConfigurationManager, get_config


def test_config_loading():
    """Test that configuration is loaded correctly."""
    config = get_config()
    
    # Check that we have basic configuration sections
    assert "api" in config.config
    assert "app" in config.config
    assert "simulation" in config.config
    
    # Check that we can get values with dot notation
    assert config.get("app.debug") is not None
    assert isinstance(config.get("app.port"), int)
    assert isinstance(config.get("simulation.browser.headless"), bool)


def test_config_defaults():
    """Test that default values are used when not specified."""
    # Create an empty configuration file
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
        f.write(b"# Empty config file\n")
        config_path = f.name
    
    try:
        # Load configuration from the empty file
        config = ConfigurationManager([config_path])
        
        # Check that default values are used
        assert config.get("api.openai.model") == "gpt-3.5-turbo"
        assert config.get("app.debug") is False
        assert config.get("app.port") == 5000
        assert config.get("simulation.browser.headless") is True
    finally:
        # Clean up
        os.unlink(config_path)


def test_config_override():
    """Test that configuration values can be overridden."""
    # Create a temporary configuration file with custom values
    custom_config = {
        "api": {
            "openai": {
                "model": "gpt-4"
            }
        },
        "app": {
            "port": 8080
        }
    }
    
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
        yaml.dump(custom_config, f)
        config_path = f.name
    
    try:
        # Load configuration from the custom file
        config = ConfigurationManager([config_path])
        
        # Check that custom values are used
        assert config.get("api.openai.model") == "gpt-4"
        assert config.get("app.port") == 8080
        
        # Check that defaults are still used for unspecified values
        assert config.get("app.debug") is False
        assert config.get("simulation.browser.headless") is True
    finally:
        # Clean up
        os.unlink(config_path)


def test_config_set():
    """Test that configuration values can be set programmatically."""
    config = get_config()
    
    # Set and verify values
    original_value = config.get("app.port")
    
    config.set("app.port", 9000)
    assert config.get("app.port") == 9000
    
    # Restore original value
    config.set("app.port", original_value)


def test_nested_config():
    """Test that nested configuration values work correctly."""
    # Create a temporary configuration file with nested values
    nested_config = {
        "simulation": {
            "browser": {
                "viewport": {
                    "desktop": {
                        "width": 1920,
                        "height": 1080
                    }
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
        yaml.dump(nested_config, f)
        config_path = f.name
    
    try:
        # Load configuration from the custom file
        config = ConfigurationManager([config_path])
        
        # Check that nested values are accessible
        assert config.get("simulation.browser.viewport.desktop.width") == 1920
        assert config.get("simulation.browser.viewport.desktop.height") == 1080
    finally:
        # Clean up
        os.unlink(config_path)


def test_config_default_param():
    """Test that the default parameter works correctly."""
    config = get_config()
    
    # Get a value that doesn't exist
    non_existent = config.get("non_existent_key", "default_value")
    assert non_existent == "default_value"
    
    # Get a nested value that doesn't exist
    non_existent_nested = config.get("app.non_existent_key", 5000)
    assert non_existent_nested == 5000 