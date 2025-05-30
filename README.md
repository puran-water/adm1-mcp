# ADM1 MCP Server

A Model Context Protocol (MCP) server implementing the Anaerobic Digestion Model No. 1 (ADM1) for professional wastewater treatment simulation and analysis.

## Overview

The ADM1 MCP Server provides a comprehensive implementation of the internationally recognized ADM1 standard, developed by the International Water Association (IWA). This server enables AI assistants to perform advanced anaerobic digestion modeling through natural language interactions via MCP clients like Claude Desktop.

### Key Features

- **Complete ADM1 Implementation**: Full biochemical and physicochemical process modeling
- **AI-Powered Feedstock Analysis**: Natural language to ADM1 parameter conversion using Google Gemini
- **Professional Report Generation**: Publication-quality reports with tables, charts, and KPI dashboards
- **Real-time Analysis**: Stream composition, inhibition analysis, and process optimization
- **Interactive Visualizations**: Process performance dashboards and biogas composition charts
- **Comprehensive Diagnostics**: Process health assessment and troubleshooting guidance

## Quick Start

### Prerequisites

- Python 3.8+
- Google API Key for AI assistant functionality
- MCP client (e.g., Claude Desktop)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/puran-water/adm1-mcp.git
   cd adm1-mcp
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your Google API key
   ```

### MCP Client Configuration

Add the server to your MCP client configuration. For Claude Desktop, add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "adm1-mcp": {
      "command": "C:\\path\\to\\your\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\adm1-mcp\\server.py"],
      "env": {
        "MCP_TIMEOUT": "600000"
      }
    }
  }
}
```

**Configuration File Locations:**
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`

After updating the configuration, restart Claude Desktop.

## Environment Setup

### Google API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Add it to your `.env` file:
   ```bash
   GOOGLE_API_KEY=your_google_api_key_here
   ```

## MCP Tools

The server exposes the following tools for AI assistant interaction:

### Core Simulation Tools

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `describe_feedstock` | Convert natural language feedstock description to ADM1 parameters | Feedstock description | State variables + explanations |
| `validate_feedstock_charge_balance` | Validate charge balance of feedstock composition | Feedstock data | Balance analysis |
| `set_flow_parameters` | Configure flow rate and simulation parameters | Flow rate, time parameters | Confirmation |
| `set_reactor_parameters` | Set reactor-specific parameters | Temperature, HRT, method | Confirmation |
| `run_simulation_tool` | Execute ADM1 simulation | Simulation index | Results + stream data |

### Analysis Tools

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `get_stream_properties` | Analyze influent, effluent, or biogas properties | Stream type | Detailed composition |
| `get_inhibition_analysis` | Process health and inhibition assessment | Simulation index | Inhibition factors + recommendations |
| `get_biomass_yields` | Calculate process performance metrics | Simulation index | COD removal, yields, efficiency |
| `check_nutrient_balance` | Verify C:N:P ratios | Simulation index | Nutrient analysis |

### Report Generation

| Tool | Description | Input | Output |
|------|-------------|-------|--------|
| `generate_report` | Create professional simulation report | Simulation index, report type | Professional HTML/PDF report |

## Report Features

### Professional Reports Include:

- **Executive Summary**: Key performance indicators and process assessment
- **Configuration Documentation**: Complete parameter and setup record
- **Process Performance Dashboard**: Interactive charts and KPI cards
- **Stream Analysis**: Detailed influent, effluent, and biogas composition
- **Process Health Assessment**: Inhibition analysis and recommendations
- **Performance Metrics**: COD removal efficiency, methane production, yields
- **Methodology Section**: Complete ADM1 model documentation

### Latest Improvements

- **Professional Number Formatting**: No scientific notation (e.g., "13,489 m³/d" instead of "1.349e+04")
- **Actual Data Extraction**: Real simulation results instead of placeholder values
- **Clean Professional Presentation**: No debug artifacts or programming messages
- **Context-Aware Formatting**: Appropriate precision for different measurement types
- **Interactive Visualizations**: Real-time charts with actual biogas composition

## Example Usage

### Basic Simulation Workflow

```
# 1. Describe your feedstock
"Analyze food waste containing 40% vegetables, 30% bread, 20% fruit, 10% meat with 85,000 mg/L COD"

