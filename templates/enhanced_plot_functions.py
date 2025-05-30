"""
Enhanced plotting functions for ADM1 simulation results
"""
import numpy as np
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from IPython.display import Markdown

def create_enhanced_cod_plot(t_eff, effluent):
    """Create an enhanced COD plot with professional styling"""
    # Access components through the components attribute
    cmps = effluent.components
    
    # Get soluble and particulate component indices
    sol_comps = [cmp for cmp in cmps if cmp.ID.startswith('S_')]
    part_comps = [cmp for cmp in cmps if cmp.ID.startswith('X_')]
    
    # Calculate total COD at each time point
    sol_cod = np.zeros(len(t_eff))
    part_cod = np.zeros(len(t_eff))
    
    for cmp in sol_comps:
        # Find index of component with this ID 
        idx = next((i for i, c in enumerate(cmps) if hasattr(c, 'ID') and c.ID == cmp.ID), None)
        if idx is not None and hasattr(cmp, 'COD'):
            # For each component, get its COD contribution over time
            sol_cod += effluent.scope.record[:, idx] * cmp.COD
            
    for cmp in part_comps:
        # Find index of component with this ID
        idx = next((i for i, c in enumerate(cmps) if hasattr(c, 'ID') and c.ID == cmp.ID), None)
        if idx is not None and hasattr(cmp, 'COD'):
            part_cod += effluent.scope.record[:, idx] * cmp.COD
            
    total_cod = sol_cod + part_cod
    
    # Create the enhanced COD plot
    cod_fig = go.Figure()
    
    # Add traces with enhanced styling
    cod_fig.add_trace(go.Scatter(
        x=t_eff,
        y=total_cod,
        mode='lines',
        name='Total COD',
        line=dict(color='#0f4c81', width=3),
        fill='tozeroy',
        fillcolor='rgba(15, 76, 129, 0.1)'
    ))
    
    cod_fig.add_trace(go.Scatter(
        x=t_eff,
        y=sol_cod,
        mode='lines',
        name='Soluble COD',
        line=dict(color='#88b0cd', width=2, dash='dot')
    ))
    
    cod_fig.add_trace(go.Scatter(
        x=t_eff,
        y=part_cod,
        mode='lines',
        name='Particulate COD',
        line=dict(color='#3c7a89', width=2, dash='dash')
    ))
    
    # Update layout with improved styling
    cod_fig.update_layout(
        title={
            'text': '<b>Effluent COD Over Time</b>',
            'font': {'size': 22, 'color': '#0f4c81'},
            'y': 0.95
        },
        xaxis_title={'text': 'Time (days)', 'font': {'size': 14}},
        yaxis_title={'text': 'COD (mg/L)', 'font': {'size': 14}},
        template='plotly_white',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='center',
            x=0.5,
            bgcolor='rgba(255, 255, 255, 0.8)',
            bordercolor='rgba(0, 0, 0, 0.2)',
            borderwidth=1
        ),
        margin=dict(t=80, b=50, l=50, r=30),
        plot_bgcolor='white',
        hoverlabel=dict(
            bgcolor='white',
            font_size=14,
            font_family='Segoe UI'
        ),
        hovermode='x unified'
    )
    
    # Add grid lines
    cod_fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(222, 226, 230, 0.6)',
        zeroline=False,
        showline=True,
        linewidth=2,
        linecolor='rgba(0, 0, 0, 0.2)'
    )
    
    cod_fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(222, 226, 230, 0.6)',
        zeroline=True,
        zerolinewidth=2,
        zerolinecolor='rgba(0, 0, 0, 0.2)',
        showline=True,
        linewidth=2,
        linecolor='rgba(0, 0, 0, 0.2)'
    )
    
    return cod_fig

