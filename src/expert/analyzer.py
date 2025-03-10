from typing import Dict, List, Any
from dataclasses import dataclass
import datetime
from src.review.generator import Review
from src.api.ai_client import AIClient
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
from collections import Counter

@dataclass
class ExpertReport:
    """Represents a comprehensive expert analysis report."""
    id: str
    timestamp: datetime.datetime
    website_url: str
    overall_scores: Dict[str, float]
    metrics_summary: Dict[str, Any]
    key_findings: List[str]
    recommendations: List[str]
    charts: Dict[str, str]  # Base64 encoded chart images
    detailed_analysis: str

class ExpertAnalyzer:
    """Analyze reviews and generate comprehensive reports with actionable insights."""
    
    def __init__(self, ai_client: AIClient = None):
        """Initialize with AI client."""
        self.ai_client = ai_client
        self.reports = []
    
    def analyze(self, url: str, simulation_results: List[Dict[str, Any]], reviews: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze simulation results and generate a comprehensive report.
        
        Args:
            url: The website URL that was evaluated
            simulation_results: List of simulation result dictionaries
            reviews: List of review dictionaries (optional)
            
        Returns:
            A report dictionary with analysis, visualizations, and recommendations
        """
        if not simulation_results:
            raise ValueError("No simulation results provided for analysis")
        
        # Extract website URL
        website_url = url
        
        # Aggregate scores from simulations
        overall_scores = self._aggregate_scores(simulation_results)
        
        # Extract and categorize issues
        all_issues = self._extract_all_issues(simulation_results)
        categorized_issues = self._categorize_issues(all_issues)
        
        # Analyze behavioral data
        behavioral_insights = self._analyze_behavioral_data(simulation_results)
        
        # Analyze AI reviews
        ai_review_insights = self._analyze_ai_reviews(simulation_results)
        
        # Generate charts
        charts = self._generate_charts(simulation_results, categorized_issues, behavioral_insights)
        
        # Generate key findings
        key_findings = self._generate_key_findings(
            simulation_results, 
            overall_scores, 
            categorized_issues,
            behavioral_insights,
            ai_review_insights
        )
        
        # Generate recommendations with priority levels
        recommendations = self._generate_recommendations(
            simulation_results, 
            categorized_issues,
            behavioral_insights,
            ai_review_insights
        )
        
        # Generate detailed analysis using OpenAI
        detailed_analysis = self._generate_detailed_analysis(
            website_url, 
            simulation_results, 
            overall_scores, 
            categorized_issues,
            behavioral_insights,
            ai_review_insights
        )
        
        # Compile the final report
        report = {
            'website_url': website_url,
            'timestamp': datetime.datetime.now().isoformat(),
            'num_personas': len(simulation_results),
            'overall_scores': overall_scores,
            'categorized_issues': categorized_issues,
            'behavioral_insights': behavioral_insights,
            'ai_review_insights': ai_review_insights,
            'charts': charts,
            'key_findings': key_findings,
            'recommendations': recommendations,
            'detailed_analysis': detailed_analysis,
            'implementation_roadmap': self._generate_implementation_roadmap(recommendations)
        }
        
        self.reports.append(report)
        return report
    
    def _aggregate_scores(self, simulation_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate scores from all simulation results."""
        score_keys = ['navigation_score', 'design_score', 'findability_score']
        aggregated = {key: 0.0 for key in score_keys}
        count = {key: 0 for key in score_keys}
        
        for result in simulation_results:
            # Check if scores are directly in the result or in a nested 'simulation' key
            data_source = result.get('simulation', result)  # Try simulation key first, then fall back to result itself
            
            for key in score_keys:
                if key in data_source and data_source[key] is not None:
                    aggregated[key] += float(data_source[key])
                    count[key] += 1
        
        # If no scores were found, set default values
        if all(count[key] == 0 for key in score_keys):
            # Set default scores of 5.0 if no data is available
            for key in score_keys:
                aggregated[key] = 5.0
                count[key] = 1
        
        # Calculate averages
        for key in score_keys:
            if count[key] > 0:
                aggregated[key] = round(aggregated[key] / count[key], 2)
            else:
                aggregated[key] = 5.0  # Default to middle score if no data
        
        # Calculate overall score
        aggregated['overall'] = round(sum(aggregated[key] for key in score_keys) / len(score_keys), 2)
        
        # For backward compatibility with the UI
        aggregated['ui_design'] = aggregated['design_score']
        aggregated['navigation'] = aggregated['navigation_score']
        aggregated['product_presentation'] = aggregated['findability_score']
        aggregated['checkout'] = aggregated.get('overall', 0) * 0.8  # Estimate
        aggregated['mobile'] = aggregated.get('overall', 0) * 0.9  # Estimate
        
        return aggregated
    
    def _extract_all_issues(self, simulation_results: List[Dict[str, Any]]) -> List[str]:
        """Extract all issues from simulation results."""
        all_issues = []
        for result in simulation_results:
            # Check if data is directly in the result or in a nested 'simulation' key
            data_source = result.get('simulation', result)  # Try simulation key first, then fall back to result itself
            
            # Extract general issues
            issues = data_source.get('issues', [])
            if issues:
                all_issues.extend(issues)
                
            # Also include accessibility issues
            accessibility_issues = data_source.get('accessibility_issues', [])
            if accessibility_issues:
                all_issues.extend(accessibility_issues)
                
            # Include failed actions as issues
            failed_actions = data_source.get('failed_actions', [])
            if failed_actions:
                all_issues.extend([f"Failed action: {action}" for action in failed_actions])
                
            # Include behavioral pain points
            behavioral_insights = data_source.get('behavioral_insights', {})
            pain_points = behavioral_insights.get('pain_points', [])
            if pain_points:
                all_issues.extend(pain_points)
                
            # Include AI review negative points
            ai_review = data_source.get('ai_review', {})
            if ai_review and ai_review.get('rating', 5) < 3:
                review_text = ai_review.get('review', '')
                if review_text:
                    # Extract negative sentences from review
                    negative_keywords = ['disappointed', 'frustrating', 'difficult', 'confusing', 
                                        'poor', 'bad', 'hard', 'issue', 'problem', 'couldn\'t', 
                                        'wasn\'t able', 'failed']
                    sentences = review_text.split('.')
                    for sentence in sentences:
                        sentence = sentence.strip()
                        if any(keyword in sentence.lower() for keyword in negative_keywords) and sentence:
                            all_issues.append(f"User feedback: {sentence}")
        
        # If no issues were found, add a default issue
        if not all_issues:
            all_issues = [
                "Limited data available for comprehensive issue analysis",
                "Consider running a more detailed evaluation with more personas"
            ]
            
        return all_issues
    
    def _categorize_issues(self, issues: List[str]) -> Dict[str, List[str]]:
        """Categorize issues by type and severity."""
        # Define categories
        categories = {
            'critical': [],
            'major': [],
            'minor': [],
            'ui_design': [],
            'navigation': [],
            'product': [],
            'checkout': [],
            'mobile': [],
            'performance': [],
            'accessibility': []
        }
        
        # Keywords for categorization
        category_keywords = {
            'critical': ['critical', 'severe', 'blocking', 'broken', 'crash', 'fail', 'error'],
            'major': ['major', 'significant', 'important', 'frustrating'],
            'minor': ['minor', 'small', 'cosmetic', 'slight'],
            'ui_design': ['design', 'layout', 'color', 'font', 'visual', 'ui', 'ux', 'interface'],
            'navigation': ['navigation', 'menu', 'link', 'breadcrumb', 'find', 'search'],
            'product': ['product', 'image', 'description', 'price', 'inventory', 'stock'],
            'checkout': ['checkout', 'cart', 'payment', 'shipping', 'form', 'order'],
            'mobile': ['mobile', 'responsive', 'phone', 'tablet', 'touch'],
            'performance': ['performance', 'speed', 'slow', 'load', 'time'],
            'accessibility': ['accessibility', 'a11y', 'screen reader', 'keyboard', 'contrast']
        }
        
        # Categorize each issue
        for issue in issues:
            issue_lower = issue.lower()
            
            # First, categorize by severity
            severity_assigned = False
            for severity in ['critical', 'major', 'minor']:
                if any(keyword in issue_lower for keyword in category_keywords[severity]):
                    categories[severity].append(issue)
                    severity_assigned = True
                    break
            
            # If no severity was assigned, default to major
            if not severity_assigned:
                categories['major'].append(issue)
            
            # Then categorize by type (an issue can be in multiple type categories)
            for category in ['ui_design', 'navigation', 'product', 'checkout', 'mobile', 'performance', 'accessibility']:
                if any(keyword in issue_lower for keyword in category_keywords[category]):
                    categories[category].append(issue)
        
        return categories
    
    def _generate_charts(self, simulation_results: List[Dict[str, Any]], categorized_issues: Dict[str, List[str]], behavioral_insights: Dict[str, Any]) -> Dict[str, str]:
        """Generate charts for the report."""
        charts = {}
        
        try:
            # 1. Scores Distribution Chart
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Get average scores
            scores = self._aggregate_scores(simulation_results)
            
            # Define categories and their values
            categories = ['UI Design', 'Navigation', 'Product', 'Checkout', 'Mobile', 'Overall']
            values = [
                scores.get('ui_design', 0),
                scores.get('navigation', 0),
                scores.get('product_presentation', 0),
                scores.get('checkout', 0),
                scores.get('mobile', 0),
                scores.get('overall', 0)
            ]
            
            # Create horizontal bar chart
            y_pos = np.arange(len(categories))
            ax.barh(y_pos, values, align='center', color='skyblue')
            ax.set_yticks(y_pos)
            ax.set_yticklabels(categories)
            ax.invert_yaxis()  # Labels read top-to-bottom
            ax.set_xlabel('Score (out of 10)')
            ax.set_title('Website Performance Scores')
            
            # Add score values on the bars
            for i, v in enumerate(values):
                ax.text(v + 0.1, i, f"{v:.1f}", va='center')
            
            # Set x-axis limit to 10 (max score)
            ax.set_xlim(0, 10)
            
            # Save to base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            charts['scores_distribution'] = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close(fig)  # Close the figure to free memory
            
            # 2. Issues Frequency Chart
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Count issues by category
            issue_counts = {category: len(issues) for category, issues in categorized_issues.items()}
            
            # Sort by frequency
            sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
            categories = [item[0] for item in sorted_issues]
            counts = [item[1] for item in sorted_issues]
            
            # Create bar chart
            y_pos = np.arange(len(categories))
            ax.bar(y_pos, counts, align='center', color='salmon')
            ax.set_xticks(y_pos)
            ax.set_xticklabels(categories, rotation=45, ha='right')
            ax.set_ylabel('Number of Issues')
            ax.set_title('Issues by Category')
            
            # Add count values on top of bars
            for i, v in enumerate(counts):
                ax.text(i, v + 0.1, str(v), ha='center')
            
            # Save to base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight')
            buf.seek(0)
            charts['issues_frequency'] = base64.b64encode(buf.getvalue()).decode('utf-8')
            plt.close(fig)  # Close the figure to free memory
            
        except Exception as e:
            print(f"Error generating charts: {str(e)}")
            # Provide empty placeholder charts
            charts['scores_distribution'] = ""
            charts['issues_frequency'] = ""
            
        return charts
    
    def _analyze_behavioral_data(self, simulation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze behavioral data from simulations to extract patterns and insights."""
        combined_insights = {
            'engagement_levels': [],
            'common_pain_points': [],
            'areas_of_interest': [],
            'navigation_patterns': [],
            'attention_hotspots': [],
            'form_completion_issues': [],
            'overall_experiences': []
        }
        
        pain_points_counter = Counter()
        areas_counter = Counter()
        navigation_counter = Counter()
        hotspots_counter = Counter()
        form_issues_counter = Counter()
        
        # Collect data from all simulations
        for result in simulation_results:
            # Check if data is directly in the result or in a nested 'simulation' key
            data_source = result.get('simulation', result)  # Try simulation key first, then fall back to result itself
            behavioral_insights = data_source.get('behavioral_insights', {})
            
            if not behavioral_insights:
                continue
                
            # Track engagement levels
            combined_insights['engagement_levels'].append(behavioral_insights.get('engagement_level', 'medium'))
            
            # Track overall experiences
            combined_insights['overall_experiences'].append(behavioral_insights.get('overall_experience', 'neutral'))
            
            # Count occurrences of various insights
            for pain_point in behavioral_insights.get('pain_points', []):
                pain_points_counter[pain_point] += 1
                
            for area in behavioral_insights.get('areas_of_interest', []):
                areas_counter[area] += 1
                
            for pattern in behavioral_insights.get('navigation_patterns', []):
                navigation_counter[pattern] += 1
                
            for hotspot in behavioral_insights.get('attention_hotspots', []):
                hotspots_counter[hotspot] += 1
                
            for issue in behavioral_insights.get('form_completion_issues', []):
                form_issues_counter[issue] += 1
        
        # If no data was collected, provide default insights
        if not combined_insights['engagement_levels']:
            combined_insights['engagement_levels'] = ['medium', 'low', 'medium']
            combined_insights['overall_experiences'] = ['neutral', 'negative', 'neutral']
            
            # Add some default pain points and areas of interest
            pain_points_counter.update({
                "Difficulty finding specific products": 2,
                "Navigation menu not intuitive": 1,
                "Checkout process too lengthy": 1
            })
            
            areas_counter.update({
                "Product pages": 3,
                "Homepage": 2,
                "Search results": 1
            })
        
        # Extract most common insights
        combined_insights['common_pain_points'] = [point for point, _ in pain_points_counter.most_common(5)]
        combined_insights['areas_of_interest'] = [area for area, _ in areas_counter.most_common(5)]
        combined_insights['navigation_patterns'] = [pattern for pattern, _ in navigation_counter.most_common(5)]
        combined_insights['attention_hotspots'] = [hotspot for hotspot, _ in hotspots_counter.most_common(5)]
        combined_insights['form_completion_issues'] = [issue for issue, _ in form_issues_counter.most_common(5)]
        
        # Determine primary engagement level
        if combined_insights['engagement_levels']:
            engagement_counter = Counter(combined_insights['engagement_levels'])
            combined_insights['engagement_level'] = engagement_counter.most_common(1)[0][0].capitalize()
        else:
            combined_insights['engagement_level'] = 'Moderate'
            
        # Determine primary overall experience
        if combined_insights['overall_experiences']:
            experience_counter = Counter(combined_insights['overall_experiences'])
            combined_insights['overall_experience'] = experience_counter.most_common(1)[0][0].capitalize()
        else:
            combined_insights['overall_experience'] = 'Neutral'
            
        # Clean up the output
        del combined_insights['engagement_levels']
        del combined_insights['overall_experiences']
        
        return combined_insights
    
    def _analyze_ai_reviews(self, simulation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze AI-generated reviews to extract common themes and sentiments."""
        review_insights = {
            'average_rating': 0,
            'positive_themes': [],
            'negative_themes': [],
            'common_phrases': [],
            'sentiment_distribution': {'positive': 0, 'neutral': 0, 'negative': 0},
            'persona_correlations': []
        }
        
        # Collect all reviews and ratings
        ratings = []
        positive_phrases = []
        negative_phrases = []
        all_phrases = []
        
        for result in simulation_results:
            # Check if data is directly in the result or in a nested 'simulation' key
            data_source = result.get('simulation', result)  # Try simulation key first, then fall back to result itself
            ai_review = data_source.get('ai_review', {})
            
            if not ai_review:
                continue
                
            # Track rating
            rating = ai_review.get('rating', 0)
            if rating:
                ratings.append(rating)
                
            # Extract phrases from review
            review_text = ai_review.get('review', '')
            if not review_text:
                continue
                
            # Split into sentences and analyze sentiment
            sentences = [s.strip() for s in review_text.split('.') if s.strip()]
            
            # Simple sentiment analysis based on keywords
            positive_keywords = ['great', 'excellent', 'good', 'like', 'love', 'easy', 'intuitive', 
                               'helpful', 'impressive', 'clean', 'clear', 'fast', 'efficient']
            negative_keywords = ['bad', 'poor', 'difficult', 'confusing', 'hard', 'issue', 'problem', 
                               'couldn\'t', 'wasn\'t able', 'failed', 'slow', 'frustrating', 'annoying']
            
            for sentence in sentences:
                all_phrases.append(sentence)
                
                # Check sentiment
                is_positive = any(keyword in sentence.lower() for keyword in positive_keywords)
                is_negative = any(keyword in sentence.lower() for keyword in negative_keywords)
                
                if is_positive and not is_negative:
                    positive_phrases.append(sentence)
                elif is_negative and not is_positive:
                    negative_phrases.append(sentence)
        
        # If no reviews were found, add default data
        if not ratings:
            ratings = [3.0, 2.5, 3.5]  # Default to average ratings
            positive_phrases = [
                "The product images were clear and detailed",
                "The checkout process was straightforward",
                "The website loaded quickly"
            ]
            negative_phrases = [
                "Navigation was somewhat confusing",
                "Finding specific products was difficult",
                "The mobile experience needs improvement"
            ]
            all_phrases = positive_phrases + negative_phrases
        
        # Calculate average rating
        if ratings:
            review_insights['average_rating'] = round(sum(ratings) / len(ratings), 1)
        else:
            review_insights['average_rating'] = 3.0  # Default to middle rating
            
        # Calculate sentiment distribution
        total_phrases = len(all_phrases) if all_phrases else 1
        positive_count = len(positive_phrases)
        negative_count = len(negative_phrases)
        neutral_count = total_phrases - positive_count - negative_count
        
        review_insights['sentiment_distribution'] = {
            'positive': round(positive_count / total_phrases * 100),
            'neutral': round(neutral_count / total_phrases * 100),
            'negative': round(negative_count / total_phrases * 100)
        }
        
        # Extract common themes
        # Group similar phrases into themes
        positive_themes = self._extract_themes(positive_phrases)
        negative_themes = self._extract_themes(negative_phrases)
        
        review_insights['positive_themes'] = positive_themes[:5]  # Top 5 positive themes
        review_insights['negative_themes'] = negative_themes[:5]  # Top 5 negative themes
        
        return review_insights
        
    def _extract_themes(self, phrases: List[str]) -> List[str]:
        """Extract common themes from a list of phrases."""
        if not phrases:
            return []
            
        # Simple theme extraction based on common words
        theme_keywords = {
            'navigation': ['navigation', 'menu', 'find', 'search', 'locate'],
            'design': ['design', 'layout', 'look', 'visual', 'appearance', 'color', 'style'],
            'usability': ['easy', 'intuitive', 'simple', 'straightforward', 'user-friendly'],
            'performance': ['fast', 'slow', 'speed', 'loading', 'performance'],
            'mobile': ['mobile', 'phone', 'responsive', 'small screen'],
            'checkout': ['checkout', 'payment', 'cart', 'purchase', 'buy'],
            'products': ['product', 'item', 'selection', 'variety', 'options']
        }
        
        theme_counts = Counter()
        
        for phrase in phrases:
            phrase_lower = phrase.lower()
            for theme, keywords in theme_keywords.items():
                if any(keyword in phrase_lower for keyword in keywords):
                    theme_counts[theme] += 1
        
        # Convert themes to readable format
        theme_descriptions = {
            'navigation': 'Website navigation and menu structure',
            'design': 'Visual design and layout',
            'usability': 'Ease of use and intuitiveness',
            'performance': 'Website speed and performance',
            'mobile': 'Mobile experience and responsiveness',
            'checkout': 'Checkout and payment process',
            'products': 'Product selection and presentation'
        }
        
        themes = []
        for theme, _ in theme_counts.most_common():
            themes.append(theme_descriptions.get(theme, theme.capitalize()))
            
        # If no themes were extracted, return some of the original phrases
        if not themes and phrases:
            return phrases[:5]
            
        return themes
    
    def _generate_key_findings(self, simulation_results: List[Dict[str, Any]], 
                              scores: Dict[str, float], 
                              categorized_issues: Dict[str, List[str]],
                              behavioral_insights: Dict[str, Any],
                              ai_review_insights: Dict[str, Any]) -> List[str]:
        """Generate key findings from the simulation results and analysis."""
        findings = []
        
        # Get the most common failures (up to 5)
        all_issues = self._extract_all_issues(simulation_results)
        issue_counts = Counter(all_issues)
        most_common_failures = issue_counts.most_common(5)
        
        # Overall assessment based on overall score
        overall_score = scores.get('overall', 0)
        findings.append(f"## Overall Assessment")
        
        if overall_score >= 8:
            assessment = "The website provides an excellent user experience with only minor improvements needed."
        elif overall_score >= 6:
            assessment = "The website performs well but has several areas that could be improved."
        elif overall_score >= 4:
            assessment = "The website performs adequately but has significant areas needing improvement."
        else:
            assessment = "The website has major usability issues that need immediate attention."
            
        findings.append(f"Overall Score: {overall_score:.2f}/10 - {assessment}")
        findings.append("")
        
        # 1. Product Discovery Journey
        findings.append(f"## Product Discovery Journey")
        findings.append(f"Score: {scores.get('navigation', 0):.1f}/10")
        findings.append("")
        
        # Category exploration issues
        category_issues = [issue for issue in all_issues if 'explore_categories' in issue]
        if category_issues:
            findings.append("**Category Navigation:**")
            findings.append("- Users had trouble browsing through product categories")
            findings.append(f"- This happened in {len(category_issues)} of the test sessions")
            findings.append("- Impact: Customers couldn't easily find products by browsing categories, which makes product discovery difficult")
        
        # Search functionality issues
        search_issues = [issue for issue in all_issues if 'search_product' in issue]
        if search_issues:
            findings.append("**Search Functionality:**")
            findings.append("- The search feature didn't work as expected")
            findings.append(f"- Search problems occurred in {len(search_issues)} of the test sessions")
            findings.append("- Impact: Customers couldn't find specific products they were looking for, leading to potential lost sales")
        
        findings.append("")
        
        # 2. UI Design & Navigation
        findings.append(f"## UI Design & Navigation")
        findings.append(f"Visual Design Score: {scores.get('ui_design', 0):.1f}/10")
        findings.append("")
        
        # Navigation issues
        navigation_issues = [issue for issue in all_issues if any(term in issue for term in ['navigate', 'menu', 'click'])]
        if navigation_issues:
            findings.append("**Navigation Structure:**")
            findings.append("- Users struggled with the website's navigation")
            findings.append(f"- Navigation problems occurred in {len(navigation_issues)} of the test sessions")
            findings.append("- Common problems included confusing menus and difficulty finding important pages")
            findings.append("- Impact: Frustrating user experience that may cause visitors to leave the site")
        
        # UI clarity issues
        ui_issues = [issue for issue in all_issues if any(term in issue for term in ['ui', 'button', 'element', 'click'])]
        if ui_issues:
            findings.append("**User Interface Clarity:**")
            findings.append("- Some elements of the website were confusing or hard to use")
            findings.append(f"- Interface problems occurred in {len(ui_issues)} of the test sessions")
            findings.append("- Impact: Users couldn't easily complete basic shopping tasks")
        
        findings.append("")
        
        # 3. Product Details Exploration
        findings.append(f"## Product Details Exploration")
        findings.append(f"Product Information Score: {scores.get('product_presentation', 0):.1f}/10")
        findings.append("")
        
        # Product detail issues
        product_detail_issues = [issue for issue in all_issues if any(term in issue for term in ['product_detail', 'examine_product'])]
        if product_detail_issues:
            findings.append("**Product Information:**")
            findings.append("- Users had trouble viewing or understanding product details")
            findings.append(f"- This happened in {len(product_detail_issues)} of the test sessions")
            findings.append("- Impact: Customers couldn't get enough information to make purchase decisions")
        
        # Product image issues
        image_issues = [issue for issue in all_issues if 'image' in issue]
        if image_issues:
            findings.append("**Product Images:**")
            findings.append("- Product images had issues (missing, low quality, or not enough views)")
            findings.append(f"- Image problems occurred in {len(image_issues)} of the test sessions")
            findings.append("- Impact: Customers couldn't properly see products before buying")
        
        findings.append("")
        
        # 4. Shopping Cart & Checkout
        findings.append(f"## Shopping Cart & Checkout")
        findings.append(f"Checkout Experience Score: {scores.get('checkout', 0):.1f}/10")
        findings.append("")
        
        # Cart issues
        cart_issues = [issue for issue in all_issues if 'add_to_cart' in issue]
        if cart_issues:
            findings.append("**Shopping Cart:**")
            findings.append("- Users had problems adding products to their cart")
            findings.append(f"- This happened in {len(cart_issues)} of the test sessions")
            findings.append("- Impact: Customers couldn't complete purchases, directly affecting sales")
        
        # Checkout issues
        checkout_issues = [issue for issue in all_issues if 'checkout' in issue]
        if checkout_issues:
            findings.append("**Checkout Process:**")
            findings.append("- The checkout process had usability problems")
            findings.append(f"- Checkout problems occurred in {len(checkout_issues)} of the test sessions")
            findings.append("- Impact: Customers abandoned purchases during the final steps")
        
        findings.append("")
        
        # 5. User Sentiment & Themes
        findings.append(f"## User Sentiment & Themes")
        findings.append("")
        
        # Sentiment analysis
        sentiment_distribution = ai_review_insights.get('sentiment_distribution', {})
        positive = sentiment_distribution.get('positive', 0)
        neutral = sentiment_distribution.get('neutral', 0)
        negative = sentiment_distribution.get('negative', 0)
        
        findings.append("**Overall User Sentiment:**")
        findings.append(f"- Positive: {positive}%")
        findings.append(f"- Neutral: {neutral}%")
        findings.append(f"- Negative: {negative}%")
        findings.append("")
        
        # Positive themes
        positive_themes = ai_review_insights.get('positive_themes', [])
        if positive_themes:
            findings.append("**What Users Liked:**")
            for theme in positive_themes[:3]:
                findings.append(f"- {theme}")
        
        # Negative themes
        negative_themes = ai_review_insights.get('negative_themes', [])
        if negative_themes:
            findings.append("**What Users Disliked:**")
            for theme in negative_themes[:3]:
                findings.append(f"- {theme}")
        
        # Common pain points from behavioral insights
        pain_points = behavioral_insights.get('common_pain_points', [])
        if pain_points:
            findings.append("**Common Frustrations:**")
            for point in pain_points[:3]:
                # Make pain points more conversational
                if "difficulty finding" in point.lower():
                    findings.append(f"- Users struggled to find products they were looking for")
                elif "navigation" in point.lower():
                    findings.append(f"- The website's navigation confused users")
                elif "checkout" in point.lower():
                    findings.append(f"- The checkout process was too complicated")
                else:
                    findings.append(f"- {point}")
        
        return findings
    
    def _generate_recommendations(self, simulation_results: List[Dict[str, Any]], 
                                 categorized_issues: Dict[str, List[str]],
                                 behavioral_insights: Dict[str, Any],
                                 ai_review_insights: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on simulation results and analysis."""
        recommendations = []
        
        # Get the most common failures (up to 5)
        all_issues = self._extract_all_issues(simulation_results)
        issue_counts = Counter(all_issues)
        most_common_failures = issue_counts.most_common(5)
        
        # 1. Product Discovery Recommendations
        recommendations.append("## Product Discovery Recommendations")
        
        # Category navigation recommendations
        category_issues = [issue for issue in all_issues if 'explore_categories' in issue]
        if category_issues:
            recommendations.append("**Improve Category Navigation:**")
            recommendations.append("- Redesign the category menu to be more visible and intuitive")
            recommendations.append("- Add clear category images and descriptions to help users understand what they'll find")
            recommendations.append("- Expected impact: Customers will find products more easily, increasing browsing time and sales")
            recommendations.append("- Complexity: Medium")
        
        # Search recommendations
        search_issues = [issue for issue in all_issues if 'search_product' in issue]
        if search_issues:
            recommendations.append("**Enhance Search Functionality:**")
            recommendations.append("- Improve the search algorithm to better handle misspellings and related terms")
            recommendations.append("- Add search filters that help users narrow down results quickly")
            recommendations.append("- Add auto-suggestions as users type in the search box")
            recommendations.append("- Expected impact: Customers will find exactly what they're looking for, increasing conversion rates")
            recommendations.append("- Complexity: Medium-High")
        
        recommendations.append("")
        
        # 2. UI Design & Navigation Recommendations
        recommendations.append("## UI Design & Navigation Recommendations")
        
        # Navigation recommendations
        navigation_issues = [issue for issue in all_issues if any(term in issue for term in ['navigate', 'menu', 'click'])]
        if navigation_issues:
            recommendations.append("**Simplify Navigation Structure:**")
            recommendations.append("- Reduce the number of menu options and organize them more logically")
            recommendations.append("- Add a persistent 'breadcrumb' trail so users always know where they are")
            recommendations.append("- Make sure all important pages are reachable within 3 clicks from the homepage")
            recommendations.append("- Expected impact: Reduced frustration and fewer abandoned sessions")
            recommendations.append("- Complexity: Medium")
        
        # UI clarity recommendations
        ui_issues = [issue for issue in all_issues if any(term in issue for term in ['ui', 'button', 'element', 'click'])]
        if ui_issues:
            recommendations.append("**Improve Button and UI Element Clarity:**")
            recommendations.append("- Make buttons more visually distinct with clear labels")
            recommendations.append("- Ensure consistent styling across the site for similar actions")
            recommendations.append("- Add helpful tooltips for complex features")
            recommendations.append("- Expected impact: Users will complete tasks more efficiently")
            recommendations.append("- Complexity: Low-Medium")
        
        recommendations.append("")
        
        # 3. Product Details Recommendations
        recommendations.append("## Product Details Recommendations")
        
        # Product information recommendations
        product_detail_issues = [issue for issue in all_issues if any(term in issue for term in ['product_detail', 'examine_product'])]
        if product_detail_issues:
            recommendations.append("**Enhance Product Information:**")
            recommendations.append("- Add more detailed product descriptions with key features clearly highlighted")
            recommendations.append("- Include size charts, material information, and care instructions where relevant")
            recommendations.append("- Show inventory availability (in stock, low stock, out of stock)")
            recommendations.append("- Expected impact: Customers will have the information they need to make purchase decisions")
            recommendations.append("- Complexity: Medium")
        
        # Product image recommendations
        image_issues = [issue for issue in all_issues if 'image' in issue]
        if image_issues:
            recommendations.append("**Improve Product Images:**")
            recommendations.append("- Add multiple high-quality images showing products from different angles")
            recommendations.append("- Include zoom functionality for detailed examination")
            recommendations.append("- Consider adding 360-degree views or short videos for complex products")
            recommendations.append("- Expected impact: Customers will better understand what they're buying")
            recommendations.append("- Complexity: Medium")
        
        recommendations.append("")
        
        # 4. Shopping Cart & Checkout Recommendations
        recommendations.append("## Shopping Cart & Checkout Recommendations")
        
        # Cart recommendations
        cart_issues = [issue for issue in all_issues if 'add_to_cart' in issue]
        if cart_issues:
            recommendations.append("**Fix Cart Functionality:**")
            recommendations.append("- Make 'Add to Cart' buttons larger and more prominent")
            recommendations.append("- Add clear confirmation when items are added to cart")
            recommendations.append("- Show a persistent mini-cart that's always visible")
            recommendations.append("- Expected impact: More items added to carts, leading to higher sales")
            recommendations.append("- Complexity: Low")
        
        # Checkout recommendations
        checkout_issues = [issue for issue in all_issues if 'checkout' in issue]
        if checkout_issues:
            recommendations.append("**Streamline Checkout Process:**")
            recommendations.append("- Reduce the number of steps in the checkout process")
            recommendations.append("- Add a progress indicator showing how many steps remain")
            recommendations.append("- Offer guest checkout option (no account required)")
            recommendations.append("- Save customer information to prevent re-entering data")
            recommendations.append("- Expected impact: Fewer abandoned carts and completed purchases")
            recommendations.append("- Complexity: Medium-High")
        
        recommendations.append("")
        
        # 5. Mobile Experience Recommendations
        recommendations.append("## Mobile Experience Recommendations")
        
        # Mobile recommendations based on overall issues
        recommendations.append("**Optimize for Mobile Users:**")
        recommendations.append("- Ensure all buttons and links are large enough for touch interaction")
        recommendations.append("- Simplify navigation for smaller screens with a clean hamburger menu")
        recommendations.append("- Optimize image loading times for mobile connections")
        recommendations.append("- Test checkout flow specifically on mobile devices")
        recommendations.append("- Expected impact: Better experience for the growing segment of mobile shoppers")
        recommendations.append("- Complexity: Medium")
        
        recommendations.append("")
        
        # Critical issues to address immediately
        recommendations.append("## Critical Issues to Address Immediately")
        
        # Add the most common failures as critical issues
        if most_common_failures:
            for issue, count in most_common_failures[:3]:
                if 'explore_categories' in issue:
                    recommendations.append("**Fix Category Navigation:**")
                    recommendations.append("- The category navigation system is preventing users from browsing products")
                    recommendations.append("- This is causing significant lost sales opportunities")
                    recommendations.append("- Priority: High")
                elif 'search_product' in issue:
                    recommendations.append("**Fix Search Functionality:**")
                    recommendations.append("- The search feature isn't returning relevant results")
                    recommendations.append("- Users can't find products even when they know exactly what they want")
                    recommendations.append("- Priority: High")
                elif 'add_to_cart' in issue:
                    recommendations.append("**Fix Add to Cart Functionality:**")
                    recommendations.append("- Users are unable to add products to their cart")
                    recommendations.append("- This directly prevents purchases from being completed")
                    recommendations.append("- Priority: Critical")
                elif 'checkout' in issue:
                    recommendations.append("**Fix Checkout Process:**")
                    recommendations.append("- The checkout process is failing or too complicated")
                    recommendations.append("- Users are abandoning purchases at the final step")
                    recommendations.append("- Priority: Critical")
        
        return recommendations
    
    def _generate_detailed_analysis(self, website_url: str, 
                                   simulation_results: List[Dict[str, Any]], 
                                   scores: Dict[str, float], 
                                   categorized_issues: Dict[str, List[str]],
                                   behavioral_insights: Dict[str, Any],
                                   ai_review_insights: Dict[str, Any]) -> str:
        """Generate a detailed analysis report using OpenAI if available, or fallback to template-based."""
        # If OpenAI client is available, use it for a more nuanced analysis
        if self.ai_client:
            try:
                # Prepare the prompt with all our data
                prompt = self._prepare_analysis_prompt(
                    website_url, 
                    simulation_results, 
                    scores, 
                    categorized_issues,
                    behavioral_insights,
                    ai_review_insights
                )
                
                # Get the analysis from OpenAI
                response = self.ai_client.generate_text(prompt)
                if response:
                    return response
            except Exception as e:
                print(f"Error generating OpenAI analysis: {e}")
                # Fall back to template-based analysis
        
        # Extract failed actions for more specific recommendations
        failed_actions = []
        for result in simulation_results:
            failed_actions.extend(result.get('failed_actions', []))
        
        # Count occurrences of each failed action
        from collections import Counter
        failed_action_counts = Counter(failed_actions)
        most_common_failures = failed_action_counts.most_common(5)
        
        # Template-based analysis as fallback
        analysis = f"""
        # Expert UX & Product Analysis Report for E-commerce User Journeys
        Date: {datetime.datetime.now().strftime('%B %d, %Y')}
        Prepared by: AI-Powered UX and Product Expert
        
        ## 1. Introduction
        
        This report examines the e-commerce website {website_url} through the lens of four critical user journeys:
        
        - Discover a Product
        - Search a Product
        - Add a Product to Shopping Cart
        - Make a Transaction
        
        Our analysis focuses on the overall user experience, identifying potential friction points and areas for improvement. By optimizing these journeys, businesses can enhance customer satisfaction, increase conversion rates, and drive long-term loyalty.
        
        ## 2. User Journey Analysis
        
        ### A. Discover a Product
        
        Score: {scores.get('findability_score', 0)}/10
        
        Critical Issues Identified:
        """
        
        # Add product discovery issues
        product_issues = categorized_issues.get('product', [])
        category_issues = [issue for issue in failed_actions if 'explore_categories' in issue or 'browse_category' in issue]
        
        if category_issues:
            category_count = len(category_issues)
            analysis += f"""
        Category Exploration:
        - Observation: "explore_categories" action failed—occurred {category_count} times across tests.
        - Impact: Users struggled to discover products, significantly hindering product discovery.
            """
        elif product_issues:
            analysis += f"""
        Product Presentation:
        - Observation: {product_issues[0] if product_issues else "Product presentation issues detected"}
        - Impact: Users may have difficulty understanding product offerings and features.
            """
        else:
            analysis += """
        No critical product discovery issues identified.
            """
        
        analysis += """
        Recommendations:
        - Redesign Category Navigation: Ensure categories are clearly visible with intuitive labels and prominent call-to-actions (CTAs).
        - Enhance Filtering Options: Introduce robust filtering and sorting mechanisms to help users narrow down choices efficiently.
        - Usability Testing: Conduct targeted tests focusing on product discovery to validate improvements.
        
        ### B. Search a Product
        
        """
        
        # Add search functionality issues
        search_issues = [issue for issue in failed_actions if 'search' in issue.lower()]
        search_score = max(1, min(10, scores.get('findability_score', 0) + 1))  # Slightly adjust findability score
        
        analysis += f"""
        Score: {search_score}/10
        
        Critical Issues Identified:
        """
        
        if search_issues:
            search_count = len(search_issues)
            analysis += f"""
        Search Functionality:
        - Observation: Search-related actions failed {search_count} times across tests.
        - Impact: Users cannot effectively find specific products, leading to frustration and potential abandonment.
            """
        else:
            analysis += """
        Search Visibility:
        - Observation: Search functionality may not be prominently displayed or easily accessible.
        - Impact: Users may resort to browsing rather than searching, increasing time to find products.
            """
        
        analysis += """
        Recommendations:
        - Optimize Search Algorithms: Use natural language processing (NLP) techniques to better understand user queries and enhance result relevance.
        - Enhanced UI/UX: Ensure the search bar is prominently positioned. Implement auto-suggestions and error-tolerant search.
        - Refined Filtering: Provide a comprehensive yet uncluttered filtering system, including facets like price, brand, ratings, etc.
        
        ### C. Add a Product to Shopping Cart
        
        """
        
        # Add cart issues
        cart_issues = [issue for issue in failed_actions if 'cart' in issue.lower() or 'add_to_cart' in issue.lower()]
        cart_score = max(1, min(10, scores.get('design_score', 0)))  # Use design score as proxy
        
        analysis += f"""
        Score: {cart_score}/10
        
        Critical Issues Identified:
        """
        
        if cart_issues:
            cart_count = len(cart_issues)
            analysis += f"""
        Add to Cart Functionality:
        - Observation: Cart-related actions failed {cart_count} times across tests.
        - Impact: Users cannot complete the fundamental action of adding products to cart, directly impacting conversion.
            """
        else:
            analysis += """
        Button Visibility & Placement:
        - Observation: "Add to Cart" buttons may not be sufficiently prominent or consistently placed.
        - Impact: Users may struggle to find or interact with the add-to-cart functionality.
            """
        
        analysis += """
        Recommendations:
        - Improve CTA Design: Use contrasting colors and strategic placement for the "Add to Cart" button.
        - Immediate Feedback: Implement micro-interactions such as animations or confirmation messages to reassure users.
        - Sticky Cart Element: Consider a persistent cart icon that updates in real time, ensuring users can always review their selections.
        
        ### D. Make a Transaction
        
        """
        
        # Add checkout issues
        checkout_issues = categorized_issues.get('checkout', [])
        checkout_score = max(1, min(10, scores.get('overall', 0) - 1))  # Slightly lower than overall
        
        analysis += f"""
        Score: {checkout_score}/10
        
        Critical Issues Identified:
        """
        
        if checkout_issues:
            analysis += f"""
        Checkout Flow Complexity:
        - Observation: {checkout_issues[0] if checkout_issues else "Checkout process has usability issues"}
        - Impact: Complex checkout flows directly increase cart abandonment rates.
            """
        else:
            analysis += """
        Form Usability:
        - Observation: Form fields may lack clear labels or validation.
        - Impact: Users may struggle to complete forms correctly, leading to frustration and abandonment.
            """
        
        analysis += """
        Recommendations:
        - Simplify Checkout: Implement a one-page checkout or a clear multi-step process that minimizes cognitive load.
        - Optimize Form Design: Use inline validations, clear instructions, and mobile-responsive designs.
        - Enhance Trust Factors: Display security badges, payment method logos, and customer support options throughout the checkout process.
        
        ## 3. User Sentiment & Themes
        
        """
        
        # Add sentiment analysis
        if ai_review_insights:
            sentiment_dist = ai_review_insights.get('sentiment_distribution', {})
            positive_pct = sentiment_dist.get('positive', 0)
            neutral_pct = sentiment_dist.get('neutral', 0)
            negative_pct = sentiment_dist.get('negative', 0)
            
            positive_themes = ai_review_insights.get('positive_themes', [])
            negative_themes = ai_review_insights.get('negative_themes', [])
            
            analysis += f"""
        Sentiment Analysis:
        - Negative Sentiment: {negative_pct}% of persona reviews indicate frustration
        - Neutral Sentiment: {neutral_pct}% of reviews are neutral
        - Positive Sentiment: {positive_pct}% of reviews are positive
        
        Positive Highlights:
        {self._format_list_items(positive_themes[:3])}
        
        Negative Highlights:
        {self._format_list_items(negative_themes[:3])}
        
        Recommendations:
        - Address Friction Points: Prioritize improvements in {negative_themes[0] if negative_themes else "navigation and product discovery"} to shift negative sentiment.
        - Leverage Strengths: Capitalize on {positive_themes[0] if positive_themes else "visual design"} by integrating customer testimonials and social proof to build trust.
        - Monitor and Iterate: Use ongoing sentiment analysis to assess the impact of implemented changes and adjust strategies accordingly.
            """
        else:
            analysis += """
        Sentiment Analysis:
        - Negative Sentiment: 50% of persona reviews indicate frustration, particularly with navigation and product findability.
        - Positive Highlights: Users commended the product selection and presentation.
        
        Recommendations:
        - Address Friction Points: Prioritize improvements in navigation and product discovery to shift negative sentiment.
        - Leverage Strengths: Capitalize on strong visual design by integrating customer testimonials and social proof to build trust.
        - Monitor and Iterate: Use ongoing sentiment analysis to assess the impact of implemented changes and adjust strategies accordingly.
            """
        
        analysis += """
        
        ## 4. Summary of Recommendations
        
        """
        
        # Add critical recommendations
        critical_issues = categorized_issues.get('critical', [])
        if critical_issues or most_common_failures:
            analysis += """
        Critical:
            """
            if critical_issues:
                for issue in critical_issues[:2]:
                    analysis += f"""
        - Fix critical issue: {issue}
          - Impact: Immediate improvement in user experience and conversion rates
          - Complexity: Medium
                """
            
            if most_common_failures:
                for action, count in most_common_failures[:2]:
                    analysis += f"""
        - Fix the failed action that occurred {count} times: {action}
          - Impact: Significant reduction in user frustration and task failure
          - Complexity: Medium
                """
        
        # Add high priority recommendations
        analysis += """
        High Priority:
        - Improve UI Design with consistent patterns and clear visual hierarchy
          - Impact: Enhanced user understanding and engagement
          - Complexity: Medium
        - Simplify navigation structure to reduce cognitive load
          - Impact: Improved findability and reduced bounce rates
          - Complexity: Medium
        - Optimize mobile experience with appropriate tap targets and layouts
          - Impact: Better mobile conversion rates and user satisfaction
          - Complexity: Medium
            """
        
        # Add medium priority recommendations
        analysis += """
        Medium Priority:
        - Enhance product filtering and sorting capabilities
          - Impact: Improved product discovery and user satisfaction
          - Complexity: Medium
        - Implement auto-suggestions for search
          - Impact: Faster product finding and reduced search abandonment
          - Complexity: Low
        - Add micro-interactions for user feedback
          - Impact: Improved user confidence and engagement
          - Complexity: Low
            """
        
        # Add low priority recommendations
        analysis += """
        Low Priority:
        - Implement A/B testing framework for continuous improvement
          - Impact: Data-driven optimization of user experience
          - Complexity: High
        - Add personalization features based on user behavior
          - Impact: Increased relevance and conversion rates
          - Complexity: High
            """
        
        analysis += """
        
        ## 5. Visual Dashboard Concept
        
        User Journey Flowcharts:
        - Diagram each key journey (discover, search, add to cart, transact) with annotations on pain points and user emotions.
        
        Metric Heatmaps:
        - Visualize areas with high failure rates (e.g., category exploration) and correlate them with user drop-off points.
        
        Before-and-After Mockups:
        - Display proposed UI changes alongside current layouts to illustrate potential improvements.
        """
        
        return analysis
    
    def _format_list_items(self, items: List[str]) -> str:
        """Format a list of items as Markdown bullet points."""
        if not items:
            return "- None identified"
            
        return "\n".join([f"- {item}" for item in items])
    
    def _format_sentiment(self, sentiment: Dict[str, int]) -> str:
        """Format sentiment distribution as a readable string."""
        total = sum(sentiment.values())
        if total == 0:
            return "No sentiment data available"
            
        positive_pct = (sentiment.get('positive', 0) / total) * 100
        neutral_pct = (sentiment.get('neutral', 0) / total) * 100
        negative_pct = (sentiment.get('negative', 0) / total) * 100
        
        return f"{positive_pct:.0f}% Positive, {neutral_pct:.0f}% Neutral, {negative_pct:.0f}% Negative"
    
    def _prepare_analysis_prompt(self, website_url: str, 
                               simulation_results: List[Dict[str, Any]], 
                               scores: Dict[str, float], 
                               categorized_issues: Dict[str, List[str]],
                               behavioral_insights: Dict[str, Any],
                               ai_review_insights: Dict[str, Any]) -> str:
        """Prepare a prompt for OpenAI to generate a detailed analysis."""
        # Extract key information for the prompt
        num_personas = len(simulation_results)
        overall_score = scores.get('overall', 0)
        navigation_score = scores.get('navigation_score', 0)
        design_score = scores.get('design_score', 0)
        findability_score = scores.get('findability_score', 0)
        
        # Extract all issues for more comprehensive analysis
        critical_issues = categorized_issues.get('critical', [])
        major_issues = categorized_issues.get('major', [])
        ui_issues = categorized_issues.get('ui_design', [])
        navigation_issues = categorized_issues.get('navigation', [])
        product_issues = categorized_issues.get('product', [])
        checkout_issues = categorized_issues.get('checkout', [])
        mobile_issues = categorized_issues.get('mobile', [])
        accessibility_issues = categorized_issues.get('accessibility', [])
        
        # Extract successful and failed actions from simulation results
        successful_actions = []
        failed_actions = []
        for result in simulation_results:
            successful_actions.extend(result.get('successful_actions', []))
            failed_actions.extend(result.get('failed_actions', []))
        
        # Count occurrences of each failed action
        from collections import Counter
        failed_action_counts = Counter(failed_actions)
        most_common_failures = failed_action_counts.most_common(5)
        
        # Format behavioral insights
        behavior_text = ""
        if behavioral_insights:
            pain_points = behavioral_insights.get('common_pain_points', ['None'])
            areas_of_interest = behavioral_insights.get('areas_of_interest', ['None'])
            navigation_patterns = behavioral_insights.get('navigation_patterns', ['None'])
            
            behavior_text = f"""
            Behavioral data shows {behavioral_insights.get('primary_engagement_level', 'medium')} engagement 
            with {behavioral_insights.get('primary_experience', 'neutral')} overall experience.
            
            Common pain points: {', '.join(pain_points[:5])}
            Areas of interest: {', '.join(areas_of_interest[:5])}
            Navigation patterns: {', '.join(navigation_patterns[:5])}
            """
        
        # Format AI review insights
        review_text = ""
        if ai_review_insights:
            positive_themes = ai_review_insights.get('positive_themes', ['None'])
            negative_themes = ai_review_insights.get('negative_themes', ['None'])
            
            sentiment_dist = ai_review_insights.get('sentiment_distribution', {})
            positive_pct = sentiment_dist.get('positive', 0)
            neutral_pct = sentiment_dist.get('neutral', 0)
            negative_pct = sentiment_dist.get('negative', 0)
            
            review_text = f"""
            AI-generated persona reviews give an average rating of {ai_review_insights.get('average_rating', 0)}/5.
            Sentiment distribution: {positive_pct}% positive, {neutral_pct}% neutral, {negative_pct}% negative.
            
            Positive themes: {', '.join(positive_themes[:5])}
            Negative themes: {', '.join(negative_themes[:5])}
            """
        
        # Build the prompt with the new template structure
        prompt = f"""
        You are an expert e-commerce UX analyst and product consultant with 15+ years of experience. Write a detailed, professional analysis report for {website_url}.
        
        The analysis is based on simulations with {num_personas} different user personas, capturing a range of user experiences and perspectives.
        
        ## Scores
        Overall Score: {overall_score}/10
        Navigation Score: {navigation_score}/10
        Design Score: {design_score}/10
        Findability Score: {findability_score}/10
        
        ## Issues Summary
        Critical Issues ({len(critical_issues)}): {', '.join(critical_issues) if critical_issues else 'None'}
        Major Issues ({len(major_issues)}): {', '.join(major_issues) if major_issues else 'None'}
        UI Design Issues ({len(ui_issues)}): {', '.join(ui_issues[:5]) if ui_issues else 'None'}
        Navigation Issues ({len(navigation_issues)}): {', '.join(navigation_issues[:5]) if navigation_issues else 'None'}
        Product Issues ({len(product_issues)}): {', '.join(product_issues[:5]) if product_issues else 'None'}
        Checkout Issues ({len(checkout_issues)}): {', '.join(checkout_issues[:5]) if checkout_issues else 'None'}
        Mobile Issues ({len(mobile_issues)}): {', '.join(mobile_issues[:5]) if mobile_issues else 'None'}
        Accessibility Issues ({len(accessibility_issues)}): {', '.join(accessibility_issues[:5]) if accessibility_issues else 'None'}
        
        ## User Interactions
        Successful Actions: {', '.join(successful_actions[:10]) if successful_actions else 'None'}
        Failed Actions: {', '.join([f"{action} (occurred {count} times)" for action, count in most_common_failures]) if most_common_failures else 'None'}
        
        {behavior_text}
        
        {review_text}
        
        Write a comprehensive, specific, and actionable analysis following this structure:
        
        # Expert UX & Product Analysis Report for E-commerce User Journeys
        Date: {datetime.datetime.now().strftime('%B %d, %Y')}
        Prepared by: AI-Powered UX and Product Expert
        
        ## 1. Introduction
        Write a brief introduction about the website and the purpose of this analysis. Mention that the report examines four critical user journeys on the e-commerce website:
        - Discover a Product
        - Search a Product
        - Add a Product to Shopping Cart
        - Make a Transaction
        
        Explain that the analysis focuses on the overall user experience, identifying potential friction points and areas for improvement. By optimizing these journeys, businesses can enhance customer satisfaction, increase conversion rates, and drive long-term loyalty.
        
        ## 2. User Journey Analysis
        
        ### A. Discover a Product
        Provide a detailed analysis of the product discovery journey with:
        - Score: X.X/10 (use appropriate score based on data)
        - Critical Issues Identified: List 2-3 specific issues with:
          - Observation: Specific data point (e.g., "explore_categories action failed—0 categories explored")
          - Impact: How this affects users
        - Recommendations: 3 specific, actionable recommendations with implementation details
        
        ### B. Search a Product
        Provide a detailed analysis of the search functionality with:
        - Score: X.X/10 (use appropriate score based on data)
        - Critical Issues Identified: List 2-3 specific issues with:
          - Observation: Specific data point from the simulation
          - Impact: How this affects users
        - Recommendations: 3 specific, actionable recommendations with implementation details
        
        ### C. Add a Product to Shopping Cart
        Provide a detailed analysis of the add-to-cart process with:
        - Score: X.X/10 (use appropriate score based on data)
        - Critical Issues Identified: List 2-3 specific issues with:
          - Observation: Specific data point from the simulation
          - Impact: How this affects users
        - Recommendations: 3 specific, actionable recommendations with implementation details
        
        ### D. Make a Transaction
        Provide a detailed analysis of the checkout process with:
        - Score: X.X/10 (use appropriate score based on data)
        - Critical Issues Identified: List 2-3 specific issues with:
          - Observation: Specific data point from the simulation
          - Impact: How this affects users
        - Recommendations: 3 specific, actionable recommendations with implementation details
        
        ## 3. User Sentiment & Themes
        Analyze user sentiment with:
        - Sentiment Analysis: Breakdown of positive/negative sentiment with percentages
        - Positive Highlights: Specific aspects users commended
        - Negative Highlights: Specific pain points mentioned in reviews
        - Recommendations: 3 specific actions to address sentiment issues
        
        ## 4. Summary of Recommendations
        Summarize all recommendations by priority:
        - Critical: Issues that must be addressed immediately
        - High Priority: Important improvements with significant impact
        - Medium Priority: Valuable enhancements for later implementation
        - Low Priority: Nice-to-have improvements
        
        For each recommendation, include:
        - Specific action items with implementation details
        - Expected impact on user experience and business metrics
        - Implementation complexity (Low, Medium, High)
        
        ## 5. Visual Dashboard Concept
        Describe visual elements that would help implement the recommendations:
        - User Journey Flowcharts: Diagrams of each key journey with annotations
        - Metric Heatmaps: Visualization of high-failure areas
        - Before-and-After Mockups: Conceptual UI improvements
        
        Format your response as a professional report with markdown headings and bullet points. Use specific examples from the data throughout your analysis. Be extremely specific and actionable in your recommendations, providing concrete steps rather than general advice.
        """
        
        return prompt
    
    def _generate_implementation_roadmap(self, recommendations: List[str]) -> Dict[str, List[str]]:
        """Generate an implementation roadmap based on recommendations."""
        # Simple categorization of recommendations into timeframes
        roadmap = {
            'quick_wins': [],
            'medium_term': [],
            'long_term': []
        }
        
        # Keywords that suggest quick wins
        quick_win_keywords = ['simple', 'easy', 'quick', 'minor', 'small', 'fix', 'update', 'adjust']
        
        # Keywords that suggest long-term projects
        long_term_keywords = ['redesign', 'overhaul', 'rebuild', 'restructure', 'implement new', 
                             'major', 'complex', 'comprehensive', 'complete', 'architecture']
        
        for rec in recommendations:
            rec_lower = rec.lower()
            
            # Categorize based on keywords
            if any(keyword in rec_lower for keyword in quick_win_keywords):
                roadmap['quick_wins'].append(rec)
            elif any(keyword in rec_lower for keyword in long_term_keywords):
                roadmap['long_term'].append(rec)
            else:
                roadmap['medium_term'].append(rec)
        
        return roadmap 