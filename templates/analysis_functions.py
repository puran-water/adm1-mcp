"""
Analysis functions for ADM1 simulation results
"""
import numpy as np
import pandas as pd

def safe_get(stream, method_name, *args, **kwargs):
    """Safely call a method on the stream if it exists"""
    try:
        if hasattr(stream, method_name):
            method = getattr(stream, method_name)
            if callable(method):
                return method(*args, **kwargs)
        return None
    except Exception as e:
        print(f"Warning: Error getting {method_name}: {e}")
        return None

def safe_composite(stream, param, particle_size=None, organic=None, volatile=None, subgroup=None):
    """Safely get composite property value with special handling for solids"""
    try:
        if hasattr(stream, 'composite'):
            # Special handling for solids (TSS calculation)
            if param == 'solids' and particle_size is None:
                # Calculate TSS correctly by including only particulate and colloidal components
                particulate = stream.composite('solids', particle_size='x')
                colloidal = stream.composite('solids', particle_size='c')
                return particulate + colloidal
            return stream.composite(param, particle_size=particle_size, 
                                   organic=organic, volatile=volatile, 
                                   subgroup=subgroup)
        return None
    except Exception as e:
        print(f"Warning: Error getting composite {param}: {e}")
        return None

def get_component_conc(stream, component_id):
    """Helper function to safely get a component's concentration"""
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
                    return stream.imass[component_id] * 1000 / stream.F_vol / 24 # kg/m3 to mg/L
                except:
                    pass
                
        return None
    except Exception as e:
        print(f"Warning: Error getting component {component_id}: {e}")
        return None

def calculate_effluent_COD(eff_stream):
    """Calculate the soluble and total COD in the effluent"""
    try:
        # Total COD is available as a property
        total_COD = eff_stream.COD  # mg/L
        
        # Soluble COD - use the composite method to get only soluble components
        soluble_COD = safe_composite(eff_stream, 'COD', particle_size='s')  # mg/L
        
        # Particulate COD
        particulate_COD = safe_composite(eff_stream, 'COD', particle_size='x')  # mg/L
        
        return {
            'soluble_COD': soluble_COD,  # mg/L
            'particulate_COD': particulate_COD,  # mg/L
            'total_COD': total_COD  # mg/L
        }
    except Exception as e:
        print(f"Warning: Error calculating effluent COD: {e}")
        return {'soluble_COD': None, 'particulate_COD': None, 'total_COD': None}

