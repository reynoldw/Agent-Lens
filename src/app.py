from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import json
import traceback
from queue import Queue
from threading import Thread
import threading
from datetime import datetime
import os
import logging
import sys
import atexit

# Import from utils
from src.utils.config import get_config
from src.utils.error_handling import (
    EvaluationError, ValidationError, SimulationError, 
    format_error_response, setup_global_exception_handler,
    log_execution_time, capture_exceptions
)

# Import modules
from src.persona.generator import PersonaGenerator
from src.interaction.simulator_bridge import SimulatorBridge
from src.review.generator import ReviewGenerator
from src.expert.analyzer import ExpertAnalyzer
from src.api.ai_client import AIClient
from src.interaction.browser_pool import BrowserPool

# Set up global exception handler
setup_global_exception_handler()

# Load configuration
config = get_config()

# Configure logging
log_level = getattr(logging, config.get("app.log_level", "INFO"))
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Initialize browser pool with error handling
try:
    browser_pool = BrowserPool(
        max_browsers=config.get("browser_pool.max_browsers", 5),
        idle_timeout=config.get("browser_pool.idle_timeout", 300),
        browser_type=config.get("browser_pool.browser_type", "chromium"),
        headless=config.get("browser_pool.headless", True)
    )
    logger.info(f"Browser pool initialized (max: {browser_pool.max_browsers}, timeout: {browser_pool.idle_timeout}s)")
except Exception as e:
    logger.error(f"Error initializing browser pool: {e}")
    browser_pool = None

# Initialize AI client
openai_api_key = os.environ.get("OPENAI_API_KEY") or config.get("api.openai_key")
anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY") or config.get("api.anthropic_key")
openai_model = os.environ.get("OPENAI_MODEL") or config.get("api.openai.model", "gpt-4")
anthropic_model = os.environ.get("ANTHROPIC_MODEL") or config.get("api.anthropic.model", "claude-3-opus-20240229")
default_provider = os.environ.get("DEFAULT_AI_PROVIDER") or config.get("api.default_provider", "openai" if openai_api_key else "anthropic")

logger.info(f"OpenAI API key present: {'Yes' if openai_api_key else 'No'}")
logger.info(f"Anthropic API key present: {'Yes' if anthropic_api_key else 'No'}")
logger.info(f"Using OpenAI model: {openai_model}")
logger.info(f"Using Anthropic model: {anthropic_model}")
logger.info(f"Default AI provider: {default_provider}")

try:
    ai_client = AIClient(
        openai_api_key=openai_api_key, 
        anthropic_api_key=anthropic_api_key
    )
    # Set default models and provider
    ai_client.openai_model = openai_model
    ai_client.anthropic_model = anthropic_model
    ai_client.default_provider = default_provider
except Exception as e:
    logger.error(f"Error initializing AI client: {e}")
    ai_client = None

# Register cleanup function
def cleanup():
    """Clean up resources on application shutdown."""
    logger.info("Cleaning up resources...")
    try:
        # Clean up browser pool
        browser_pool.shutdown()
        logger.info("Browser pool shutdown complete")
        
        # Clean up progress queues and results
        with evaluation_lock:
            progress_queues.clear()
            evaluation_results.clear()
            
        # Force destroy any remaining Tkinter resources
        try:
            import tkinter as tk
            if tk._default_root:
                tk._default_root.quit()
                tk._default_root.destroy()
        except Exception as e:
            logger.error(f"Error cleaning up Tkinter resources: {e}")
            
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")

atexit.register(cleanup)

# Global progress queues and results dictionary
progress_queues = {}
evaluation_results = {}
evaluation_lock = threading.RLock()

# Initialize components with AI client
persona_generator = PersonaGenerator(ai_client=ai_client)
simulator = SimulatorBridge(use_legacy=False, browser_pool=browser_pool)  # Pass browser pool instance
review_generator = ReviewGenerator(ai_client=ai_client)
expert_analyzer = ExpertAnalyzer(ai_client=ai_client)

# Create required directories
for directory in [
    config.get("app.temp_dir", "./temp"),
    config.get("app.output_dir", "./output"),
    config.get("app.screenshots_dir", "./screenshots")
]:
    os.makedirs(directory, exist_ok=True)

def send_progress(evaluation_id: str, message: str, percentage: int = None):
    """Send progress update to client."""
    data = {
        'message': message,
        'percentage': percentage
    }
    if evaluation_id in progress_queues:
        progress_queues[evaluation_id].put(data)


@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('index.html')


