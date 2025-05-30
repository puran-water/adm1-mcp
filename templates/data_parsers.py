"""
Comprehensive data parsers and table generators for ADM1 tool responses.
Transforms raw JSON tool responses into professional tables and charts.
"""
import json
import pandas as pd
import numpy as np
from datetime import datetime
from IPython.display import HTML, display, Markdown
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def parse_tool_response_data(tool_responses, tool_name, simulation_index=None):
    """
    Parse tool response data into structured format for table creation.
    
    Args:
        tool_responses: Dictionary of tool responses
        tool_name: Name of the tool to extract data for
        simulation_index: Optional simulation index for filtering
        
    Returns:
        Parsed data dictionary or None if not found
    """
    if tool_name not in tool_responses:
        return None
    
    # Get the latest response for the tool
    latest_response = tool_responses[tool_name][-1]
    
    # Parse JSON data
    try:
        if isinstance(latest_response['data'], str):
            data = json.loads(latest_response['data'])
        else:
            data = latest_response['data']
            
        # Filter by simulation index if provided
        if simulation_index is not None and 'simulation_index' in data:
            if data['simulation_index'] != simulation_index:
                # Look for matching simulation index
                for response in tool_responses[tool_name]:
                    try:
                        response_data = json.loads(response['data']) if isinstance(response['data'], str) else response['data']
                        if response_data.get('simulation_index') == simulation_index:
                            return response_data
                    except:
                        continue
                return None
                
        return data
    except Exception as e:
        # Suppress error messages to avoid MCP protocol interference
        # print(f"Error parsing tool response data for {tool_name}: {e}")
        return None

def format_value(value, precision=4):
    """
    Format a numeric value for professional display - avoid scientific notation for most values.
    
    Args:
        value: The value to format
        precision: Number of significant figures
        
    Returns:
        Formatted string
    """
    if value is None:
        return "N/A"
    
    if isinstance(value, (int, float)):
        if value == 0:
            return "0.0000"
        elif abs(value) >= 0.001 and abs(value) < 1000000:  # Extend range to avoid scientific notation
            if abs(value) >= 1000:
                return f"{value:,.0f}"  # Use comma separators for large numbers
            elif abs(value) >= 1:
                return f"{value:.{min(precision, 3)}f}"  # Limit decimal places for readability
            else:
                return f"{value:.{precision}g}"
        else:
            return f"{value:.{precision-1}e}"  # Only use scientific for very large/small values
    else:
        return str(value)

def format_value_for_context(value, context="general", precision=4):
    """
    Format values based on context (biogas, flow, concentration, etc.)
    
    Args:
        value: The value to format
        context: Context type for appropriate formatting
        precision: Number of significant figures
        
    Returns:
        Formatted string
    """
    if value is None:
        return "N/A"
    
    if isinstance(value, (int, float)):
        if context == "biogas_flow":
            return f"{value:,.0f}" if value >= 1000 else f"{value:.1f}"
        elif context == "percentage":
            return f"{value:.1f}"
        elif context == "concentration":
            if value >= 1000:
                return f"{value:,.0f}"
            else:
                return f"{value:.{precision}g}"
        else:
            return format_value(value, precision)
    
    return str(value)

def extract_actual_biogas_data(tool_responses, simulation_index):
    """Extract actual biogas data from tool responses"""
    biogas_data = {'methane_content': 0, 'biogas_production': 0, 'co2_content': 0}
    
    # Look for biogas stream properties
    if 'get_stream_properties' in tool_responses:
        for response in tool_responses['get_stream_properties']:
            try:
                data = json.loads(response['data']) if isinstance(response['data'], str) else response['data']
                if data.get('stream_type') == f'biogas{simulation_index}':
                    props = data.get('properties', {})
                    basic_props = props.get('basic', {})
                    biogas_data['methane_content'] = basic_props.get('methane_percent', 0)
                    biogas_data['biogas_production'] = basic_props.get('flow_total', 0)
                    biogas_data['co2_content'] = basic_props.get('co2_percent', 0)
                    break
            except:
                pass
    
    return biogas_data

