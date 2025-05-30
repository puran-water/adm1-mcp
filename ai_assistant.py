# -*- coding: utf-8 -*-
"""
AI assistant for ADM1 parameter generation
"""
import json
import re
import os
import sys
import traceback  # Import traceback
import google.generativeai as genai
from dotenv import load_dotenv

# Keep load_dotenv() here for potential standalone use, but server.py also calls it.
load_dotenv()


class GeminiClient:
    """
    Client for interacting with the Gemini API
    """

    def __init__(self):
        """
        Initialize the GeminiClient
        """
        print("DEBUG [GeminiClient]: __init__ called.")  # DEBUG Init Start
        self.client = self._setup_client()
        if self.client:
            print("DEBUG [GeminiClient]: Initialization successful, self.client is set.")  # DEBUG Init Success
        else:
            print("DEBUG [GeminiClient]: Initialization FAILED, self.client is None.")  # DEBUG Init Fail

    def _setup_client(self):
        """
        Initialize the Gemini API client
        """
        print("DEBUG [GeminiClient]: _setup_client called.")  # DEBUG Setup Start
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            print("DEBUG ERROR [GeminiClient]: GOOGLE_API_KEY not found in environment variables during _setup_client!")  # DEBUG Key Missing
            return None

        print(f"DEBUG [GeminiClient]: Found API Key starting with: {api_key[:5]}...")  # DEBUG Key Found

        try:
            # Explicitly configure genai here if not done globally
            genai.configure(api_key=api_key) # Might be redundant if server already configures, but can help isolate issues

            # --- Try/Except around model initialization ---
            print("DEBUG [GeminiClient]: Attempting to create GenerativeModel...")
            model_name = "gemini-2.5-pro-preview-05-06"  # TRY THIS STABLE MODEL NAME FIRST
            # model_name="gemini-2.5-pro-exp-03-25" # Original experimental name
            print(f"DEBUG [GeminiClient]: Using model_name: {model_name}")
            client = genai.GenerativeModel(
                model_name=model_name
            )
            print("DEBUG [GeminiClient]: GenerativeModel created successfully.")  # DEBUG Model Create Success
            return client
        except Exception as e:
            print(f"DEBUG ERROR [GeminiClient]: Error initializing GenerativeModel: {e}")  # DEBUG Model Create Fail
            traceback.print_exc()  # Print full traceback
            return None

    def get_adm1_recommendations(self, feedstock_description, include_kinetics=True):
        """
        Get recommendations for ADM1 model parameters based on feedstock description

        Parameters
        ----------
        feedstock_description : str
            Description of the feedstock
        include_kinetics : bool, optional
            Whether to include kinetic parameters in the recommendations, by default True

        Returns
        -------
        str or None
            JSON string containing the recommendations or None if an error occurs
        """
        print("DEBUG [GeminiClient]: get_adm1_recommendations called.")  # DEBUG Method Start
        if not self.client:
            print("DEBUG ERROR [GeminiClient]: self.client is None in get_adm1_recommendations. Cannot proceed.")  # DEBUG Client None
            return None

        # System prompt definition (removed for brevity, assuming it's correct)
        # google_search_tool definition (removed for brevity, assuming it's correct)
        google_search_tool = {
            'function_declarations': [
                {
                    'name': 'search',
                    'description': 'Search for information on the web',
                    'parameters': {
                        'type': 'object',
                        'properties': {
                            'query': {
                                'type': 'string',
                                'description': 'The search query'
                            }
                        },
                        'required': ['query']
                    }
                }
            ]
        }

        if include_kinetics:
            prompt = self._build_full_prompt(feedstock_description)
            print("DEBUG [GeminiClient]: Built full prompt (with kinetics).")  # DEBUG Prompt Type
        else:
            prompt = self._build_feedstock_prompt(feedstock_description)
            print("DEBUG [GeminiClient]: Built feedstock-only prompt.")  # DEBUG Prompt Type

        # --- Try/Except around API call ---
        try:
            print(f"DEBUG [GeminiClient]: Calling self.client.generate_content with prompt starting: {prompt[:100]}...")  # DEBUG API Call Start
            response = self.client.generate_content(
                contents=prompt,
                tools=google_search_tool
            )
            print(f"DEBUG [GeminiClient]: API call successful. Response type: {type(response)}")  # DEBUG API Call Success
            if hasattr(response, 'text'):
                print(f"DEBUG [GeminiClient]: Response text preview: {response.text[:100]}...")  # DEBUG API Response Preview
                return response.text
            else:
                print("DEBUG WARNING [GeminiClient]: Response object does not have 'text' attribute.")
                # Handle potential different response structures (e.g., if function calling occurs)
                # For now, return a representation or None
                print(f"DEBUG [GeminiClient]: Full response object: {response}")
                # Attempt to extract text differently if needed, or indicate non-text response
                # If it's a function call response part, we might not get simple text.
                # For this tool's purpose, we expect text.
                return None  # Indicate failure to get text

        except Exception as e:
            print(f"DEBUG ERROR [GeminiClient]: Exception during self.client.generate_content: {e}")  # DEBUG API Call Fail
            traceback.print_exc()  # Print full traceback
            return None  # Return None on failure

    def _build_full_prompt(self, feedstock_description):
        """ Builds the full prompt string """
        # (Keep the existing long prompt string here - omitted for brevity)
        return f"""
        I need you to recommend:
        1) Feedstock state variable values (S_su, S_aa, S_fa, ..., X_su, X_fa, etc.).

        2) Substrate-dependent kinetic parameters (including disintegration, hydrolysis,
        uptake, decay, yields, and fractionation) relevant to ADM1.
        
        Please provide your recommendations for these state and kinetic variables in JSON format with these specific keys:

        IMPORTANT: Ensure all explanations use only simple ASCII characters (avoid special symbols, 
        mathematical notation, or non-English characters). Keep explanations brief and use simple language.


        {{
            "S_su": [value, "kg/m3", "explanation"],
            "S_aa": [value, "kg/m3", "explanation"],
            "S_fa": [value, "kg/m3", "explanation"],
            "S_va": [value, "kg/m3", "explanation"],
            "S_bu": [value, "kg/m3", "explanation"],
            "S_pro": [value, "kg/m3", "explanation"],
            "S_ac": [value, "kg/m3", "explanation"],
            "S_h2": [value, "kg/m3", "explanation"],
            "S_ch4": [value, "kg/m3", "explanation"],
            "S_IC": [value, "kg/m3", "explanation"],
            "S_IN": [value, "kg/m3", "explanation"],
            "S_I": [value, "kg/m3", "explanation"],
            "X_c": [value, "kg/m3", "explanation"],
            "X_ch": [value, "kg/m3", "explanation"],
            "X_pr": [value, "kg/m3", "explanation"],
            "X_li": [value, "kg/m3", "explanation"],
            "X_su": [value, "kg/m3", "explanation"],
            "X_aa": [value, "kg/m3", "explanation"],
            "X_fa": [value, "kg/m3", "explanation"],
            "X_c4": [value, "kg/m3", "explanation"],
            "X_pro": [value, "kg/m3", "explanation"],
            "X_ac": [value, "kg/m3", "explanation"],
            "X_h2": [value, "kg/m3", "explanation"],
            "X_I": [value, "kg/m3", "explanation"],
            "S_cat": [value, "keq/m3", "explanation"],
            "S_an": [value, "keq/m3", "explanation"],
            "q_dis": [value, "d^-1", "explanation"],
            "q_ch_hyd": [value, "d^-1", "explanation"],
            "q_pr_hyd": [value, "d^-1", "explanation"],
            "q_li_hyd": [value, "d^-1", "explanation"],
            "k_su": [value, "kgCOD/m3/d", "explanation"],
            "k_aa": [value, "kgCOD/m3/d", "explanation"],
            "k_fa": [value, "kgCOD/m3/d", "explanation"],
            "k_c4": [value, "kgCOD/m3/d", "explanation"],
            "k_pro": [value, "kgCOD/m3/d", "explanation"],
            "k_ac": [value, "kgCOD/m3/d", "explanation"],
            "k_h2": [value, "kgCOD/m3/d", "explanation"],
            "b_su": [value, "d^-1", "explanation"],
            "b_aa": [value, "d^-1", "explanation"],
            "b_fa": [value, "d^-1", "explanation"],
            "b_c4": [value, "d^-1", "explanation"],
            "b_pro": [value, "d^-1", "explanation"],
            "b_ac": [value, "d^-1", "explanation"],
            "b_h2": [value, "d^-1", "explanation"],
            "K_su": [value, "kg COD/m³", "explanation"],
            "K_aa": [value, "kg COD/m³", "explanation"],
            "K_fa": [value, "kg COD/m³", "explanation"],
            "K_c4": [value, "kg COD/m³", "explanation"],
            "K_pro": [value, "kg COD/m³", "explanation"],
            "K_ac": [value, "kg COD/m³", "explanation"],
            "K_h2": [value, "kg COD/m³", "explanation"],
            "KI_h2_fa": [value, "kg COD/m³", "explanation"],
            "KI_h2_c4": [value, "kg COD/m³", "explanation"],
            "KI_h2_pro": [value, "kg COD/m³", "explanation"],
            "KI_nh3": [value, "M", "explanation"],
            "KS_IN": [value, "M", "explanation"],
            "Y_su": [value, "kg COD/kg COD", "explanation"],
            "Y_aa": [value, "kg COD/kg COD", "explanation"],
            "Y_fa": [value, "kg COD/kg COD", "explanation"],
            "Y_c4": [value, "kg COD/kg COD", "explanation"],
            "Y_pro": [value, "kg COD/kg COD", "explanation"],
            "Y_ac": [value, "kg COD/kg COD", "explanation"],
            "Y_h2": [value, "kg COD/kg COD", "explanation"],
            "f_bu_su": [value, "kg COD/kg COD", "explanation"],
            "f_pro_su": [value, "kg COD/kg COD", "explanation"],
            "f_ac_su": [value, "kg COD/kg COD", "explanation"],
            "f_va_aa": [value, "kg COD/kg COD", "explanation"],
            "f_bu_aa": [value, "kg COD/kg COD", "explanation"],
            "f_pro_aa": [value, "kg COD/kg COD", "explanation"],
            "f_ac_aa": [value, "kg COD/kg COD", "explanation"],
            "f_ac_fa": [value, "kg COD/kg COD", "explanation"],
            "f_pro_va": [value, "kg COD/kg COD", "explanation"],
            "f_ac_va": [value, "kg COD/kg COD", "explanation"],
            "f_ac_bu": [value, "kg COD/kg COD", "explanation"],
            "f_ac_pro": [value, "kg COD/kg COD", "explanation"]
        }}

        In which:
        **S_su**: Monosaccharides, **S_aa**: Amino acids, **S_fa**: Total long-chain fatty acids, **S_va**: Total valerate, **S_bu**: Total butyrate,
        **S_pro**: Total propionate, **S_ac**: Total acetate, **S_h2**: Hydrogen gas, **S_ch4**: Methane gas, **S_IC**: Inorganic carbon, **S_IN**: Inorganic nitrogen,
        **S_I**: Soluble inerts (i.e. recalcitrant soluble COD), **X_c**: Composites, **X_ch**: Carobohydrates, **X_pr**: Proteins, **X_li**: Lipids, **X_su**: Biomass uptaking sugars, **X_aa**: Biomass uptaking amino acids,
        **X_fa**: Biomass uptaking long chain fatty acids, **X_c4**: Biomass uptaking c4 fatty acids (valerate and butyrate), **X_pro**: Biomass uptaking propionate,
        **X_ac**: Biomass uptaking acetate, **X_h2**: Biomass uptaking hydrogen, **X_I**: Particulate inerts (i.e. recalcitrant particulate COD), **S_cat**: Other cations, **S_an**: Other anions
        q_dis: Composite disintegration rate constant,
        q_ch_hyd: Carbohydrate (sugar) hydrolysis rate constant,
        q_pr_hyd: Protein hydrolysis rate constant,
        q_li_hyd: Lipid hydrolysis rate constant,
        k_su: Sugar uptake rate constant,
        k_aa: Amino acid uptake rate constant,
        k_fa: LCFA (long-chain fatty acid) uptake rate constant,
        k_c4: C₄ fatty acid (butyrate/valerate) uptake rate constant,
        k_pro: Propionate uptake rate constant,
        k_ac: Acetate uptake rate constant,
        k_h2: Hydrogen uptake rate constant,
        b_su: Decay rate constant for sugar-degrading biomass,
        b_aa: Decay rate constant for amino acid-degrading biomass,
        b_fa: Decay rate constant for LCFA-degrading biomass,
        b_c4: Decay rate constant for butyrate/valerate-degrading biomass,
        b_pro: Decay rate constant for propionate-degrading biomass,
        b_ac: Decay rate constant for acetate-degrading biomass,
        b_h2: Decay rate constant for hydrogen-degrading biomass,
        K_su: Half-saturation coefficient for sugar uptake,
        K_aa: Half-saturation coefficient for amino acid uptake,
        K_fa: Half-saturation coefficient for LCFA uptake,
        K_c4: Half-saturation coefficient for butyrate/valerate uptake,
        K_pro: Half-saturation coefficient for propionate uptake,
        K_ac: Half-saturation coefficient for acetate uptake,
        K_h2: Half-saturation coefficient for hydrogen uptake,
        KI_h2_fa: Hydrogen inhibition coefficient for LCFA uptake,
        KI_h2_c4: Hydrogen inhibition coefficient for butyrate/valerate uptake,
        KI_h2_pro: Hydrogen inhibition coefficient for propionate uptake,
        KI_nh3: Free ammonia inhibition coefficient for acetate uptake,
        KS_IN: Inorganic nitrogen inhibition coefficient for substrate uptake,
        Y_su: Biomass yield for sugar uptake,
        Y_aa: Biomass yield for amino acid uptake,
        Y_fa: Biomass yield for LCFA uptake,
        Y_c4: Biomass yield for butyrate/valerate uptake,
        Y_pro: Biomass yield for propionate uptake,
        Y_ac: Biomass yield for acetate uptake,
        Y_h2: Biomass yield for hydrogen uptake,
        f_bu_su: Fraction of sugars converted to butyrate,
        f_pro_su: Fraction of sugars converted to propionate,
        f_ac_su: Fraction of sugars converted to acetate,
        f_va_aa: Fraction of amino acids converted to valerate,
        f_bu_aa: Fraction of amino acids converted to butyrate,
        f_pro_aa: Fraction of amino acids converted to propionate,
        f_ac_aa: Fraction of amino acids converted to acetate,
        f_ac_fa: Fraction of LCFAs converted to acetate,
        f_pro_va: Fraction of LCFAs (via valerate) converted to propionate,
        f_ac_va: Fraction of valerate converted to acetate,
        f_ac_bu: Fraction of butyrate converted to acetate, and
        f_ac_pro: Fraction of propionate converted to acetate.

        Units of S_su, S_aa, S_fa, S_va, S_bu, S_pro, S_ac, S_h2, S_ch4, S_I, X_c, X_ch, X_pr, X_li, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2, X_I are kg COD/m3.

        Units of S_IC are kg C/m3.

        Units of S_IN are kg N/m3.

        Units of S_cat and S_an are kg/m3 as cations and anions, respectively.

        Make sure you provide the explanation for why each value is chosen
        (the domain reason, such as typical range for certain feedstock).

        **IMPORTANT REQUIREMENTS**

        1. When suggesting feedstock state variables, ensure electroneutrality:

        The total positive charges from S_cat plus any NH₄⁺ plus H+ ions if the feestock pH is <7 is equal to the total negative charges from S_an plus the deprotonated fractions of S_IC (assume HCO₃⁻ if pH near neutral) and the OH- ions if pH is >7.
        EXAMPLE:
        - Anions 
            1. From Alkalinity/pH:                                                                                                                                                                                 
                - Assume a feedstock pH of 10 and feedstock Alk = 10 meq/L as provided by the user.
                - The main contributors are [HCO3-] ≈ 5.1 meq/L and 2*[CO3--] ≈ 4.8 meq/L. Total contribution ≈ 9.9 meq/L.                                         
                - Hydroxide [OH-] = 10⁻⁴ mol/L = 0.1 meq/L.                                                                                                                                                               
            2. Anions from organic acids:
                - Determine the meq/L of organic acids based on the following: 64.0 g COD/mol Acetate, 112.0 g COD/mol Propionate, 
                160.0 g COD/mol Butyrate, 208.0 g COD/mol Valerate and 1 eq/mol (assume the total concentration of organic anions is 
                X meq/L in this example)
            3. Anions from S_an:                                                                                                                                                                                          
                - Provide the balance assuming the S_an is as Cl- (if the user provides a TDS value, use this as the basis.  Otherwise, use your knowledge and research to assume a feedstock TDS and assign a value). 
                For example, S_an = 0.1 keq/m³ = 100 meq/L.                                                           
            4. Total Anions: 9.9 (IC) + 0.1 (OH) + 100 (S_an) + X (ac_ion + pro_ion + bu_ion + va_ion) ≈ 110 + X meq/L.                                                                                                                                                
        - Cations
            1. Cations from S_IN:                                                                                                                                                                                         
                - Based on user input on feedstock N or based on your knowledge and research of feedstock N content, assign a value. For example, S_IN = 0.008 kg N/m³ = 0.57 mmol/L. At pH 10 (pKa NH4+ ~9.25), the charged form [NH4+] ≈ 0.086 mmol/L ≈ 86 meq/L.
            2. Cations from S_cat:                                                                                                                                                                                        
                - This is the variable used to balance the remaining charge.                                                                                                                                              
                Balancing:                                                                                                                                                                                                 
                    - Required Total Cations = Total Anions ≈ 110 + X meq/L.                                                                                                                                                     
                    - Required S_cat = Total Cations - [NH4+] ≈ 110 + X - 86 = 24 + X meq/L (or 0.024 + X/1000 keq/m³).
        
        2. Remember that S_I is recalcitrant soluble COD and X_I is recalcitrant particulate COD.  The feedstock source will dictate what a reasonable estimate of these values should be - it is NOT something that can be calculated i.e. you cannot assume the user provided TSS less the user provided VSS is equivalent to X_I since X_I is volatile.  Rather, based on the source of the feedstock, a reasonable value shou
        be provided.
        For instance, feedstock from food and beverage waste would have low levels of both S_I and X_I since the material is highly degradable.  On the other hand, agrowaste with large lignocellulosic content and waste activated sludge with difficult to degrade volatile solids would contain larger amounts of X_I.  Another example, textile wastewater with dyes would contain larger amounts of S_I.

        3. IF USER DEFINED PARAMETERS (e.g COD, TSS, TKN) ARE PROVIDED IN THE FEEDSTOCK DESCRIPTION** - ensure the resulting characterization (e.g. COD, TSS, TKN) calculated based on your
        estimates of state variables are equivalent to the concentrations provided in the feedstock description. For instance, if a feedstock COD concentration is provided, ensure the sum of your state variable estimates is consistent with that COD.

        Here is the feedstock description:

        {feedstock_description}

        Only include these exact state variables and provide values with appropriate units for ADM1 model inputs.
        """  # Use triple quotes for multi-line f-string

    def _build_feedstock_prompt(self, feedstock_description):
        """ Builds the feedstock-only prompt string """
        # (Keep the existing long prompt string here - omitted for brevity)
        return f"""
        I need you to recommend state variable values for the following feedstock:

        {feedstock_description}

        Please provide your recommendations for these state variables in JSON format with these specific keys:

        IMPORTANT: Ensure all explanations use only simple ASCII characters (avoid special symbols, 
        mathematical notation, or non-English characters). Keep explanations brief and use simple language.

        {{
            "S_su": [value, "kg/m3", "explanation"],
            "S_aa": [value, "kg/m3", "explanation"],
            "S_fa": [value, "kg/m3", "explanation"],
            "S_va": [value, "kg/m3", "explanation"],
            "S_bu": [value, "kg/m3", "explanation"],
            "S_pro": [value, "kg/m3", "explanation"],
            "S_ac": [value, "kg/m3", "explanation"],
            "S_h2": [value, "kg/m3", "explanation"],
            "S_ch4": [value, "kg/m3", "explanation"],
            "S_IC": [value, "kg/m3", "explanation"],
            "S_IN": [value, "kg/m3", "explanation"],
            "S_I": [value, "kg/m3", "explanation"],
            "X_c": [value, "kg/m3", "explanation"],
            "X_ch": [value, "kg/m3", "explanation"],
            "X_pr": [value, "kg/m3", "explanation"],
            "X_li": [value, "kg/m3", "explanation"],
            "X_su": [value, "kg/m3", "explanation"],
            "X_aa": [value, "kg/m3", "explanation"],
            "X_fa": [value, "kg/m3", "explanation"],
            "X_c4": [value, "kg/m3", "explanation"],
            "X_pro": [value, "kg/m3", "explanation"],
            "X_ac": [value, "kg/m3", "explanation"],
            "X_h2": [value, "kg/m3", "explanation"],
            "X_I": [value, "kg/m3", "explanation"],
            "S_cat": [value, "keq/m3", "explanation"],
            "S_an": [value, "keq/m3", "explanation"]
        }}

        In which:
        **S_su**: Monosaccharides, **S_aa**: Amino acids, **S_fa**: Total long-chain fatty acids, **S_va**: Total valerate, **S_bu**: Total butyrate,
        **S_pro**: Total propionate, **S_ac**: Total acetate, **S_h2**: Hydrogen gas, **S_ch4**: Methane gas, **S_IC**: Inorganic carbon, **S_IN**: Inorganic nitrogen,
        **S_I**: Soluble inerts (i.e. recalcitrant soluble COD), **X_c**: Composites, **X_ch**: Carobohydrates, **X_pr**: Proteins, **X_li**: Lipids, **X_su**: Biomass uptaking sugars, **X_aa**: Biomass uptaking amino acids,
        **X_fa**: Biomass uptaking long chain fatty acids, **X_c4**: Biomass uptaking c4 fatty acids (valerate and butyrate), **X_pro**: Biomass uptaking propionate,
        **X_ac**: Biomass uptaking acetate, **X_h2**: Biomass uptaking hydrogen, **X_I**: Particulate inerts (i.e. recalcitrant particulate COD), **S_cat**: Other cations, **S_an**: Other anions

        Units of S_su, S_aa, S_fa, S_va, S_bu, S_pro, S_ac, S_h2, S_ch4, S_I, X_c, X_ch, X_pr, X_li, X_aa, X_fa, X_c4, X_pro, X_ac, X_h2, X_I are kg COD/m3.

        Units of S_IC are kg C/m3.

        Units of S_IN are kg N/m3.

        Units of S_cat and S_an are keq/m3 as cations and anions, respectively.

        Make sure you provide the explanation for why each value is chosen
        (the domain reason, such as typical range for certain feedstock).

        **IMPORTANT REQUIREMENTS**

        1. When suggesting feedstock state variables, ensure electroneutrality:

        The total positive charges from S_cat plus any NH₄⁺ plus H+ ions if the feestock pH is <7 is equal to the total negative charges from S_an plus the deprotonated fractions of S_IC (assume HCO₃⁻ if pH near neutral) and the OH- ions if pH is >7.
        EXAMPLE:
        1. When suggesting feedstock state variables, ensure electroneutrality:

        The total positive charges from S_cat plus any NH₄⁺ plus H+ ions if the feestock pH is <7 is equal to the total negative charges from S_an plus the deprotonated fractions of S_IC (assume HCO₃⁻ if pH near neutral) and the OH- ions if pH is >7.
        EXAMPLE:
        - Anions 
            1. From Alkalinity/pH:                                                                                                                                                                                 
                - Assume a feedstock pH of 10 and feedstock Alk = 10 meq/L as provided by the user.
                - The main contributors are [HCO3-] ≈ 5.1 meq/L and 2*[CO3--] ≈ 4.8 meq/L. Total contribution ≈ 9.9 meq/L.                                         
                - Hydroxide [OH-] = 10⁻⁴ mol/L = 0.1 meq/L.                                                                                                                                                               
            2. Anions from organic acids:
                - Determine the meq/L of organic acids based on the following: 64.0 g COD/mol Acetate, 112.0 g COD/mol Propionate, 
                160.0 g COD/mol Butyrate, 208.0 g COD/mol Valerate and 1 eq/mol (assume the total concentration of organic anions is 
                X meq/L in this example)
            3. Anions from S_an:                                                                                                                                                                                          
                - Provide the balance assuming the S_an is as Cl- (if the user provides a TDS value, use this as the basis.  Otherwise, use your knowledge and research to assume a feedstock TDS and assign a value). 
                For example, S_an = 0.1 keq/m³ = 100 meq/L.                                                           
            4. Total Anions: 9.9 (IC) + 0.1 (OH) + 100 (S_an) + X (ac_ion + pro_ion + bu_ion + va_ion) ≈ 110 + X meq/L.                                                                                                                                                
        - Cations
            1. Cations from S_IN:                                                                                                                                                                                         
                - Based on user input on feedstock N or based on your knowledge and research of feedstock N content, assign a value. For example, S_IN = 0.008 kg N/m³ = 0.57 mmol/L. At pH 10 (pKa NH4+ ~9.25), the charged form [NH4+] ≈ 0.086 mmol/L ≈ 86 meq/L.
            2. Cations from S_cat:                                                                                                                                                                                        
                - This is the variable used to balance the remaining charge.                                                                                                                                              
                Balancing:                                                                                                                                                                                                 
                    - Required Total Cations = Total Anions ≈ 110 + X meq/L.                                                                                                                                                     
                    - Required S_cat = Total Cations - [NH4+] ≈ 110 + X - 86 = 24 + X meq/L (or 0.024 + X/1000 keq/m³).

        2. Remember that S_I is recalcitrant soluble COD and X_I is recalcitrant particulate COD.  The feedstock source will dictate what a reasonable estimate of these values should be - it is NOT something that can be calculated i.e. you cannot assume the user provided TSS less the user provided VSS is equivalent to X_I since X_I is volatile.  Rather, based on the source of the feedstock, a reasonable value shou
        be provided.
        For instance, feedstock from food and beverage waste would have low levels of both S_I and X_I since the material is highly degradable.  On the other hand, agrowaste with large lignocellulosic content and waste activated sludge with difficult to degrade volatile solids would contain larger amounts of X_I.  Another example, textile wastewater with dyes would contain larger amounts of S_I.

        3. IF USER DEFINED PARAMETERS (e.g COD, TSS, TKN) ARE PROVIDED IN THE FEEDSTOCK DESCRIPTION** - ensure the resulting characterization (e.g. COD, TSS, TKN) calculated based on your
        estimates of state variables are equivalent to the concentrations provided in the feedstock description. For instance, if a feedstock COD concentration is provided, ensure the sum of your state variable estimates is consistent with that COD.

        Only include these exact state variables and provide values with appropriate units for ADM1 model inputs.
        """  # Use triple quotes for multi-line f-string

    def parse_recommendations(self, response_text, include_kinetics=True):
        """
        Parse the response from the Gemini API into dictionaries

        Parameters
        ----------
        response_text : str
            Response text from the API
        include_kinetics : bool, optional
            Whether to parse kinetic parameters, by default True

        Returns
        -------
        tuple
            (feedstock_values, feedstock_explanations, kinetic_values, kinetic_explanations)
        """
        # (Keep the existing parsing logic here - it seems okay, but errors in API call/init prevent it from running)
        # Known feedstock keys
        feedstock_keys = {
            "S_su", "S_aa", "S_fa", "S_va", "S_bu", "S_pro", "S_ac", "S_h2", "S_ch4", "S_IC", "S_IN", "S_I",
            "X_c", "X_ch", "X_pr", "X_li", "X_su", "X_aa", "X_fa", "X_c4", "X_pro", "X_ac", "X_h2", "X_I",
            "S_cat", "S_an"
        }
        # Known kinetic keys
        kinetic_keys = {
            "q_dis", "q_ch_hyd", "q_pr_hyd", "q_li_hyd",
            "k_su", "k_aa", "k_fa", "k_c4", "k_pro", "k_ac", "k_h2",
            "b_su", "b_aa", "b_fa", "b_c4", "b_pro", "b_ac", "b_h2",
            "K_su", "K_aa", "K_fa", "K_c4", "K_pro", "K_ac", "K_h2",
            "KI_h2_fa", "KI_h2_c4", "KI_h2_pro", "KI_nh3", "KS_IN",
            "Y_su", "Y_aa", "Y_fa", "Y_c4", "Y_pro", "Y_ac", "Y_h2",
            "f_bu_su", "f_pro_su", "f_ac_su", "f_va_aa", "f_bu_aa",
            "f_pro_aa", "f_ac_aa", "f_ac_fa", "f_pro_va", "f_ac_va",
            "f_ac_bu", "f_ac_pro"
        }

        feedstock_values = {}
        feedstock_explanations = {}
        kinetic_values = {}
        kinetic_explanations = {}

        if not response_text:  # Handle empty response text
            print("DEBUG WARNING [GeminiClient]: parse_recommendations received empty response_text.")
            return (feedstock_values, feedstock_explanations, kinetic_values, kinetic_explanations)

        # Extract JSON - Improved robustness
        json_str = None
        # Try finding JSON within ```json ... ``` blocks first
        match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL | re.IGNORECASE)
        if match:
            json_str = match.group(1)
        else:
            # Fallback: find the first '{' and last '}'
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response_text[start:end + 1]

        if not json_str:
            print("DEBUG ERROR [GeminiClient]: Could not find JSON block in response.")
            # Optionally, raise a specific error here or return empty dicts
            # raise ValueError("Could not extract JSON from AI response.")
            return (feedstock_values, feedstock_explanations, kinetic_values, kinetic_explanations)

        try:
            # Clean potential leading/trailing non-JSON characters if fallback was used
            # json_str = json_str.strip() # Basic strip
            data = json.loads(json_str)
            for key, arr in data.items():
                # Add more validation for the array structure
                if isinstance(arr, list) and len(arr) >= 1:
                    try:
                        val = float(arr[0])  # Ensure value is float
                        explanation = str(arr[2]) if len(arr) >= 3 else "No explanation provided."
                        unit = str(arr[1]) if len(arr) >= 2 else "N/A"  # Get unit if available

                        if key in feedstock_keys:
                            feedstock_values[key] = val
                            feedstock_explanations[key] = f"{explanation} (Unit: {unit})"
                        elif include_kinetics and key in kinetic_keys:
                            kinetic_values[key] = val
                            kinetic_explanations[key] = f"{explanation} (Unit: {unit})"
                        # else: # Optional: log unexpected keys
                        #     print(f"DEBUG WARNING [GeminiClient]: Unexpected key '{key}' found in parsed JSON.")

                    except (ValueError, TypeError, IndexError) as e_item:
                        print(f"DEBUG WARNING [GeminiClient]: Skipping invalid item for key '{key}': {arr}. Error: {e_item}")
                        continue  # Skip this item if value is not a number or structure is wrong
                else:
                    print(f"DEBUG WARNING [GeminiClient]: Skipping invalid structure for key '{key}': {arr}")

            return (feedstock_values, feedstock_explanations, kinetic_values, kinetic_explanations)

        except json.JSONDecodeError as e:
            print(f"DEBUG ERROR [GeminiClient]: JSONDecodeError - {e}")
            print(f"Failed JSON string was: {json_str}")
            raise ValueError(f"Error parsing AI JSON response: {e}")  # Re-raise for the tool to catch
        except Exception as e:
            print(f"DEBUG ERROR [GeminiClient]: Unexpected error during parsing: {e}")
            traceback.print_exc()