@app.route('/api/evaluate', methods=['POST'])
@log_execution_time(logger, logging.INFO)
def evaluate_website():
    """API endpoint to evaluate a website."""
    try:
        # Validate request
        if not request.json:
            raise ValidationError("Missing JSON data", field="request")
            
        website_url = request.json.get('url')
        if not website_url:
            raise ValidationError("Missing URL parameter", field="url")
            
        # Get number of personas from request
        num_personas = request.json.get('num_personas', 3)
        try:
            num_personas = int(num_personas)
            # Limit to a reasonable range
            num_personas = max(1, min(num_personas, 10))
        except (ValueError, TypeError):
            num_personas = 3  # Default if invalid
            
        # Generate a unique evaluation ID
        evaluation_id = f"eval_{int(datetime.now().timestamp())}"
        
        # Create progress queue for this evaluation
        progress_queues[evaluation_id] = Queue()
        
        # Start evaluation in a separate thread
        thread = Thread(
            target=run_evaluation,
            args=(evaluation_id, website_url, num_personas),
            daemon=True
        )
        thread.start()
        
        return jsonify({
            'success': True,
            'evaluation_id': evaluation_id,
            'message': 'Evaluation started'
        })
        
    except Exception as e:
        logger.error(f"Error in evaluate_website: {e}")
        return jsonify(format_error_response(e)), 400


