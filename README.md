# AgentReviewHub

![Version](https://img.shields.io/badge/version-1.2.0-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

**AgentReviewHub** is an AI-powered platform that evaluates websites through the lens of diverse simulated user personas. By combining advanced AI agents, browser automation, and expert analysis, it provides comprehensive insights into website usability, design, and user experience.

![AgentReviewHub Dashboard](docs/images/dashboard.png)

## 🌟 Key Features

- **AI Persona Generation**: Creates diverse, realistic user personas with varying demographics, technical skills, and preferences
- **Automated Website Simulation**: Simulates real user interactions including navigation, search, and product exploration
- **Multi-Perspective Analysis**: Evaluates websites from multiple user viewpoints to uncover diverse usability issues
- **AI-Generated Reviews**: Produces detailed, human-like reviews based on simulation experiences
- **Expert Analysis**: Aggregates data to identify patterns, common issues, and improvement opportunities
- **Professional Reports**: Generates comprehensive reports with visualizations, scores, and actionable recommendations
- **Detailed Debugging**: Provides extensive logging for transparency in the evaluation process

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- A valid OpenAI API key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/reynoldw/AgentReviewHub.git
   cd AgentReviewHub
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install browser automation dependencies:
   ```bash
   playwright install
   ```

5. Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

### Running the Application

1. Start the application:
   ```bash
   python run.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Enter a website URL and the number of personas to generate, then click "Start Evaluation"
## 🔧 Configuration

You can customize the evaluation process by modifying the following files:

- `config.py`: General configuration settings
- `src/persona/templates.py`: Persona generation templates and parameters
- `src/expert/analyzer.py`: Analysis parameters and scoring weights

## 🌐 Use Cases

- **E-commerce Optimization**: Identify and fix usability issues that impact conversion rates
- **UX Research**: Gather diverse perspectives on website usability without expensive user testing
- **Competitive Analysis**: Compare your website against competitors across multiple dimensions
- **Accessibility Testing**: Identify potential accessibility issues for users with different needs
- **Pre-launch Validation**: Test new designs or features before public release

## 🔮 Future Expansion

### Social Interactions
- **Multi-Agent Conversations**: Simulate interactions between multiple personas discussing products
- **Social Proof Simulation**: Model how social signals influence purchasing decisions
- **Community Engagement**: Evaluate community features like forums and review sections

### Memory and Adaptive Behavior
- **Long-term User Journeys**: Simulate returning users with memory of previous interactions
- **Learning Behaviors**: Model how users adapt to interfaces over time
- **Preference Evolution**: Track how user preferences change based on experiences

### Social Dynamics
- **Group Decision Making**: Simulate family or team purchasing decisions
- **Influence Networks**: Model how opinions spread through simulated social networks
- **Cultural Variations**: Evaluate how cultural differences affect user experience

### Beyond E-commerce
- **Educational Platforms**: Evaluate learning experiences and knowledge retention
- **Healthcare Interfaces**: Assess medical information accessibility and comprehension
- **Government Services**: Test civic service portals for usability across diverse populations
- **Financial Services**: Evaluate banking and investment platform experiences

## 🛣️ Roadmap

Our immediate focus is on improving the simulation functionality:

1. **Enhanced Browser Interaction**: Developing a custom browser interaction module to replace Playwright for more nuanced control
2. **Expanded Persona Capabilities**: Adding more sophisticated behavioral models and decision-making processes
3. **Custom Persona Creation**: Allowing users to define specific personas for targeted testing
4. **A/B Testing**: Implementing comparison features for evaluating design alternatives
5. **Historical Tracking**: Adding support for tracking website improvements over time

## 📚 Documentation

For more detailed information, please refer to the following documentation:

- [Architecture Overview](docs/architecture.md)
- [Persona Generation](docs/personas.md)
- [Simulation Process](docs/simulation.md)
- [Analysis Methodology](docs/analysis.md)
- [API Reference](docs/api.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- OpenAI for providing the API that powers our AI components
- Playwright for browser automation capabilities
- All contributors who have helped shape this project

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/reynoldw">reynoldw</a>
</p> 