def get_unit_for_parameter(param_name):
    """
    Get the appropriate unit for a parameter based on its name.
    
    Args:
        param_name: Parameter name
        
    Returns:
        Unit string
    """
    param_lower = param_name.lower()
    
    # Flow parameters
    if 'flow' in param_lower or param_lower in ['q']:
        return 'm³/d'
    
    # pH and alkalinity
    if param_lower == 'ph':
        return '-'
    if 'alkalinity' in param_lower:
        return 'mg CaCO₃/L'
    
    # Concentrations
    if any(x in param_lower for x in ['cod', 'bod', 'thod', 'concentration']):
        return 'mg/L'
    
    # VFA components
    if any(x in param_lower for x in ['acetate', 'propionate', 'butyrate', 'valerate']):
        return 'mg COD/L'
    
    # Nutrients
    if any(x in param_lower for x in ['nitrogen', 'phosphorus', 'nh3', 'nh4']):
        return 'mg N/L' if 'n' in param_lower else 'mg P/L'
    
    # Solids
    if any(x in param_lower for x in ['tss', 'vss', 'solids']):
        return 'mg/L'
    
    # Percentages
    if 'percent' in param_lower or '%' in param_lower:
        return '%'
    
    # Inhibition factors
    if 'inhibition' in param_lower:
        return '%'
    
    # Default
    return ''

def create_styled_dataframe(data, title="Data Table"):
    """
    Create a styled pandas DataFrame for professional display.
    
    Args:
        data: List of dictionaries or DataFrame
        title: Table title
        
    Returns:
        Styled DataFrame
    """
    if isinstance(data, list) and len(data) > 0:
        df = pd.DataFrame(data)
    elif isinstance(data, pd.DataFrame):
        df = data
    else:
        return pd.DataFrame({"Parameter": ["No data available"], "Value": ["N/A"]}).style.set_caption(title)
    
    # Style the DataFrame
    styled_df = df.style.set_caption(title) \
                      .hide(axis="index") \
                      .set_table_styles([
                          {'selector': 'caption',
                           'props': [('caption-side', 'top'),
                                    ('font-size', '1.2em'),
                                    ('font-weight', 'bold'),
                                    ('color', '#0f4c81'),
                                    ('text-align', 'left'),
                                    ('margin-bottom', '10px')]},
                          {'selector': 'th',
                           'props': [('background-color', '#0f4c81'),
                                    ('color', 'white'),
                                    ('font-weight', 'bold'),
                                    ('text-align', 'left'),
                                    ('padding', '12px 15px')]},
                          {'selector': 'td',
                           'props': [('padding', '10px 15px'),
                                    ('border-bottom', '1px solid #dee2e6')]},
                          {'selector': 'tr:nth-child(even)',
                           'props': [('background-color', '#f8f9fa')]},
                          {'selector': 'table',
                           'props': [('border-collapse', 'separate'),
                                    ('border-spacing', '0'),
                                    ('border-radius', '5px'),
                                    ('overflow', 'hidden'),
                                    ('box-shadow', '0 4px 8px rgba(0, 0, 0, 0.1)'),
                                    ('margin', '20px 0'),
                                    ('width', '100%')]}
                      ])
    
    return styled_df

def create_feedstock_composition_table(feedstock_data):
    """
    Convert feedstock tool response into comprehensive composition table.
    
    Args:
        feedstock_data: Parsed feedstock tool response data
        
    Returns:
        Styled DataFrame
    """
    if not feedstock_data or not feedstock_data.get('success'):
        return create_styled_dataframe([], "Feedstock Composition - No Data Available")
    
    table_data = []
    
    # Extract state variables
    state_vars = feedstock_data.get('state_variables', {})
    
    # Organize by component categories
    categories = {
        'Soluble Components': [k for k in state_vars.keys() if k.startswith('S_')],
        'Particulate Components': [k for k in state_vars.keys() if k.startswith('X_')],
        'Cations': [k for k in state_vars.keys() if k.startswith('S_cat')],
        'Anions': [k for k in state_vars.keys() if k.startswith('S_an')],
        'Other': [k for k in state_vars.keys() if not any(k.startswith(prefix) for prefix in ['S_', 'X_'])]
    }
    
    for category, components in categories.items():
        if not components:
            continue
            
        # Add category header
        table_data.append({
            'Component': f"--- {category} ---",
            'Value': "",
            'Unit': "",
            'Description': ""
        })
        
        for component in sorted(components):
            value = state_vars[component]
            
            # Get description based on component name
            description = get_component_description(component)
            unit = get_unit_for_parameter(component)
            
            table_data.append({
                'Component': component,
                'Value': format_value(value),
                'Unit': unit,
                'Description': description
            })
    
    return create_styled_dataframe(table_data, "Feedstock Composition")

