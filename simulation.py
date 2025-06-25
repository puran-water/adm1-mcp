"""
Core simulation logic for ADM1 MCP server
"""
import os
import sys
import numpy as np
from qsdsan import sanunits as su, processes as pc, WasteStream, System
from chemicals.elements import molecular_weight as get_mw
from utils import C_mw, N_mw, CALCULATE_PH_AVAILABLE

# Add the parent directory to sys.path
parent_dir = os.path.dirname(os.path.abspath(__file__))
adm1_dir = os.path.join(os.path.dirname(parent_dir), "adm1")
sys.path.insert(0, adm1_dir)

# Import the pH and alkalinity calculation module
try:
    from calculate_ph_and_alkalinity_fixed import update_ph_and_alkalinity
except ImportError:
    print("Warning: pH calculation module not found. pH and alkalinity will use default values.")
    # Define a dummy update function if the module is not available
        def update_ph_and_alkalinity(stream):
            if hasattr(stream, '_pH'):
                stream._pH = 7.0
            if hasattr(stream, '_SAlk'):
                stream._SAlk = 2.5
            return stream

def create_influent_stream(Q, Temp, concentrations):
    """
    Create an Influent stream without running the simulation, for display.
    
    Parameters
    ----------
    Q : float
        Flow rate in m3/d
    Temp : float
        Temperature in K
    concentrations : dict
        Dictionary of component concentrations
        
    Returns
    -------
    WasteStream
        Influent stream with calculated pH and alkalinity
    """
    try:
        inf = WasteStream('Influent', T=Temp)
        
        default_conc = {
            'S_su': 0.01,
            'S_aa': 1e-3,
            'S_fa': 1e-3,
            'S_va': 1e-3,
            'S_bu': 1e-3,
            'S_pro': 1e-3,
            'S_ac': 1e-3,
            'S_h2': 1e-8,
            'S_ch4': 1e-5,
            'S_IC': 0.04 * C_mw,
            'S_IN': 0.01 * N_mw,
            'S_I': 0.02,
            'X_c': 2.0,
            'X_ch': 5.0,
            'X_pr': 20.0,
            'X_li': 5.0,
            'X_su': 1e-2,
            'X_aa': 1e-2,
            'X_fa': 1e-2,
            'X_c4': 1e-2,
            'X_pro': 1e-2,
            'X_ac': 1e-2,
            'X_h2': 1e-2,
            'X_I': 25,
            'S_cat': 0.04,
            'S_an': 0.02,
        }
        
        # Explicitly set ADM1 nitrogen component values
        if 'S_NH4' not in default_conc and 'S_NH4' in inf.components.IDs:
            default_conc['S_NH4'] = 25.0  # Default ammonia concentration
        if 'S_NO2' not in default_conc and 'S_NO2' in inf.components.IDs:
            default_conc['S_NO2'] = 0.0   # Default nitrite concentration
        if 'S_NO3' not in default_conc and 'S_NO3' in inf.components.IDs:
            default_conc['S_NO3'] = 0.0   # Default nitrate concentration
        
        # Update default concentrations with provided values
        for k, value in concentrations.items():
            if k in default_conc:
                default_conc[k] = value
        
        inf_kwargs = {
            'concentrations': default_conc,
            'units': ('m3/d', 'kg/m3')
        }
        inf.set_flow_by_concentration(Q, **inf_kwargs)
        
        # Calculate pH and alkalinity based on acid-base equilibria if module is available
        update_ph_and_alkalinity(inf)
        
        return inf
    except Exception as e:
        raise RuntimeError(f"Error creating influent stream: {e}")

