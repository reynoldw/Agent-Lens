import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
logger.info("Loading environment variables...")
load_dotenv()

# Check OpenAI API key
openai_key = os.getenv('OPENAI_API_KEY')
logger.info(f"OpenAI API key found: {'Yes' if openai_key else 'No'}")
if openai_key:
    logger.info(f"OpenAI API key length: {len(openai_key)}")
    logger.info(f"OpenAI API key starts with: {openai_key[:10]}...")

# Print current working directory
logger.info(f"Current working directory: {os.getcwd()}")

# Check if .env file exists
env_file = os.path.join(os.getcwd(), '.env')
logger.info(f".env file exists: {os.path.exists(env_file)}")

if os.path.exists(env_file):
    with open(env_file, 'r') as f:
        logger.info("First line of .env file:")
        logger.info(f.readline().strip()) 