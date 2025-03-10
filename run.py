import os
import sys
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug.log')
    ]
)
logger = logging.getLogger(__name__)

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

logger.info(f"Project root: {project_root}")
logger.info(f"Python path: {sys.path}")
logger.info(f"OpenAI API key present: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")

try:
    # Import and run the Flask application
    from src.app import app
    logger.info("Successfully imported app")
    
    if __name__ == '__main__':
        logger.info("Starting Flask application...")
        app.run(debug=True)
except Exception as e:
    logger.error(f"Error starting application: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    sys.exit(1) 