def get_component_description(component_name):
    """
    Get a description for an ADM1 component.
    
    Args:
        component_name: ADM1 component name
        
    Returns:
        Description string
    """
    descriptions = {
        'S_su': 'Monosaccharides',
        'S_aa': 'Amino acids',
        'S_fa': 'Long chain fatty acids (LCFA)',
        'S_va': 'Total valerate',
        'S_bu': 'Total butyrate',
        'S_pro': 'Total propionate',
        'S_ac': 'Total acetate',
        'S_h2': 'Hydrogen gas',
        'S_ch4': 'Methane',
        'S_IC': 'Inorganic carbon',
        'S_IN': 'Inorganic nitrogen',
        'S_I': 'Soluble inerts',
        'X_c': 'Composite',
        'X_ch': 'Carbohydrates',
        'X_pr': 'Proteins',
        'X_li': 'Lipids',
        'X_su': 'Sugar degraders',
        'X_aa': 'Amino acid degraders',
        'X_fa': 'LCFA degraders',
        'X_c4': 'Valerate and butyrate degraders',
        'X_pro': 'Propionate degraders',
        'X_ac': 'Acetate degraders',
        'X_h2': 'Hydrogen degraders',
        'X_I': 'Particulate inerts',
        'S_cation': 'Cation concentration',
        'S_anion': 'Anion concentration'
    }
    
    return descriptions.get(component_name, 'ADM1 state variable')

def create_stream_properties_table(stream_properties_data):
    """
    Convert stream properties JSON into comprehensive professional table.
    
    Args:
        stream_properties_data: Parsed stream properties tool response
        
    Returns:
        Styled DataFrame
    """
    if not stream_properties_data or not stream_properties_data.get('success'):
        return create_styled_dataframe([], "Stream Properties - No Data Available")
    
    properties = stream_properties_data.get('properties', {})
    stream_type = stream_properties_data.get('stream_type', 'Unknown Stream')
    
    # Create comprehensive table with ALL parameters
    all_data = []
    
    # Define section order and styling
    section_order = ['basic', 'oxygen_demand', 'carbon', 'nitrogen', 'solids', 'vfa', 'components']
    section_names = {
        'basic': 'Basic Properties',
        'oxygen_demand': 'Oxygen Demand',
        'carbon': 'Carbon Species',
        'nitrogen': 'Nitrogen Species',
        'solids': 'Solids Content',
        'vfa': 'Volatile Fatty Acids',
        'components': 'Model Components'
    }
    
    for section in section_order:
        if section not in properties:
            continue
            
        section_data = properties[section]
        if not section_data:
            continue
        
        # Add section header
        all_data.append({
            'Category': f"--- {section_names[section]} ---",
            'Parameter': "",
            'Value': "",
            'Unit': ""
        })
        
        # Add all parameters in this section
        for param, value in section_data.items():
            # Format parameter name for display
            display_name = param.replace('_', ' ').title()
            if param.upper() in ['COD', 'BOD', 'THOD', 'TSS', 'VSS', 'pH']:
                display_name = param.upper()
            elif param in ['alkalinity', 'nh3_free', 'nh4_plus']:
                display_name = param.replace('_', ' ').replace('nh3', 'NH₃').replace('nh4', 'NH₄').title()
            
            all_data.append({
                'Category': section_names[section],
                'Parameter': display_name,
                'Value': format_value(value),
                'Unit': get_unit_for_parameter(param)
            })
    
    # Add any additional properties not in standard sections
    for key, value in properties.items():
        if key not in section_order and isinstance(value, (int, float, str)):
            all_data.append({
                'Category': 'Additional Properties',
                'Parameter': key.replace('_', ' ').title(),
                'Value': format_value(value),
                'Unit': get_unit_for_parameter(key)
            })
    
    title = f"{stream_type.replace('_', ' ').title()} Properties"
    return create_styled_dataframe(all_data, title)

