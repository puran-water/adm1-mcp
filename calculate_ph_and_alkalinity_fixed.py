"""
Revised utility script to calculate pH and alkalinity from ADM1 state variables

This implementation addresses issues with the previous version by directly accessing
component concentrations by ID rather than using array indices, and corrects the
conversion of VFA concentrations from COD units to molar units.
"""

import numpy as np
from scipy.optimize import brenth
from qsdsan import WasteStream
from chemicals.elements import molecular_weight as get_mw

# Constants
R = 8.314e-2  # Gas constant (bar·L/mol/K)
C_mw = get_mw({'C': 1})  # Carbon molecular weight (g/mol)
N_mw = get_mw({'N': 1})  # Nitrogen molecular weight (g/mol)

# Molecular weights (used for reference, but not directly for VFA conversion from COD)
# MW_AC = 60.05   # Acetate
# MW_PRO = 74.08  # Propionate
# MW_BU = 88.11   # Butyrate
# MW_VA = 102.13  # Valerate

# *** CORRECTED SECTION: COD Equivalent Weights (g COD / mol Acid) ***
# Calculated based on oxygen required for complete oxidation
# e.g., Acetate: CH3COOH + 2 O2 -> 2 CO2 + 2 H2O => 2 * 32 = 64 g O2/mol
COD_EQ_AC = 64.0    # g COD/mol Acetate
COD_EQ_PRO = 112.0   # g COD/mol Propionate (C3H6O2 + 3.5 O2 -> ...)
COD_EQ_BU = 160.0   # g COD/mol Butyrate   (C4H8O2 + 5 O2 -> ...)
COD_EQ_VA = 208.0   # g COD/mol Valerate   (C5H10O2 + 6.5 O2 -> ...)
# *** END CORRECTED SECTION ***

def acid_base_rxn(h_ion, components_molarity, Ka):
    """
    Charge balance equation for acid-base reactions

    Parameters
    ----------
    h_ion : float
        Hydrogen ion concentration [M] (mol/L)
    components_molarity : dict
        Dictionary of component molarities [M] (mol/L)
    Ka : array-like
        Acid dissociation constants [Kw, Ka_nh, Ka_co2, Ka_ac, Ka_pr, Ka_bu, Ka_va]

    Returns
    -------
    float
        Charge balance (should be zero at equilibrium)
    """
    # Extract components from dictionary (defaulting to 0 if not present)
    # Note: S_cat and S_an are assumed to be in keq/m³ or eq/L directly
    S_cat = components_molarity.get('S_cat', 0)
    S_an = components_molarity.get('S_an', 0)
    # Other components are in mol/L
    S_IN = components_molarity.get('S_IN', 0)
    S_IC = components_molarity.get('S_IC', 0)
    S_ac = components_molarity.get('S_ac', 0)
    S_pro = components_molarity.get('S_pro', 0)
    S_bu = components_molarity.get('S_bu', 0)
    S_va = components_molarity.get('S_va', 0)

    # Calculate dissociated species
    Kw = Ka[0]
    Ka_nh = Ka[1]
    Ka_co2 = Ka[2]
    Ka_ac = Ka[3]
    Ka_pr = Ka[4]
    Ka_bu = Ka[5]
    Ka_va = Ka[6]

    oh_ion = Kw/h_ion
    nh3 = S_IN * Ka_nh / (Ka_nh + h_ion) # Ammonia (NH3) concentration
    nh4 = S_IN - nh3                    # Ammonium (NH4+) concentration
    hco3 = S_IC * Ka_co2 / (Ka_co2 + h_ion) # Bicarbonate (HCO3-) concentration

    # *** ADDED: Calculate Carbonate (CO3^2-) concentration ***
    # pKa2 is approximately 10.3 at 25°C
    Ka2_co2 = 10**(-10.3)  # Second dissociation constant for carbonic acid
    co3 = hco3 * Ka2_co2 / h_ion # Carbonate concentration

    ac_ion = S_ac * Ka_ac / (Ka_ac + h_ion) # Acetate ion
    pro_ion = S_pro * Ka_pr / (Ka_pr + h_ion) # Propionate ion
    bu_ion = S_bu * Ka_bu / (Ka_bu + h_ion) # Butyrate ion
    va_ion = S_va * Ka_va / (Ka_va + h_ion) # Valerate ion

    # Charge balance equation: Sum(cations) - Sum(anions) = 0
    # Cations: S_cat (eq/L), H+, NH4+
    # Anions: S_an (eq/L), OH-, HCO3-, CO3^2- (note charge of -2), Ac-, Pro-, Bu-, Va-
    return S_cat + h_ion + nh4 - S_an - oh_ion - hco3 - (2 * co3) - ac_ion - pro_ion - bu_ion - va_ion

