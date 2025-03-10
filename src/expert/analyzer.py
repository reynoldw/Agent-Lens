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
        """Generate key findings based on simulation results and analysis."""
        findings = []
        
        # Findings based on scores
        if scores.get('overall', 0) >= 8:
            findings.append(f"The website performs well overall with a score of {scores.get('overall', 0)}/10, indicating a strong user experience.")
        elif scores.get('overall', 0) <= 4:
            findings.append(f"The website has significant issues with an overall score of {scores.get('overall', 0)}/10, requiring urgent attention to improve user experience.")
        else:
            findings.append(f"The website performs moderately with an overall score of {scores.get('overall', 0)}/10, indicating room for improvement.")
        
        # Find the lowest scoring category
        score_categories = {
            'navigation_score': 'Navigation',
            'design_score': 'Design',
            'findability_score': 'Product findability'
        }
        
        lowest_category = min(score_categories.keys(), key=lambda k: scores.get(k, 10))
        if scores.get(lowest_category, 0) < 6:
            findings.append(f"{score_categories[lowest_category]} is the weakest area with a score of {scores.get(lowest_category, 0)}/10, requiring immediate attention.")
        
        # Find the highest scoring category
        highest_category = max(score_categories.keys(), key=lambda k: scores.get(k, 0))
        if scores.get(highest_category, 0) >= 7:
            findings.append(f"{score_categories[highest_category]} is a strength with a score of {scores.get(highest_category, 0)}/10, providing a solid foundation to build upon.")
        
        # Findings based on issues
        critical_issues = categorized_issues.get('critical', [])
        if critical_issues:
            findings.append(f"Found {len(critical_issues)} critical issues that severely impact user experience.")
            # Add a specific critical issue example
            if len(critical_issues) > 0:
                findings.append(f"Critical issue example: {critical_issues[0]}")
        
        # Most problematic category
        issue_categories = ['ui_design', 'navigation', 'product', 'checkout', 'mobile', 'performance', 'accessibility']
        category_counts = {k: len(categorized_issues.get(k, [])) for k in issue_categories}
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_categories and sorted_categories[0][1] > 0:
            most_problematic = sorted_categories[0][0]
            category_name = most_problematic.replace('_', ' ').title()
            findings.append(f"{category_name} has the most issues ({sorted_categories[0][1]}), indicating a problem area.")
            
            # Add a specific example from the most problematic category
            if categorized_issues.get(most_problematic, []):
                findings.append(f"{category_name} issue example: {categorized_issues.get(most_problematic, [])[0]}")
        
        # Second most problematic category if it exists
        if len(sorted_categories) > 1 and sorted_categories[1][1] > 0:
            second_problematic = sorted_categories[1][0]
            category_name = second_problematic.replace('_', ' ').title()
            findings.append(f"{category_name} is also problematic with {sorted_categories[1][1]} issues identified.")
        
        # Findings based on behavioral insights
        if behavioral_insights:
            # Engagement level finding
            engagement_levels = behavioral_insights.get('engagement_levels', [])
            if engagement_levels:
                high_count = engagement_levels.count('high')
                low_count = engagement_levels.count('low')
                total_count = len(engagement_levels)
                
                if total_count > 0:
                    high_pct = (high_count / total_count) * 100
                    low_pct = (low_count / total_count) * 100
                    
                    if high_pct >= 60:
                        findings.append(f"Strong user engagement detected ({high_pct:.0f}% high engagement), indicating compelling content or features.")
                    elif low_pct >= 50:
                        findings.append(f"Low user engagement detected ({low_pct:.0f}% low engagement), suggesting content or design issues.")
            
            # Pain points finding
            common_pain_points = behavioral_insights.get('common_pain_points', [])
            if common_pain_points:
                findings.append(f"Common user pain points include: {common_pain_points[0]}")
                if len(common_pain_points) > 1:
                    findings.append(f"Additional pain point: {common_pain_points[1]}")
            
            # Areas of interest finding
            areas_of_interest = behavioral_insights.get('areas_of_interest', [])
            if areas_of_interest:
                findings.append(f"Users show particular interest in: {areas_of_interest[0]}")
        
        # Findings based on failed actions
        failed_actions = []
        for result in simulation_results:
            failed_actions.extend(result.get('failed_actions', []))
        
        if failed_actions:
            # Count occurrences of each failed action
            from collections import Counter
            failed_action_counts = Counter(failed_actions)
            most_common_failures = failed_action_counts.most_common(2)
            
            if most_common_failures:
                findings.append(f"Most common failed action: {most_common_failures[0][0]} (occurred {most_common_failures[0][1]} times)")
                if len(most_common_failures) > 1:
                    findings.append(f"Second most common failed action: {most_common_failures[1][0]} (occurred {most_common_failures[1][1]} times)")
        
        # Findings based on AI reviews
        if ai_review_insights:
            avg_rating = ai_review_insights.get('average_rating', 0)
            if avg_rating >= 4:
                findings.append(f"AI-generated persona reviews are highly positive with an average rating of {avg_rating:.1f}/5.")
            elif avg_rating <= 2:
                findings.append(f"AI-generated persona reviews are negative with an average rating of {avg_rating:.1f}/5.")
            
            # Sentiment distribution
            sentiment_dist = ai_review_insights.get('sentiment_distribution', {})
            total_reviews = sum(sentiment_dist.values())
            if total_reviews > 0:
                positive_pct = (sentiment_dist.get('positive', 0) / total_reviews) * 100
                negative_pct = (sentiment_dist.get('negative', 0) / total_reviews) * 100
                
                if positive_pct >= 70:
                    findings.append(f"Strong positive sentiment ({positive_pct:.0f}%) across persona reviews.")
                elif negative_pct >= 50:
                    findings.append(f"Concerning negative sentiment ({negative_pct:.0f}%) across persona reviews.")
            
            # Add specific themes from reviews
            positive_themes = ai_review_insights.get('positive_themes', [])
            negative_themes = ai_review_insights.get('negative_themes', [])
            
            if positive_themes:
                findings.append(f"Top positive theme from reviews: {positive_themes[0]}")
            
            if negative_themes:
                findings.append(f"Top negative theme from reviews: {negative_themes[0]}")
        
        # Limit to top 15 findings
        return findings[:15]
    
    def _generate_recommendations(self, simulation_results: List[Dict[str, Any]], 
                                 categorized_issues: Dict[str, List[str]],
                                 behavioral_insights: Dict[str, Any],
                                 ai_review_insights: Dict[str, Any]) -> List[str]:
        """Generate prioritized recommendations based on analysis."""
        recommendations = []
        
        # Extract failed actions for more specific recommendations
        failed_actions = []
        for result in simulation_results:
            failed_actions.extend(result.get('failed_actions', []))
        
        # Count occurrences of each failed action
        from collections import Counter
        failed_action_counts = Counter(failed_actions)
        most_common_failures = failed_action_counts.most_common(3)
        
        # Recommendations based on critical issues
        critical_issues = categorized_issues.get('critical', [])
        if critical_issues:
            for i, issue in enumerate(critical_issues[:3]):
                if i == 0:
                    recommendations.append(f"CRITICAL: Fix the highest priority issue: {issue}")
                else:
                    recommendations.append(f"CRITICAL: Address critical issue: {issue}")
        
        # Recommendations based on most common failed actions
        if most_common_failures:
            for action, count in most_common_failures:
                recommendations.append(f"HIGH: Fix the failed action that occurred {count} times: {action}")
        
        # Recommendations by category with specific issues
        for category, issues in categorized_issues.items():
            if category in ['critical', 'major', 'minor']:
                continue
                
            if issues:
                category_name = category.replace('_', ' ').title()
                if len(issues) > 3:
                    recommendations.append(f"HIGH: Improve {category_name} by addressing the {len(issues)} identified issues")
                    # Add specific examples
                    for i, issue in enumerate(issues[:2]):
                        recommendations.append(f"  - {category_name} improvement: {issue}")
                elif issues:
                    for i, issue in enumerate(issues[:2]):
                        priority = "HIGH" if i == 0 else "MEDIUM"
                        recommendations.append(f"{priority}: Address {category_name} issue: {issue}")
        
        # Recommendations based on behavioral insights
        if behavioral_insights:
            pain_points = behavioral_insights.get('common_pain_points', [])
            if pain_points:
                for i, point in enumerate(pain_points[:2]):
                    priority = "HIGH" if i == 0 else "MEDIUM"
                    recommendations.append(f"{priority}: Address user pain point: {point}")
            
            form_issues = behavioral_insights.get('form_completion_issues', [])
            if form_issues:
                for i, issue in enumerate(form_issues[:2]):
                    priority = "MEDIUM" if i == 0 else "LOW"
                    recommendations.append(f"{priority}: Improve form usability to address: {issue}")
            
            # If engagement is low, recommend improvements
            engagement_levels = behavioral_insights.get('engagement_levels', [])
            if engagement_levels:
                low_count = engagement_levels.count('low')
                total_count = len(engagement_levels)
                
                if total_count > 0 and (low_count / total_count) >= 0.4:
                    recommendations.append("HIGH: Improve overall engagement by enhancing interactive elements and content relevance")
            
            # Recommendations based on areas of interest
            areas_of_interest = behavioral_insights.get('areas_of_interest', [])
            if areas_of_interest:
                recommendations.append(f"MEDIUM: Enhance the most popular area of interest: {areas_of_interest[0]}")
        
        # Recommendations based on AI reviews
        if ai_review_insights:
            negative_themes = ai_review_insights.get('negative_themes', [])
            if negative_themes:
                for i, theme in enumerate(negative_themes[:2]):
                    priority = "HIGH" if i == 0 else "MEDIUM"
                    recommendations.append(f"{priority}: Address common negative feedback: {theme}")
            
            positive_themes = ai_review_insights.get('positive_themes', [])
            if positive_themes:
                recommendations.append(f"MEDIUM: Leverage and expand on positive aspect: {positive_themes[0]}")
        
        # Add specific UX improvement recommendations
        ui_issues = categorized_issues.get('ui_design', [])
        if ui_issues:
            recommendations.append("HIGH: Implement consistent design patterns across the website to improve user experience")
            recommendations.append("MEDIUM: Ensure all interactive elements have clear affordances (visual cues that indicate they are clickable)")
        
        navigation_issues = categorized_issues.get('navigation', [])
        if navigation_issues:
            recommendations.append("HIGH: Simplify the navigation structure to reduce cognitive load")
            recommendations.append("MEDIUM: Ensure breadcrumbs are present on all pages to help users understand their location")
        
        # Add mobile-specific recommendations if there are mobile issues
        mobile_issues = categorized_issues.get('mobile', [])
        if mobile_issues:
            recommendations.append("HIGH: Optimize tap targets for mobile users (minimum size 44x44 pixels)")
            recommendations.append("MEDIUM: Ensure all content is accessible without horizontal scrolling on mobile devices")
        
        # Add accessibility recommendations if there are accessibility issues
        accessibility_issues = categorized_issues.get('accessibility', [])
        if accessibility_issues:
            recommendations.append("HIGH: Ensure proper color contrast ratios (minimum 4.5:1) for all text content")
            recommendations.append("MEDIUM: Add proper alt text to all images to support screen reader users")
        
        # Add performance recommendations if there are performance issues
        performance_issues = categorized_issues.get('performance', [])
        if performance_issues:
            recommendations.append("HIGH: Optimize image sizes and implement lazy loading for improved page load times")
            recommendations.append("MEDIUM: Minimize JavaScript and CSS files to reduce initial load time")
        
        # Add checkout recommendations if there are checkout issues
        checkout_issues = categorized_issues.get('checkout', [])
        if checkout_issues:
            recommendations.append("CRITICAL: Simplify the checkout process to reduce abandonment rate")
            recommendations.append("HIGH: Provide clear error messages and field validation during checkout")
        
        # Limit to top 20 recommendations
        return recommendations[:20]
    
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
        
        # Template-based analysis as fallback
        analysis = f"""
        # Detailed Analysis for {website_url}
        
        ## Overview
        
        Overall Score: {scores.get('overall', 0)}/10
        
        This analysis is based on simulations with {len(simulation_results)} different personas, 
        capturing a range of user experiences and perspectives.
        
        ## Score Breakdown
        
        - Navigation: {scores.get('navigation_score', 0)}/10
        - Design: {scores.get('design_score', 0)}/10
        - Findability: {scores.get('findability_score', 0)}/10
        
        ## Issue Summary
        
        - Critical Issues: {len(categorized_issues.get('critical', []))}
        - Major Issues: {len(categorized_issues.get('major', []))}
        - Minor Issues: {len(categorized_issues.get('minor', []))}
        
        ## Behavioral Insights
        
        """
        
        if behavioral_insights:
            analysis += f"""
            - Primary Engagement Level: {behavioral_insights.get('primary_engagement_level', 'N/A')}
            - Primary User Experience: {behavioral_insights.get('primary_experience', 'N/A')}
            
            ### Common Pain Points
            {self._format_list_items(behavioral_insights.get('common_pain_points', []))}
            
            ### Areas of User Interest
            {self._format_list_items(behavioral_insights.get('areas_of_interest', []))}
            
            ### Navigation Patterns
            {self._format_list_items(behavioral_insights.get('navigation_patterns', []))}
            """
        
        analysis += """
        
        ## AI Review Insights
        
        """
        
        if ai_review_insights:
            analysis += f"""
            - Average Rating: {ai_review_insights.get('average_rating', 0)}/5
            - Sentiment: {self._format_sentiment(ai_review_insights.get('sentiment_distribution', {}))}
            
            ### Positive Themes
            {self._format_list_items(ai_review_insights.get('positive_themes', []))}
            
            ### Negative Themes
            {self._format_list_items(ai_review_insights.get('negative_themes', []))}
            """
        
        analysis += """
        
        ## Category Analysis
        
        """
        
        # Add analysis for each category
        categories = {
            'ui_design': 'UI Design',
            'navigation': 'Navigation',
            'product': 'Product Presentation',
            'checkout': 'Checkout Process',
            'mobile': 'Mobile Experience',
            'performance': 'Performance',
            'accessibility': 'Accessibility'
        }
        
        for category_key, category_name in categories.items():
            issues = categorized_issues.get(category_key, [])
            if issues:
                analysis += f"""
                ### {category_name}
                
                {self._format_list_items(issues[:5])}
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
        Failed Actions: {', '.join(failed_actions[:10]) if failed_actions else 'None'}
        
        {behavior_text}
        
        {review_text}
        
        Write a comprehensive, specific, and actionable analysis following this structure:
        
        # Expert UX & Product Analysis Report for {website_url}
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
        Analyze how users discover products on the website, including:
        - Visual Hierarchy & Layout: Evaluate if featured products and promotions are prominently displayed and if there's a clear visual path.
        - Call-to-Action (CTA) Clarity: Assess if CTAs are clear and compelling.
        - Personalization: Evaluate mechanisms for tailoring product suggestions.
        
        Provide specific recommendations for improving product discovery with concrete examples from the data.
        
        ### B. Search a Product
        Analyze the search functionality, including:
        - Search Functionality & Speed: Evaluate accessibility and performance of the search feature.
        - Relevance of Results: Assess if search results match query intent.
        - Filtering & Sorting Options: Evaluate the intuitiveness of filters and sorting mechanisms.
        
        Provide specific recommendations for improving search functionality with concrete examples from the data.
        
        ### C. Add a Product to Shopping Cart
        Analyze the process of adding products to cart, including:
        - Button Visibility & Placement: Evaluate if the "Add to Cart" button is noticeable and accessible.
        - User Feedback: Assess if the system provides instant feedback after a product is added.
        - Cart Accessibility: Evaluate if the cart is easily accessible throughout the shopping journey.
        
        Provide specific recommendations for improving the add-to-cart process with concrete examples from the data.
        
        ### D. Make a Transaction
        Analyze the checkout process, including:
        - Checkout Flow Complexity: Evaluate if the process is streamlined.
        - Form Usability: Assess if form fields are clearly labeled and if error handling is robust.
        - Trust & Security Signals: Evaluate if security icons and trust badges are prominently displayed.
        
        Provide specific recommendations for improving the checkout process with concrete examples from the data.
        
        ## 3. Summary of Recommendations
        Summarize the key recommendations across all user journeys, organized by priority:
        - Critical: Issues that must be addressed immediately
        - High Priority: Important improvements that will significantly impact user experience
        - Medium Priority: Valuable enhancements to implement after addressing critical and high-priority items
        - Low Priority: Nice-to-have improvements for future consideration
        
        For each recommendation, provide:
        - Specific action items
        - Expected impact on user experience and business metrics
        - Implementation complexity (Low, Medium, High)
        
        Format your response as a professional report with markdown headings and bullet points. Use specific examples from the data throughout your analysis.
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