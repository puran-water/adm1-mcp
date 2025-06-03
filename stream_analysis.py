"""
Stream property calculations and analysis
"""
from simulation import calculate_effluent_COD, calculate_gas_properties, calculate_biomass_yields
from utils import CALCULATE_PH_AVAILABLE
from calculate_ph_and_alkalinity_fixed import update_ph_and_alkalinity as update_ph_alk_fixed 
import sys
import os
import numpy as np


# Add the parent directory to sys.path
parent_dir = os.path.dirname(os.path.abspath(__file__))
adm1_dir = os.path.join(os.path.dirname(parent_dir), "adm1")
sys.path.insert(0, adm1_dir)

def safe_get(stream, method_name, *args, **kwargs):
    """
    Safely call a method on the stream if it exists
    
    Parameters
    ----------
    stream : WasteStream
        The stream object
    method_name : str
        Name of the method to call
    *args, **kwargs
        Arguments to pass to the method
        
    Returns
    -------
    Result of the method or None if method doesn't exist or fails
    """
    try:
        if hasattr(stream, method_name):
            method = getattr(stream, method_name)
            if callable(method):
                return method(*args, **kwargs)
        return None
    except:
        return None

def safe_composite(stream, param, particle_size=None, organic=None, volatile=None, subgroup=None):
    """
    Safely get composite property value with special handling for solids to fix TSS calculation
    
    Parameters
    ----------
    stream : WasteStream
        The stream to get property from
    param : str
        The property to get
    particle_size : str or None
        Particle size filter to apply
    organic : bool or None
        Filter for organic/inorganic components
    volatile : bool or None
        Filter for volatile/non-volatile components
    subgroup : list or None
        Specific subgroup of components to consider
        
    Returns
    -------
    float or None
        The property value or None if not available
    """
    try:
        if hasattr(stream, 'composite'):
            # Special handling for solids (TSS calculation)
            if param == 'solids' and particle_size is None:
                # Calculate TSS correctly by only including particulate and colloidal components
                particulate = stream.composite('solids', particle_size='x')
                colloidal = stream.composite('solids', particle_size='c')
                return particulate + colloidal
            return stream.composite(param, particle_size=particle_size, 
                                   organic=organic, volatile=volatile, 
                                   subgroup=subgroup)
        return None
    except:
        return None

def get_component_conc(stream, component_id):
    """
    Helper function to safely get a component's concentration in mg/L
    
    Parameters
    ----------
    stream : WasteStream
        The stream object
    component_id : str
        Component ID to get concentration for
        
    Returns
    -------
    float or None
        Component concentration or None if not available
    """
    try:
        # Check if component exists
        if component_id not in stream.components.IDs:
            return None
        
        # Try different methods to get the concentration
        if hasattr(stream, 'get_mass_concentration'):
            try:
                concentrations = stream.get_mass_concentration(IDs=[component_id])
                return concentrations[0]
            except:
                pass
        
        if hasattr(stream, 'iconc'):
            try:
                return stream.iconc[component_id]
            except:
                pass
                
        if hasattr(stream, 'mass'):
            # Fallback to calculating from mass
            if stream.F_vol > 0:
                try:
                    return stream.imass[component_id] * 1000 / stream.F_vol  # kg/m3 to mg/L
                except:
                    pass
        
        # One more attempt with state data if available
        if hasattr(stream, 'state') and stream.state is not None:
            try:
                idx = stream.components.index(component_id)
                if idx < len(stream.state) - 1:  # -1 for flow at the end
                    return stream.state[idx]
            except:
                pass
                
        return None
    except:
        return None