def create_inhibition_analysis_table(inhibition_data):
    """
    Create comprehensive inhibition analysis table.
    
    Args:
        inhibition_data: Parsed inhibition analysis tool response
        
    Returns:
        Styled DataFrame
    """
    if not inhibition_data or not inhibition_data.get('success'):
        return create_styled_dataframe([], "Inhibition Analysis - No Data Available")
    
    analysis = inhibition_data.get('analysis', {})
    
    # Process inhibition details - include ALL processes
    process_data = []
    
    if 'process_inhibition' in analysis:
        for process_info in analysis['process_inhibition']:
            process_data.append({
                'Process': process_info.get('process', '').replace('_', ' ').title(),
                'pH Inhibition (%)': format_value(process_info.get('pH_inhibition', 0) * 100, 1),
                'H₂ Inhibition (%)': format_value(process_info.get('h2_inhibition', 0) * 100, 1),
                'N Limitation (%)': format_value(process_info.get('n_limitation', 0) * 100, 1),
                'NH₃ Inhibition (%)': format_value(process_info.get('nh3_inhibition', 0) * 100, 1),
                'Substrate Limitation (%)': format_value(process_info.get('substrate_limitation', 0) * 100, 1),
                'Overall Inhibition (%)': format_value(process_info.get('overall_inhibition', 0) * 100, 1),
                'Process Rate': format_value(process_info.get('process_rate', 0), 6)
            })
    
    # Add summary information
    if 'summary' in analysis:
        summary = analysis['summary']
        summary_data = []
        
        for key, value in summary.items():
            if isinstance(value, (int, float)):
                if 'inhibition' in key.lower() or 'limitation' in key.lower():
                    formatted_value = format_value(value * 100, 1) + '%'
                else:
                    formatted_value = format_value(value)
            else:
                formatted_value = str(value)
                
            summary_data.append({
                'Metric': key.replace('_', ' ').title(),
                'Value': formatted_value
            })
    
    if process_data:
        process_table = create_styled_dataframe(process_data, "Process Inhibition Analysis")
        return process_table
    else:
        return create_styled_dataframe([], "Inhibition Analysis - No Process Data Available")

def create_biomass_yields_table(yields_data):
    """
    Create comprehensive biomass yields table.
    
    Args:
        yields_data: Parsed biomass yields tool response
        
    Returns:
        Styled DataFrame
    """
    if not yields_data or not yields_data.get('success'):
        return create_styled_dataframe([], "Biomass Yields - No Data Available")
    
    yields = yields_data.get('yields', {})
    
    # Create comprehensive yields table
    yields_table_data = []
    
    # Group yields by category
    categories = {
        'COD Performance': ['COD_removal_efficiency', 'COD_in', 'COD_out', 'COD_removed'],
        'Methane Production': ['CH4_yield', 'CH4_production_rate', 'specific_CH4_production'],
        'Biomass Yields': ['Y_su', 'Y_aa', 'Y_fa', 'Y_c4', 'Y_pro', 'Y_ac', 'Y_h2'],
        'Solids Performance': ['VSS_removal', 'TSS_removal', 'solids_retention_time']
    }
    
    for category, parameters in categories.items():
        category_has_data = False
        category_data = []
        
        for param in parameters:
            if param in yields:
                value = yields[param]
                
                # Format based on parameter type
                if 'efficiency' in param or 'removal' in param:
                    formatted_value = format_value(value * 100, 2) + '%' if isinstance(value, (int, float)) else str(value)
                elif 'yield' in param or 'production' in param:
                    formatted_value = format_value(value, 4)
                else:
                    formatted_value = format_value(value)
                
                category_data.append({
                    'Category': category,
                    'Parameter': param.replace('_', ' ').title(),
                    'Value': formatted_value,
                    'Unit': get_unit_for_parameter(param)
                })
                category_has_data = True
        
        if category_has_data:
            yields_table_data.extend(category_data)
    
    # Add any additional yields not in categories
    for param, value in yields.items():
        if not any(param in cat_params for cat_params in categories.values()):
            yields_table_data.append({
                'Category': 'Additional Metrics',
                'Parameter': param.replace('_', ' ').title(),
                'Value': format_value(value),
                'Unit': get_unit_for_parameter(param)
            })
    
    return create_styled_dataframe(yields_table_data, "Biomass Yields and Process Performance")