# 2. Set operating parameters  
"Configure reactor 1 with 35°C temperature, 25-day HRT, and 150 m³/d flow rate"

# 3. Run simulation
"Execute the ADM1 simulation and analyze the results"

# 4. Generate professional report
"Create a comprehensive report for simulation 1 with all analysis and recommendations"
```

### Advanced Analysis

```
# Process optimization
"What inhibition factors are limiting performance in reactor 2?"

# Comparative analysis
"Compare methane production between reactors 1, 2, and 3"

# Troubleshooting
"The pH is dropping in my reactor. What's causing this and how can I fix it?"
```

## Architecture

### Core Components

```
adm1_mcp_server/
├── server.py              # Main MCP server with tool definitions
├── simulation.py          # ADM1 simulation engine
├── ai_assistant.py        # Google Gemini AI integration
├── stream_analysis.py     # Stream composition analysis
├── inhibition.py          # Process inhibition analysis
├── utils.py               # Utility functions
└── templates/
    ├── data_parsers.py     # Data formatting and table generation
    ├── enhanced_functions.py # Professional formatting tools
    ├── enhanced_plot_functions.py # Advanced visualizations
    ├── professional_template.ipynb # Report template
    └── styles.css          # Professional styling
```

### Technology Stack

- **QSDsan**: Process simulation framework
- **Google Gemini AI**: Natural language parameter generation
- **FastMCP**: High-performance MCP server implementation
- **Plotly**: Interactive data visualization
- **Jupyter/Quarto**: Professional report generation
- **Pandas**: Data manipulation and analysis

## Scientific Background

### ADM1 Model

The Anaerobic Digestion Model No. 1 (ADM1) simulates:

1. **Biochemical Processes**:
   - Disintegration of complex particulates
   - Hydrolysis of carbohydrates, proteins, and lipids
   - Acidogenesis and acetogenesis
   - Methanogenesis (acetotrophic and hydrogenotrophic)

2. **Physicochemical Processes**:
   - Liquid-gas transfer (CH₄, CO₂, H₂)
   - Ion association/dissociation
   - Dynamic pH calculation

3. **Inhibition Mechanisms**:
   - pH inhibition
   - Free ammonia inhibition
   - Hydrogen inhibition
   - VFA inhibition

## Testing

The server includes comprehensive test suites to verify functionality:

```bash
# Test core functionality
python test_end_to_end.py

# Test report improvements
python test_report_improvements.py
```

## Development

### File Organization

- **Core modules**: Primary simulation and analysis logic
- **Templates**: Report generation and visualization
- **Archive**: Deprecated files and development history
- **Generated reports**: Output location for HTML/PDF reports

### Contributing

1. Follow existing code style and patterns
2. Test all changes with the provided test suite
3. Update documentation for new features
4. Maintain professional report quality standards

## Security

- **API Key Protection**: Never commit `.env` files
- **Input Validation**: All user inputs are validated
- **Error Handling**: Graceful degradation for missing dependencies
- **Safe Execution**: Sandboxed simulation environment

## References

1. Batstone, D.J., et al. (2002). The IWA Anaerobic Digestion Model No 1 (ADM1). *Water Science and Technology*, 45(10), 65-73.
2. QSDsan Documentation: [https://qsdsan.readthedocs.io/](https://qsdsan.readthedocs.io/)
3. Model Context Protocol: [https://github.com/anthropics/mcp](https://github.com/anthropics/mcp)

## Support

For questions, issues, or contributions:

- Create an issue in the GitHub repository
- Check the documentation in the repository
- Review example usage and test files

## License

This project builds upon the original ADM1 implementation and follows appropriate licensing for scientific software.

---

*Built for the water treatment engineering community*