def analyze_liquid_stream(stream, include_components=False):
    """
    Analyze a liquid stream (influent/effluent) and return key properties
    
    Parameters
    ----------
    stream : WasteStream
        The liquid stream to analyze
    include_components : bool, optional
        Whether to include individual component concentrations, by default False
        
    Returns
    -------
    dict
        Dictionary of stream properties
    """
    if stream is None:
        return {
            "success": False,
            "message": "Stream is not available."
        }
        
    try:
        flow = 0
        try:
            flow = stream.get_total_flow('m3/d')
        except:
            try:
                flow = stream.F_vol / 1000 * 24  # m3/d
            except:
                pass
        
        # Calculate all required values
        tss_value = safe_composite(stream, 'solids')  # Particulate + colloidal
        vss_value = safe_get(stream, 'get_VSS')
        iss_value = safe_get(stream, 'get_ISS')
        tds_value = safe_get(stream, 'get_TDS', include_colloidal=False)  # Pure dissolved solids
        
        # Map ADM1 component names to nitrogen species
        ammonia_component = 'S_NH4' if 'S_NH4' in stream.components.IDs else 'S_IN'
        nitrite_component = 'S_NO2' if 'S_NO2' in stream.components.IDs else None
        nitrate_component = 'S_NO3' if 'S_NO3' in stream.components.IDs else None
        
        # Get nitrogen component concentrations
        ammonia_conc = get_component_conc(stream, ammonia_component)
        
        # For nitrite and nitrate, assume 0.0 mg/L for ADM1 influent streams
        # In anaerobic digestion, these are typically near zero
        if nitrite_component and isinstance(get_component_conc(stream, nitrite_component), (int, float)):
            nitrite_conc = get_component_conc(stream, nitrite_component)
        else:
            nitrite_conc = 0.0
            
        if nitrate_component and isinstance(get_component_conc(stream, nitrate_component), (int, float)):
            nitrate_conc = get_component_conc(stream, nitrate_component)
        else:
            nitrate_conc = 0.0
        
        # Map ADM1 component names for VFAs
        acetate_component = 'S_ac' if 'S_ac' in stream.components.IDs else 'S_Ac'
        propionate_component = 'S_pro' if 'S_pro' in stream.components.IDs else 'S_Prop'
        
        # Get VFA concentrations
        acetate_conc = get_component_conc(stream, acetate_component)
        propionate_conc = get_component_conc(stream, propionate_component)
        
        # Calculate total VFAs if both values are numeric
        if isinstance(acetate_conc, (int, float)) and isinstance(propionate_conc, (int, float)):
            total_vfa = acetate_conc + propionate_conc
        else:
            total_vfa = None
        # ****** START REVISED INSERTION ******
        # Ensure pH and Alkalinity are calculated based on current components
        # using the logic from calculate_ph_and_alkalinity_fixed.py
        try:
            # Check if it's a valid WasteStream and has components
            if isinstance(stream, WasteStream) and hasattr(stream, 'components') and stream.components:
                    # Call the function to update pH and SAlk attributes in-place
                    update_ph_alk_fixed(stream) # Using the imported function (potentially aliased)
            else:
                # Handle case where stream is None, not a WasteStream, or missing components
                print(f"Warning: Stream {getattr(stream, 'ID', 'Unknown')} is not suitable for pH/Alkalinity calculation. Skipping update.")
                # Ensure defaults are set if attributes exist
                if hasattr(stream, '_pH'): stream._pH = 7.0
                if hasattr(stream, '_SAlk'): stream._SAlk = 0.0 # Defaulting to 0 for safety/clarity
        except Exception as e_ph_alk:
            print(f"Error during pH/Alkalinity calculation for stream {getattr(stream, 'ID', 'Unknown')}: {e_ph_alk}")
            # Set defaults on error
            if hasattr(stream, '_pH'): stream._pH = 7.0
            if hasattr(stream, '_SAlk'): stream._SAlk = 0.0
        # ****** END REVISED INSERTION ******

        # Build the result dictionary
        result = {
            "success": True,
            "basic": {
                "flow": flow,  # m³/d
                "pH": getattr(stream, 'pH', 7.0),
                "alkalinity": getattr(stream, 'SAlk', 0.0) * 50.0 # Convert meq/L to mg/L as CaCO3 (1 meq/L = 50 mg/L CaCO3)
            },
            "oxygen_demand": {
                "COD": safe_composite(stream, 'COD'),  # mg/L
                "BOD": safe_composite(stream, 'BOD'),  # mg/L
                "uBOD": getattr(stream, 'uBOD', safe_composite(stream, 'uBOD')),  # mg/L
                "ThOD": getattr(stream, 'ThOD', safe_composite(stream, 'ThOD')),  # mg/L
                "cnBOD": getattr(stream, 'cnBOD', safe_composite(stream, 'cnBOD'))  # mg/L
            },
            "carbon": {
                "TC": getattr(stream, 'TC', safe_composite(stream, 'C')),  # mg/L
                "TOC": getattr(stream, 'TOC', safe_composite(stream, 'C', organic=True))  # mg/L
            },
            "nitrogen": {
                "TN": safe_composite(stream, 'N'),  # mg/L
                "TKN": getattr(stream, 'TKN', None),  # mg/L
                "ammonia_n": ammonia_conc,  # mg/L
                "nitrite_n": nitrite_conc,  # mg/L
                "nitrate_n": nitrate_conc  # mg/L
            },
            "other_nutrients": {
                "TP": safe_composite(stream, 'P'),  # mg/L
                "TK": getattr(stream, 'TK', safe_composite(stream, 'K')),  # mg/L
                "TMg": getattr(stream, 'TMg', safe_composite(stream, 'Mg')),  # mg/L
                "TCa": getattr(stream, 'TCa', safe_composite(stream, 'Ca'))  # mg/L
            },
            "solids": {
                "TSS": tss_value,  # mg/L
                "VSS": vss_value,  # mg/L
                "ISS": iss_value,  # mg/L
                "TDS": tds_value,  # mg/L
                "TS": getattr(stream, 'dry_mass', None)  # mg/L
            },
            "vfa": {
                "acetate": acetate_conc,  # mg/L
                "propionate": propionate_conc,  # mg/L
                "total_vfa": total_vfa  # mg/L
            }
        }
        
        # Optionally include component concentrations
        if include_components:
            component_concs = {}
            for comp_id in stream.components.IDs:
                component_concs[comp_id] = get_component_conc(stream, comp_id)
            
            result["components"] = component_concs
        
        # Add COD breakdown
        try:
            cod_values = calculate_effluent_COD(stream)
            result["cod_breakdown"] = {
                "soluble_COD": cod_values['soluble_COD'],  # mg/L
                "particulate_COD": cod_values['particulate_COD'],  # mg/L
                "total_COD": cod_values['total_COD']  # mg/L
            }
        except:
            pass
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error analyzing liquid stream: {str(e)}"
        }