def analyze_liquid_stream(stream, include_components=False):
    """Analyze a liquid stream (influent/effluent) and return key properties"""
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
                flow = stream.F_vol * 24 # m3/d
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

        # Build the result dictionary
        result = {
            "success": True,
            "basic": {
                "flow": flow,  # m³/d
                "pH": getattr(stream, 'pH', 7.0),
                "alkalinity": getattr(stream, 'SAlk', 0.0) * 50.0 # Convert meq/L to mg/L as CaCO3
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
        except Exception as e:
            print(f"Warning: Error calculating COD breakdown: {e}")
            pass
        
        return result
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error analyzing liquid stream: {str(e)}"
        }

def calculate_gas_properties(gas_stream):
    """Calculate gas stream properties with proper unit conversions"""
    MW_CH4 = 16.04
    MW_CO2 = 44.01
    MW_H2 = 2.02
    MW_C = 12.01
    
    DENSITY_CH4 = 0.716  # kg/m³ @ STP
    DENSITY_CO2 = 1.977  # kg/m³ @ STP
    DENSITY_H2 = 0.0899  # kg/m³ @ STP
    
    COD_CH4 = 4.0  # kg COD/kg CH4
    COD_H2 = 8.0   # kg COD/kg H2
    
    flow_vol_total = 0.0
    methane_flow = 0.0
    co2_flow = 0.0
    h2_flow = 0.0
    
    try:
        if hasattr(gas_stream, 'imass'):
            # Convert from kg/hr to kg/d (x24)
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
        print(f"Error calculating gas properties: {e}")
        return {
            'flow_total': 0.0,
            'methane_flow': 0.0,
            'co2_flow': 0.0,
            'h2_flow': 0.0,
            'methane_percent': 0.0,
            'co2_percent': 0.0,
            'h2_ppmv': 0.0
        }

def analyze_gas_stream(stream):
    """Analyze a gas stream and return key properties"""
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

def calculate_biomass_yields(inf, eff):
    """Calculate net biomass yield in terms of kg VSS/kg COD and kg TSS/kg COD"""
    try:
        # Calculate COD consumed
        try:
            # Try using direct properties first
            influent_COD = inf.COD  # mg/L
            effluent_COD = eff.COD  # mg/L
        except:
            # Fall back to composite method
            influent_COD = safe_composite(inf, 'COD')  # mg/L
            effluent_COD = safe_composite(eff, 'COD')  # mg/L

        COD_consumed = influent_COD - effluent_COD  # mg/L

        if COD_consumed <= 0:
            return {'VSS_yield': 0, 'TSS_yield': 0}

        # Get the solids concentrations
        eff_vss = safe_get(eff, 'get_VSS') or 0  # mg/L
        inf_vss = safe_get(inf, 'get_VSS') or 0  # mg/L

        # Get TSS (total suspended solids) - all particulates
        eff_tss = safe_get(eff, 'get_TSS') or safe_composite(eff, 'solids') or 0  # mg/L
        inf_tss = safe_get(inf, 'get_TSS') or safe_composite(inf, 'solids') or 0  # mg/L

        # Calculate the biomass yield as the amount of effluent biomass per unit of substrate consumed
        vss_yield = eff_vss / COD_consumed  # mg/mg = kg/kg
        tss_yield = eff_tss / COD_consumed  # mg/mg = kg/kg

        # Calculate solids production rates
        vss_prod = eff_vss * eff.F_vol * 24 / 1000  # kg VSS/d
        tss_prod = eff_tss * eff.F_vol * 24 / 1000  # kg TSS/d

        # Calculate COD removal efficiency
        cod_removal = (1 - effluent_COD/influent_COD) if influent_COD > 0 else 0

        return {
            'VSS_yield': vss_yield,      # kg VSS/kg COD
            'TSS_yield': tss_yield,      # kg TSS/kg COD
            'VSS_prod': vss_prod,        # kg VSS/d
            'TSS_prod': tss_prod,        # kg TSS/d
            'COD_removed': cod_removal   # fraction
        }
    except Exception as e:
        print(f"Error calculating biomass yields: {e}")
        return {
            'VSS_yield': 0,
            'TSS_yield': 0,
            'VSS_prod': 0,
            'TSS_prod': 0,
            'COD_removed': 0
        }

def analyze_biomass_yields(inf_stream, eff_stream):
    """Calculate and analyze biomass yields"""
    if inf_stream is None or eff_stream is None:
        return {
            "success": False,
            "message": "Streams are not available."
        }

    try:
        # Calculate biomass yields
        yields = calculate_biomass_yields(inf_stream, eff_stream)

        # Calculate methane yield
        methane_flow = 0.0
        try:
            gas_data = calculate_gas_properties(biogas)
            methane_flow = gas_data['methane_flow']
        except:
            pass

        try:
            # Calculate the COD removed in kg/d
            inf_cod_conc = inf_stream.COD  # mg/L = g/m³
            eff_cod_conc = eff_stream.COD  # mg/L = g/m³
            inf_flow = inf_stream.F_vol * 24    # m³/d
            cod_removed_kgd = (inf_cod_conc - eff_cod_conc) * inf_flow / 1000  # kg COD/d

            # Calculate methane yield if COD removal is positive
            if cod_removed_kgd > 0:
                ch4_per_cod = methane_flow / cod_removed_kgd  # Nm³ CH₄/kg COD removed
            else:
                ch4_per_cod = 0.0
        except:
            ch4_per_cod = 0.0

        # Add methane yield to results
        yields['CH4_prod_per_COD'] = ch4_per_cod

        return {
            "success": True,
            "VSS_yield": yields['VSS_yield'],              # kg VSS/kg COD
            "TSS_yield": yields['TSS_yield'],              # kg TSS/kg COD
            "VSS_production_rate": yields['VSS_prod'],     # kg VSS/d
            "TSS_production_rate": yields['TSS_prod'],     # kg TSS/d
            "COD_removal_efficiency": yields['COD_removed'],  # fraction
            "CH4_yield": yields['CH4_prod_per_COD']        # Nm³ CH₄/kg COD removed
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error calculating biomass yields: {str(e)}"
        }

def calculate_inhibition_factors(system):
    """
    Calculate inhibition factors from the ADM1 model using the same approach
    as the original server implementation
    """
    try:
        # Get the anaerobic unit from the system
        if system is None:
            return None
            
        # Try to access the inhibition data stored by the ADM1 model during simulation
        try:
            # The ADM1 model in QSDsan stores inhibition data in the model's root attribute
            # This is stored during rate calculation in the _rhos_adm1 function
            root_data = system._path[0].model.rate_function._params['root'].data
            
            if root_data is None:
                return None
                
            # Extract inhibition factors in the same format as our current implementation 
            inhibition_factors = {
                # pH inhibition
                'pH_inhibition_aa': root_data.get('Iph', [1, 1, 1, 1, 1, 1, 1, 1])[1],  # Index 1 for amino acids
                'pH_inhibition_ac': root_data.get('Iph', [1, 1, 1, 1, 1, 1, 1, 1])[6],  # Index 6 for acetate
                'pH_inhibition_h2': root_data.get('Iph', [1, 1, 1, 1, 1, 1, 1, 1])[7],  # Index 7 for hydrogen
                
                # Free ammonia inhibition (nitrogen)
                'ammonia_inhibition_ac': root_data.get('Inh3', 1),
                
                # Hydrogen inhibition - indices correspond to original implementation
                'h2_inhibition_fa': root_data.get('Ih2', [1, 1, 1, 1])[0],  # LCFA 
                'h2_inhibition_c4': root_data.get('Ih2', [1, 1, 1, 1])[1],  # C4
                'h2_inhibition_pro': root_data.get('Ih2', [1, 1, 1, 1])[2],  # Propionate
                
                # VFA inhibition
                'vfa_inhibition_c4': root_data.get('I_5_c4', 1.0),
                'vfa_inhibition_pro': root_data.get('I_6_pro', 1.0),
                'vfa_inhibition_ac': root_data.get('I_7_ac', 1.0),
                'vfa_inhibition_h2': root_data.get('I_8_h2', 1.0)
            }
            
            return inhibition_factors
            
        except (KeyError, AttributeError, IndexError) as e:
            print(f"Error accessing inhibition data: {e}")
            return None
            
    except Exception as e:
        print(f"Error calculating inhibition factors: {e}")
        return None

def get_effluent_pH(effluent, system):
    """
    Retrieve the pH value of the effluent stream from the simulation.
    """
    try:
        # First, try to get pH from effluent attribute (set by update_ph_and_alkalinity)
        if hasattr(effluent, 'pH'):
            return effluent.pH
        # Alternatively, try to get it from root data if available at the final time step
        root_data = system._path[0].model.rate_function._params['root'].data if system._path else None
        if root_data and 'pH' in root_data:
            return root_data['pH']
        return None
    except Exception as e:
        print(f"Error retrieving effluent pH: {e}")
        return None

def analyze_inhibition(system):
    """Analyze inhibition factors and identify potential issues."""
    inhibition_factors = calculate_inhibition_factors(system)
    
    if inhibition_factors is None:
        return {
            "success": False,
            "message": "Could not extract inhibition data from the system."
        }
    
    # Define thresholds for inhibition severity
    # Values close to 1 mean little or no inhibition
    # Values close to 0 mean severe inhibition
    thresholds = {
        "severe": 0.5,  # Below this is severe inhibition
        "moderate": 0.7,  # Below this is moderate inhibition
        "mild": 0.9     # Below this is mild inhibition
    }
    
    # Categorize inhibition by severity
    inhibition_categories = {
        "severe": [],
        "moderate": [],
        "mild": [],
        "none": []
    }
    
    for factor_name, factor_value in inhibition_factors.items():
        if factor_value < thresholds["severe"]:
            inhibition_categories["severe"].append((factor_name, factor_value))
        elif factor_value < thresholds["moderate"]:
            inhibition_categories["moderate"].append((factor_name, factor_value))
        elif factor_value < thresholds["mild"]:
            inhibition_categories["mild"].append((factor_name, factor_value))
        else:
            inhibition_categories["none"].append((factor_name, factor_value))
    
    # Determine overall status
    overall_status = "No significant inhibition detected"
    
    if inhibition_categories["severe"]:
        overall_status = "Severe inhibition detected"
    elif inhibition_categories["moderate"]:
        overall_status = "Moderate inhibition detected"
    elif inhibition_categories["mild"]:
        overall_status = "Mild inhibition detected"
    
    return {
        "success": True,
        "overall_status": overall_status,
        "factors": inhibition_factors,
        "categories": inhibition_categories
    }

def calculate_nutrient_limitations(effluent, system):
    """
    Calculate nutrient limitation factors based on Monod kinetics using effluent concentrations
    and the half-saturation constants from the simulation parameters.
    """
    try:
        # Extract effluent nutrient concentrations
        # Nitrogen (typically as S_IN or S_NH4 in ADM1)
        if 'S_IN' in effluent.components.IDs:
            S_NH4 = get_component_conc(effluent, 'S_IN')  # mg-N/L (converted from kg/m3 in function)
        elif 'S_NH4' in effluent.components.IDs:
            S_NH4 = get_component_conc(effluent, 'S_NH4')
        else:
            S_NH4 = 0.0
        
        # Phosphorus is not always explicitly modeled in standard ADM1, but check if available
        if 'S_P' in effluent.components.IDs:
            S_P = get_component_conc(effluent, 'S_P')  # mg-P/L
        else:
            S_P = 0.0  # Assume no explicit phosphorus tracking if not available
        
        # Retrieve the half-saturation constant for inorganic nitrogen (KS_IN) from simulation parameters
        # Access the ADM1 model parameters from the system object
        try:
            # Assuming the system stores the ADM1 model parameters in the first unit's model
            adm1_params = system._path[0].model.rate_function._params if system._path else None
            if adm1_params and 'KS_IN' in adm1_params:
                KS_IN = adm1_params['KS_IN'] * 1000  # Convert from kg-N/m3 to mg-N/L
            else:
                # Default value from ADM1 literature if not accessible (Batstone et al., 2002)
                KS_IN = 0.0001 * 1000  # 0.0001 kg/m3 = 0.1 mg-N/L, typical for methanogens in ADM1
                print("Warning: Could not retrieve KS_IN from simulation, using default value of 0.1 mg-N/L.")
        except Exception as e:
            print(f"Error retrieving KS_IN: {e}. Using default value.")
            KS_IN = 0.0001 * 1000  # Default fallback
        
        # Phosphorus half-saturation constant (if modeled, use a typical value as placeholder)
        # Note: Phosphorus is not standard in ADM1, so using a typical value if needed
        K_P_H = 0.01 * 1000  # Convert from kg-P/m3 to mg-P/L (0.01 kg/m3 = 10 mg/L)
        
        # Calculate Monod limitation factors
        # Nitrogen limitation factor for heterotrophs/methanogens
        if S_NH4 + KS_IN > 0:
            nitrogen_limit = S_NH4 / (KS_IN + S_NH4)
        else:
            nitrogen_limit = 0.0
        
        # Phosphorus limitation factor (if P is modeled)
        if S_P + K_P_H > 0:
            phosphorus_limit = S_P / (K_P_H + S_P)
        else:
            phosphorus_limit = 1.0  # Assume no limitation if P is not modeled
        
        return {
            'nitrogen_limit': nitrogen_limit,
            'phosphorus_limit': phosphorus_limit
        }
    except Exception as e:
        print(f"Error calculating nutrient limitations: {e}")
        return {
            'nitrogen_limit': 0.0,
            'phosphorus_limit': 0.0
        }

def analyze_nutrient_limitations(effluent, system):
    """Analyze nutrient limitation factors and identify potential issues."""
    nutrient_limits = calculate_nutrient_limitations(effluent, system)
    
    if not nutrient_limits:
        return {
            "success": False,
            "message": "Could not calculate nutrient limitation factors."
        }
    
    # Define thresholds for limitation severity (similar to inhibition factors)
    thresholds = {
        "severe": 0.5,   # Below this is severe limitation
        "moderate": 0.7, # Below this is moderate limitation
        "mild": 0.9      # Below this is mild limitation
    }
    
    # Categorize limitations by severity
    limitation_categories = {
        "severe": [],
        "moderate": [],
        "mild": [],
        "none": []
    }
    
    for factor_name, factor_value in nutrient_limits.items():
        if factor_value < thresholds["severe"]:
            limitation_categories["severe"].append((factor_name, factor_value))
        elif factor_value < thresholds["moderate"]:
            limitation_categories["moderate"].append((factor_name, factor_value))
        elif factor_value < thresholds["mild"]:
            limitation_categories["mild"].append((factor_name, factor_value))
        else:
            limitation_categories["none"].append((factor_name, factor_value))
    
    # Determine overall status
    overall_status = "No significant nutrient limitation detected"
    if limitation_categories["severe"]:
        overall_status = "Severe nutrient limitation detected"
    elif limitation_categories["moderate"]:
        overall_status = "Moderate nutrient limitation detected"
    elif limitation_categories["mild"]:
        overall_status = "Mild nutrient limitation detected"
    
    return {
        "success": True,
        "overall_status": overall_status,
        "factors": nutrient_limits,
        "categories": limitation_categories
    }
