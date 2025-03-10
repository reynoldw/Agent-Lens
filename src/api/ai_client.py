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
        
        # Default models
        self.openai_model = "gpt-4o-mini"
        self.anthropic_model = "claude-3-opus-20240229"
    
    def test_connection(self, provider: Optional[ModelProvider] = None) -> bool:
        """Test the AI API connection."""
        provider = provider or self.default_provider
        
        try:
            if provider == "openai" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Use a smaller model for testing
                    messages=[{"role": "system", "content": "Test connection"}],
                    max_tokens=1
                )
            elif provider == "anthropic" and self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model="claude-3-haiku-20240307",  # Use a smaller model for testing
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
                model = model or self.openai_model
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
                model = model or self.anthropic_model
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
        """Analyze sentiment of text."""
        provider = provider or self.default_provider
        
        prompt = f"""
        Analyze the sentiment of the following text and return a JSON object with the following structure:
        {{
            "positive": 0.0 to 1.0,
            "neutral": 0.0 to 1.0,
            "negative": 0.0 to 1.0,
            "overall": "positive", "neutral", or "negative"
        }}
        
        Text to analyze:
        {text}
        
        Return only the JSON object, no other text.
        """
        
        try:
            if provider == "openai" and self.openai_client:
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[
                        {"role": "system", "content": "You are a sentiment analysis assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=200
                )
                result = response.choices[0].message.content
                
            elif provider == "anthropic" and self.anthropic_client:
                response = self.anthropic_client.messages.create(
                    model=self.anthropic_model,
                    max_tokens=200,
                    messages=[
                        {"role": "system", "content": "You are a sentiment analysis assistant."},
                        {"role": "user", "content": prompt}
                    ]
                )
                result = response.content[0].text
                
            else:
                raise ValueError(f"No client available for provider: {provider}")
                
            # Extract JSON from response
            import json
            import re
            
            # Find JSON in the response
            json_match = re.search(r'({.*})', result, re.DOTALL)
            if json_match:
                sentiment = json.loads(json_match.group(1))
                return sentiment
            else:
                raise ValueError("Could not extract sentiment JSON from response")
                
        except Exception as e:
            raise Exception(f"Sentiment analysis error: {str(e)}")
    
    def enhance_review(self, raw_review: Dict[Any, Any], provider: Optional[ModelProvider] = None) -> str:
        """Enhance a raw review with more details and better structure."""
        provider = provider or self.default_provider
        
        prompt = f"""
        Enhance the following e-commerce website review with more details and better structure.
        Make it sound natural and conversational while maintaining the original sentiment and key points.
        
        Original review:
        {raw_review.get('content', '')}
        
        Rating: {raw_review.get('rating', 3)}/5
        Sentiment: {raw_review.get('sentiment', 'neutral')}
        
        Return the enhanced review with clear sections for different aspects of the website.
        """
        
        return self.generate_text(prompt, provider=provider, max_tokens=1000)
    
    def synthesize_report(self, reviews: list, provider: Optional[ModelProvider] = None) -> str:
        """Synthesize a report from multiple reviews."""
        provider = provider or self.default_provider
        
        reviews_text = "\n\n".join([f"Review {i+1}: {r.get('content', '')}" for i, r in enumerate(reviews)])
        
        prompt = f"""
        Synthesize a comprehensive report based on the following user reviews of an e-commerce website.
        Identify common themes, issues, and positive aspects mentioned across reviews.
        
        Reviews:
        {reviews_text}
        
        Your report should include:
        1. Executive summary
        2. Common positive aspects
        3. Common issues or pain points
        4. Recommendations for improvement
        5. Overall assessment
        
        Format the report with clear headings and bullet points where appropriate.
        """
        
        return self.generate_text(prompt, provider=provider, max_tokens=1500) 