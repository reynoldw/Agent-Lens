from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re
import datetime
from src.persona.generator import Persona
from src.interaction.simulator import SimulationResult
from src.api.ai_client import AIClient

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
    
    def __init__(self, ai_client: AIClient = None):
        """Initialize with AI client."""
        self.ai_client = ai_client
        self.reviews = []
    
    def generate(self, website_url, persona, simulation_result):
        """Generate a comprehensive review based on simulation results and persona."""
        # If no AI client is available, generate a basic review
        if not self.ai_client:
            return self._generate_basic_review(website_url, persona, simulation_result)
            
        # Extract key information from simulation result
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
        
        Please respond with a detailed review in a friendly, conversational tone that reflects your persona's unique perspective. 
        Your review should feel natural, include specific examples from your experience, and provide clear suggestions that the website could implement to improve the user experience.
        """
        
        # Generate the review using AI
        review_text = self.ai_client.generate_text(prompt, max_tokens=1500)
        
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

    def _generate_basic_review(self, website_url, persona, simulation_result):
        """Generate a basic review when AI is not available."""
        import random
        from datetime import datetime
        
        # Extract scores from simulation result
        navigation_score = simulation_result.get('navigation_score', random.uniform(3.0, 8.0))
        design_score = simulation_result.get('design_score', random.uniform(3.0, 8.0))
        findability_score = simulation_result.get('findability_score', random.uniform(3.0, 8.0))
        
        # Calculate overall score
        overall_score = round((navigation_score + design_score + findability_score) / 3, 1)
        
        # Extract issues
        issues = simulation_result.get('issues', [])
        if not issues:
            issues = ["Website navigation could be improved", "Product information could be more detailed"]
            
        # Extract successful actions
        successful_actions = simulation_result.get('successful_actions', [])
        
        # Extract failed actions
        failed_actions = simulation_result.get('failed_actions', [])
        
        # Generate sentiment
        sentiment_options = ["positive", "neutral", "negative"]
        sentiment_weights = [0.4, 0.3, 0.3]  # Slightly biased towards positive
        sentiment = random.choices(sentiment_options, weights=sentiment_weights, k=1)[0]
        
        # Generate rating based on overall score and sentiment
        rating = min(5, max(1, round(overall_score / 2)))  # Convert 10-point scale to 5-point scale
        
        # Adjust rating based on sentiment
        if sentiment == "positive" and rating < 4:
            rating = min(5, rating + 1)
        elif sentiment == "negative" and rating > 2:
            rating = max(1, rating - 1)
        
        # Extract persona information
        persona_name = persona.get('name', 'Anonymous User')
        persona_age = persona.get('demographics', {}).get('age', 35)
        persona_gender = persona.get('demographics', {}).get('gender', 'Unknown')
        persona_occupation = persona.get('demographics', {}).get('occupation', 'Professional')
        persona_tech_level = persona.get('technical', {}).get('tech_proficiency', 'moderate')
        persona_shopping_frequency = persona.get('shopping_behavior', {}).get('online_shopping_frequency', 'occasionally')
        persona_price_sensitivity = persona.get('shopping_behavior', {}).get('price_sensitivity', 'moderate')
        persona_preferred_categories = persona.get('shopping_behavior', {}).get('preferred_categories', [])
        
        # Generate review content based on scores and actions
        positive_phrases = [
            "I found the website easy to navigate",
            "The design is clean and modern",
            "Product information was clear and helpful",
            "The checkout process was straightforward",
            "I liked how the products were categorized",
            "The search functionality worked well",
            "The website loaded quickly on my device",
            "The product images were high quality and showed good detail",
            "I appreciated the customer reviews for products",
            "The filtering options made it easy to find what I wanted"
        ]
        
        negative_phrases = [
            "The website was difficult to navigate",
            "The design feels outdated",
            "Product information was lacking",
            "The checkout process was confusing",
            "The categorization of products wasn't intuitive",
            "The search functionality didn't work as expected",
            "The website loaded slowly on my device",
            "The product images were low quality and didn't show enough detail",
            "There weren't enough customer reviews to make informed decisions",
            "The filtering options were limited and unhelpful"
        ]
        
        neutral_phrases = [
            "The website has a standard layout",
            "The design is functional but not exceptional",
            "Product information was adequate",
            "The checkout process was typical",
            "The categorization of products was as expected",
            "The search functionality was basic",
            "The website loaded at an average speed",
            "The product images were of acceptable quality",
            "There were some customer reviews but more would be helpful",
            "The filtering options were standard"
        ]
        
        # Select phrases based on sentiment and scores
        selected_phrases = []
        
        # Navigation comments
        if navigation_score >= 7:
            selected_phrases.append("The navigation was intuitive and I could easily find my way around the site.")
        elif navigation_score <= 4:
            selected_phrases.append("I struggled with the navigation and often felt lost on the site.")
        else:
            selected_phrases.append("The navigation was adequate but could be more intuitive.")
            
        # Design comments
        if design_score >= 7:
            selected_phrases.append("The design was visually appealing and created a pleasant shopping experience.")
        elif design_score <= 4:
            selected_phrases.append("The design was unappealing and detracted from my shopping experience.")
        else:
            selected_phrases.append("The design was functional but didn't particularly stand out.")
            
        # Findability comments
        if findability_score >= 7:
            selected_phrases.append("I could easily find the products I was looking for.")
        elif findability_score <= 4:
            selected_phrases.append("I had difficulty finding specific products I was interested in.")
        else:
            selected_phrases.append("Finding products was somewhat challenging but manageable.")
        
        # Add tech-level specific comments
        if persona_tech_level == 'low':
            if navigation_score <= 5:
                selected_phrases.append("As someone who isn't very tech-savvy, I found the website challenging to use.")
            else:
                selected_phrases.append("Even though I'm not very tech-savvy, I found the website easy enough to use.")
        elif persona_tech_level == 'high':
            selected_phrases.append("As someone comfortable with technology, I noticed the website could use some technical improvements.")
        
        # Add price sensitivity comments
        if persona_price_sensitivity == 'high':
            selected_phrases.append("I always look for good deals, and I found the pricing on this site to be " + 
                                   ("competitive." if sentiment == "positive" else "too high."))
        elif persona_price_sensitivity == 'low':
            selected_phrases.append("While price isn't my main concern, I appreciate the " + 
                                   ("quality products offered." if sentiment == "positive" else "products but found the quality questionable."))
        
        # Add comments about successful and failed actions
        if successful_actions:
            successful_action_sample = random.sample(successful_actions, min(3, len(successful_actions)))
            for action in successful_action_sample:
                selected_phrases.append(f"I was able to {action.lower()} without any issues.")
            
        if failed_actions:
            failed_action_sample = random.sample(failed_actions, min(3, len(failed_actions)))
            for action in failed_action_sample:
                selected_phrases.append(f"I had trouble with {action.lower()}, which was frustrating.")
        
        # Add category-specific comments if applicable
        if persona_preferred_categories and len(persona_preferred_categories) > 0:
            category = random.choice(persona_preferred_categories)
            if sentiment == "positive":
                selected_phrases.append(f"As someone interested in {category}, I found the selection in this category to be good.")
            elif sentiment == "negative":
                selected_phrases.append(f"As someone interested in {category}, I was disappointed with the limited selection in this category.")
            else:
                selected_phrases.append(f"As someone interested in {category}, I found the selection in this category to be adequate.")
        
        # Add more general phrases based on sentiment
        if sentiment == "positive":
            additional_phrases = random.sample(positive_phrases, min(3, len(positive_phrases)))
        elif sentiment == "negative":
            additional_phrases = random.sample(negative_phrases, min(3, len(negative_phrases)))
        else:
            additional_phrases = random.sample(neutral_phrases, min(3, len(neutral_phrases)))
        
        selected_phrases.extend(additional_phrases)
        random.shuffle(selected_phrases)  # Mix up the phrases for a more natural flow
        
        # Create introduction based on persona
        introduction = f"I'm {persona_name}, a {persona_age}-year-old {persona_occupation} who shops online {persona_shopping_frequency}. "
        introduction += f"I recently visited {website_url} to look for " + (f"{random.choice(persona_preferred_categories)}" if persona_preferred_categories else "products") + "."
        
        # Create detailed review sections
        navigation_section = f"\n\nNAVIGATION (Score: {navigation_score}/10):\n"
        navigation_section += "The website's navigation was " + ("intuitive and well-organized" if navigation_score >= 7 else 
                                                               "adequate but could be improved" if navigation_score >= 5 else 
                                                               "confusing and difficult to use") + ". "
        if failed_actions and any("navigate" in action.lower() or "find" in action.lower() or "explore" in action.lower() for action in failed_actions):
            navigation_section += "I encountered specific issues with finding my way around the site. "
        
        design_section = f"\n\nDESIGN (Score: {design_score}/10):\n"
        design_section += "The visual design was " + ("appealing and modern" if design_score >= 7 else 
                                                    "acceptable but not impressive" if design_score >= 5 else 
                                                    "outdated and unappealing") + ". "
        design_section += "The layout was " + ("clean and helped me focus on products" if design_score >= 7 else 
                                             "somewhat cluttered" if design_score <= 4 else 
                                             "standard for an e-commerce site") + "."
        
        product_section = f"\n\nPRODUCT PRESENTATION (Score: {findability_score}/10):\n"
        product_section += "Products were " + ("well-presented with clear information" if findability_score >= 7 else 
                                             "adequately presented but lacking some details" if findability_score >= 5 else 
                                             "poorly presented with insufficient information") + ". "
        if successful_actions and any("product" in action.lower() for action in successful_actions):
            product_section += "I was able to find and examine products of interest. "
        if failed_actions and any("product" in action.lower() for action in failed_actions):
            product_section += "I had difficulty examining some products in detail. "
        
        # Create conclusion based on overall experience
        if sentiment == "positive":
            conclusion = f"\n\nOVERALL EXPERIENCE (Rating: {rating}/5):\n"
            conclusion += "I had a positive experience on this website and would likely return for future purchases. "
            conclusion += "The site's strengths are " + ("its navigation and user-friendly design" if navigation_score > design_score else "its product presentation and visual appeal") + ". "
            if issues:
                conclusion += f"However, there is room for improvement in {random.choice(issues).lower()}."
        elif sentiment == "negative":
            conclusion = f"\n\nOVERALL EXPERIENCE (Rating: {rating}/5):\n"
            conclusion += "I had a disappointing experience on this website and would hesitate to return. "
            conclusion += "The main issues were " + ("the confusing navigation and poor user experience" if navigation_score < design_score else "the poor product presentation and visual design") + ". "
            if issues:
                conclusion += f"Specifically, {random.choice(issues).lower()} was particularly problematic."
        else:
            conclusion = f"\n\nOVERALL EXPERIENCE (Rating: {rating}/5):\n"
            conclusion += "My experience on this website was average. "
            conclusion += "While there were no major issues, the site didn't particularly impress me either. "
            if issues:
                conclusion += f"Areas for improvement include {random.choice(issues).lower()}."
        
        # Combine all sections into a comprehensive review
        review_content = introduction + "\n\nSUMMARY:\n" + " ".join(selected_phrases[:5]) + navigation_section + design_section + product_section + conclusion
        
        # Create a review dictionary with all necessary information
        review = {
            'review': review_content,
            'rating': rating,
            'sentiment': sentiment,
            'scores': {
                'navigation': navigation_score,
                'design': design_score,
                'findability': findability_score,
                'overall': overall_score
            },
            'persona': {
                'name': persona_name,
                'age': persona_age,
                'gender': persona_gender,
                'occupation': persona_occupation,
                'tech_level': persona_tech_level,
                'shopping_frequency': persona_shopping_frequency
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return review 