"""
Test configuration and fixtures for the E-Commerce Website Evaluator.
"""

import os
import sys
import pytest
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.utils.config import get_config
from src.api.ai_client import AIClient
from src.persona.generator import PersonaGenerator
from src.interaction.job_definitions import JobRegistry
from src.interaction.simulator_bridge import SimulatorBridge


@pytest.fixture(scope='session')
def config():
    """Provide the configuration manager for tests."""
    # Load config from test settings
    config_paths = [
        os.path.join(project_root, 'tests', 'config.test.yaml'),
        os.path.join(project_root, 'config.yaml')
    ]
    return get_config(config_paths)


@pytest.fixture(scope='session')
def ai_client(config):
    """Provide an AI client for tests."""
    openai_api_key = config.get("api.openai.api_key")
    anthropic_api_key = config.get("api.anthropic.api_key")
    
    # If no API keys in config, try environment variables
    if not openai_api_key:
        openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not anthropic_api_key:
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    # Create client with available API keys
    if not (openai_api_key or anthropic_api_key):
        pytest.skip("No API keys available for AI services")
    
    return AIClient(openai_api_key=openai_api_key, anthropic_api_key=anthropic_api_key)


@pytest.fixture(scope='session')
def persona_generator(ai_client):
    """Provide a persona generator for tests."""
    return PersonaGenerator(ai_client=ai_client)


@pytest.fixture(scope='session')
def job_registry():
    """Provide a job registry for tests."""
    return JobRegistry()


@pytest.fixture(scope='session')
def playwright():
    """Provide a playwright instance for browser tests."""
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope='function')
def browser(playwright):
    """Provide a browser instance for tests."""
    browser = playwright.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture(scope='function')
def browser_context(browser):
    """Provide a browser context for tests."""
    context = browser.new_context(viewport={'width': 1280, 'height': 720})
    yield context
    context.close()


@pytest.fixture(scope='function')
def page(browser_context):
    """Provide a page for tests."""
    page = browser_context.new_page()
    yield page
    page.close()


@pytest.fixture(scope='function')
def simulator_bridge():
    """Provide a simulator bridge for tests."""
    # Use legacy simulator to avoid dependency on browser pool in tests
    bridge = SimulatorBridge(use_legacy=True)
    yield bridge


@pytest.fixture(scope='function')
def sample_persona():
    """Provide a sample persona for tests that don't need AI generation."""
    return {
        "demographics": {
            "name": "John Smith",
            "age": 35,
            "gender": "Male",
            "location": "New York, USA",
            "occupation": "Software Engineer",
            "income_level": "High",
            "family_status": "Married",
            "education_level": "Master's"
        },
        "shopping_behavior": {
            "frequency": "Weekly",
            "average_order_value": "$100",
            "price_sensitivity": "Mid-range",
            "brand_loyalty": "Medium",
            "research_behavior": "Researcher",
            "product_categories": ["Electronics", "Books"]
        },
        "technical": {
            "devices": {
                "mobile": 30,
                "desktop": 60,
                "tablet": 10
            },
            "proficiency": 8,
            "social_media": ["Twitter", "LinkedIn"],
            "payment_methods": ["Credit Card", "PayPal"]
        },
        "e_commerce_specific": {
            "online_shopping_experience": 9,
            "patience_level": 7,
            "importance_of_reviews": 8,
            "importance_of_shipping_speed": 6
        },
        "accessibility_needs": [],
        "goals": {
            "primary": "Find a specific product",
            "secondary": "Compare prices"
        }
    } 