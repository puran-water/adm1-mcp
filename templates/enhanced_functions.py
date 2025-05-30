"""
Enhanced functions for tool response formatting in ADM1 reports
"""
import json
from datetime import datetime
from IPython.display import display, Markdown

# Define tool descriptions and icons dictionary
TOOL_METADATA = {
    "describe_feedstock": {
        "description": "Generates ADM1 state variables from a natural language description of feedstock.",
        "purpose": "This tool translates a plain language description of a feedstock into the specific state variables required by the ADM1 model. It provides the initial composition values for the simulation.",
        "icon": "fa-leaf"
    },
    "describe_kinetics": {
        "description": "Generates kinetic parameters based on feedstock description and updates state variables.",
        "purpose": "This tool determines the appropriate kinetic parameters for the specific feedstock, which control the reaction rates in the model based on the feedstock's biodegradability characteristics.",
        "icon": "fa-tachometer-alt"
    },
    "validate_feedstock_charge_balance": {
        "description": "Validates the electroneutrality of the feedstock by comparing cation and anion equivalents.",
        "purpose": "This tool checks that the feedstock composition maintains a proper charge balance, which is essential for accurate pH prediction in the simulation.",
        "icon": "fa-balance-scale"
    },
    "set_flow_parameters": {
        "description": "Sets the influent flow rate and other simulation parameters.",
        "purpose": "This tool configures the hydraulic parameters of the simulation, including flow rates that determine the hydraulic retention time (HRT) of the system.",
        "icon": "fa-water"
    },
    "set_reactor_parameters": {
        "description": "Sets parameters for a specific reactor simulation scenario.",
        "purpose": "This tool configures the physical and operational parameters of the anaerobic digester, such as volume, temperature, and mixing conditions.",
        "icon": "fa-flask"
    },
    "run_simulation_tool": {
        "description": "Runs the ADM1 simulation with the current parameters.",
        "purpose": "This tool executes the actual numerical simulation of the anaerobic digestion process using the configured parameters, solving the ADM1 differential equations.",
        "icon": "fa-play-circle"
    },
    "get_stream_properties": {
        "description": "Gets detailed properties of a specified stream from the simulation results.",
        "purpose": "This tool extracts comprehensive data about the composition and properties of the influent, effluent, or biogas streams from the simulation results.",
        "icon": "fa-stream"
    },
    "get_inhibition_analysis": {
        "description": "Gets process health and inhibition analysis for a specific simulation scenario.",
        "purpose": "This tool analyzes potential inhibitory factors in the anaerobic digestion process, such as ammonia toxicity, pH inhibition, or VFA accumulation.",
        "icon": "fa-exclamation-triangle"
    },
    "get_biomass_yields": {
        "description": "Calculates biomass yields from a specific simulation scenario.",
        "purpose": "This tool computes the efficiency of the process in terms of biomass production relative to substrate consumption, providing insights into the overall process performance.",
        "icon": "fa-seedling"
    },
    "check_nutrient_balance": {
        "description": "Checks a specific simulation for nutrient limitation based on inhibition metrics.",
        "purpose": "This tool evaluates whether the process might be limited by essential nutrients like nitrogen or phosphorus, which could impact microbial growth.",
        "icon": "fa-vial"
    },
    "generate_report": {
        "description": "Generates a professional ADM1 simulation report using results from previously executed tools.",
        "purpose": "This tool compiles the results from all previous tool executions into a comprehensive, well-formatted report document for analysis and presentation.",
        "icon": "fa-file-alt"
    }
}

# Function to get an appropriate icon for a stream type
def get_stream_type_icon(stream_type):
    """
    Get an appropriate icon for a stream type.
    
    Args:
        stream_type: String identifying the stream type
        
    Returns:
        Font Awesome icon class
    """
    if stream_type.startswith('influent'):
        return "fa-arrow-right"
    elif stream_type.startswith('effluent'):
        return "fa-arrow-left"
    elif stream_type.startswith('biogas'):
        return "fa-wind"
    else:
        return "fa-stream"

# Function to format JSON data for display
def format_json_for_display(data):
    """
    Format JSON data for display with syntax highlighting.
    
    Args:
        data: JSON data (string or dict)
        
    Returns:
        Formatted JSON string
    """
    # Parse to dict if string
    if isinstance(data, str):
        try:
            parsed_data = json.loads(data)
        except:
            # Not valid JSON, return as is
            return data
    else:
        parsed_data = data
    
    # Format the JSON for display
    formatted_json = json.dumps(parsed_data, indent=2)
    
    # Apply basic syntax highlighting - real highlighting will be done via CSS
    formatted_json = formatted_json.replace('"', '&quot;')
    
    return formatted_json

