from flask import Flask, render_template, request, jsonify, Response
from dotenv import load_dotenv
import os
import json
import traceback
from queue import Queue
from threading import Thread
import threading
from datetime import datetime

# Import modules
from src.persona.generator import PersonaGenerator
from src.interaction.simulator import WebsiteSimulator
from src.review.generator import ReviewGenerator
from src.expert.analyzer import ExpertAnalyzer
from src.api.ai_client import AIClient

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize AI client with available API keys
ai_client = AIClient(
    openai_api_key=os.getenv('OPENAI_API_KEY'),
    anthropic_api_key=os.getenv('ANTHROPIC_API_KEY')
)

# Initialize components with AI client
persona_generator = PersonaGenerator(ai_client=ai_client)
website_simulator = WebsiteSimulator()
review_generator = ReviewGenerator(ai_client=ai_client)
expert_analyzer = ExpertAnalyzer(ai_client=ai_client)

# Global progress queue and results dictionary
progress_queue = Queue()
evaluation_results = {}
evaluation_lock = threading.Lock()

def send_progress(message: str, percentage: int = None):
    """Send progress update to client."""
    data = {
        'message': message,
        'percentage': percentage
    }
    progress_queue.put(data)

@app.route('/')
def index():
    """Render the main dashboard."""
    return render_template('index.html')