def create_flow_parameters_table(flow_data):
    """
    Create flow parameters table.
    
    Args:
        flow_data: Parsed flow parameters data
        
    Returns:
        Styled DataFrame
    """
    if not flow_data:
        return create_styled_dataframe([], "Flow Parameters - No Data Available")
    
    table_data = []
    
    # Extract flow parameters
    if 'parameters' in flow_data:
        params = flow_data['parameters']
    else:
        params = flow_data
    
    for key, value in params.items():
        table_data.append({
            'Parameter': key.replace('_', ' ').title(),
            'Value': format_value(value),
            'Unit': get_unit_for_parameter(key)
        })
    
    return create_styled_dataframe(table_data, "Flow Parameters")

def create_reactor_parameters_table(reactor_data):
    """
    Create reactor parameters table.
    
    Args:
        reactor_data: Parsed reactor parameters data
        
    Returns:
        Styled DataFrame
    """
    if not reactor_data:
        return create_styled_dataframe([], "Reactor Parameters - No Data Available")
    
    table_data = []
    
    # Extract reactor parameters
    if 'parameters' in reactor_data:
        params = reactor_data['parameters']
    else:
        params = reactor_data
    
    for key, value in params.items():
        if key in ['simulation_index', 'success']:
            continue
            
        # Format parameter name
        display_name = key.replace('_', ' ').title()
        if key == 'HRT':
            display_name = 'Hydraulic Retention Time (HRT)'
        elif key == 'Temp':
            display_name = 'Temperature'
        
        # Format value with appropriate units
        if key == 'Temp':
            formatted_value = f"{format_value(value)} K ({format_value(value - 273.15)} °C)"
            unit = ""
        elif key == 'HRT':
            formatted_value = format_value(value)
            unit = "days"
        else:
            formatted_value = format_value(value)
            unit = get_unit_for_parameter(key)
        
        table_data.append({
            'Parameter': display_name,
            'Value': formatted_value,
            'Unit': unit
        })
    
    return create_styled_dataframe(table_data, "Reactor Parameters")

