from typing import Optional, Dict, Any, Literal
import openai
from anthropic import Anthropic

ModelProvider = Literal["openai", "anthropic"]

class AIClient:
    """Client for interacting with AI APIs (OpenAI and Anthropic Claude)."""
    
    def __init__(self, openai_api_key: Optional[str] = None, anthropic_api_key: Optional[str] = None):
        """Initialize the AI client with API keys."""
        self.openai_api_key = openai_api_key
        self.anthropic_api_key = anthropic_api_key
        
        if not (openai_api_key or anthropic_api_key):
            raise ValueError("At least one API key (OpenAI or Anthropic) is required")
        
        self.openai_client = openai.OpenAI(api_key=openai_api_key) if openai_api_key else None
        self.anthropic_client = Anthropic(api_key=anthropic_api_key) if anthropic_api_key else None
        
        # Default to available client
        self.default_provider = "openai" if openai_api_key else "anthropic"
    
    def test_connection(self, provider: Optional[ModelProvider] = None) -> bool:
        """Test the AI API connection."""
        provider = provider or self.default_provider
        
        try:
            if provider == "openai" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": "Test connection"}],
                    max_tokens=1
                )
            elif provider == "anthropic" and self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=1,
                    messages=[{"role": "user", "content": "Test connection"}]
                )
            return True
        except Exception as e:
            raise Exception(f"Failed to connect to {provider.upper()} API: {str(e)}")
    
    def generate_text(self, 
                     prompt: str, 
                     provider: Optional[ModelProvider] = None,
                     model: Optional[str] = None,
                     max_tokens: int = 500) -> str:
        """Generate text using AI models."""
        provider = provider or self.default_provider
        
        try:
            if provider == "openai" and self.openai_client:
                model = model or "gpt-4"
                response = self.openai_client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant specializing in e-commerce and user experience analysis."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
                
            elif provider == "anthropic" and self.anthropic_client:
                model = model or "claude-3-opus-20240229"
                response = self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant specializing in e-commerce and user experience analysis."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                return response.content[0].text
                
            else:
                raise ValueError(f"No client available for provider: {provider}")
                
        except Exception as e:
            raise Exception(f"{provider.upper()} API error: {str(e)}")
    
    def analyze_sentiment(self, text: str, provider: Optional[ModelProvider] = None) -> Dict[str, float]:
        """Analyze sentiment of text using AI."""
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
            response = self.generate_text(prompt, provider=provider)
            scores = {}
            for line in response.split('\n'):
                if ':' in line:
                    key, value = line.split(':')
                    scores[key.strip().lower()] = float(value.strip())
            return scores
        except Exception as e:
            raise Exception(f"Sentiment analysis failed: {str(e)}")
    
    def enhance_review(self, raw_review: Dict[Any, Any], provider: Optional[ModelProvider] = None) -> str:
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
        
        return self.generate_text(prompt, provider=provider)
    
    def synthesize_report(self, reviews: list, provider: Optional[ModelProvider] = None) -> str:
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
        
        return self.generate_text(prompt, provider=provider, max_tokens=1000) 