def analyze_gas_stream(stream):
    """
    Analyze a gas stream and return key properties
    
    Parameters
    ----------
    stream : WasteStream
        The gas stream to analyze
        
    Returns
    -------
    dict
        Dictionary of gas properties
    """
    if stream is None:
        return {
            "success": False,
            "message": "Stream is not available."
        }
    
    try:
        gas_props = calculate_gas_properties(stream)
        
        return {
            "success": True,
            "flow_total": gas_props['flow_total'],  # Nm³/d
            "methane_flow": gas_props['methane_flow'],  # Nm³/d
            "methane_percent": gas_props['methane_percent'],  # %
            "co2_flow": gas_props['co2_flow'],  # Nm³/d
            "co2_percent": gas_props['co2_percent'],  # %
            "h2_flow": gas_props['h2_flow'],  # Nm³/d
            "h2_ppmv": gas_props['h2_ppmv']  # ppmv
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error analyzing gas stream: {str(e)}"
        }

def analyze_biomass_yields(inf_stream, eff_stream):
    """
    Calculate and analyze biomass yields
    
    Parameters
    ----------
    inf_stream : WasteStream
        Influent stream
    eff_stream : WasteStream
        Effluent stream
        
    Returns
    -------
    dict
        Dictionary containing biomass yields and removal efficiency
    """
    if inf_stream is None or eff_stream is None:
        return {
            "success": False,
            "message": "Streams are not available."
        }
    
    try:
        # Calculate biomass yields
        yields = calculate_biomass_yields(inf_stream, eff_stream)
        
        # Calculate removal efficiency
        cod_removal = (1 - eff_stream.COD/inf_stream.COD) * 100
        
        return {
            "success": True,
            "VSS_yield": yields['VSS_yield'],  # kg VSS/kg COD
            "TSS_yield": yields['TSS_yield'],  # kg TSS/kg COD
            "COD_removal_efficiency": cod_removal  # %
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error calculating biomass yields: {str(e)}"
        }

