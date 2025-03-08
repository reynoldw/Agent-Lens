from typing import Optional, Dict, Any
import openai

class OpenAIClient:
    """Client for interacting with OpenAI API."""
    
    def __init__(self, api_key: str):
        """Initialize the OpenAI client with API key."""
        self.api_key = api_key
        if not api_key:
            raise ValueError("OpenAI API key is required")
        self.client = openai.OpenAI(api_key=api_key)
    
    def test_connection(self):
        """Test the OpenAI API connection."""
        try:
            # Make a simple API call to test the connection
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": "Test connection"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            raise Exception(f"Failed to connect to OpenAI API: {str(e)}")
    
    def generate_text(self, prompt: str, model: str = "gpt-4", max_tokens: int = 500) -> str:
        """Generate text using OpenAI's GPT models."""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant specializing in e-commerce and user experience analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment of text using OpenAI."""
        prompt = f"""
        Analyze the sentiment of the following text and return scores for:
        - Positivity (0-1)
        - Negativity (0-1)
        - Neutrality (0-1)
        
        Text: {text}
        
        Return only the scores in the format:
        Positive: X.XX
        Negative: X.XX
        Neutral: X.XX
        """
        
        try:
            response = self.generate_text(prompt)
            scores = {}
            for line in response.split('\n'):
                if ':' in line:
                    key, value = line.split(':')
                    scores[key.strip().lower()] = float(value.strip())
            return scores
        except Exception as e:
            raise Exception(f"Sentiment analysis failed: {str(e)}")
    
    def enhance_review(self, raw_review: Dict[Any, Any]) -> str:
        """Convert raw review data into natural language review text."""
        prompt = f"""
        Convert this raw review data into a natural, detailed review:
        
        Website: {raw_review.get('website_url')}
        Navigation Score: {raw_review.get('navigation_score')}/10
        Design Score: {raw_review.get('design_score')}/10
        Product Findability: {raw_review.get('findability_score')}/10
        Key Issues: {', '.join(raw_review.get('issues', []))}
        
        Write a detailed but concise review from the perspective of a user,
        highlighting both positive aspects and areas for improvement.
        """
        
        return self.generate_text(prompt)
    
    def synthesize_report(self, reviews: list) -> str:
        """Synthesize multiple reviews into a comprehensive report."""
        reviews_summary = "\n".join([
            f"Review {i+1}: {review.get('summary', 'No summary available')}"
            for i, review in enumerate(reviews)
        ])
        
        prompt = f"""
        Analyze these reviews and create a comprehensive report:
        
        {reviews_summary}
        
        Include:
        1. Overall assessment
        2. Common positive aspects
        3. Common issues or concerns
        4. Specific recommendations for improvement
        5. Priority areas to address
        
        Format the report with clear sections and bullet points.
        """
        
        return self.generate_text(prompt, max_tokens=1000) 