def solve_ph(components_molarity, Ka):
    """
    Solve for pH using the charge balance equation

    Parameters
    ----------
    components_molarity : dict
        Dictionary of component molarities [M] (mol/L), except S_cat/S_an (eq/L)
    Ka : array-like
        Acid dissociation constants

    Returns
    -------
    float
        Hydrogen ion concentration [M] (mol/L)
    """
    # The brenth algorithm finds the root of the acid_base_rxn function
    try:
        h = brenth(acid_base_rxn, 1e-14, 1.0,
                   args=(components_molarity, Ka),
                   xtol=1e-12, maxiter=100)
        return h
    except ValueError:
        # If root finding fails, return a reasonable default (pH 7)
        # Might indicate a problem with input concentrations or balance
        print("Warning: pH solver failed to find root. Returning default pH 7.")
        return 1e-7

def calculate_alkalinity(components_molarity, pH, Ka):
    """
    Calculate alkalinity based on component molarities and pH

    Parameters
    ----------
    components_molarity : dict
        Dictionary of component molarities [M] (mol/L), except S_cat/S_an (eq/L)
    pH : float
        pH value
    Ka : array-like
        Acid dissociation constants

    Returns
    -------
    float
        Alkalinity in meq/L
    """
    h_ion = 10**(-pH)

    # Extract components (defaulting to 0 if not present)
    # S_cat/S_an assumed eq/L
    S_cat = components_molarity.get('S_cat', 0)
    S_an = components_molarity.get('S_an', 0)
    # Others mol/L
    S_IN = components_molarity.get('S_IN', 0)
    S_IC = components_molarity.get('S_IC', 0)
    S_ac = components_molarity.get('S_ac', 0)
    S_pro = components_molarity.get('S_pro', 0)
    S_bu = components_molarity.get('S_bu', 0)
    S_va = components_molarity.get('S_va', 0)

    # Calculate species concentrations at the given pH
    Kw = Ka[0]
    Ka_nh = Ka[1]
    Ka_co2 = Ka[2]
    Ka_ac = Ka[3]
    Ka_pr = Ka[4]
    Ka_bu = Ka[5]
    Ka_va = Ka[6]

    oh_ion = Kw/h_ion
    nh3 = S_IN * Ka_nh / (Ka_nh + h_ion) # Ammonia
    hco3 = S_IC * Ka_co2 / (Ka_co2 + h_ion) # Bicarbonate

    # Calculate carbonate ion concentration
    Ka2_co2 = 10**(-10.3)  # Second dissociation constant for carbonic acid
    co3 = hco3 * Ka2_co2 / h_ion  # Carbonate concentration

    ac_ion = S_ac * Ka_ac / (Ka_ac + h_ion) # Acetate ion
    pro_ion = S_pro * Ka_pr / (Ka_pr + h_ion) # Propionate ion
    bu_ion = S_bu * Ka_bu / (Ka_bu + h_ion) # Butyrate ion
    va_ion = S_va * Ka_va / (Ka_va + h_ion) # Valerate ion

    # Alkalinity definition (based on titration to carbonic acid endpoint):
    # Alk = [HCO3-] + 2*[CO3^2-] + [NH3] + [Ac-] + [Pro-] + [Bu-] + [Va-] + [OH-] - [H+]
    # Note: This is one common definition. Sometimes S_cat and S_an are included if
    # they represent the *net* strong base/acid added. However, often in ADM1,
    # S_cat/S_an represent background ions, and alkalinity is defined by the buffer species.
    # Let's stick to the buffer species definition here.
    alk_molar = hco3 + 2*co3 + nh3 + ac_ion + pro_ion + bu_ion + va_ion + oh_ion - h_ion # mol/L

    # Convert to meq/L (1 mol/L = 1 eq/L for singly charged species)
    alk_meq = alk_molar * 1000

    # Ensure non-negative value
    return max(0, alk_meq)


