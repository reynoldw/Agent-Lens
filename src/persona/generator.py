import random
from typing import List, Dict
from dataclasses import dataclass
from src.api.ai_client import AIClient

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
    
    def __init__(self, ai_client: AIClient = None):
        """Initialize with AI client."""
        self.ai_client = ai_client
        self.personas = []
        
        # Define possible values for persona attributes
        self.genders = ['Male', 'Female', 'Non-binary']
        self.education_levels = ['High School', 'Bachelor\'s', 'Master\'s', 'PhD']
        self.shopping_frequencies = ['Daily', 'Weekly', 'Monthly', 'Rarely']
        self.categories = ['Electronics', 'Fashion', 'Home', 'Books', 'Sports']
        self.accessibility_needs = ['None', 'Visual', 'Motor', 'Cognitive']
    
    def generate(self) -> dict:
        """Generate a single persona with e-commerce specific attributes."""
        # If no AI client is available, generate a random persona
        if not self.ai_client:
            return self._generate_random_persona()
            
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
           - Shopping frequency (Daily, Weekly, Monthly, Rarely)
           - Preferred product categories (at least 2-3 specific categories)
           - Price sensitivity (Low, Medium, High)
           - Brand loyalty (Low, Medium, High)
           - Research behavior (Minimal, Moderate, Extensive)
           
        3. Technical Profile:
           - Tech proficiency (1-10 scale, where 10 is expert)
           - Devices used for shopping (Desktop, Mobile, Tablet, with percentages)
           - Preferred payment methods (at least 2)
           - Social media usage (platforms and frequency)
           - Accessibility needs (if any)
           
        4. Goals and Pain Points:
           - Primary shopping goal
           - Secondary shopping goal
           - Major frustrations with online shopping
           - Features they value most
           
        Format the response as a JSON object with these exact keys:
        {
          "name": "",
          "demographics": {
            "age": 0,
            "gender": "",
            "location": "",
            "occupation": "",
            "income": "",
            "family_status": "",
            "education": ""
          },
          "shopping": {
            "frequency": "",
            "categories": [],
            "price_sensitivity": "",
            "brand_loyalty": "",
            "research_behavior": ""
          },
          "technical": {
            "proficiency": 0,
            "devices": {},
            "payment_methods": [],
            "social_media": {},
            "accessibility_needs": []
          },
          "goals": {
            "primary": "",
            "secondary": "",
            "frustrations": [],
            "valued_features": []
          }
        }
        """
        
        try:
            response = self.ai_client.generate_text(prompt)
            
            # Process the response to ensure it's valid JSON
            import json
            import re
            
            # Extract JSON from the response (in case there's additional text)
            json_match = re.search(r'({[\s\S]*})', response)
            if json_match:
                json_str = json_match.group(1)
                try:
                    persona = json.loads(json_str)
                    # Add a unique ID
                    persona['id'] = f"persona_{len(self.personas) + 1}"
                    self.personas.append(persona)
                    return persona
                except json.JSONDecodeError:
                    # If JSON parsing fails, fall back to random generation
                    return self._generate_random_persona()
            else:
                # If no JSON found, fall back to random generation
                return self._generate_random_persona()
                
        except Exception as e:
            # If AI generation fails, fall back to random generation
            return self._generate_random_persona()
            
    def _generate_random_persona(self) -> dict:
        """Generate a random persona when AI generation is not available."""
        import random
        
        # Generate a random name
        first_names = ["John", "Jane", "Michael", "Emily", "David", "Sarah", "Robert", "Lisa", "William", "Emma"]
        last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis", "Miller", "Wilson", "Moore", "Taylor"]
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        
        # Generate random demographics
        age = random.randint(18, 75)
        gender = random.choice(self.genders)
        locations = ["New York, USA", "London, UK", "Toronto, Canada", "Sydney, Australia", "Berlin, Germany"]
        location = random.choice(locations)
        
        occupations = ["Software Developer", "Teacher", "Marketing Manager", "Doctor", "Student", "Retired", "Sales Representative"]
        occupation = random.choice(occupations)
        
        income_levels = ["Low ($30,000)", "Medium ($60,000)", "High ($100,000+)"]
        income = random.choice(income_levels)
        
        family_statuses = ["Single", "Married", "Married with children", "Single parent", "Divorced"]
        family_status = random.choice(family_statuses)
        
        education = random.choice(self.education_levels)
        
        # Generate random shopping behavior
        frequency = random.choice(self.shopping_frequencies)
        num_categories = random.randint(2, 4)
        categories = random.sample(self.categories, num_categories)
        
        sensitivity_levels = ["Low", "Medium", "High"]
        price_sensitivity = random.choice(sensitivity_levels)
        brand_loyalty = random.choice(sensitivity_levels)
        
        research_behaviors = ["Minimal", "Moderate", "Extensive"]
        research_behavior = random.choice(research_behaviors)
        
        # Generate random technical profile
        proficiency = random.randint(1, 10)
        
        devices = {
            "Desktop": random.randint(0, 100),
            "Mobile": random.randint(0, 100),
            "Tablet": random.randint(0, 100)
        }
        # Normalize to 100%
        total = sum(devices.values())
        devices = {k: round(v / total * 100) for k, v in devices.items()}
        
        payment_methods = random.sample(["Credit Card", "PayPal", "Apple Pay", "Google Pay", "Bank Transfer"], random.randint(1, 3))
        
        social_platforms = ["Facebook", "Instagram", "Twitter", "LinkedIn", "TikTok"]
        social_media = {platform: random.choice(["Never", "Rarely", "Sometimes", "Often", "Daily"]) 
                        for platform in random.sample(social_platforms, random.randint(1, 4))}
        
        num_accessibility_needs = random.randint(0, 2)
        accessibility_needs = random.sample(self.accessibility_needs, num_accessibility_needs)
        if "None" in accessibility_needs and len(accessibility_needs) > 1:
            accessibility_needs.remove("None")
        
        # Generate random goals and pain points
        primary_goals = [
            "Find a specific product",
            "Browse for deals",
            "Research options before buying",
            "Make a quick purchase",
            "Check prices"
        ]
        primary_goal = random.choice(primary_goals)
        
        secondary_goals = [
            "Compare prices across sites",
            "Read reviews",
            "Find discount codes",
            "Check shipping options",
            "Learn about return policies"
        ]
        secondary_goal = random.choice(secondary_goals)
        
        frustrations = [
            "Slow loading pages",
            "Complicated checkout process",
            "Limited payment options",
            "Poor product descriptions",
            "Difficult navigation",
            "Hidden shipping costs",
            "Lack of customer reviews"
        ]
        num_frustrations = random.randint(1, 3)
        selected_frustrations = random.sample(frustrations, num_frustrations)
        
        valued_features = [
            "Fast checkout",
            "Detailed product information",
            "Customer reviews",
            "Easy navigation",
            "Clear return policy",
            "Multiple payment options",
            "Free shipping"
        ]
        num_features = random.randint(1, 3)
        selected_features = random.sample(valued_features, num_features)
        
        # Create the persona dictionary
        persona = {
            "id": f"persona_{len(self.personas) + 1}",
            "name": name,
            "demographics": {
                "age": age,
                "gender": gender,
                "location": location,
                "occupation": occupation,
                "income": income,
                "family_status": family_status,
                "education": education
            },
            "shopping": {
                "frequency": frequency,
                "categories": categories,
                "price_sensitivity": price_sensitivity,
                "brand_loyalty": brand_loyalty,
                "research_behavior": research_behavior
            },
            "technical": {
                "proficiency": proficiency,
                "devices": devices,
                "payment_methods": payment_methods,
                "social_media": social_media,
                "accessibility_needs": accessibility_needs
            },
            "goals": {
                "primary": primary_goal,
                "secondary": secondary_goal,
                "frustrations": selected_frustrations,
                "valued_features": selected_features
            }
        }
        
        self.personas.append(persona)
        return persona
    
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
            response = self.ai_client.generate_text(prompt)
            return response.strip()
        except Exception as e:
            print(f"Failed to generate narrative: {e}")
            return "" 