def format_tool_response_markdown(tool_name, response_data, timestamp=None, stream_type=None):
    """
    Format a tool response for display in the report using Markdown with embedded HTML.
    
    This approach ensures the HTML is properly rendered in the final HTML report when
    converted with nbconvert or Quarto.
    
    Args:
        tool_name: Name of the tool
        response_data: JSON string or dict containing the tool response
        timestamp: Optional timestamp for when the tool was executed
        stream_type: Optional stream type for get_stream_properties tool
        
    Returns:
        Markdown object with formatted tool response
    """
    # Handle special case for get_stream_properties with stream type
    original_tool_name = tool_name
    if stream_type:
        tool_name = f"{tool_name} ({stream_type})"
    
    # Extract stream type from response data if not provided
    if not stream_type and original_tool_name == "get_stream_properties":
        try:
            if isinstance(response_data, str):
                response_dict = json.loads(response_data)
            else:
                response_dict = response_data
            
            stream_type = response_dict.get("stream_type", "")
        except:
            stream_type = ""
    
    # Convert timestamp to readable format if provided
    timestamp_str = ""
    if timestamp:
        if isinstance(timestamp, str):
            # Try to parse string timestamp
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp_str = f"Executed at: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            except:
                timestamp_str = f"Executed at: {timestamp}"
        else:
            timestamp_str = f"Executed at: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Format the response content
    formatted_content = format_json_for_display(response_data)
    
    # Get tool metadata
    base_tool_name = original_tool_name.split(" ")[0] if " " in original_tool_name else original_tool_name
    tool_meta = TOOL_METADATA.get(base_tool_name, {
        "description": "Tool to perform a specific function in the ADM1 simulation.",
        "purpose": "This tool provides specific functionality for the ADM1 simulation process.",
        "icon": "fa-wrench"
    })
    
    # Choose icon based on the tool or stream type
    if stream_type:
        icon = get_stream_type_icon(stream_type)
    else:
        icon = tool_meta.get("icon", "fa-wrench")
    
    # Create Markdown with embedded HTML for the tool response card
    markdown_output = f"""
<div class="tool-response-card">
    <div class="tool-response-header">
        <h4><i class="fas {icon}"></i> {tool_name}</h4>
        <div class="tool-response-timestamp">{timestamp_str}</div>
    </div>
    <div class="tool-response-description">
        <p><i class="fas fa-info-circle"></i> <em>{tool_meta.get("description")}</em></p>
        <p>{tool_meta.get("purpose")}</p>
    </div>
    <div class="tool-response-content">
        <pre><code class="json">{formatted_content}</code></pre>
    </div>
</div>
"""
    
    return Markdown(markdown_output)

def extract_tool_responses_by_chronology(tool_responses):
    """
    Extract all tool responses and sort by timestamp.
    
    Args:
        tool_responses: Dictionary of tool responses
        
    Returns:
        List of tuples (tool_name, response, timestamp) sorted by timestamp
    """
    all_responses = []
    
    for tool_name, responses in tool_responses.items():
        for response in responses:
            timestamp = response.get('timestamp', datetime.min)
            all_responses.append((tool_name, response, timestamp))
    
    # Sort all responses by timestamp
    return sorted(all_responses, key=lambda x: x[2])