def create_enhanced_methane_plot(t_gas, biogas):
    """Create enhanced methane production plot with professional styling"""
    # Get components
    cmps = biogas.components
    
    # Get methane and carbon dioxide indices
    try:
        # Find indices by looking for components with matching IDs
        ch4_idx = next((i for i, c in enumerate(cmps) if hasattr(c, 'ID') and c.ID == 'S_ch4'), None)
        ic_idx = next((i for i, c in enumerate(cmps) if hasattr(c, 'ID') and c.ID == 'S_IC'), None)
        
        # If indices weren't found, try direct lookup (in case cmps is a list of IDs rather than component objects)
        if ch4_idx is None and 'S_ch4' in cmps:
            ch4_idx = cmps.index('S_ch4')
        if ic_idx is None and 'S_IC' in cmps:
            ic_idx = cmps.index('S_IC')
            
        # Check that we found both indices
        if ch4_idx is None or ic_idx is None:
            raise ValueError("Could not find required component indices for S_ch4 and S_IC")
        
        # Convert from concentration to volumetric flow
        MW_CH4 = 16.04
        MW_CO2 = 44.01
        MW_C = 12.01
        
        DENSITY_CH4 = 0.716  # kg/m³ @ STP
        DENSITY_CO2 = 1.977  # kg/m³ @ STP
        
        COD_CH4 = 4.0  # kg COD/kg CH4
        
        # Get methane data - convert from COD to volumetric flow
        methane_cod = biogas.scope.record[:, ch4_idx]
        methane_mass = methane_cod / COD_CH4
        methane_flow = methane_mass / DENSITY_CH4
        
        # Get CO2 data - convert from C to CO2
        carbon_mass = biogas.scope.record[:, ic_idx]
        co2_mass = carbon_mass * (MW_CO2 / MW_C)
        co2_flow = co2_mass / DENSITY_CO2
        
        # Create enhanced plot
        ch4_fig = go.Figure()
        
        # Add traces with enhanced styling
        ch4_fig.add_trace(go.Scatter(
            x=t_gas,
            y=methane_flow,
            mode='lines',
            name='Methane Flow',
            line=dict(color='#e6a817', width=3),
            fill='tozeroy',
            fillcolor='rgba(230, 168, 23, 0.1)'
        ))
        
        ch4_fig.add_trace(go.Scatter(
            x=t_gas,
            y=co2_flow,
            mode='lines',
            name='CO₂ Flow',
            line=dict(color='#3c7a89', width=2)
        ))
        
        # Add percentage trace on secondary y-axis with enhanced styling
        total_flow = methane_flow + co2_flow
        methane_percent = np.where(total_flow > 0, methane_flow / total_flow * 100, 0)
        
        ch4_fig.add_trace(go.Scatter(
            x=t_gas,
            y=methane_percent,
            mode='lines',
            name='Methane Content (%)',
            line=dict(color='#c94c4c', width=2, dash='dot'),
            yaxis='y2'
        ))
        
        # Update layout with improved styling
        ch4_fig.update_layout(
            title={
                'text': '<b>Biogas Production Over Time</b>',
                'font': {'size': 22, 'color': '#0f4c81'},
                'y': 0.95
            },
            xaxis_title={'text': 'Time (days)', 'font': {'size': 14}},
            yaxis_title={'text': 'Flow Rate (Nm³/d)', 'font': {'size': 14}},
            yaxis2=dict(
                title={'text': 'Methane Content (%)', 'font': {'size': 14}},
                overlaying='y',
                side='right',
                range=[0, 100],
                showgrid=False,
                showline=True,
                linecolor='rgba(201, 76, 76, 0.3)',
                linewidth=2,
                tickfont=dict(color='#c94c4c')
            ),
            template='plotly_white',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='center',
                x=0.5,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1
            ),
            margin=dict(t=80, b=50, l=50, r=50),
            plot_bgcolor='white',
            hoverlabel=dict(
                bgcolor='white',
                font_size=14,
                font_family='Segoe UI'
            ),
            hovermode='x unified'
        )
        
        # Add grid lines
        ch4_fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(222, 226, 230, 0.6)',
            zeroline=False,
            showline=True,
            linewidth=2,
            linecolor='rgba(0, 0, 0, 0.2)'
        )
        
        ch4_fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(222, 226, 230, 0.6)',
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor='rgba(0, 0, 0, 0.2)',
            showline=True,
            linewidth=2,
            linecolor='rgba(0, 0, 0, 0.2)'
        )
        
        return ch4_fig
        
    except (ValueError, IndexError) as e:
        print(f"Error accessing methane data: {e}")
        return None

