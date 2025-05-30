# ADM1 MCP Server

This MCP server enables natural language control of anaerobic digestion modeling through the internationally recognized Anaerobic Digestion Model No. 1 (ADM1). It bridges Claude or other LLM clients with professional wastewater treatment simulation for process design, optimization, and analysis through conversational prompts.

## Key Features

### Core Simulation Capabilities
- Complete ADM1 implementation with 35+ biochemical and physicochemical processes
- AI-powered feedstock analysis using Google Gemini for natural language to parameter conversion
- Multi-reactor simulation support (up to 3 reactor configurations)
- Dynamic pH calculation with comprehensive inhibition modeling
- Professional report generation with publication-quality visualizations

### Advanced Analysis Tools
- **Stream Analysis**: Detailed composition analysis for influent, effluent, and biogas streams
- **Process Health Assessment**: Comprehensive inhibition analysis with optimization recommendations
- **Performance Metrics**: COD removal efficiency, methane production, and biomass yields
- **Charge Balance Validation**: Thermodynamic consistency verification for feedstock definitions
- **Interactive Visualizations**: Real-time charts with actual simulation data

### Professional Reporting
- **Publication-Quality Reports**: Professional HTML/PDF reports with comprehensive analysis
- **KPI Dashboards**: Interactive performance indicators and process metrics
- **Technical Documentation**: Complete methodology sections with scientific references
- **Data Export**: Professional formatting with no scientific notation artifacts

## Prerequisites

- **Python 3.8 or higher**
- **Google API Key** (for AI-powered feedstock analysis)
- **Claude Desktop** or other MCP client application
- **QSDsan** (automatically installed with dependencies)

## Setup Instructions

### 1. Install Dependencies
```bash
git clone https://github.com/puran-water/adm1-mcp.git
cd adm1-mcp
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your Google API key:
# GOOGLE_API_KEY=your_google_api_key_here
```

**Get Google API Key:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create new API key
3. Add to `.env` file

### 3. Configure Claude Desktop

Add to your `claude_desktop_config.json`:

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

### 4. Restart Claude Desktop

After updating the configuration, restart Claude Desktop to load the ADM1 server.

## Available Tools

### Core Simulation Tools
- `describe_feedstock`: Convert natural language feedstock description to ADM1 state variables
- `describe_kinetics`: Generate both state variables AND kinetic parameters from feedstock description
- `set_flow_parameters`: Configure influent flow rate and simulation timing parameters
- `set_reactor_parameters`: Set reactor-specific parameters (temperature, HRT, integration method)
- `run_simulation_tool`: Execute ADM1 simulation with current parameters

### Analysis Tools
- `get_stream_properties`: Analyze detailed properties of influent, effluent, or biogas streams
- `get_inhibition_analysis`: Process health assessment with inhibition factors and recommendations
- `get_biomass_yields`: Calculate process performance metrics and efficiency
- `validate_feedstock_charge_balance`: Verify thermodynamic consistency of feedstock definition
- `check_nutrient_balance`: Analyze C:N:P ratios for process optimization

### Utility Tools
- `get_parameter`: Retrieve current parameter values from simulation state
- `set_parameter`: Modify specific simulation parameters
- `generate_report`: Create comprehensive professional simulation reports
- `reset_simulation`: Reset all parameters to default values

## System Prompt for LLM Integration

When using this MCP server with Claude or other LLMs, use this system prompt for optimal performance:

```markdown
**Available Tools**

You have access to the following ADM1 simulation tools:

1. describe_feedstock - Generate ADM1 state variables from a natural language description. Either this tool or describe_kinetics should be called prior to a simulation - there will never be a case where both tools need to be called.
 - Input: feedstock_description (string) - Detailed description of the feedstock
 - Use this to convert user descriptions of waste/feedstock into precise ADM1 parameters

2. describe_kinetics - Generate **both state variables AND kinetic parameters** from a natural language description. Either this tool or describe_feedstock should be called prior to a simulation - there will never be a case where both tools need to be called.
 - Input: feedstock_description (string) - Detailed description of the feedstock
 - Use this when users want customized kinetic parameters for their specific feedstock
 
3. set_flow_parameters - Set the influent flow rate and simulation timing parameters
 - Inputs: flow_rate (m³/d), simulation_time (days), time_step (days)
 - Use this to configure the basic hydraulic and simulation parameters
 
4. set_reactor_parameters - Set parameters for a specific reactor simulation
 - Inputs: reactor_index (1-3), temperature (K), hrt (days), integration_method (string)
 - Valid integration methods: "BDF", "RK45", "RK23", "DOP853", "Radau", "LSODA"
 - Use this to customize up to three different reactor configurations
 
5. run_simulation_tool - Run the ADM1 simulation with current parameters
 - No inputs required - uses previously set parameters
 - Call this after setting up feedstock and reactor parameters
                
6. get_stream_properties - Get detailed properties of a specified stream
 - Input: stream_type (string) - One of: "influent", "effluent1", "effluent2", "effluent3", "biogas1", "biogas2", "biogas3"
 - Use this to analyze composition and properties of input/output streams
 
7. get_inhibition_analysis - Get process health and inhibition analysis
 - Input: simulation_index (1-3) - Which simulation to analyze
 - Use this to diagnose process issues and get optimization recommendations
  
8. get_biomass_yields - Calculate biomass yields from a simulation
 - Input: simulation_index (1-3) - Which simulation to analyze
 - Use this to determine VSS and TSS yields and process efficiency
  
9. reset_simulation - Reset all simulation parameters to defaults
 - No inputs required
 - Use this to start fresh with default settings                    
         
10. Other tools (available for specific situations):
 - validate_feedstock_charge_balance: Check charge balance consistency after feedstock definition
 - get_parameter: Retrieve current parameter values
 - set_parameter: Modify specific parameters (invalidates previous simulation results)
 - generate_report: Create professional simulation reports

**Interaction Guidelines**

Anaerobic Digestion Simulation Support Protocol:

1. Guide the user through the following steps prior to running a simulation - asking for permission to proceed to the next step following the completion of each step. If the user asks for changes, perform the step again with the changes.

 - Step 1: Take the user's prompt and request clarifications on the feedstock characteristics (most importantly, COD concentration, TKN concentration, pH, and alkalinity) and flowrate. Further, request clarity on whether the user would like you to determine the feedstock state variables alone or both the feedstock state variables and kinetic parameters. This will determine whether you use the describe_feedstock or describe_kinetics function using the user's description of the feedstock.
                
 - Step 2: Call either the describe_feedstock or describe_kinetics tool based on the result of Step 1. Present the output of this tool call in a table that presents the variable name, the units of measurement, the variable value, and the reason/explanation for why this value was chosen (all of which are outputs of the tool call).
                
 - Step 3: Use the validate_feedstock_charge_balance tool to check the charge balance of the feedstock. If the charge balance is not valid based on the predicted concentration of H+ and OH- compared with the feedstock pH, present the user with your suggestion on how you can use the set_parameter tool to adjust the S_cat and/or S_an values to ensure that the charge balance is valid.
  
 - Step 4: After receiving user confirmation, proceed with setting the parameter to ensure the charge balance is valid.
                
 - Step 5: Request the user's permission to proceed with the simulation. Unless the user already specified the HRT, temperature, simulation time, and simulation time step, present your intention of running three simulations (Index 1 at a 20 d HRT reactor volume, Index 2 at a 30 d HRT reactor volume, and Index 3 at a 45 d HRT reactor volume) at a 38 deg C reactor temperature, 300 d simulation time, 0.1 d time step, and the BDF integration method.
 
 - Step 6: Run the simulation and present the results of the simulation as follows:
  - get_stream_properties and present a table **for all parameters that the tool returns** for the feedstock and the effluent
  - get_stream_properties and present a table **for all parameters that the tool returns** for the biogas flow and composition
  - get_biomass_yields and present a table **for all parameters that the tool returns** presenting excess sludge production
  - get_inhibition_analysis and present a table **for all parameters that the tool returns** for the health of the process
```

## Usage Examples

### Basic Simulation Workflow
```
"I want to simulate anaerobic digestion of food waste containing 40% vegetables, 30% bread, 20% fruit, 10% meat with 85,000 mg/L COD"

"Set up a reactor at 35°C with 25-day HRT and 150 m³/d flow rate"

"Run the simulation and analyze the biogas production and process efficiency"
```