def create_tool_response_section_markdown(tool_responses, simulation_index, include_technical_details):
    """
    Create formatted tool response sections for the report using Markdown with embedded HTML.
    
    Args:
        tool_responses: Dictionary of tool responses
        simulation_index: Simulation index to extract responses for
        include_technical_details: Whether to include all responses or just a summary
        
    Returns:
        Dictionary of section generators for different parts of the report
    """
    sections = {}
    
    # Configuration section generator
    def get_config_section():
        config_tools = ['describe_feedstock', 'describe_kinetics', 'validate_feedstock_charge_balance', 
                      'set_flow_parameters', 'set_reactor_parameters']
        
        for tool_name in config_tools:
            if tool_name in tool_responses and tool_responses[tool_name]:
                # For reactor parameters, find the one matching this simulation index
                if tool_name == 'set_reactor_parameters':
                    matching_responses = []
                    for response in tool_responses[tool_name]:
                        try:
                            data = json.loads(response['data']) if isinstance(response['data'], str) else response['data']
                            if 'simulation_index' in data and data['simulation_index'] == simulation_index:
                                matching_responses.append(response)
                        except:
                            pass
                    
                    if matching_responses:
                        # Sort by timestamp and display latest
                        sorted_responses = sorted(matching_responses, 
                                                key=lambda x: x.get('timestamp', datetime.min))
                        latest_response = sorted_responses[-1]
                        display(format_tool_response_markdown(
                            tool_name, 
                            latest_response['data'], 
                            latest_response.get('timestamp')
                        ))
                else:
                    # For other config tools, get the latest response
                    sorted_responses = sorted(tool_responses[tool_name], 
                                            key=lambda x: x.get('timestamp', datetime.min))
                    latest_response = sorted_responses[-1]
                    display(format_tool_response_markdown(
                        tool_name, 
                        latest_response['data'], 
                        latest_response.get('timestamp')
                    ))
    
    sections['configuration'] = get_config_section
    
    # Simulation execution section generator
    def get_execution_section():
        if 'run_simulation_tool' in tool_responses and tool_responses['run_simulation_tool']:
            # Find the latest simulation response
            sorted_responses = sorted(tool_responses['run_simulation_tool'], 
                                    key=lambda x: x.get('timestamp', datetime.min))
            latest_response = sorted_responses[-1]
            
            display(format_tool_response_markdown(
                'run_simulation_tool', 
                latest_response['data'], 
                latest_response.get('timestamp')
            ))
    
    sections['execution'] = get_execution_section
    
    # Results section generator - stream properties and analysis
    def get_results_section():
        # Stream properties
        stream_types = ['influent', f'effluent{simulation_index}', f'biogas{simulation_index}']
        
        if 'get_stream_properties' in tool_responses and tool_responses['get_stream_properties']:
            for stream_type in stream_types:
                # Find responses for this stream type
                matching_responses = []
                for response in tool_responses['get_stream_properties']:
                    try:
                        response_data = json.loads(response['data']) if isinstance(response['data'], str) else response['data']
                        if response_data.get('stream_type') == stream_type:
                            matching_responses.append(response)
                    except:
                        pass
                
                if matching_responses:
                    # Sort by timestamp and display latest
                    sorted_responses = sorted(matching_responses, 
                                            key=lambda x: x.get('timestamp', datetime.min))
                    latest_response = sorted_responses[-1]
                    
                    display(Markdown(f"## <i class='fas {get_stream_type_icon(stream_type)}'></i> {stream_type.capitalize()} Properties"))
                    display(format_tool_response_markdown(
                        'get_stream_properties', 
                        latest_response['data'], 
                        latest_response.get('timestamp'),
                        stream_type
                    ))
        
        # Process analysis tools
        analysis_tools = ['get_inhibition_analysis', 'get_biomass_yields', 'check_nutrient_balance']
        
        for tool_name in analysis_tools:
            if tool_name in tool_responses and tool_responses[tool_name]:
                # Find responses for this simulation index
                matching_responses = []
                for response in tool_responses[tool_name]:
                    try:
                        response_data = json.loads(response['data']) if isinstance(response['data'], str) else response['data']
                        if response_data.get('simulation_index') == simulation_index:
                            matching_responses.append(response)
                    except:
                        pass
                
                if matching_responses:
                    # Sort by timestamp and display latest
                    sorted_responses = sorted(matching_responses, 
                                            key=lambda x: x.get('timestamp', datetime.min))
                    latest_response = sorted_responses[-1]
                    
                    # Convert tool name to title case with spaces
                    title = tool_name.replace('_', ' ').title()
                    display(Markdown(f"## <i class='fas {TOOL_METADATA.get(tool_name, {}).get('icon', 'fa-microscope')}'></i> {title}"))
                    display(format_tool_response_markdown(
                        tool_name, 
                        latest_response['data'], 
                        latest_response.get('timestamp')
                    ))
    
    sections['results'] = get_results_section
    
    # Technical appendix with all tool responses in chronological order
    def get_appendix_section():
        display(Markdown("# <i class='fas fa-info-circle'></i> Appendix: Tool Execution Flow"))
        display(Markdown("The following section documents the complete tool execution flow in chronological order, providing a comprehensive record of the simulation process and enhancing the educational value of the report."))
        
        sorted_responses = extract_tool_responses_by_chronology(tool_responses)
        
        for tool_name, response, timestamp in sorted_responses:
            display(format_tool_response_markdown(tool_name, response['data'], timestamp))
    
    if include_technical_details:
        sections['appendix'] = get_appendix_section
    
    return sections