def create_process_performance_charts(tool_responses, simulation_index):
    """
    Generate professional charts for process performance.
    
    Args:
        tool_responses: Dictionary of tool responses
        simulation_index: Simulation index to extract data for
        
    Returns:
        Plotly figure with multiple subplots
    """
    # Extract data from tool responses
    stream_data = parse_tool_response_data(tool_responses, 'get_stream_properties', simulation_index)
    inhibition_data = parse_tool_response_data(tool_responses, 'get_inhibition_analysis', simulation_index)
    yields_data = parse_tool_response_data(tool_responses, 'get_biomass_yields', simulation_index)
    
    # Create multi-panel figure
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('COD Removal Efficiency', 'Biogas Composition', 
                       'Process Inhibition Factors', 'Biomass Yields'),
        specs=[[{"type": "bar"}, {"type": "pie"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Color scheme
    colors = {
        'primary': '#0f4c81',
        'secondary': '#88b0cd',
        'accent': '#3c7a89',
        'success': '#2e8b57',
        'warning': '#e6a817',
        'danger': '#c94c4c'
    }
    
    # 1. COD Removal Efficiency
    if yields_data and 'yields' in yields_data:
        yields = yields_data['yields']
        cod_removal = yields.get('COD_removal_efficiency', 0) * 100
        
        fig.add_trace(
            go.Bar(
                x=['COD Removal'],
                y=[cod_removal],
                name='Efficiency %',
                marker_color=colors['success'] if cod_removal > 80 else colors['warning'] if cod_removal > 60 else colors['danger'],
                text=[f"{cod_removal:.1f}%"],
                textposition='auto',
                showlegend=False
            ),
            row=1, col=1
        )
    
    # 2. Biogas Composition - extract actual data
    biogas_data = extract_actual_biogas_data(tool_responses, simulation_index)
    biogas_ch4 = biogas_data['methane_content']
    biogas_co2 = biogas_data['co2_content']
    biogas_other = max(0, 100 - biogas_ch4 - biogas_co2)
    
    fig.add_trace(
        go.Pie(
            labels=['Methane', 'CO₂', 'Other'],
            values=[biogas_ch4, biogas_co2, biogas_other],
            marker_colors=[colors['success'], colors['accent'], colors['secondary']],
            showlegend=False
        ),
        row=1, col=2
    )
    
    # 3. Process Inhibition Factors
    if inhibition_data and 'analysis' in inhibition_data:
        analysis = inhibition_data['analysis']
        if 'process_inhibition' in analysis:
            processes = []
            inhibitions = []
            
            for process_info in analysis['process_inhibition'][:5]:  # Top 5 processes
                processes.append(process_info.get('process', '').replace('_', ' ').title())
                inhibitions.append(process_info.get('overall_inhibition', 0) * 100)
            
            fig.add_trace(
                go.Bar(
                    x=processes,
                    y=inhibitions,
                    name='Inhibition %',
                    marker_color=[colors['danger'] if x > 50 else colors['warning'] if x > 25 else colors['success'] for x in inhibitions],
                    showlegend=False
                ),
                row=2, col=1
            )
    
    # 4. Biomass Yields
    if yields_data and 'yields' in yields_data:
        yields = yields_data['yields']
        yield_types = []
        yield_values = []
        
        for key in ['Y_su', 'Y_aa', 'Y_fa', 'Y_ac']:
            if key in yields:
                yield_types.append(key.replace('Y_', '').upper())
                yield_values.append(yields[key])
        
        if yield_types:
            fig.add_trace(
                go.Bar(
                    x=yield_types,
                    y=yield_values,
                    name='Yield',
                    marker_color=colors['primary'],
                    showlegend=False
                ),
                row=2, col=2
            )
    
    # Update layout
    fig.update_layout(
        height=800,
        title_text="Process Performance Dashboard",
        title_font_size=20,
        title_font_color=colors['primary'],
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # Update axes
    fig.update_xaxes(showgrid=True, gridcolor='rgba(222, 226, 230, 0.6)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(222, 226, 230, 0.6)')
    
    return fig

def create_kpi_cards(tool_responses, simulation_index):
    """
    Create KPI cards for key performance indicators.
    
    Args:
        tool_responses: Dictionary of tool responses
        simulation_index: Simulation index to extract data for
        
    Returns:
        HTML object with KPI cards
    """
    # Extract data
    yields_data = parse_tool_response_data(tool_responses, 'get_biomass_yields', simulation_index)
    
    # Extract stream properties for different streams
    stream_responses = {}
    if 'get_stream_properties' in tool_responses:
        for response in tool_responses['get_stream_properties']:
            try:
                data = json.loads(response['data']) if isinstance(response['data'], str) else response['data']
                stream_type = data.get('stream_type', '')
                if stream_type:
                    stream_responses[stream_type] = data
            except:
                pass
    
    # Calculate KPIs
    cod_removal = 0
    methane_content = 0
    biogas_production = 0
    effluent_ph = 7.0
    
    if yields_data and 'yields' in yields_data:
        cod_removal = yields_data['yields'].get('COD_removal_efficiency', 0) * 100
    
    # Extract biogas properties using the new extraction function
    biogas_data = extract_actual_biogas_data(tool_responses, simulation_index)
    methane_content = biogas_data['methane_content']
    biogas_production = biogas_data['biogas_production']
    
    # Extract effluent pH
    effluent_stream = stream_responses.get(f'effluent{simulation_index}', {})
    if effluent_stream and 'properties' in effluent_stream:
        props = effluent_stream['properties']
        effluent_ph = props.get('basic', {}).get('pH', 7.0)
    
    # Create KPI cards HTML with professional formatting
    kpi_html = f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-icon"><i class="fas fa-recycle"></i></div>
            <div class="kpi-title">COD Removal Efficiency</div>
            <div class="kpi-value">{format_value_for_context(cod_removal, 'percentage')}</div>
            <div class="kpi-unit">%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon"><i class="fas fa-fire"></i></div>
            <div class="kpi-title">Methane Content</div>
            <div class="kpi-value">{format_value_for_context(methane_content, 'percentage')}</div>
            <div class="kpi-unit">%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon"><i class="fas fa-wind"></i></div>
            <div class="kpi-title">Biogas Production</div>
            <div class="kpi-value">{format_value_for_context(biogas_production, 'biogas_flow')}</div>
            <div class="kpi-unit">Nm³/d</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon"><i class="fas fa-vial"></i></div>
            <div class="kpi-title">Effluent pH</div>
            <div class="kpi-value">{effluent_ph:.2f}</div>
            <div class="kpi-unit">-</div>
        </div>
    </div>
    """
    
    return HTML(kpi_html)