### Process Optimization
```
"What inhibition factors are limiting performance in reactor 2?"

"Compare methane production between different HRT scenarios"

"The pH is dropping in my reactor. What's causing this and how can I fix it?"
```

### Advanced Analysis
```
"Generate a comprehensive report for simulation 1 with all analysis and recommendations"

"Analyze the nutrient balance for my POME feedstock at pH 4.5"

"Compare the performance of primary sludge vs food waste as feedstock"
```

## Scientific Background

### ADM1 Model Implementation

The server implements the complete IWA ADM1 standard including:

1. **Biochemical Processes**:
   - Disintegration of complex particulates
   - Hydrolysis of carbohydrates, proteins, and lipids
   - Acidogenesis and acetogenesis
   - Methanogenesis (acetotrophic and hydrogenotrophic)

2. **Physicochemical Processes**:
   - Liquid-gas transfer (CH₄, CO₂, H₂)
   - Ion association/dissociation
   - Dynamic pH calculation based on charge balance

3. **Inhibition Mechanisms**:
   - pH inhibition affecting all microbial groups
   - Free ammonia inhibition (particularly acetoclastic methanogens)
   - Hydrogen inhibition affecting acetogenic processes
   - VFA inhibition from organic acid accumulation

### Integration Methods

Supports multiple numerical integration methods:
- **BDF**: Backward Differentiation Formula (recommended for stiff systems)
- **RK45**: Runge-Kutta 4(5) method
- **RK23**: Runge-Kutta 2(3) method
- **LSODA**: Livermore Solver for ODEs with automatic method switching
- **Radau**: Implicit Runge-Kutta method
- **DOP853**: Dormand-Prince 8(5,3) method

## Performance Features

### Professional Report Generation
- **No Scientific Notation**: Large values display as "13,489 m³/d" instead of "1.349e+04"
- **Actual Data Extraction**: Real simulation results instead of placeholder values
- **Context-Aware Formatting**: Appropriate precision for different measurement types
- **Clean Presentation**: No debug artifacts or programming messages

### Optimization Features
- **AI-Powered Parameter Generation**: Natural language to ADM1 parameter conversion
- **Multi-Reactor Scenarios**: Compare up to 3 different configurations simultaneously
- **Comprehensive Validation**: Charge balance and nutrient ratio verification
- **Process Diagnostics**: Detailed inhibition analysis with optimization guidance

## Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure virtual environment is activated and dependencies installed
pip install -r requirements.txt --force-reinstall
```

**2. Google API Key Issues**
```bash
# Verify .env file format
cat .env
# Should show: GOOGLE_API_KEY=your_key_here
```

**3. Claude Desktop Connection Issues**
- Verify file paths in MCP configuration are correct
- Ensure Python executable path is accurate
- Restart Claude Desktop after configuration changes
- Check MCP_TIMEOUT is set to 600000 for complex simulations

**4. Simulation Convergence Issues**
- Try different integration methods (BDF recommended for most cases)
- Adjust time step (0.1 days recommended)
- Check feedstock charge balance before simulation
- Verify realistic feedstock concentrations

## What's New in This Version

### Latest Improvements
- ✅ **Professional Number Formatting**: Eliminated scientific notation in reports
- ✅ **Real Data Extraction**: Actual simulation results replace placeholder values
- ✅ **Enhanced AI Integration**: Improved Google Gemini feedstock analysis
- ✅ **Comprehensive Validation**: Advanced charge balance and nutrient checking
- ✅ **Publication-Quality Reports**: Professional visualizations and documentation
- ✅ **MCP Protocol Optimization**: Improved performance and reliability
- ✅ **Security Enhancements**: Proper API key protection and input validation

## License

This project builds upon the original ADM1 implementation and follows appropriate licensing for scientific software.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test with both basic and advanced simulation scenarios
4. Submit a pull request with clear documentation

## Support

- **Issues**: [GitHub Issues](https://github.com/puran-water/adm1-mcp/issues)
- **Documentation**: Check repository documentation files
- **Scientific References**: IWA ADM1 documentation and QSDsan framework

---

*Built for the water treatment engineering community with professional-grade simulation capabilities.*