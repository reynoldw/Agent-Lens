# Changelog

All notable changes to AgentReviewHub will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2023-07-15

### Added
- Journey-based structure for key findings and recommendations
- Print-optimized CSS for better report sharing
- Improved error handling for browser pool initialization
- Resource cleanup function registered with `atexit`
- More detailed scoring visualization in reports

### Changed
- **Major UI Enhancement**: Completely redesigned key findings section with:
  - Overall assessment section with clear scoring
  - Product Discovery Journey section with category exploration insights
  - UI Design & Navigation section with visual design evaluation
  - Product Details Exploration section with product page analysis
  - Shopping Cart & Checkout section with conversion path analysis
  - User Sentiment & Themes section with improved sentiment visualization
  
- **Recommendations Redesign**:
  - Structured into journey-based categories
  - Added implementation complexity indicators (Low, Medium, High)
  - Added expected impact descriptions for each recommendation
  - Highlighted critical issues requiring immediate attention
  
- **Visual Improvements**:
  - Enhanced typography with better heading hierarchy
  - Improved spacing and layout for readability
  - Added color coding for different types of information
  - Better mobile responsiveness for the entire application
  
- **Language Improvements**:
  - Replaced technical terms with human-readable language
  - Simplified complex descriptions for better understanding
  - More conversational tone in findings and recommendations

### Fixed
- Frame navigation event handler now correctly identifies main frames
- Browser pool resource leaks resolved with proper cleanup
- Improved error handling for evaluation not found errors
- Fixed inconsistent sentiment analysis with limited data
- Resolved issues with progress reporting during simulations

## [1.2.0] - 2023-06-01

### Added
- **Enhanced Persona Modeling**: Evolved personas from simple profiles to dynamic representations
  - Added behavioral traits like patience levels and attention spans
  - Implemented realistic distractions and delays in user interactions
  - Created age and tech-proficiency based interaction patterns
  - Developed more authentic shopping experiences for each persona type

- **Advanced Website Browsing Simulations**: Implemented four key shopping journeys
  - **Discover a Product**: Journey automatically tailored to website content
  - **Search for a Product**: Realistic search behaviors with typo simulation
  - **Add a Product to Shopping Cart**: Complete conversion path testing
  - **Complete a Transaction**: End-to-end checkout process evaluation

- Support for Anthropic Claude 3 models (Opus, Sonnet, and Haiku)
- Multi-persona evaluation capabilities with parallel testing
- Enhanced behavioral tracking for more detailed interaction analysis
- Detailed accessibility analysis for inclusive design evaluation

### Changed
- Improved simulation accuracy with more realistic timing and behaviors
- Enhanced report visualizations with journey-specific metrics
- Updated persona generation templates with more diverse characteristics
- Expanded browser automation capabilities for complex interactions

### Fixed
- Browser automation stability issues during long simulation sessions
- Memory leaks in long-running simulations with multiple personas
- Inconsistent scoring in certain e-commerce website scenarios
- Improved error handling for unusual website structures

## [1.1.0] - 2023-04-15

### Added
- AI-powered review generation
- Expert analysis system
- Visualization components for reports
- Expanded persona attributes

### Changed
- Improved browser automation reliability
- Enhanced UI for evaluation results
- Updated documentation

### Fixed
- Various stability issues
- Inconsistent persona generation
- Report formatting problems

## [1.0.0] - 2023-03-01

### Added
- Initial release
- Basic persona generation
- Website simulation with Playwright
- Simple reporting functionality
- Configuration system 