def get_component_molarities(stream):
    """
    Extract component concentrations from stream and convert to molarities

    Parameters
    ----------
    stream : WasteStream
        The waste stream to analyze

    Returns
    -------
    dict
        Dictionary of component molarities/equivalents
    """
    # Dictionary to store molar concentrations (mol/L) or equivalents (eq/L)
    components_molarity = {}

    # Get component concentrations (assumed in kg/m³ or g/L)
    concentrations = {}
    # Define the components needed for pH/Alkalinity calculation
    required_comps = ['S_cat', 'S_an', 'S_IC', 'S_IN', 'S_ac', 'S_pro', 'S_bu', 'S_va']
    for comp_id in stream.components.IDs:
        if comp_id in required_comps:
            try:
                # Attempt to get concentration, default to 0.0 if not set or invalid
                conc_val = float(stream.iconc[comp_id])
                concentrations[comp_id] = conc_val if np.isfinite(conc_val) else 0.0
            except (KeyError, ValueError, TypeError):
                 concentrations[comp_id] = 0.0 # Set to 0 if component missing or value is invalid

    # Convert to molarities (mol/L) or equivalents (eq/L)
    # Note: ADM1 S_cat/S_an are typically in keq/m^3 already. Convert to eq/L.
    if 'S_cat' in concentrations:
        components_molarity['S_cat'] = concentrations['S_cat'] / 1000.0 # keq/m³ -> eq/L

    if 'S_an' in concentrations:
        components_molarity['S_an'] = concentrations['S_an'] / 1000.0 # keq/m³ -> eq/L

    # Convert mass concentrations (kg/m³ or g/L) to molar (mol/L)
    if 'S_IN' in concentrations:
        # Inorganic nitrogen (as N) -> mol N/L
        if N_mw > 0:
             components_molarity['S_IN'] = concentrations['S_IN'] / (N_mw * 1000.0)
        else:
             components_molarity['S_IN'] = 0.0

    if 'S_IC' in concentrations:
        # Inorganic carbon (as C) -> mol C/L
        if C_mw > 0:
            components_molarity['S_IC'] = concentrations['S_IC'] / (C_mw * 1000.0)
        else:
            components_molarity['S_IC'] = 0.0

    # *** CORRECTED SECTION: Use COD Equivalent Weights for VFAs ***
    if 'S_ac' in concentrations:
        # Acetate (from kg COD/m³ or g COD/L) -> mol Acetate/L
        if COD_EQ_AC > 0:
            components_molarity['S_ac'] = concentrations['S_ac'] / (COD_EQ_AC * 1000.0)
        else:
            components_molarity['S_ac'] = 0.0

    if 'S_pro' in concentrations:
        # Propionate (from kg COD/m³ or g COD/L) -> mol Propionate/L
        if COD_EQ_PRO > 0:
             components_molarity['S_pro'] = concentrations['S_pro'] / (COD_EQ_PRO * 1000.0)
        else:
             components_molarity['S_pro'] = 0.0

    if 'S_bu' in concentrations:
        # Butyrate (from kg COD/m³ or g COD/L) -> mol Butyrate/L
        if COD_EQ_BU > 0:
            components_molarity['S_bu'] = concentrations['S_bu'] / (COD_EQ_BU * 1000.0)
        else:
            components_molarity['S_bu'] = 0.0

    if 'S_va' in concentrations:
        # Valerate (from kg COD/m³ or g COD/L) -> mol Valerate/L
        if COD_EQ_VA > 0:
             components_molarity['S_va'] = concentrations['S_va'] / (COD_EQ_VA * 1000.0)
        else:
             components_molarity['S_va'] = 0.0
    # *** END CORRECTED SECTION ***

    return components_molarity

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
        stream._pH = 7.0
        stream._SAlk = 0.0 # Alkalinity often not relevant for gas streams
        return stream

    # Define the acid dissociation constants at 25°C (approximate)
    # [Kw, Ka_nh, Ka_co2, Ka_ac, Ka_pr, Ka_bu, Ka_va]
    # Using standard textbook values
    pKa_base = [14.0, 9.25, 6.35, 4.76, 4.88, 4.82, 4.86] # Common literature pKa values
    Ka = np.array([10**(-pKa) for pKa in pKa_base])

    # Get component molarities/equivalents
    components_molarity = get_component_molarities(stream)

    # If we couldn't get any components, return default values
    if not components_molarity:
        stream._pH = 7.0
        stream._SAlk = 2.5 * 1000 # Default alkalinity in meq/L (typical dilute water)
        return stream

    # Calculate pH
    h_ion = solve_ph(components_molarity, Ka)
    pH = -np.log10(h_ion) if h_ion > 0 else 14.0 # Avoid log(0)

    # Calculate alkalinity
    alk = calculate_alkalinity(components_molarity, pH, Ka)

    # # Optional: Check if alkalinity seems reasonable based on S_IC
    # # This logic might be overly simplistic and removed for now
    # S_IC_molarity = components_molarity.get('S_IC', 0)
    # if S_IC_molarity > 1e-4: # If significant inorganic carbon
    #     # Estimate alkalinity roughly from S_IC (assuming pH near 7)
    #     # At pH 7, mostly HCO3- (1 eq/mol), some CO3^2- (2 eq/mol)
    #     # Approximate factor around 1.1 eq/mol C
    #     direct_alk_estimate = S_IC_molarity * 1.1 * 1000 # meq/L
    #     # Use the larger of the calculated values only if calculated is very low
    #     if alk < 0.1 * direct_alk_estimate:
    #          alk = direct_alk_estimate

    # Update stream properties
    stream._pH = pH
    stream._SAlk = alk # Already in meq/L

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
    # Concentrations in kg/m³
    test_conc = {
        'S_su': 0.01, 'S_aa': 0.001, 'S_fa': 0.001,
        'S_va': 0.1, # Higher VFA (as COD)
        'S_bu': 0.1, # Higher VFA (as COD)
        'S_pro': 0.2, # Higher VFA (as COD)
        'S_ac': 0.5, # Higher Acetate (as COD)
        'S_h2': 1e-8, 'S_ch4': 1e-5,
        'S_IC': 0.6,   # kg C/m³ (was 0.5 * C_mw = 6 kg/m³)
        'S_IN': 0.05,  # kg N/m³ (was 0.05 * N_mw = 0.7 kg/m³)
        'S_I': 0.02,
        'S_cat': 40.0, # keq/m³
        'S_an': 20.0, # keq/m³
    }
    ws.set_flow_by_concentration(100, test_conc, units=('m3/d', 'kg/m3'))

    print("Initial concentrations (kg/m³):")
    for k, v in test_conc.items():
        print(f"  {k}: {v}")

    print("\nCalculating molarities/equivalents (mol/L or eq/L):")
    molarities = get_component_molarities(ws)
    for k, v in molarities.items():
        unit = "eq/L" if k in ['S_cat', 'S_an'] else "mol/L"
        print(f"  {k}: {v:.4e} {unit}")


    # Calculate and update pH and alkalinity
    update_ph_and_alkalinity(ws)

    # Print the results
    print(f"\nCalculated pH: {ws.pH:.2f}")
    print(f"Calculated Alkalinity: {ws.SAlk:.2f} meq/L")
    print(f"Input S_IC: {ws.iconc['S_IC']:.2f} kg C/m³") # Input was kg C/m³

if __name__ == "__main__":
    main()
