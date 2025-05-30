"""
KPI Card generator for ADM1 simulation results
"""
from IPython.display import HTML

def create_kpi_cards(biogas_props, yields, effluent):
    """
    Create KPI cards for key performance metrics
    
    Args:
        biogas_props: Dictionary of biogas properties
        yields: Dictionary of yield data
        effluent: Effluent stream object
    
    Returns:
        HTML object containing KPI cards
    """
    # Extract key metrics
    cod_removal = yields.get("COD_removal_efficiency", 0) * 100
    methane_pct = biogas_props.get("methane_percent", 0)
    biogas_flow = biogas_props.get("flow_total", 0)
    effluent_ph = getattr(effluent, 'pH', 7.0)
    methane_yield = yields.get("CH4_yield", 0)
    
    # Create HTML for KPI cards
    html_output = """<div class='kpi-container'>
    <div class='kpi-card'>
        <i class='fas fa-filter kpi-icon'></i>
        <div class='kpi-title'>COD Removal</div>
        <div class='kpi-value'>{:.1f}</div>
        <div class='kpi-unit'>%</div>
    </div>
    
    <div class='kpi-card'>
        <i class='fas fa-burn kpi-icon'></i>
        <div class='kpi-title'>Methane Content</div>
        <div class='kpi-value'>{:.1f}</div>
        <div class='kpi-unit'>%</div>
    </div>
    
    <div class='kpi-card'>
        <i class='fas fa-chart-line kpi-icon'></i>
        <div class='kpi-title'>Biogas Production</div>
        <div class='kpi-value'>{:.1f}</div>
        <div class='kpi-unit'>Nm³/d</div>
    </div>
    
    <div class='kpi-card'>
        <i class='fas fa-flask kpi-icon'></i>
        <div class='kpi-title'>Effluent pH</div>
        <div class='kpi-value'>{:.2f}</div>
        <div class='kpi-unit'>-</div>
    </div>
    
    <div class='kpi-card'>
        <i class='fas fa-tachometer-alt kpi-icon'></i>
        <div class='kpi-title'>Methane Yield</div>
        <div class='kpi-value'>{:.3f}</div>
        <div class='kpi-unit'>Nm³-CH₄/kg-COD</div>
    </div>
    </div>""".format(cod_removal, methane_pct, biogas_flow, effluent_ph, methane_yield)
    
    return HTML(html_output)
