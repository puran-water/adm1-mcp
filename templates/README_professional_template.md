# Professional ADM1 Report Template

This directory contains the template and utilities for generating professional ADM1 simulation reports.

## Overview

The professional template provides an enhanced reporting capability for the ADM1 MCP server. It preserves the step-by-step educational flow of tool execution while producing comprehensive, aesthetically pleasing reports.

## Files

The template consists of the following key components:

- `professional_template.ipynb`: The main Jupyter notebook template for report generation
- `professional_template_utils.py`: Utility functions specific to the professional report template
- `report_metadata.py`: Functions to handle and format report metadata
- `tool_response_formatter.py`: Functions to format tool responses for the report
- `styles.css`: CSS styling for the report output
- `analysis_functions.py`: Functions for analyzing simulation results
- `enhanced_plot_functions.py`: Functions for creating plots
- `kpi_cards.py`: Functions for creating key performance indicator cards

## Integration with ADM1 MCP Server

The template integrates with the ADM1 MCP server by capturing tool responses during simulation and using them to generate the report. The `generate_report()` tool function in the server uses Papermill to execute the template with the appropriate parameters.

## Usage

The report template can be used in two ways:

1. Through the `generate_report()` tool in the ADM1 MCP server
2. Manually by executing the test script: `python test_professional_report.py`

### Parameters

When executing the template, the following parameters must be provided:

- `feedstock_params`: Dictionary of feedstock composition parameters
- `kinetic_params`: Dictionary of kinetic parameters
- `flow_params`: Dictionary of flow parameters
- `reactor_params`: Dictionary of reactor parameters
- `simulation_index`: Index of the simulation to be reported (1-3)
- `tool_responses`: Dictionary of tool responses captured during simulation
- `include_technical_details`: Boolean flag to control technical detail level

Example:

```python
parameters = {
    "feedstock_params": {
        "carbohydrates [%]": 55.0,
        "proteins [%]": 20.0,
        "lipids [%]": 15.0,
        "inerts [%]": 10.0
    },
    "kinetic_params": {
        "k_dis [d^-1]": 0.5,
        "k_hyd_ch [d^-1]": 10.0
    },
    "flow_params": {
        "flow_rate [m³/d]": 100.0
    },
    "reactor_params": {
        "reactor_volume [m³]": 1000.0,
        "temperature [°C]": 35.0
    },
    "simulation_index": 1,
    "tool_responses": {...},  # Dictionary of tool responses
    "include_technical_details": True
}
```

## Report Structure

The generated report includes the following sections:

1. **Title Page**: Report title, simulation identifier, and metadata
2. **Executive Summary**: Key performance indicators and brief description
3. **Simulation Configuration**: Configuration parameters used for the simulation
4. **Simulation Execution**: Details of the simulation run
5. **Simulation Results**: Detailed results and analysis
6. **Conclusion and Recommendations**: Performance assessment and recommendations
7. **Methodology**: Explanation of the ADM1 model and simulation approach
8. **Appendix**: Complete tool execution flow (if `include_technical_details` is True)

## Customization

The template can be customized in several ways:

1. Modify `styles.css` to change the visual appearance
2. Edit the template notebook to add or remove sections
3. Update the utility functions to change the behavior of specific features

## Testing

To test the template without running the full ADM1 MCP server:

```bash
python test_professional_report.py
```

This will generate a test report with sample data in the `generated_reports` directory.

## Requirements

- Python 3.8+
- Jupyter Notebook
- Papermill
- nbconvert
- nbformat
- plotly
- pandas
- numpy
- IPython