def create_enhanced_ph_plot(t_eff, effluent, system):
    """Create enhanced pH plot with professional styling"""
    try:
        # Try to extract pH time series data
        # Since pH is not a standard state variable, it might not be in scope.record
        # For simplicity, check if effluent.pH is available and assume constant
        if hasattr(effluent, 'pH') and effluent.pH is not None:
            pH_value = effluent.pH
            pH_series = np.full(len(t_eff), pH_value)  # Constant value as approximation
            print("Note: pH time series approximated as constant final value due to lack of dynamic tracking.")
        else:
            pH_series = np.full(len(t_eff), 7.0)  # Neutral pH as fallback
            print("Note: pH time series unavailable and set to neutral (7.0) as placeholder.")
        
        # Create enhanced pH plot
        pH_fig = go.Figure()
        
        # Add trace with enhanced styling
        pH_fig.add_trace(go.Scatter(
            x=t_eff,
            y=pH_series,
            mode='lines',
            name='Effluent pH',
            line=dict(color='#2e8b57', width=3),
            fill='tozeroy',
            fillcolor='rgba(46, 139, 87, 0.1)'
        ))
        
        # Add reference zones for pH
        # Acidic range (pH < 6.5)
        pH_fig.add_shape(
            type="rect",
            x0=t_eff[0],
            x1=t_eff[-1],
            y0=0,
            y1=6.5,
            fillcolor="rgba(201, 76, 76, 0.1)",
            line=dict(width=0),
            layer="below"
        )
        
        # Optimal range (6.5 <= pH <= 8.2)
        pH_fig.add_shape(
            type="rect",
            x0=t_eff[0],
            x1=t_eff[-1],
            y0=6.5,
            y1=8.2,
            fillcolor="rgba(46, 139, 87, 0.1)",
            line=dict(width=0),
            layer="below"
        )
        
        # Alkaline range (pH > 8.2)
        pH_fig.add_shape(
            type="rect",
            x0=t_eff[0],
            x1=t_eff[-1],
            y0=8.2,
            y1=14,
            fillcolor="rgba(201, 76, 76, 0.1)",
            line=dict(width=0),
            layer="below"
        )
        
        # Add annotations for pH zones
        pH_fig.add_annotation(
            x=t_eff[int(len(t_eff)*0.05)],
            y=5.5,
            text="Acidic Zone",
            showarrow=False,
            font=dict(size=10, color="rgba(201, 76, 76, 0.7)")
        )
        
        pH_fig.add_annotation(
            x=t_eff[int(len(t_eff)*0.05)],
            y=7.5,
            text="Optimal Zone",
            showarrow=False,
            font=dict(size=10, color="rgba(46, 139, 87, 0.7)")
        )
        
        pH_fig.add_annotation(
            x=t_eff[int(len(t_eff)*0.05)],
            y=9.5,
            text="Alkaline Zone",
            showarrow=False,
            font=dict(size=10, color="rgba(201, 76, 76, 0.7)")
        )
        
        # Update layout with improved styling
        pH_fig.update_layout(
            title={
                'text': '<b>Effluent pH Over Time</b>',
                'font': {'size': 22, 'color': '#0f4c81'},
                'y': 0.95
            },
            xaxis_title={'text': 'Time (days)', 'font': {'size': 14}},
            yaxis_title={'text': 'pH (unitless)', 'font': {'size': 14}},
            template='plotly_white',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='center',
                x=0.5,
                bgcolor='rgba(255, 255, 255, 0.8)',
                bordercolor='rgba(0, 0, 0, 0.2)',
                borderwidth=1
            ),
            margin=dict(t=80, b=50, l=50, r=30),
            plot_bgcolor='white',
            hoverlabel=dict(
                bgcolor='white',
                font_size=14,
                font_family='Segoe UI'
            ),
            hovermode='x unified',
            yaxis=dict(
                range=[4, 10]  # Set y-axis range to show pH scale more clearly
            )
        )
        
        # Add grid lines
        pH_fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(222, 226, 230, 0.6)',
            zeroline=False,
            showline=True,
            linewidth=2,
            linecolor='rgba(0, 0, 0, 0.2)'
        )
        
        pH_fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(222, 226, 230, 0.6)',
            zeroline=False,
            showline=True,
            linewidth=2,
            linecolor='rgba(0, 0, 0, 0.2)'
        )
        
        return pH_fig
        
    except Exception as e:
        print(f"Error creating enhanced pH time series plot: {e}")
        return None

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
    
    # Format the JSON for display with indentation
    formatted_json = json.dumps(parsed_data, indent=2)
    
    return formatted_json

# New function that uses Markdown to render tool responses properly
def format_tool_response(tool_name, response_data, timestamp=None, stream_type=None):
    """
    Format a tool response for display in the report using Markdown with embedded HTML.
    This approach ensures the HTML is properly rendered in the final HTML report.
    
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