def run_evaluation(evaluation_id: str, website_url: str, num_personas: int = 3):
    """Run the complete evaluation process."""
    try:
        # Ensure progress queue exists
        if evaluation_id not in progress_queues:
            logger.error(f"Progress queue for evaluation {evaluation_id} not found. Creating a new one.")
            progress_queues[evaluation_id] = Queue()
        
        # Send initial progress update
        send_progress(evaluation_id, "Starting evaluation...", 5)
        logger.info(f"Starting evaluation {evaluation_id} for {website_url} with {num_personas} personas")
        
        # Generate personas
        send_progress(evaluation_id, f"Generating personas ({num_personas})...", 10)
        persona_generator = PersonaGenerator(ai_client=ai_client)
        
        try:
            personas = persona_generator.generate_batch(num_personas)
            logger.info(f"Generated {len(personas)} personas")
        except Exception as e:
            logger.error(f"Error generating personas: {str(e)}")
            raise ValueError(f"Failed to generate personas: {str(e)}")
        
        # Log generated personas
        for i, persona in enumerate(personas):
            logger.debug(f"Persona {i+1}: {persona}")
            # Log detailed persona information to the debug log
            send_progress(evaluation_id, f"Full Persona {i+1} Details: {json.dumps(persona, indent=2)}")
        
        # Simulate website interactions
        send_progress(evaluation_id, "Simulating website interactions...", 20)
        
        # Ensure browser pool is initialized
        if not browser_pool:
            logger.error("Browser pool is not initialized")
            raise ValueError("Browser pool is not initialized")
            
        simulator = SimulatorBridge(use_legacy=False, browser_pool=browser_pool)
        simulation_results = []
        
        for i, persona in enumerate(personas):
            send_progress(evaluation_id, f"Simulating persona {i+1}/{len(personas)}", 20 + (i * 20 // len(personas)))
            try:
                result = simulator.simulate(website_url, persona)
                simulation_results.append(result)
                logger.info(f"Completed simulation for persona {i+1}: {persona.get('name', 'Unknown')}")
                # Log detailed simulation results to the debug log
                send_progress(evaluation_id, f"Detailed simulation results for persona {i+1}: {json.dumps(result, default=str, indent=2)}")
            except Exception as e:
                logger.error(f"Error simulating persona {i+1}: {str(e)}")
                # Create a default result with error information
                error_result = {
                    "website_url": website_url,
                    "error": str(e),
                    "persona_name": persona.get('name', 'Unknown')
                }
                simulation_results.append(error_result)
                send_progress(evaluation_id, f"Error simulating persona {i+1}: {str(e)}", 20 + (i * 20 // len(personas)))
        
        # Generate reviews
        send_progress(evaluation_id, "Generating reviews...", 60)
        review_generator = ReviewGenerator(ai_client=ai_client)
        reviews = []
        
        for i, (persona, simulation) in enumerate(zip(personas, simulation_results)):
            send_progress(evaluation_id, f"Generating review {i+1}/{len(personas)}", 60 + (i * 15 // len(personas)))
            try:
                review = review_generator.generate(website_url, persona, simulation)
                reviews.append(review)
                # Log detailed review to the debug log
                send_progress(evaluation_id, f"Generated review {i+1} from {persona.get('name', 'Unknown')}: {json.dumps(review, default=str, indent=2)}")
                # Log the full text of the review for better readability
                if isinstance(review, dict) and 'review' in review:
                    send_progress(evaluation_id, f"Full Text of Review {i+1} from {persona.get('name', 'Unknown')}: {review.get('review', '')}")
                elif hasattr(review, 'detailed_review'):
                    send_progress(evaluation_id, f"Full Text of Review {i+1} from {persona.get('name', 'Unknown')}: {review.detailed_review}")
            except Exception as e:
                logger.error(f"Error generating review for persona {i+1}: {str(e)}")
                # Create a default review with error information
                error_review = {
                    "review": f"Error generating review: {str(e)}",
                    "rating": 0,
                    "sentiment": "neutral",
                    "error": str(e)
                }
                reviews.append(error_review)
                send_progress(evaluation_id, f"Error generating review {i+1}: {str(e)}", 60 + (i * 15 // len(personas)))
        
        # Analyze results and generate report
        send_progress(evaluation_id, "Analyzing results and generating report...", 80)
        analyzer = ExpertAnalyzer(ai_client=ai_client)
        
        try:
            report = analyzer.analyze(website_url, simulation_results, reviews)
            # Log the detailed analysis to the debug log
            send_progress(evaluation_id, f"Detailed Analysis Report: {json.dumps(report, default=str, indent=2)}")
        except Exception as e:
            logger.error(f"Error analyzing results: {str(e)}")
            # Create a default report with error information
            report = {
                "website_url": website_url,
                "error": str(e),
                "overall_scores": {
                    "overall": 5.0,
                    "navigation": 5.0,
                    "design": 5.0,
                    "findability": 5.0
                },
                "key_findings": [f"Error analyzing results: {str(e)}"],
                "recommendations": ["Try again with a different website or fewer personas"]
            }
            send_progress(evaluation_id, f"Error analyzing results: {str(e)}", 80)
        
        # Ensure report has all required fields for the UI
        if 'scores' not in report:
            report['scores'] = {
                'overall': report.get('overall_scores', {}).get('overall', 5.0),
                'navigation': report.get('overall_scores', {}).get('navigation', 5.0),
                'ui_design': report.get('overall_scores', {}).get('ui_design', 5.0),
                'product_presentation': report.get('overall_scores', {}).get('product_presentation', 5.0),
                'checkout': report.get('overall_scores', {}).get('checkout', 5.0),
                'mobile': report.get('overall_scores', {}).get('mobile', 5.0)
            }
        
        # Prepare final results
        send_progress(evaluation_id, "Preparing final results...", 95)
        
        # Convert reviews to the format expected by the UI
        formatted_reviews = []
        for review_data in reviews:
            formatted_review = {
                'content': review_data.get('review', '') if isinstance(review_data, dict) else 
                          (review_data.detailed_review if hasattr(review_data, 'detailed_review') else ''),
                'rating': review_data.get('rating', 3) if isinstance(review_data, dict) else 
                         (review_data.scores.get('overall', 3) if hasattr(review_data, 'scores') else 3),
                'sentiment': review_data.get('sentiment', 'neutral') if isinstance(review_data, dict) else 
                            (review_data.sentiment_scores.get('overall', 'neutral') if hasattr(review_data, 'sentiment_scores') else 'neutral')
            }
            formatted_reviews.append(formatted_review)
        
        final_results = {
            'website_url': website_url,
            'personas': personas,
            'simulation_results': simulation_results,
            'reviews': formatted_reviews,
            'report': report,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store results
        with evaluation_lock:
            evaluation_results[evaluation_id] = final_results
        
        send_progress(evaluation_id, "Evaluation complete!", 100)
        logger.info(f"Evaluation {evaluation_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Error in evaluation: {str(e)}\n{traceback.format_exc()}")
        send_progress(evaluation_id, f"Error in evaluation: {str(e)}", 100)
        with evaluation_lock:
            evaluation_results[evaluation_id] = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    finally:
        # Ensure progress queue exists before trying to clean it up
        with evaluation_lock:
            if evaluation_id in progress_queues:
                # Don't delete the queue yet, it might still be needed for the client to get the final message
                pass


@app.route('/api/progress/<evaluation_id>')
def get_progress(evaluation_id: str):
    """Stream progress updates to the client."""
    def generate():
        if evaluation_id not in progress_queues:
            logger.error(f"Progress queue for evaluation {evaluation_id} not found")
            yield 'data: ' + json.dumps({
                'message': 'Evaluation not found. Please try starting a new evaluation.',
                'percentage': 100,
                'error': True
            }) + '\n\n'
            return
            
        while True:
            # Check if we have results
            with evaluation_lock:
                if evaluation_id in evaluation_results:
                    results = evaluation_results[evaluation_id]
                    if 'error' in results:
                        # Error occurred during evaluation
                        error_msg = results['error']
                        logger.error(f"Evaluation {evaluation_id} failed: {error_msg}")
                        yield 'data: ' + json.dumps({
                            'message': f"Error: {error_msg}", 
                            'percentage': 100,
                            'error': True
                        }) + '\n\n'
                    else:
                        # Successful completion
                        logger.info(f"Evaluation {evaluation_id} completed successfully")
                        yield 'data: ' + json.dumps({
                            'message': 'Evaluation complete!', 
                            'percentage': 100,
                            'complete': True
                        }) + '\n\n'
                    
                    # Clean up progress queue after sending final message
                    if evaluation_id in progress_queues:
                        del progress_queues[evaluation_id]
                    
                    break
            
            # Wait for progress
            try:
                progress = progress_queues[evaluation_id].get(timeout=1.0)
                yield 'data: ' + json.dumps(progress) + '\n\n'
            except Exception as e:
                # Queue timeout or evaluation_id removed, check if evaluation exists
                with evaluation_lock:
                    if evaluation_id not in progress_queues:
                        logger.error(f"Progress queue for evaluation {evaluation_id} was removed")
                        yield 'data: ' + json.dumps({
                            'message': 'Evaluation was cancelled or timed out', 
                            'percentage': 100,
                            'error': True
                        }) + '\n\n'
                        break
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@app.route('/api/results/<evaluation_id>')
def get_results(evaluation_id: str):
    """Retrieve evaluation results."""
    with evaluation_lock:
        if evaluation_id not in evaluation_results:
            logger.error(f"Results not found for evaluation ID: {evaluation_id}")
            return jsonify({
                'success': False,
                'error': 'Evaluation not found'
            }), 404
        
        results = evaluation_results[evaluation_id]
        if 'error' in results:
            logger.error(f"Error in results for evaluation ID {evaluation_id}: {results['error']}")
            return jsonify({
                'success': False,
                'error': results['error']
            }), 500
        
        # Log the structure of the results
        logger.info(f"Returning results for evaluation ID {evaluation_id}")
        logger.debug(f"Results structure: {list(results.keys())}")
        
        # Ensure all required fields are present
        if 'report' not in results:
            logger.error(f"Missing 'report' in results for evaluation ID {evaluation_id}")
            results['report'] = {
                'scores': {
                    'overall': 5.0,
                    'navigation': 5.0,
                    'ui_design': 5.0,
                    'product_presentation': 5.0,
                    'checkout': 5.0,
                    'mobile': 5.0
                },
                'key_findings': ['No findings available'],
                'recommendations': ['No recommendations available']
            }
        
        return jsonify({
            'success': True,
            'results': results
        })


@app.route('/api/test_connection')
def test_connection():
    """Test the connection to AI APIs."""
    try:
        openai_status = "Not configured"
        anthropic_status = "Not configured"
        
        if config.get("api.openai.api_key"):
            try:
                ai_client.test_connection("openai")
                openai_status = "Connected"
            except Exception as e:
                openai_status = f"Error: {str(e)}"
                
        if config.get("api.anthropic.api_key"):
            try:
                ai_client.test_connection("anthropic")
                anthropic_status = "Connected"
            except Exception as e:
                anthropic_status = f"Error: {str(e)}"
        
        return jsonify({
            'success': True,
            'connections': {
                'openai': openai_status,
                'anthropic': anthropic_status
            }
        })
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        return jsonify(format_error_response(e)), 500


@app.route('/api/personas', methods=['GET'])
def get_personas():
    """Generate and return personas for testing."""
    try:
        count = int(request.args.get('count', 1))
        if count < 1 or count > 5:
            raise ValidationError("Count must be between 1 and 5", field="count", value=count)
        
        personas = []
        for _ in range(count):
            persona = persona_generator.generate()
            personas.append(persona)
        
        return jsonify({
            'success': True,
            'personas': personas
        })
    except Exception as e:
        logger.error(f"Error generating personas: {e}")
        return jsonify(format_error_response(e)), 400


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    logger.error(f"Server error: {e}")
    return render_template('500.html'), 500


if __name__ == '__main__':
    try:
        debug_mode = config.get("app.debug", False)
        host = config.get("app.host", "127.0.0.1")
        port = config.get("app.port", 5000)
        
        logger.info(f"Starting server on {host}:{port} (debug={debug_mode})")
        app.run(debug=debug_mode, host=host, port=port)
    except Exception as e:
        logger.critical(f"Failed to start server: {e}")
        sys.exit(1) 