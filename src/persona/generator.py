import random
from typing import List, Dict
from dataclasses import dataclass
from src.api.openai_client import OpenAIClient

@dataclass
class Persona:
    """Represents a user persona with various attributes."""
    id: str
    age: int
    gender: str
    location: str
    education: str
    occupation: str
    tech_savviness: int  # 1-10 scale
    shopping_frequency: str
    preferred_categories: List[str]
    accessibility_needs: List[str]
    narrative: str = ""  # AI-generated narrative about the persona

class PersonaGenerator:
    """Generate realistic user personas for website evaluation."""
    
    def __init__(self, openai_client: OpenAIClient = None):
        """Initialize with OpenAI client."""
        self.openai_client = openai_client
        self.personas = []
        
        # Define possible values for persona attributes
        self.genders = ['Male', 'Female', 'Non-binary']
        self.education_levels = ['High School', 'Bachelor\'s', 'Master\'s', 'PhD']
        self.shopping_frequencies = ['Daily', 'Weekly', 'Monthly', 'Rarely']
        self.categories = ['Electronics', 'Fashion', 'Home', 'Books', 'Sports']
        self.accessibility_needs = ['None', 'Visual', 'Motor', 'Cognitive']
    
    def generate(self) -> dict:
        """Generate a single persona with e-commerce specific attributes."""
        prompt = """
        Create a detailed e-commerce shopper persona with the following attributes:
        
        1. Identity:
           - Full name (first and last name)
           - Age (a specific number between 18-75)
           - Gender (Male, Female, Non-binary)
           - Location (City, Country)
           - Occupation (specific job title)
           - Income level (Low, Medium, High with approximate annual amount)
           - Family status (single, married, children)
           - Education level (High School, Bachelor's, Master's, PhD)
        
        2. Shopping Behavior:
           - Shopping frequency (daily, weekly, monthly)
           - Average order value (in USD)
           - Price sensitivity (budget, mid-range, luxury)
           - Brand loyalty (loyal to brands or price-driven)
           - Research behavior (impulse buyer vs. extensive researcher)
        
        3. Technical Profile:
           - Devices used (mobile, tablet, desktop, percentages of each)
           - Technical proficiency (specific number on 1-10 scale)
           - Social media usage (platforms and frequency)
           - Preferred payment methods (credit card, PayPal, etc.)
        
        4. E-commerce Specific:
           - Product categories of interest (specific categories)
           - Previous online shopping experience (specific number on 1-10 scale)
           - Patience level for website issues (specific number on 1-10 scale)
           - Importance of reviews/ratings (specific number on 1-10 scale)
           - Importance of shipping speed/cost (specific number on 1-10 scale)
        
        5. Accessibility Needs:
           - Any visual, motor, or cognitive considerations (be specific)
        
        6. Shopping Goals:
           - Primary goal for visiting an e-commerce site
           - Secondary objectives
           - Success criteria for a shopping experience
        
        Return as a JSON object with these exact fields. Do not include any explanatory text outside the JSON.
        """
        
        try:
            response = self.openai_client.generate_text(prompt)
            
            # Process the response to ensure it's valid JSON
            import json
            import re
            
            # Extract JSON if it's wrapped in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response
                
            # Clean up any non-JSON text
            json_str = re.sub(r'^[^{]*', '', json_str)
            json_str = re.sub(r'[^}]*$', '', json_str)
            
            try:
                persona = json.loads(json_str)
                
                # Validate and provide defaults for essential fields
                self._validate_and_fix_persona(persona)
                
                return persona
            except json.JSONDecodeError as e:
                print(f"Error parsing persona JSON: {e}")
                print(f"Raw JSON string: {json_str}")
                return self._generate_fallback_persona()
        except Exception as e:
            print(f"Error generating persona: {e}")
            return self._generate_fallback_persona()
    
    def _validate_and_fix_persona(self, persona):
        """Validate persona data and fill in defaults for missing fields."""
        # Ensure demographics exist
        if 'demographics' not in persona:
            persona['demographics'] = {}
            
        demographics = persona['demographics']
        if not demographics.get('name'):
            demographics['name'] = self._generate_random_name()
        if not demographics.get('age'):
            demographics['age'] = random.randint(18, 75)
        if not demographics.get('gender'):
            demographics['gender'] = random.choice(['Male', 'Female', 'Non-binary'])
        if not demographics.get('location'):
            demographics['location'] = f"{random.choice(['New York', 'London', 'Tokyo', 'Sydney', 'Berlin'])}, {random.choice(['USA', 'UK', 'Japan', 'Australia', 'Germany'])}"
        if not demographics.get('occupation'):
            demographics['occupation'] = random.choice(['Software Developer', 'Teacher', 'Marketing Manager', 'Doctor', 'Student', 'Retail Worker'])
            
        # Ensure shopping behavior exists
        if 'shopping_behavior' not in persona:
            persona['shopping_behavior'] = {}
            
        shopping = persona['shopping_behavior']
        if not shopping.get('frequency'):
            shopping['frequency'] = random.choice(['Daily', 'Weekly', 'Monthly', 'Rarely'])
        if not shopping.get('price_sensitivity'):
            shopping['price_sensitivity'] = random.choice(['Budget', 'Mid-range', 'Luxury'])
        if not shopping.get('product_categories'):
            shopping['product_categories'] = random.sample(['Electronics', 'Fashion', 'Home', 'Books', 'Sports', 'Beauty', 'Food'], k=random.randint(1, 3))
            
        # Ensure technical profile exists
        if 'technical' not in persona:
            persona['technical'] = {}
            
        technical = persona['technical']
        if not technical.get('proficiency'):
            technical['proficiency'] = random.randint(1, 10)
        if not technical.get('devices'):
            technical['devices'] = {'mobile': random.randint(20, 80), 'desktop': random.randint(20, 80), 'tablet': random.randint(0, 40)}
            # Normalize to 100%
            total = sum(technical['devices'].values())
            for key in technical['devices']:
                technical['devices'][key] = int((technical['devices'][key] / total) * 100)
                
        # Ensure accessibility needs exist
        if 'accessibility_needs' not in persona:
            persona['accessibility_needs'] = random.choice([
                [],
                ['Visual - Needs larger text'],
                ['Motor - Difficulty with precise clicking'],
                ['Cognitive - Prefers simple interfaces']
            ])
            
        # Ensure goals exist
        if 'goals' not in persona:
            persona['goals'] = {
                'primary': random.choice(['Find a specific product', 'Browse for deals', 'Research options', 'Make a purchase']),
                'secondary': random.choice(['Compare prices', 'Read reviews', 'Check shipping options', 'Find contact information'])
            }
    
    def _generate_random_name(self):
        """Generate a random full name."""
        first_names = [
            'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda', 
            'William', 'Elizabeth', 'David', 'Susan', 'Richard', 'Jessica', 'Joseph', 'Sarah',
            'Thomas', 'Karen', 'Charles', 'Nancy', 'Christopher', 'Lisa', 'Daniel', 'Margaret',
            'Matthew', 'Betty', 'Anthony', 'Sandra', 'Mark', 'Ashley', 'Donald', 'Dorothy',
            'Steven', 'Kimberly', 'Paul', 'Emily', 'Andrew', 'Donna', 'Joshua', 'Michelle',
            'Kenneth', 'Carol', 'Kevin', 'Amanda', 'Brian', 'Melissa', 'George', 'Deborah',
            'Timothy', 'Stephanie', 'Ronald', 'Rebecca', 'Edward', 'Laura', 'Jason', 'Sharon',
            'Jeffrey', 'Cynthia', 'Ryan', 'Kathleen', 'Jacob', 'Amy', 'Gary', 'Shirley',
            'Nicholas', 'Angela', 'Eric', 'Helen', 'Jonathan', 'Anna', 'Stephen', 'Brenda',
            'Larry', 'Pamela', 'Justin', 'Nicole', 'Scott', 'Samantha', 'Brandon', 'Katherine',
            'Benjamin', 'Emma', 'Samuel', 'Ruth', 'Gregory', 'Christine', 'Alexander', 'Catherine',
            'Frank', 'Debra', 'Patrick', 'Rachel', 'Raymond', 'Carolyn', 'Jack', 'Janet',
            'Dennis', 'Virginia', 'Jerry', 'Maria', 'Tyler', 'Heather', 'Aaron', 'Diane',
            'Jose', 'Julie', 'Adam', 'Joyce', 'Nathan', 'Victoria', 'Henry', 'Kelly',
            'Zachary', 'Christina', 'Douglas', 'Lauren', 'Peter', 'Joan', 'Kyle', 'Evelyn'
        ]
        
        last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
            'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
            'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
            'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
            'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores',
            'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell',
            'Carter', 'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner', 'Diaz', 'Parker',
            'Cruz', 'Edwards', 'Collins', 'Reyes', 'Stewart', 'Morris', 'Morales', 'Murphy',
            'Cook', 'Rogers', 'Gutierrez', 'Ortiz', 'Morgan', 'Cooper', 'Peterson', 'Bailey',
            'Reed', 'Kelly', 'Howard', 'Ramos', 'Kim', 'Cox', 'Ward', 'Richardson', 'Watson',
            'Brooks', 'Chavez', 'Wood', 'James', 'Bennett', 'Gray', 'Mendoza', 'Ruiz', 'Hughes',
            'Price', 'Alvarez', 'Castillo', 'Sanders', 'Patel', 'Myers', 'Long', 'Ross',
            'Foster', 'Jimenez', 'Powell', 'Jenkins', 'Perry', 'Russell', 'Sullivan', 'Bell'
        ]
        
        return f"{random.choice(first_names)} {random.choice(last_names)}"
    
    def _generate_fallback_persona(self):
        """Generate a basic fallback persona if the AI generation fails."""
        name = self._generate_random_name()
        age = random.randint(18, 75)
        gender = random.choice(['Male', 'Female', 'Non-binary'])
        location = f"{random.choice(['New York', 'London', 'Tokyo', 'Sydney', 'Berlin'])}, {random.choice(['USA', 'UK', 'Japan', 'Australia', 'Germany'])}"
        
        return {
            "demographics": {
                "name": name,
                "age": age,
                "gender": gender,
                "location": location,
                "occupation": random.choice(['Software Developer', 'Teacher', 'Marketing Manager', 'Doctor', 'Student', 'Retail Worker']),
                "income_level": random.choice(['Low', 'Medium', 'High']),
                "family_status": random.choice(['Single', 'Married', 'Married with children']),
                "education_level": random.choice(['High School', 'Bachelor\'s', 'Master\'s', 'PhD'])
            },
            "shopping_behavior": {
                "frequency": random.choice(['Daily', 'Weekly', 'Monthly', 'Rarely']),
                "average_order_value": f"${random.randint(20, 500)}",
                "price_sensitivity": random.choice(['Budget', 'Mid-range', 'Luxury']),
                "brand_loyalty": random.choice(['Brand loyal', 'Price-driven']),
                "research_behavior": random.choice(['Impulse buyer', 'Researcher'])
            },
            "technical": {
                "devices": {
                    "mobile": random.randint(20, 80),
                    "desktop": random.randint(20, 80),
                    "tablet": random.randint(0, 40)
                },
                "proficiency": random.randint(1, 10),
                "social_media": random.sample(['Facebook', 'Instagram', 'Twitter', 'TikTok', 'LinkedIn'], k=random.randint(1, 3)),
                "payment_methods": random.sample(['Credit Card', 'PayPal', 'Apple Pay', 'Google Pay'], k=random.randint(1, 2))
            },
            "e_commerce_specific": {
                "product_categories": random.sample(['Electronics', 'Fashion', 'Home', 'Books', 'Sports', 'Beauty', 'Food'], k=random.randint(1, 3)),
                "online_shopping_experience": random.randint(1, 10),
                "patience_level": random.randint(1, 10),
                "importance_of_reviews": random.randint(1, 10),
                "importance_of_shipping": random.randint(1, 10)
            },
            "accessibility_needs": random.choice([
                [],
                ['Visual - Needs larger text'],
                ['Motor - Difficulty with precise clicking'],
                ['Cognitive - Prefers simple interfaces']
            ]),
            "goals": {
                "primary": random.choice(['Find a specific product', 'Browse for deals', 'Research options', 'Make a purchase']),
                "secondary": random.choice(['Compare prices', 'Read reviews', 'Check shipping options', 'Find contact information']),
                "success_criteria": random.choice(['Finding the right product', 'Getting a good price', 'Fast checkout process', 'Clear product information'])
            }
        }
    
    def generate_batch(self, count: int) -> list:
        """Generate multiple personas."""
        return [self.generate() for _ in range(count)]
    
    def list_all(self) -> List[Dict]:
        """Return all generated personas."""
        return [vars(p) for p in self.personas]
    
    def _generate_location(self) -> str:
        """Generate a random location."""
        cities = ['New York', 'London', 'Tokyo', 'Paris', 'Sydney', 'Toronto']
        return random.choice(cities)
    
    def _generate_occupation(self) -> str:
        """Generate a random occupation."""
        occupations = [
            'Software Engineer', 'Teacher', 'Doctor', 'Artist',
            'Business Analyst', 'Student', 'Retired', 'Entrepreneur'
        ]
        return random.choice(occupations)
    
    def _generate_narrative(self, persona: Persona) -> str:
        """Generate a rich narrative description of the persona using OpenAI API."""
        prompt = f"""
        Create a brief but rich narrative description of this e-commerce website user:
        - {persona.age} year old {persona.gender}
        - Lives in {persona.location}
        - {persona.occupation} with {persona.education} education
        - Tech savviness: {persona.tech_savviness}/10
        - Shops {persona.shopping_frequency.lower()}
        - Interested in: {', '.join(persona.preferred_categories)}
        - Accessibility needs: {', '.join(persona.accessibility_needs)}
        
        Focus on their online shopping habits, preferences, and pain points.
        """
        
        try:
            response = self.openai_client.generate_text(prompt)
            return response.strip()
        except Exception as e:
            print(f"Failed to generate narrative: {e}")
            return "" 