@app.route('/api/progress')
def progress():
    """SSE endpoint for progress updates."""
    def generate():
        while True:
            data = progress_queue.get()
            yield f"data: {json.dumps(data)}\n\n"
            if data.get('percentage') == 100 or (data.get('message') and data['message'].startswith('Error')):
                break
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/evaluate', methods=['POST'])
def evaluate_website():
    """Handle website evaluation request."""
    data = request.json
    website_url = data.get('url')
    num_personas = data.get('num_personas', 20)
    evaluation_id = f"eval_{len(evaluation_results)}"
    
    def run_evaluation():
        try:
            # Validate OpenAI API key
            if not os.getenv('OPENAI_API_KEY'):
                raise ValueError("OpenAI API key is not set. Please check your .env file.")
            
            # Test OpenAI API connection
            try:
                send_progress("Testing OpenAI API connection...", 5)
                ai_client.test_connection()
                send_progress("OpenAI API connection successful", 10)
            except Exception as e:
                raise ValueError(f"Failed to connect to OpenAI API: {str(e)}")
            
            print(f"Starting evaluation for {website_url} with {num_personas} personas...")
            
            # Generate personas
            send_progress(f"Generating {num_personas} personas...", 10)
            try:
                personas = persona_generator.generate_batch(num_personas)
                print(f"Generated {len(personas)} personas successfully")
                
                # Log persona details
                persona_details = []
                for i, persona in enumerate(personas, 1):
                    if isinstance(persona, dict):
                        # Extract key details for logging
                        demographics = persona.get('demographics', {})
                        tech = persona.get('technical', {})
                        shopping = persona.get('shopping_behavior', {})
                        
                        details = {
                            'id': f"persona_{i}",
                            'age': demographics.get('age', 'Unknown'),
                            'gender': demographics.get('gender', 'Unknown'),
                            'location': demographics.get('location', 'Unknown'),
                            'occupation': demographics.get('occupation', 'Unknown'),
                            'tech_proficiency': tech.get('proficiency', 'Unknown'),
                            'shopping_frequency': shopping.get('frequency', 'Unknown'),
                            'product_categories': shopping.get('product_categories', []),
                            'accessibility_needs': persona.get('accessibility_needs', [])
                        }
                        persona_details.append(details)
                    else:
                        # Handle old format
                        persona_details.append({
                            'id': getattr(persona, 'id', f"persona_{i}"),
                            'age': getattr(persona, 'age', 'Unknown'),
                            'gender': getattr(persona, 'gender', 'Unknown'),
                            'location': getattr(persona, 'location', 'Unknown'),
                            'tech_savviness': getattr(persona, 'tech_savviness', 'Unknown'),
                            'shopping_frequency': getattr(persona, 'shopping_frequency', 'Unknown'),
                            'preferred_categories': getattr(persona, 'preferred_categories', []),
                            'accessibility_needs': getattr(persona, 'accessibility_needs', [])
                        })
                
                # Send persona details as a progress update
                send_progress(f"Generated {len(personas)} personas: " + json.dumps(persona_details), 15)
                
                # Log full persona details for debugging
                for i, persona in enumerate(personas, 1):
                    send_progress(f"Full Persona {i} Details: " + json.dumps(persona), 15)
                
            except Exception as e:
                print(f"Error generating personas: {str(e)}")
                raise
            
            # Simulate interactions
            simulation_results = []
            for i, persona in enumerate(personas, 1):
                progress = 15 + (i / len(personas) * 35)  # 15-50%
                send_progress(f"Simulating interaction for persona {i}/{len(personas)}...", int(progress))
                try:
                    result = website_simulator.simulate(website_url, persona)
                    simulation_results.append(result)
                    
                    # Log simulation result summary
                    result_summary = {
                        'persona_id': f"persona_{i}",
                        'navigation_score': result.get('navigation_score', 0),
                        'design_score': result.get('design_score', 0),
                        'findability_score': result.get('findability_score', 0),
                        'issues_count': len(result.get('issues', [])),
                        'successful_actions': len(result.get('successful_actions', [])),
                        'failed_actions': len(result.get('failed_actions', []))
                    }
                    send_progress(f"Completed simulation for persona {i}: " + json.dumps(result_summary), int(progress))
                    
                    # Log detailed simulation results
                    detailed_results = {
                        'successful_actions': result.get('successful_actions', []),
                        'failed_actions': result.get('failed_actions', []),
                        'issues': result.get('issues', []),
                        'accessibility_issues': result.get('accessibility_issues', []),
                        'load_times': result.get('load_times', {})
                    }
                    send_progress(f"Detailed simulation results for persona {i}: " + json.dumps(detailed_results), int(progress))
                    
                    print(f"Completed simulation for persona {i}")
                except Exception as e:
                    print(f"Error in simulation for persona {i}: {str(e)}")
                    raise
            
            # Generate reviews
            send_progress("Generating reviews...", 50)
            reviews = []
            for i, (result, persona) in enumerate(zip(simulation_results, personas), 1):
                progress = 50 + (i / len(personas) * 30)  # 50-80%
                send_progress(f"Generating review {i}/{len(personas)}...", int(progress))
                try:
                    review = review_generator.generate(result, persona)
                    reviews.append(review)
                    
                    # Log review summary
                    review_summary = {
                        'persona_id': f"persona_{i}",
                        'scores': review.get('scores', {}),
                        'issues_count': len(review.get('issues', [])),
                        'recommendations_count': len(review.get('recommendations', []))
                    }
                    send_progress(f"Generated review {i}: " + json.dumps(review_summary), int(progress))
                    
                    # Log full review text
                    full_review_text = review.get('full_review', '')
                    if full_review_text:
                        # Truncate if too long for the progress message
                        if len(full_review_text) > 1000:
                            truncated_review = full_review_text[:1000] + "... [truncated]"
                            send_progress(f"Review {i} Full Text (truncated): " + truncated_review, int(progress))
                        else:
                            send_progress(f"Review {i} Full Text: " + full_review_text, int(progress))
                    
                    print(f"Generated review {i}")
                except Exception as e:
                    print(f"Error generating review {i}: {str(e)}")
                    raise
            
            # Generate expert analysis
            send_progress("Generating expert analysis...", 80)
            try:
                report = expert_analyzer.analyze(website_url, simulation_results, reviews)
                
                # Log report summary
                report_summary = {
                    'overall_score': report.get('overall_scores', {}).get('overall', 0),
                    'findings_count': len(report.get('key_findings', [])),
                    'recommendations_count': len(report.get('recommendations', []))
                }
                send_progress(f"Expert analysis completed: " + json.dumps(report_summary), 90)
                
                print("Expert analysis completed successfully")
            except Exception as e:
                print(f"Error in expert analysis: {str(e)}")
                raise
            
            # Store results
            with evaluation_lock:
                evaluation_results[evaluation_id] = {
                    'status': 'success',
                    'report': report
                }
            
            send_progress("Evaluation complete!", 100)
            print("Evaluation completed successfully")
        
        except Exception as e:
            print(f"Evaluation failed: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            error_details = {
                'error': str(e),
                'traceback': traceback.format_exc()
            }
            with evaluation_lock:
                evaluation_results[evaluation_id] = {
                    'status': 'error',
                    'message': str(e),
                    'details': error_details
                }
            send_progress(f"Error: {str(e)}", None)
    
    # Start evaluation in a background thread
    thread = Thread(target=run_evaluation)
    thread.daemon = True  # Make thread daemon so it doesn't block server shutdown
    thread.start()
    
    return jsonify({
        'status': 'started',
        'evaluation_id': evaluation_id
    })

@app.route('/api/results/<evaluation_id>', methods=['GET'])
def get_results(evaluation_id):
    """Get the results of an evaluation."""
    with evaluation_lock:
        if evaluation_id not in evaluation_results:
            return jsonify({
                'status': 'error',
                'message': 'Evaluation not found'
            }), 404
        return jsonify(evaluation_results[evaluation_id])

@app.route('/api/personas', methods=['GET'])
def list_personas():
    """List all generated personas."""
    personas = persona_generator.list_all()
    return jsonify(personas)

@app.route('/api/reviews', methods=['GET'])
def list_reviews():
    """List all generated reviews."""
    reviews = review_generator.list_all()
    return jsonify(reviews)

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('favicon.ico')

if __name__ == '__main__':
    app.run(debug=True) 