def calculate_charge_balance(conc_dict, cmps):
    """
    Calculates the sum of positive (cation) and negative (anion) equivalents
    based on component concentrations and their defined i_charge.

    Args:
        conc_dict (dict): Dictionary of component concentrations {comp_id: value}.
                          Units are expected to be kg/m3 (or kg COD/m3 if measured_as='COD').
        cmps (CompiledComponents): The QSDsan CompiledComponents object containing
                                   the component definitions used in the simulation.

    Returns:
        tuple: (total_cation_eq_m3, total_anion_eq_m3) or (None, None) if calculation fails.
    """
    total_cation_eq_m3 = 0.0
    total_anion_eq_m3 = 0.0

    if not cmps:
        sys.stderr.write("ERROR: CompiledComponents object ('cmps') not provided to calculate_charge_balance.\n")
        sys.stderr.flush()
        return None, None

    # Debug info
    sys.stderr.write(f"DEBUG: Loading components for charge balance calculation. Component count: {len(cmps.IDs) if hasattr(cmps, 'IDs') else 'unknown'}\n")
    sys.stderr.flush()
    
    # Special handling for S_cat and S_an if they exist in conc_dict
    if 'S_cat' in conc_dict and conc_dict['S_cat'] is not None:
        # S_cat is always a cation with a charge of +1 keq/kg
        total_cation_eq_m3 += conc_dict['S_cat'] * 1.0  # assuming 1 keq/kg
        sys.stderr.write(f"DEBUG: Added S_cat to cations: {conc_dict['S_cat']} kg/m3 * 1.0 = {conc_dict['S_cat']} keq/m3\n")
        sys.stderr.flush()
    
    if 'S_an' in conc_dict and conc_dict['S_an'] is not None:
        # S_an is always an anion with a charge of -1 keq/kg
        total_anion_eq_m3 += conc_dict['S_an'] * 1.0  # assuming 1 keq/kg
        sys.stderr.write(f"DEBUG: Added S_an to anions: {conc_dict['S_an']} kg/m3 * 1.0 = {conc_dict['S_an']} keq/m3\n")
        sys.stderr.flush()

    # Process all other components
    for comp_id, value_kg_m3 in conc_dict.items():
        # Skip S_cat and S_an as they were already handled
        if comp_id in ['S_cat', 'S_an']:
            continue
            
        if value_kg_m3 is None or value_kg_m3 == 0.0:
            continue

        try:
            comp = getattr(cmps, comp_id, None) # Get Component object by ID
            if comp is None:
                sys.stderr.write(f"DEBUG: Component '{comp_id}' not found in cmps\n")
                sys.stderr.flush()
                continue
                
            if not hasattr(comp, 'i_charge'):
                sys.stderr.write(f"DEBUG: Component '{comp_id}' has no i_charge attribute\n")
                sys.stderr.flush()
                continue

            i_charge_keq_kg = getattr(comp, 'i_charge', 0.0) # Units: mol+/g = keq/kg
            if i_charge_keq_kg is None:
                # Handle null charge case
                sys.stderr.write(f"DEBUG: Component '{comp_id}' has None i_charge, treating as 0\n")
                sys.stderr.flush()
                i_charge_keq_kg = 0.0
                
            if abs(i_charge_keq_kg) < 1e-12: # Ignore non-ionic components
                continue

            # 'value_kg_m3' is the concentration in kg/m3 or kg COD/m3
            # 'i_charge_keq_kg' is the charge in keq/kg or keq/(kg COD)
            # We need to ensure the base unit matches (kg component or kg COD)

            equivalents_keq_m3 = 0.0
            measured_as = getattr(comp, 'measured_as', None)
            
            if measured_as and measured_as.upper() == 'COD':
                # value is kg COD/m3, i_charge should be keq/(kg COD)
                equivalents_keq_m3 = value_kg_m3 * i_charge_keq_kg
                sys.stderr.write(f"DEBUG: Component '{comp_id}' (COD): {value_kg_m3} kg COD/m3 * {i_charge_keq_kg} keq/kg COD = {equivalents_keq_m3} keq/m3\n")
                sys.stderr.flush()
            elif not measured_as: # Measured as kg Comp/m3
                equivalents_keq_m3 = value_kg_m3 * i_charge_keq_kg # (kg Comp/m3) * (keq / kg Comp) = keq/m3
                sys.stderr.write(f"DEBUG: Component '{comp_id}' (Mass): {value_kg_m3} kg/m3 * {i_charge_keq_kg} keq/kg = {equivalents_keq_m3} keq/m3\n")
                sys.stderr.flush()
            else:
                # Handle other 'measured_as' cases if necessary
                # Default calculation (same as mass-based)
                equivalents_keq_m3 = value_kg_m3 * i_charge_keq_kg
                sys.stderr.write(f"DEBUG: Component '{comp_id}' (Other): {value_kg_m3} kg/m3 * {i_charge_keq_kg} keq/kg = {equivalents_keq_m3} keq/m3\n")
                sys.stderr.flush()

            if equivalents_keq_m3 > 0:
                total_cation_eq_m3 += equivalents_keq_m3
                sys.stderr.write(f"DEBUG: Added {equivalents_keq_m3} keq/m3 to cations for '{comp_id}'\n")
                sys.stderr.flush()
            elif equivalents_keq_m3 < 0:
                total_anion_eq_m3 += abs(equivalents_keq_m3) # Sum absolute value for anions
                sys.stderr.write(f"DEBUG: Added {abs(equivalents_keq_m3)} keq/m3 to anions for '{comp_id}'\n")
                sys.stderr.flush()

        except Exception as e_comp:
            sys.stderr.write(f"ERROR processing component '{comp_id}' for charge balance: {e_comp}\n")
            sys.stderr.flush()
            # Continue calculation even if one component fails

    # Return equivalents in eq/m3 (or meq/L)
    sys.stderr.write(f"DEBUG FINAL: Cations = {total_cation_eq_m3} keq/m3, Anions = {total_anion_eq_m3} keq/m3\n")
    sys.stderr.write(f"DEBUG FINAL: Returning {total_cation_eq_m3 * 1000} eq/m3, {total_anion_eq_m3 * 1000} eq/m3\n")
    sys.stderr.flush()
    
    return total_cation_eq_m3 * 1000, total_anion_eq_m3 * 1000
