import os
import sys

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import and run the Flask application
from src.app import app

if __name__ == '__main__':
    app.run(debug=True) 