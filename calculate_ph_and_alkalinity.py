"""
Utility script to calculate pH and alkalinity from ADM1 state variables

This script provides functions to calculate pH and alkalinity based on the acid-base equilibria
of components in the ADM1 model. It uses the same algorithms as the ADM1 model itself.
"""

import numpy as np
from scipy.optimize import brenth
from qsdsan import WasteStream
from chemicals.elements import molecular_weight as get_mw

# Constants
R = 8.314e-2  # Gas constant (bar·L/mol/K)
C_mw = get_mw({'C': 1})
N_mw = get_mw({'N': 1})

def solve_ph(state_arr, Ka, unit_conversion):
    """
    Solve for the pH using the charge balance equation from ADM1
    
    Parameters
    ----------
    state_arr : array-like
        Array of state variables (concentrations)
    Ka : array-like
        Acid dissociation constants [Kw, Ka_nh, Ka_co2, Ka_ac, Ka_pr, Ka_bu, Ka_va]
    unit_conversion : array-like
        Conversion factors from mass units to molar units
    
    Returns
    -------
    float
        Hydrogen ion concentration [M]
    """
    # In ADM1, the indices are:
    # S_cat(24), S_an(25), S_IN(10), S_IC(9), S_ac(6), S_pro(5), S_bu(4), S_va(3)
    weak_acids = state_arr[[24, 25, 10, 9, 6, 5, 4, 3]] * unit_conversion
    
    # Use brenth (bracketing method) to find the root of the charge balance equation
    h = brenth(acid_base_rxn, 1e-14, 1.0,
              args=(weak_acids, Ka),
              xtol=1e-12, maxiter=100)
    return h

def acid_base_rxn(h_ion, weak_acids_tot, Kas):
    """
    Charge balance equation for acid-base reactions
    
    Parameters
    ----------
    h_ion : float
        Hydrogen ion concentration [M]
    weak_acids_tot : array-like
        Array of total weak acids/bases concentrations [S_cat, S_an, S_IN, S_IC, S_ac, S_pro, S_bu, S_va]
    Kas : array-like
        Acid dissociation constants [Kw, Ka_nh, Ka_co2, Ka_ac, Ka_pr, Ka_bu, Ka_va]
        
    Returns
    -------
    float
        Charge balance (should be zero at equilibrium)
    """
    S_cat, S_an, S_IN = weak_acids_tot[:3]
    Kw = Kas[0]
    oh_ion = Kw/h_ion
    nh3, hco3, ac, pro, bu, va = Kas[1:] * weak_acids_tot[2:] / (Kas[1:] + h_ion)
    return S_cat + h_ion + (S_IN - nh3) - S_an - oh_ion - hco3 - ac - pro - bu - va

def calculate_alkalinity(state_arr, pH, unit_conversion, Ka):
    """
    Calculate alkalinity in meq/L based on state variables
    
    Parameters
    ----------
    state_arr : array-like
        Array of state variables (concentrations)
    pH : float
        pH value
    unit_conversion : array-like
        Conversion factors from mass units to molar units
    Ka : array-like
        Acid dissociation constants
        
    Returns
    -------
    float
        Alkalinity in meq/L
    """
    h_ion = 10**(-pH)
    
    # Get the concentrations of relevant species
    S_cat, S_an = state_arr[[24, 25]] * unit_conversion[:2]  # Cations and anions
    S_IN, S_IC = state_arr[[10, 9]] * unit_conversion[2:4]   # Inorganic N and C
    S_ac, S_pro, S_bu, S_va = state_arr[[6, 5, 4, 3]] * unit_conversion[4:8]  # VFAs
    
    # Calculate concentrations of species that contribute to alkalinity
    Kw = Ka[0]
    oh_ion = Kw/h_ion
    
    # Ammonia (contributes to alkalinity as NH3)
    Ka_nh = Ka[1]
    nh3 = S_IN * Ka_nh / (Ka_nh + h_ion)
    
    # Bicarbonate (primary contributor to alkalinity)
    Ka_co2 = Ka[2]
    hco3 = S_IC * Ka_co2 / (Ka_co2 + h_ion)
    
    # Acetate
    Ka_ac = Ka[3]
    ac = S_ac * Ka_ac / (Ka_ac + h_ion)
    
    # Propionate
    Ka_pr = Ka[4]
    pro = S_pro * Ka_pr / (Ka_pr + h_ion)
    
    # Butyrate
    Ka_bu = Ka[5]
    bu = S_bu * Ka_bu / (Ka_bu + h_ion)
    
    # Valerate
    Ka_va = Ka[6]
    va = S_va * Ka_va / (Ka_va + h_ion)
    
    # Calculate alkalinity (in molar units)
    # Alkalinity = [HCO3-] + 2[CO3--] + [OH-] - [H+] + [NH3] + [Ac-] + [Pr-] + [Bu-] + [Va-]
    # Calculate carbonate ion concentration using the second dissociation constant
    # pKa2 is approximately 10.3 at 25°C
    Ka2_co2 = 10**(-10.3)  # Second dissociation constant for carbonic acid
    co3 = hco3 * Ka2_co2 / h_ion  # Carbonate concentration
    
    # Full alkalinity calculation including carbonate contribution
    # Each mole of CO3^2- contributes 2 eq of alkalinity
    alk_molar = hco3 + 2*co3 + oh_ion - h_ion + nh3 + ac + pro + bu + va + S_cat - S_an
    
    # Convert to meq/L (1 mol of HCO3- = 1 eq)
    return alk_molar * 1000  # Convert mol/L to meq/L