def run_simulation(Q, Temp, HRT, concentrations, kinetic_params,
                  simulation_time, t_step, method, use_kinetics=True):
    """
    Run ADM1 with either user-provided kinetic parameters (if use_kinetics=True) 
    or default QSDsan parameters (if use_kinetics=False).
    
    Parameters
    ----------
    Q : float
        Flow rate in m3/d
    Temp : float
        Temperature in K
    HRT : float
        Hydraulic retention time in days
    concentrations : dict
        Dictionary of component concentrations
    kinetic_params : dict
        Dictionary of kinetic parameters
    simulation_time : float
        Simulation time in days
    t_step : float
        Time step in days
    method : str
        Integration method (e.g., "BDF", "RK45")
    use_kinetics : bool, optional
        Whether to use user-provided kinetic parameters, by default True
        
    Returns
    -------
    tuple
        (System, Influent, Effluent, Biogas)
    """
    try:
        # Set up the model with appropriate kinetics
        if use_kinetics and kinetic_params:
            adm1 = pc.ADM1(**kinetic_params)
        else:
            # Use default kinetics
            adm1 = pc.ADM1()  # no overrides

        # Create the influent stream using the same method as create_influent_stream
        # to ensure consistency
        inf = create_influent_stream(Q, Temp, concentrations)
        eff = WasteStream('Effluent', T=Temp)
        gas = WasteStream('Biogas')

        # AnaerobicCSTR
        AD = su.AnaerobicCSTR(
            'AD', ins=inf, outs=(gas, eff),
            model=adm1, V_liq=Q*HRT, V_gas=Q*HRT*0.1, T=Temp
        )
        
        # Default init cond
        default_init_conds = {
            'S_su': 0.0124*1e3,
            'S_aa': 0.0055*1e3,
            'S_fa': 0.1074*1e3,
            'S_va': 0.0123*1e3,
            'S_bu': 0.0140*1e3,
            'S_pro': 0.0176*1e3,
            'S_ac': 0.0893*1e3,
            'S_h2': 2.5055e-7*1e3,
            'S_ch4': 0.0555*1e3,
            'S_IC': 0.0951*C_mw*1e3,
            'S_IN': 0.0945*N_mw*1e3,
            'S_I': 0.1309*1e3,
            'X_ch': 0.0205*1e3,
            'X_pr': 0.0842*1e3,
            'X_li': 0.0436*1e3,
            'X_su': 0.3122*1e3,
            'X_aa': 0.9317*1e3,
            'X_fa': 0.3384*1e3,
            'X_c4': 0.3258*1e3,
            'X_pro': 0.1011*1e3,
            'X_ac': 0.6772*1e3,
            'X_h2': 0.2848*1e3,
            'X_I': 17.2162*1e3
        }
        AD.set_init_conc(**default_init_conds)

        # Set up the system
        sys = System('Anaerobic_Digestion', path=(AD,))
        sys.set_dynamic_tracker(eff, gas)
        
        # Run dynamic simulation
        sys.simulate(
            state_reset_hook='reset_cache',
            t_span=(0, simulation_time),
            t_eval=np.arange(0, simulation_time+t_step, t_step),
            method=method
        )
        
        # Calculate pH and alkalinity for the effluent stream
        update_ph_and_alkalinity(eff)
        
        return sys, inf, eff, gas
    except Exception as e:
        raise RuntimeError(f"Error running simulation: {e}")

def calculate_biomass_yields(inf, eff):
    """
    Calculate net biomass yield in terms of kg VSS/kg COD and kg TSS/kg COD
    
    Parameters
    ----------
    inf : WasteStream
        Influent stream
    eff : WasteStream
        Effluent stream
    
    Returns
    -------
    dict
        A dictionary containing biomass yields
    """
    # Calculate COD consumed
    try:
        # Try using direct properties first
        influent_COD = inf.COD  # mg/L
        effluent_COD = eff.COD  # mg/L
    except:
        # Fall back to composite method
        influent_COD = inf.composite('COD')  # mg/L
        effluent_COD = eff.composite('COD')  # mg/L
    
    COD_consumed = influent_COD - effluent_COD  # mg/L
    
    if COD_consumed <= 0:
        return {'VSS_yield': 0, 'TSS_yield': 0}
    
    # Identify biomass components
    biomass_IDs = ['X_su', 'X_aa', 'X_fa', 'X_c4', 'X_pro', 'X_ac', 'X_h2']
    
    # Get the solids concentrations
    eff_vss = eff.get_VSS()  # mg/L
    inf_vss = inf.get_VSS()  # mg/L
    
    # Get TSS (total suspended solids) - all particulates 
    eff_tss = eff.get_TSS()  # mg/L
    inf_tss = inf.get_TSS()  # mg/L
    
    # Calculate the biomass yield as the amount of effluent biomass per unit of substrate consumed
    # For anaerobic digestion, we're interested in how much biomass remains relative to what was degraded
    vss_yield = eff_vss / COD_consumed  # mg/mg = kg/kg
    tss_yield = eff_tss / COD_consumed  # mg/mg = kg/kg
    
    return {
        'VSS_yield': vss_yield,  # kg VSS/kg COD
        'TSS_yield': tss_yield,  # kg TSS/kg COD
    }

