from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re
import datetime
from src.persona.generator import Persona
from src.interaction.simulator import SimulationResult
from src.api.openai_client import OpenAIClient

@dataclass
class Review:
    """Represents a complete website review."""
    id: str
    timestamp: datetime
    website_url: str
    persona_id: str
    scores: Dict[str, float]
    metrics: Dict[str, any]
    issues: List[str]
    summary: str
    detailed_review: str
    sentiment_scores: Optional[Dict[str, float]] = None

class ReviewGenerator:
    """Generate detailed website reviews based on simulated interactions."""
    
    def __init__(self, openai_client):
        """Initialize with OpenAI client."""
        self.openai_client = openai_client
        self.reviews = []
    
    def generate(self, simulation_result, persona):
        """Generate a comprehensive review based on simulation results and persona."""
        # Extract key information from simulation result
        website_url = simulation_result.get('website_url', 'Unknown')
        interaction_data = simulation_result.get('interaction_data', {})
        
        # Create a detailed prompt for the AI
        prompt = f"""
      You are  {self._format_persona(persona)} Today, you visited the  WEBSITE: {website_url}, an e-commerce platform. As someone who values user experience, reliability, and ease of use, please provide a detailed review of your experience on this website. In your review, consider the following aspects:
        
        Here are some of your interactions with the website, if this data is not available or broken, please use your own knowledge of the website to provide a review.
        {self._format_interaction_data(interaction_data)}
                
        1. OVERALL ASSESSMENT:
           - Detailed summary of your own experience (2-3 sentences)
           - Overall rating (1-10)
        
        2. UX/UI EVALUATION:
           - Visual design assessment (colors, typography, imagery)
           - Layout and information hierarchy
           - Responsive design effectiveness
           - Brand consistency
           - Score: X/10
        
        3. NAVIGATION & INFORMATION ARCHITECTURE:
           - Menu structure and organization
           - Search functionality
           - Filtering and sorting options
           - Breadcrumbs and wayfinding
           - Category organization
           - Score: X/10
        
        4. PRODUCT PRESENTATION:
           - Product image quality and quantity
           - Product descriptions and specifications
           - Pricing presentation
           - Inventory/availability information
           - Cross-selling and upselling
           - Score: X/10
        
        5. CHECKOUT PROCESS:
           - Cart functionality
           - Checkout flow
           - Form design and validation
           - Payment options
           - Order summary clarity
           - Score: X/10
        
        6. MOBILE EXPERIENCE:
           - Touch targets and interactions
           - Content readability on small screens
           - Performance on mobile
           - Score: X/10
        
        7. KEY ISSUES (prioritized):
           - Critical issues (blocking purchases)
           - Major issues (causing significant friction)
           - Minor issues (small annoyances)
        
        8. POSITIVE ASPECTS:
           - What the site does particularly well
        
        9. SPECIFIC RECOMMENDATIONS:
           - Quick wins (easy to implement)
           - Medium-term improvements
           - Strategic changes
        
        10. COMPETITIVE ANALYSIS:
            - How this site compares to industry standards
            - Areas where competitors perform better
        
        Please respond with a detailed review in a friendly, conversational tone that reflects your persona’s unique perspective. 
        Your review should feel natural, include specific examples from your experience, and provide clear suggestions that the website could implement to improve the user experience.”
        """
        
        # Generate the review using OpenAI
        review_text = self.openai_client.generate_text(prompt, max_tokens=1500)
        
        # Extract scores using regex
        # Default scores
        scores = {
            "ui_design": 5,
            "navigation": 5,
            "product_presentation": 5,
            "checkout": 5,
            "mobile": 5,
            "overall": 5
        }
        
        # Extract scores from the review text
        ui_match = re.search(r'UI.*?Score:\s*(\d+(?:\.\d+)?)/10', review_text, re.DOTALL)
        nav_match = re.search(r'Navigation.*?Score:\s*(\d+(?:\.\d+)?)/10', review_text, re.DOTALL)
        product_match = re.search(r'Product Presentation.*?Score:\s*(\d+(?:\.\d+)?)/10', review_text, re.DOTALL)
        checkout_match = re.search(r'Checkout.*?Score:\s*(\d+(?:\.\d+)?)/10', review_text, re.DOTALL)
        mobile_match = re.search(r'Mobile.*?Score:\s*(\d+(?:\.\d+)?)/10', review_text, re.DOTALL)
        overall_match = re.search(r'Overall.*?rating.*?(\d+(?:\.\d+)?)/10', review_text, re.DOTALL)
        
        if ui_match: scores['ui_design'] = float(ui_match.group(1))
        if nav_match: scores['navigation'] = float(nav_match.group(1))
        if product_match: scores['product_presentation'] = float(product_match.group(1))
        if checkout_match: scores['checkout'] = float(checkout_match.group(1))
        if mobile_match: scores['mobile'] = float(mobile_match.group(1))
        if overall_match: scores['overall'] = float(overall_match.group(1))
        
        # Extract issues using regex
        issues_section = re.search(r'KEY ISSUES.*?(?:POSITIVE ASPECTS|SPECIFIC RECOMMENDATIONS)', review_text, re.DOTALL)
        issues = []
        if issues_section:
            issues_text = issues_section.group(0)
            # Extract bullet points or numbered items
            issues = re.findall(r'[-•*]\s*(.*?)(?=\n|$)', issues_text)
            if not issues:  # Try numbered list
                issues = re.findall(r'\d+\.\s*(.*?)(?=\n|$)', issues_text)
        
        # Extract recommendations
        recommendations_section = re.search(r'SPECIFIC RECOMMENDATIONS.*?(?:COMPETITIVE ANALYSIS|$)', review_text, re.DOTALL)
        recommendations = []
        if recommendations_section:
            recommendations_text = recommendations_section.group(0)
            recommendations = re.findall(r'[-•*]\s*(.*?)(?=\n|$)', recommendations_text)
            if not recommendations:  # Try numbered list
                recommendations = re.findall(r'\d+\.\s*(.*?)(?=\n|$)', recommendations_text)
        
        # Create structured review object
        review = {
            'website_url': website_url,
            'persona': persona,
            'scores': scores,
            'full_review': review_text,
            'issues': issues,
            'recommendations': recommendations,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        self.reviews.append(review)
        return review
    
    def _format_persona(self, persona):
        """Format persona data for the prompt."""
        if isinstance(persona, dict):
            # Format the dictionary as a string
            formatted = []
            for key, value in persona.items():
                if isinstance(value, dict):
                    formatted.append(f"{key.upper()}:")
                    for subkey, subvalue in value.items():
                        formatted.append(f"- {subkey}: {subvalue}")
                else:
                    formatted.append(f"{key}: {value}")
            return "\n".join(formatted)
        else:
            # If it's already a string or other format, return as is
            return str(persona)
    
    def _format_interaction_data(self, data):
        """Format interaction data for the prompt."""
        if isinstance(data, dict):
            formatted = []
            for key, value in data.items():
                if isinstance(value, dict):
                    formatted.append(f"{key.upper()}:")
                    for subkey, subvalue in value.items():
                        formatted.append(f"- {subkey}: {subvalue}")
                elif isinstance(value, list):
                    formatted.append(f"{key.upper()}:")
                    for item in value:
                        formatted.append(f"- {item}")
                else:
                    formatted.append(f"{key}: {value}")
            return "\n".join(formatted)
        else:
            return str(data)
    
    def list_all(self):
        """Return all generated reviews."""
        return self.reviews 