def update_ph_and_alkalinity(stream):
    """
    Update the pH and alkalinity for a WasteStream based on its component concentrations
    
    Parameters
    ----------
    stream : WasteStream
        The waste stream to update
        
    Returns
    -------
    WasteStream
        The updated waste stream (same object, modified in-place)
    """
    if stream.phase != 'l':
        # For non-liquid streams, set default values
        if hasattr(stream, '_pH'):
            stream._pH = 7.0
        if hasattr(stream, '_SAlk'):
            stream._SAlk = 0.0
        return stream
    
    # Define the acid dissociation constants at 25°C
    # [Kw, Ka_nh, Ka_co2, Ka_ac, Ka_pr, Ka_bu, Ka_va]
    pKa_base = [14, 9.25, 6.35, 4.76, 4.88, 4.82, 4.86]
    Ka = np.array([10**(-pKa) for pKa in pKa_base])
    
    # Define the conversion factors from concentration to molarity
    # We'll use simple approximate conversions for this demonstration
    # For a more accurate version, we would use the actual molecular weights from the components
    component_order = ['S_cat', 'S_an', 'S_IN', 'S_IC', 'S_ac', 'S_pro', 'S_bu', 'S_va']
    
    # Create conversion factors (mg/L to mol/L)
    # These are approximate and should be refined based on actual component properties
    conversion_factors = np.array([
        1/1000,           # S_cat (assuming average MW of 1 g/mol)
        1/1000,           # S_an (assuming average MW of 1 g/mol)
        1/(N_mw*1000),    # S_IN (assuming NH4+)
        1/(C_mw*1000),    # S_IC (assuming HCO3-)
        1/60000,          # S_ac (approximate MW = 60 g/mol)
        1/74000,          # S_pro (approximate MW = 74 g/mol)
        1/88000,          # S_bu (approximate MW = 88 g/mol)
        1/102000,         # S_va (approximate MW = 102 g/mol)
    ])
    
    # Get concentrations from the stream
    concentrations = np.zeros(26)
    for i, comp_id in enumerate(component_order):
        if comp_id in stream.components.IDs:
            concentrations[24+i-len(component_order)] = stream.iconc[comp_id]
    
    # Solve for pH
    h_ion = solve_ph(concentrations, Ka, conversion_factors)
    pH = -np.log10(h_ion)
    
    # Calculate alkalinity
    alk = calculate_alkalinity(concentrations, pH, conversion_factors, Ka)
    
    # Update the stream properties
    stream._pH = pH
    stream._SAlk = alk
    
    return stream

def main():
    """
    Test function to demonstrate the pH and alkalinity calculations
    """
    from qsdsan import Components, set_thermo
    
    # Load default components
    cmps = Components.load_default()
    set_thermo(cmps)
    
    # Create a test stream
    ws = WasteStream('test_stream')
    ws.set_flow_by_concentration(100, {
        'S_su': 0.01,
        'S_aa': 0.001,
        'S_fa': 0.001,
        'S_va': 0.001,
        'S_bu': 0.001,
        'S_pro': 0.001,
        'S_ac': 0.001,
        'S_h2': 1e-8,
        'S_ch4': 1e-5,
        'S_IC': 0.1 * C_mw,  # Higher inorganic carbon
        'S_IN': 0.02 * N_mw,  # Higher inorganic nitrogen
        'S_I': 0.02,
        'S_cat': 0.04,
        'S_an': 0.02,
    }, units=('m3/d', 'kg/m3'))
    
    # Calculate and update pH and alkalinity
    update_ph_and_alkalinity(ws)
    
    # Print the results
    print(f"pH: {ws.pH:.2f}")
    print(f"Alkalinity: {ws.SAlk:.2f} meq/L")
    
    # Now try with different S_IC and S_IN values
    ws2 = WasteStream('test_stream2')
    ws2.set_flow_by_concentration(100, {
        'S_su': 0.01,
        'S_aa': 0.001,
        'S_fa': 0.001,
        'S_va': 0.001,
        'S_bu': 0.001,
        'S_pro': 0.001, 
        'S_ac': 0.01,      # Higher acetate (should reduce pH)
        'S_h2': 1e-8,
        'S_ch4': 1e-5,
        'S_IC': 0.05 * C_mw,  # Different inorganic carbon
        'S_IN': 0.03 * N_mw,  # Different inorganic nitrogen
        'S_I': 0.02,
        'S_cat': 0.02,      # Lower cations 
        'S_an': 0.04,       # Higher anions (should reduce pH)
    }, units=('m3/d', 'kg/m3'))
    
    # Calculate and update pH and alkalinity
    update_ph_and_alkalinity(ws2)
    
    # Print the results
    print(f"\npH: {ws2.pH:.2f}")
    print(f"Alkalinity: {ws2.SAlk:.2f} meq/L")

if __name__ == "__main__":
    main()