def calculate_effluent_COD(eff_stream):
    """
    Calculate the soluble and total COD in the effluent
    
    Parameters
    ----------
    eff_stream : WasteStream
        Effluent stream
    
    Returns
    -------
    dict
        A dictionary containing soluble and total COD values
    """
    # Total COD is already available as a property
    total_COD = eff_stream.COD  # mg/L
    
    # Soluble COD - use the composite method to get only soluble components
    soluble_COD = eff_stream.composite('COD', particle_size='s')  # mg/L
    
    # Particulate COD
    particulate_COD = eff_stream.composite('COD', particle_size='x')  # mg/L
    
    return {
        'soluble_COD': soluble_COD,  # mg/L
        'particulate_COD': particulate_COD,  # mg/L
        'total_COD': total_COD  # mg/L
    }

def calculate_gas_properties(gas_stream):
    """
    Calculate gas stream properties with proper unit conversions

    Parameters
    ----------
    gas_stream : WasteStream
        Gas stream from the simulation

    Returns
    -------
    dict
        Dictionary with gas properties (flow rates, concentrations, etc.)
    """
    MW_CH4 = 16.04
    MW_CO2 = 44.01
    MW_H2 = 2.02
    MW_C = 12.01
    
    DENSITY_CH4 = 0.716
    DENSITY_CO2 = 1.977
    DENSITY_H2 = 0.0899
    
    COD_CH4 = 4.0
    COD_H2 = 8.0
    
    flow_vol_total = 0.0
    methane_flow = 0.0
    co2_flow = 0.0
    h2_flow = 0.0
    
    try:
        if hasattr(gas_stream, 'imass'):
            mass_cod_ch4 = gas_stream.imass['S_ch4'] * 24
            mass_ch4 = mass_cod_ch4 / COD_CH4
            methane_flow = mass_ch4 / DENSITY_CH4

            mass_c = gas_stream.imass['S_IC'] * 24
            mass_co2 = mass_c * (MW_CO2 / MW_C)
            co2_flow = mass_co2 / DENSITY_CO2

            mass_cod_h2 = gas_stream.imass['S_h2'] * 24
            mass_h2 = mass_cod_h2 / COD_H2
            h2_flow = mass_h2 / DENSITY_H2

        flow_vol_total = methane_flow + co2_flow + h2_flow
        methane_pct = (methane_flow / flow_vol_total * 100) if flow_vol_total > 0 else 0
        co2_pct = (co2_flow / flow_vol_total * 100) if flow_vol_total > 0 else 0
        h2_ppmv = (h2_flow / flow_vol_total * 1e6) if flow_vol_total > 0 else 0
        
        return {
            'flow_total': flow_vol_total,  # Nm³/d
            'methane_flow': methane_flow,  # Nm³/d
            'co2_flow': co2_flow,  # Nm³/d
            'h2_flow': h2_flow,  # Nm³/d
            'methane_percent': methane_pct,  # %
            'co2_percent': co2_pct,  # %
            'h2_ppmv': h2_ppmv  # ppmv
        }

    except Exception as e:
        raise RuntimeError(f"Error calculating gas properties: {e}")