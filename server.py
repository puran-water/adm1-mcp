# -*- coding: utf-8 -*-
"""
Main MCP server file with tool definitions for ADM1 simulation
"""
import json
import os
import sys
import traceback  # Import traceback for better error reporting
import math # Needed for isclose
import numpy as np
import platform  # Add platform for OS detection
import subprocess  # Add subprocess for running commands
from numbers import Number # To check if a value is numeric
# --- QSDsan Imports ---                                                                                                                                                                                                                                                                                                                                                                                                           ┃
from qsdsan import processes as pc
# from qsdsan.utils import load_components # Import necessary QSDsan functions
from mcp.server.fastmcp import FastMCP
from adm1_mcp_server.simulation import run_simulation, create_influent_stream
from adm1_mcp_server.ai_assistant import GeminiClient  # Keep import
from adm1_mcp_server.inhibition import analyze_inhibition
from adm1_mcp_server.stream_analysis import analyze_liquid_stream, analyze_gas_stream, analyze_biomass_yields
from adm1_mcp_server.simulation import create_influent_stream # Needs this function
from adm1_mcp_server.stream_analysis import calculate_charge_balance

from dotenv import load_dotenv

# Load environment variables from .env file
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=env_path, override=True)

# Verify required API key is available
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("Warning: GOOGLE_API_KEY not found. AI assistant functionality will be limited.")
    print("Please copy .env.example to .env and add your Google API key.")
# Define a global state object to store simulation state
class ADM1SimulationState:
    def __init__(self):
        self.influent_values = {}
        self.influent_explanations = {}
        self.kinetic_params = {}
        self.kinetic_explanations = {}
        self.use_kinetics = False
        self.Q = 170.0  # Default Q value
        self.sim_params = [  # Default simulation scenarios
            {'Temp': 308.15, 'HRT': 30.0, 'method': 'BDF'},
            {'Temp': 308.15, 'HRT': 45.0, 'method': 'BDF'},
            {'Temp': 308.15, 'HRT': 60.0, 'method': 'BDF'}
        ]
        self.sim_results = [None, None, None]  # To store (sys, inf, eff, gas) tuples
        self.simulation_time = 150.0  # Default sim time in days
        self.t_step = 0.1  # Default time step in days
        self.ai_recommendations = None  # Store raw AI response if needed
        self.cmps = None # Store the components
        self.tool_responses = {}  # Dictionary to store tool responses by name and timestamp

    def add_tool_response(self, tool_name, response_data, timestamp=None):
        """Store a tool response with metadata"""
        from datetime import datetime

        if timestamp is None:
            timestamp = datetime.now()

        if tool_name not in self.tool_responses:
            self.tool_responses[tool_name] = []

        self.tool_responses[tool_name].append({
            "data": response_data,
            "timestamp": timestamp
        })

# Create a global state instance - MOVED HERE BEFORE COMPONENT INITIALIZATION
simulation_state = ADM1SimulationState()


def setup_windows_env_for_quarto():
    """
    Set up environment variables for Quarto, regardless of platform.
    This ensures Quarto has all the variables it needs to run successfully.
    """
    try:
        # Check if we have required environment variables, regardless of platform
        required_vars = ['APPDATA', 'LOCALAPPDATA', 'USERPROFILE']
        missing_vars = [var for var in required_vars if var not in os.environ]
        
        # If no variables are missing, we're good to go
        if not missing_vars:
            log_debug("All required environment variables are present")
            return True
            
        # If we're on Windows, we should get them from the system
        # This case shouldn't happen normally, but handle it anyway
        if platform.system() == "Windows":
            log_debug(f"Running on Windows, but missing environment variables: {missing_vars}")
            
            # Try to set them using standard Windows locations if we can infer them
            if 'USERPROFILE' in os.environ and 'APPDATA' not in os.environ:
                os.environ['APPDATA'] = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming')
                log_debug(f"Set APPDATA to {os.environ['APPDATA']}")
                
            if 'USERPROFILE' in os.environ and 'LOCALAPPDATA' not in os.environ:
                os.environ['LOCALAPPDATA'] = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local')
                log_debug(f"Set LOCALAPPDATA to {os.environ['LOCALAPPDATA']}")
                
            # If USERPROFILE is missing, try to get it from the current user's home directory
            if 'USERPROFILE' not in os.environ:
                import getpass
                username = getpass.getuser()
                if os.path.exists(f"C:\\Users\\{username}"):
                    os.environ['USERPROFILE'] = f"C:\\Users\\{username}"
                    log_debug(f"Set USERPROFILE to {os.environ['USERPROFILE']}")
            
            # Check again if we're good now
            missing_vars = [var for var in required_vars if var not in os.environ]
            if not missing_vars:
                return True
                
        # For WSL, we need to get them from Windows
        if platform.system() == "Linux" and "microsoft" in platform.uname().release.lower():
            log_debug("Running in WSL, setting up Windows environment variables for Quarto")
            
            # Try to get Windows environment variables
            try:
                # Get APPDATA
                if 'APPDATA' not in os.environ:
                    cmd = ["powershell.exe", "-Command", "echo $env:APPDATA"]
                    app_data = subprocess.check_output(cmd).decode('utf-8').strip()
                    if app_data:
                        os.environ["APPDATA"] = app_data
                        log_debug(f"Set APPDATA to {app_data}")
                
                # Get LOCALAPPDATA
                if 'LOCALAPPDATA' not in os.environ:
                    cmd = ["powershell.exe", "-Command", "echo $env:LOCALAPPDATA"]
                    local_app_data = subprocess.check_output(cmd).decode('utf-8').strip()
                    if local_app_data:
                        os.environ["LOCALAPPDATA"] = local_app_data
                        log_debug(f"Set LOCALAPPDATA to {local_app_data}")
                
                # Get USERPROFILE
                if 'USERPROFILE' not in os.environ:
                    cmd = ["powershell.exe", "-Command", "echo $env:USERPROFILE"]
                    user_profile = subprocess.check_output(cmd).decode('utf-8').strip()
                    if user_profile:
                        os.environ["USERPROFILE"] = user_profile
                        log_debug(f"Set USERPROFILE to {user_profile}")
                
                return True
            except Exception as e:
                log_debug(f"Failed to get Windows environment variables: {e}")
        
        # If we reached here, we couldn't set some variables
        log_debug(f"Warning: Could not set all required environment variables: {missing_vars}")
        return False
        
    except Exception as e:
        log_debug(f"Error setting up environment variables: {e}")
        return False

def log_debug(message):
    # Log debug message to stderr without affecting JSON response
    sys.stderr.write(f"DEBUG: {message}\n")
    sys.stderr.flush()
# --- Initialize QSDsan Components and Thermo ---
sys.stderr.write("DEBUG: Initializing QSDsan components and thermo...\n")
sys.stderr.flush()
try:
    # Load default components suitable for ADM1
    cmps_loaded = pc.create_adm1_cmps()
    sys.stderr.write("DEBUG: QSDsan thermo package set successfully.\n")
    sys.stderr.flush()
    simulation_state.cmps = cmps_loaded # Now this will work because simulation_state exists
except Exception as e_thermo:
    sys.stderr.write(f"ERROR: Failed to initialize QSDsan components/thermo: {e_thermo}\n")
    sys.stderr.flush()
    traceback.print_exc(file=sys.stderr)
# --- End QSDsan Init ---

# --- Initialize GeminiClient ONCE ---
sys.stderr.write("DEBUG: Initializing GLOBAL GeminiClient instance...\n")
sys.stderr.flush()
try:
    ai_client_global = GeminiClient()  # Initialize the global GeminiClient
    if not ai_client_global.client:
        sys.stderr.write("ERROR: Global GeminiClient failed to initialize properly (API key issue?).\n")
        sys.stderr.flush()
        # Decide how to handle this - maybe tools should check ai_client_global before proceeding
        # For now, tools will likely fail if they try to use it.
    else:
        sys.stderr.write("DEBUG: Global GeminiClient initialized successfully.\n")
        sys.stderr.flush()
except Exception as e_init:
    sys.stderr.write(f"ERROR: Exception during global GeminiClient initialization: {e_init}\n")
    sys.stderr.flush()
    ai_client_global = None  # Ensure it's None if init failed

# Create the MCP server
mcp = FastMCP("adm1-simulation")

# Define paths for report generation
SERVER_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(SERVER_ROOT, "templates", "enhanced_template.ipynb")
PROFESSIONAL_TEMPLATE_PATH = os.path.join(SERVER_ROOT, "templates", "professional_template.ipynb")
OUTPUT_DIR = os.path.join(SERVER_ROOT, "generated_reports")
CSS_PATH = os.path.join(SERVER_ROOT, "templates", "styles.css")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Log template paths for debugging
log_debug(f"TEMPLATE_PATH: {TEMPLATE_PATH}")
log_debug(f"PROFESSIONAL_TEMPLATE_PATH: {PROFESSIONAL_TEMPLATE_PATH}")
log_debug(f"OUTPUT_DIR: {OUTPUT_DIR}")
log_debug(f"CSS_PATH: {CSS_PATH}")

# Decorator to capture tool responses
import functools
from datetime import datetime

def capture_response(func):
    """Decorator to capture tool responses in simulation state"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        try:
            # Extract tool name from function
            tool_name = func.__name__
            # Store response in simulation state
            simulation_state.add_tool_response(tool_name, response)
            sys.stderr.write(f"DEBUG: Captured response from tool {tool_name}\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"DEBUG ERROR: Failed to capture tool response: {e}\n")
            sys.stderr.flush()
        return response
    return wrapper


# ADM1SimulationState class and simulation_state instance defined above


@mcp.tool()
@capture_response
def describe_feedstock(feedstock_description: str) -> str:
    """
    Generate ADM1 state variables from a natural language description of feedstock.
    """
    try:
        sys.stderr.write("DEBUG: Tool describe_feedstock called.\n")
        sys.stderr.flush()

        if not ai_client_global or not ai_client_global.client:
            sys.stderr.write("DEBUG ERROR: Global AI client not available or not initialized.\n")
            sys.stderr.flush()
            return json.dumps({
                "success": False,
                "message": "AI Assistant (GeminiClient) is not available or failed to initialize. Check server logs and API key."
            }, indent=2)

        sys.stderr.write("DEBUG: Using global AI client to get recommendations.\n")
        sys.stderr.flush()
        response = ai_client_global.get_adm1_recommendations(
            feedstock_description,
            include_kinetics=False
        )

        # --- ADDED DEBUG WITH UNICODE HANDLING ---
        try:
            # Use repr() to safely print the response without unicode encoding issues
            sys.stderr.write(f"DEBUG: Value of 'response' received from get_adm1_recommendations: {repr(response[:200])}...\n")  # Print safe representation of response (truncated)
            sys.stderr.flush()
        except Exception as e_print:
            sys.stderr.write(f"DEBUG: Error printing response: {e_print}\n")
            sys.stderr.flush()

        if not response:  # Check if response is None or empty
            sys.stderr.write("DEBUG: No response content received from AI client call (response is None or empty).\n")
            sys.stderr.flush()
            # Return the specific error message seen by the user
            return json.dumps({
                "success": False,
                "message": "AI Assistant did not return recommendations. Check API key, quotas, or try rephrasing."
            }, indent=2)

        # Store the raw recommendations (optional)
        simulation_state.ai_recommendations = response

        # Parse the response
        sys.stderr.write("DEBUG: Parsing AI response...\n")
        sys.stderr.flush()
        try:
            # Use the global client instance for parsing as well
            feedstock_values, feedstock_explanations, _, _ = ai_client_global.parse_recommendations(
                response,
                include_kinetics=False
            )
        except ValueError as e_parse:  # Catch specific parsing error
            sys.stderr.write(f"DEBUG ERROR: Failed to parse AI response: {e_parse}\n")
            sys.stderr.flush()
            return json.dumps({
                "success": False,
                "message": f"Failed to parse AI response: {e_parse}",
                "raw_response": response  # Include raw response for debugging
            }, indent=2)

        sys.stderr.write(f"DEBUG: Parsed values: {len(feedstock_values) if feedstock_values else 0}\n")
        sys.stderr.flush()

        # Store in global state
        simulation_state.influent_values.update(feedstock_values)
        simulation_state.influent_explanations.update(feedstock_explanations)
        # Reset kinetics if only feedstock is described now
        simulation_state.kinetic_params = {}
        simulation_state.kinetic_explanations = {}
        simulation_state.use_kinetics = False

        # Format response for LLM
        result = {
            "success": True,
            "message": "Successfully generated ADM1 state variables from feedstock description.",
            "state_variables": feedstock_values,
            "explanations": feedstock_explanations
        }

        return json.dumps(result, indent=2)

    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in describe_feedstock: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)  # Print full traceback to server console
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)

@mcp.tool()
@capture_response
def validate_feedstock_charge_balance(relative_tolerance: float = None) -> str:
    """
    Validates the electroneutrality of the current feedstock definition by
    comparing the sum of positive (cation) and negative (anion) equivalents
    derived *only* from the defined ADM1 state variable concentrations (e.g., S_cat,
    S_an, VFAs, S_IN, S_IC) and their predefined charges in the component library.

    **Important Note:** This calculation EXCLUDES the contribution of H+ and OH- ions
    and does NOT account for pH-dependent dissociation of weak acids/bases. It serves
    as a consistency check for the defined strong ions against other charged components.
    A significant imbalance suggests the true equilibrium pH might differ from any
    assumed pH used to define the components (like VFAs).

    Args:
        relative_tolerance: Allowable relative difference between cation and anion
                        equivalents before flagging an imbalance (default 0.05 for 5%).

    Returns:
        JSON string containing:
        - success (bool): True if calculation succeeded.
        - is_balanced (bool): True if relative difference is within tolerance.
        - cation_equivalents_eq_m3 (float): Sum of positive equivalents (eq/m³).
        - anion_equivalents_eq_m3 (float): Sum of absolute negative equivalents (eq/m³).
        - relative_difference (float): Absolute difference / max(abs(cat), abs(an)).
        - message (str): Summary message indicating balance status and values.
    """
    # Use sys.stderr for debug output to avoid interfering with JSON response
    sys.stderr.write("DEBUG: Tool validate_feedstock_charge_balance called.\n")
    sys.stderr.flush()

    try:
        # Apply default value if None or not provided
        if relative_tolerance is None:
            relative_tolerance = 0.05

        # Check if influent values exist in state
        if not simulation_state.influent_values:
            return json.dumps({"success": False, "message": "Influent state variables not set. Cannot validate."}, indent=2)

        # Try to load components if not already available
        if not simulation_state.cmps:
            try:
                sys.stderr.write("DEBUG: Components not found in state, attempting to load...\n")
                sys.stderr.flush()
                cmps_loaded = pc.create_adm1_cmps()
                simulation_state.cmps = cmps_loaded
                sys.stderr.write("DEBUG: Successfully loaded components on demand.\n")
                sys.stderr.flush()
            except Exception as e_load:
                sys.stderr.write(f"DEBUG ERROR: Failed to load components on demand: {str(e_load)}\n")
                sys.stderr.flush()
                return json.dumps({
                    "success": False,
                    "message": "Component definitions not available and could not be loaded. Cannot validate charge balance."
                }, indent=2)

        # Calculate charge balance using the helper function
        cations_eq_m3, anions_eq_m3 = calculate_charge_balance(
            simulation_state.influent_values,
            simulation_state.cmps
        )

        if cations_eq_m3 is None or anions_eq_m3 is None:
            return json.dumps({
                "success": False,
                "is_balanced": None,
                "cation_equivalents": None,
                "anion_equivalents": None,
                "imbalance_ratio": None,
                "message": "Failed to calculate charge balance due to errors during component processing. Check server logs."
            }, indent=2)

        # Check for balance using relative tolerance
        is_balanced = False
        imbalance_ratio = 0.0
        denominator = max(abs(cations_eq_m3), abs(anions_eq_m3))

        if denominator > 1e-9: # Avoid division by zero if both are zero/tiny
            imbalance_ratio = abs(cations_eq_m3 - anions_eq_m3) / denominator
            if imbalance_ratio <= relative_tolerance:
                is_balanced = True
        elif abs(cations_eq_m3 - anions_eq_m3) < 1e-9: # If both are near zero, consider it balanced
            is_balanced = True
            imbalance_ratio = 0.0

        # Formulate message
        if is_balanced:
            message = (f"Feedstock appears reasonably charge balanced. "
                      f"(Cations: {cations_eq_m3:.3f} eq/m³, Anions: {anions_eq_m3:.3f} eq/m³, "
                      f"Rel. Diff.: {imbalance_ratio:.2%})")
        else:
            message = (f"Warning: Potential feedstock charge imbalance detected. "
                      f"(Cations: {cations_eq_m3:.3f} eq/m³, Anions: {anions_eq_m3:.3f} eq/m³, "
                      f"Rel. Diff.: {imbalance_ratio:.2%}). Check definition of S_cat/S_an and charged components.")

        # Create and return the JSON response
        result = {
            "success": True,
            "is_balanced": is_balanced,
            "cation_equivalents_eq_m3": cations_eq_m3,
            "anion_equivalents_eq_m3": anions_eq_m3,
            "relative_difference": imbalance_ratio,
            "message": message
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in validate_feedstock_charge_balance: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(stderr=True)
        return json.dumps({"success": False, "error": f"An unexpected error occurred: {str(e)}"}, indent=2)

@mcp.tool()
@capture_response
def describe_kinetics(feedstock_description: str) -> str:
    """
    Generate kinetic parameters based on feedstock description. Also updates state vars.

    Args:
        feedstock_description: Natural language description of the feedstock

    Returns:
        JSON string with kinetic parameters, state variables, and explanations
    """
    try:
        sys.stderr.write("DEBUG: Tool describe_kinetics called.\n")
        sys.stderr.flush()

        # --- Use the GLOBAL AI client ---
        if not ai_client_global or not ai_client_global.client:
            sys.stderr.write("DEBUG ERROR: Global AI client not available or not initialized.\n")
            sys.stderr.flush()
            return json.dumps({
                "success": False,
                "message": "AI Assistant (GeminiClient) is not available or failed to initialize. Check server logs and API key."
            }, indent=2)

        sys.stderr.write("DEBUG: Using global AI client to get recommendations (with kinetics).\n")
        sys.stderr.flush()
        response = ai_client_global.get_adm1_recommendations(
            feedstock_description,
            include_kinetics=True
        )

        sys.stderr.write(f"DEBUG: Got response: {response is not None}\n")
        sys.stderr.flush()
        if response:
            sys.stderr.write(f"DEBUG: Response preview: {repr(response[:100])}...\n")
            sys.stderr.flush()

        if not response:
            sys.stderr.write("DEBUG: No response from AI client call.\n")
            sys.stderr.flush()
            return json.dumps({
                "success": False,
                "message": "AI Assistant did not return recommendations. Check API key, quotas, or try rephrasing."
            }, indent=2)

        # Store the raw recommendations (optional)
        simulation_state.ai_recommendations = response

        # Parse the response with kinetics
        sys.stderr.write("DEBUG: Parsing AI response (with kinetics)...\n")
        sys.stderr.flush()
        try:
            feedstock_values, feedstock_explanations, kinetic_values, kinetic_explanations = ai_client_global.parse_recommendations(
                response,
                include_kinetics=True
            )
        except ValueError as e_parse:  # Catch specific parsing error
            sys.stderr.write(f"DEBUG ERROR: Failed to parse AI response: {e_parse}\n")
            sys.stderr.flush()
            return json.dumps({
                "success": False,
                "message": f"Failed to parse AI response: {e_parse}",
                "raw_response": response  # Include raw response for debugging
            }, indent=2)

        sys.stderr.write(f"DEBUG: Parsed values: {len(feedstock_values)} feedstock, {len(kinetic_values)} kinetics\n")
        sys.stderr.flush()

        # Store in global state
        simulation_state.influent_values.update(feedstock_values)
        simulation_state.influent_explanations.update(feedstock_explanations)
        simulation_state.kinetic_params.update(kinetic_values)
        simulation_state.kinetic_explanations.update(kinetic_explanations)
        simulation_state.use_kinetics = True  # Flag that kinetics were provided

        # Format response for LLM
        result = {
            "success": True,
            "message": "Successfully generated kinetic parameters and state variables.",
            "state_variables": feedstock_values,
            "kinetic_parameters": kinetic_values,
            "kinetic_explanations": kinetic_explanations  # Include kinetic explanations
        }

        return json.dumps(result, indent=2)
    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in describe_kinetics: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)  # Print full traceback to server console
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)


# --- Added import dependencies for report generation ---
import papermill as pm
import nbformat
from nbconvert import HTMLExporter
import uuid
import platform

# Define function directly instead of importing
def setup_windows_env_for_quarto():
    """
    Set up environment variables for Quarto, regardless of platform.
    This ensures Quarto has all the variables it needs to run successfully.
    """
    try:
        # Check if we have required environment variables, regardless of platform
        required_vars = ['APPDATA', 'LOCALAPPDATA', 'USERPROFILE']
        missing_vars = [var for var in required_vars if var not in os.environ]
        
        # If no variables are missing, we're good to go
        if not missing_vars:
            log_debug("All required environment variables are present")
            return True
            
        # If we're on Windows, we should get them from the system
        # This case shouldn't happen normally, but handle it anyway
        if platform.system() == "Windows":
            log_debug(f"Running on Windows, but missing environment variables: {missing_vars}")
            
            # Try to set them using standard Windows locations if we can infer them
            if 'USERPROFILE' in os.environ and 'APPDATA' not in os.environ:
                os.environ['APPDATA'] = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming')
                log_debug(f"Set APPDATA to {os.environ['APPDATA']}")
                
            if 'USERPROFILE' in os.environ and 'LOCALAPPDATA' not in os.environ:
                os.environ['LOCALAPPDATA'] = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local')
                log_debug(f"Set LOCALAPPDATA to {os.environ['LOCALAPPDATA']}")
                
            # If USERPROFILE is missing, try to get it from the current user's home directory
            if 'USERPROFILE' not in os.environ:
                import getpass
                username = getpass.getuser()
                if os.path.exists(f"C:\\Users\\{username}"):
                    os.environ['USERPROFILE'] = f"C:\\Users\\{username}"
                    log_debug(f"Set USERPROFILE to {os.environ['USERPROFILE']}")
            
            # Check again if we're good now
            missing_vars = [var for var in required_vars if var not in os.environ]
            if not missing_vars:
                return True
                
        # For WSL, we need to get them from Windows
        if platform.system() == "Linux" and "microsoft" in platform.uname().release.lower():
            log_debug("Running in WSL, setting up Windows environment variables for Quarto")
            
            # Try to get Windows environment variables
            try:
                # Get APPDATA
                if 'APPDATA' not in os.environ:
                    cmd = ["powershell.exe", "-Command", "echo $env:APPDATA"]
                    app_data = subprocess.check_output(cmd).decode('utf-8').strip()
                    if app_data:
                        os.environ["APPDATA"] = app_data
                        log_debug(f"Set APPDATA to {app_data}")
                
                # Get LOCALAPPDATA
                if 'LOCALAPPDATA' not in os.environ:
                    cmd = ["powershell.exe", "-Command", "echo $env:LOCALAPPDATA"]
                    local_app_data = subprocess.check_output(cmd).decode('utf-8').strip()
                    if local_app_data:
                        os.environ["LOCALAPPDATA"] = local_app_data
                        log_debug(f"Set LOCALAPPDATA to {local_app_data}")
                
                # Get USERPROFILE
                if 'USERPROFILE' not in os.environ:
                    cmd = ["powershell.exe", "-Command", "echo $env:USERPROFILE"]
                    user_profile = subprocess.check_output(cmd).decode('utf-8').strip()
                    if user_profile:
                        os.environ["USERPROFILE"] = user_profile
                        log_debug(f"Set USERPROFILE to {user_profile}")
                
                return True
            except Exception as e:
                log_debug(f"Failed to get Windows environment variables: {e}")
        
        # If we reached here, we couldn't set some variables
        log_debug(f"Warning: Could not set all required environment variables: {missing_vars}")
        return False
        
    except Exception as e:
        log_debug(f"Error setting up environment variables: {e}")
        return False

from IPython.display import Markdown

@mcp.tool()
@capture_response
def set_flow_parameters(flow_rate: float, simulation_time: float, time_step: float) -> str:
    """
    Set the influent flow rate and other parameters.

    Args:
        flow_rate: Flow rate (m³/d)
        simulation_time: Simulation time (days)
        time_step: Time step (days)

    Returns:
        Confirmation message
    """
    try:
        # Validate inputs
        if flow_rate <= 0:
            return json.dumps({
                "success": False,
                "message": "Flow rate must be positive."
            }, indent=2)

        if simulation_time <= 0:
            return json.dumps({
                "success": False,
                "message": "Simulation time must be positive."
            }, indent=2)

        if time_step <= 0 or time_step > simulation_time:
            return json.dumps({
                "success": False,
                "message": "Time step must be positive and less than simulation time."
            }, indent=2)

        # Update the simulation state
        simulation_state.Q = flow_rate
        simulation_state.simulation_time = simulation_time
        simulation_state.t_step = time_step

        return json.dumps({
            "success": True,
            "message": "Flow parameters set successfully.",
            "parameters": {
                "flow_rate": flow_rate,
                "simulation_time": simulation_time,
                "time_step": time_step
            }
        }, indent=2)
    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in set_flow_parameters: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)


@mcp.tool()
@capture_response
def set_reactor_parameters(reactor_index: int, temperature: float, hrt: float, integration_method: str) -> str:
    """
    Set parameters for a specific reactor simulation.

    Args:
        reactor_index: Reactor simulation index (1, 2, or 3)
        temperature: Temperature (K)
        hrt: Hydraulic retention time (days)
        integration_method: Integration method (e.g., "BDF", "RK45")

    Returns:
        Confirmation message
    """
    try:
        # Validate inputs
        if reactor_index < 1 or reactor_index > 3:
            return json.dumps({
                "success": False,
                "message": "Reactor index must be 1, 2, or 3."
            }, indent=2)

        if temperature < 273.15 or temperature > 373.15:  # Check reasonable temp range
            return json.dumps({
                "success": False,
                "message": "Temperature must be between 0°C (273.15 K) and 100°C (373.15 K)."
            }, indent=2)

        if hrt <= 0:
            return json.dumps({
                "success": False,
                "message": "HRT must be positive."
            }, indent=2)

        # Validate integration method
        valid_methods = ["BDF", "RK45", "RK23", "DOP853", "Radau", "LSODA"]
        if integration_method not in valid_methods:
            return json.dumps({
                "success": False,
                "message": f"Integration method must be one of: {', '.join(valid_methods)}."
            }, indent=2)

        # Update the simulation parameters for the specified reactor
        idx = reactor_index - 1

        # Create parameter dictionary
        params = {
            'Temp': temperature,
            'HRT': hrt,
            'method': integration_method
        }

        # Update state
        simulation_state.sim_params[idx] = params

        return json.dumps({
            "success": True,
            "message": f"Reactor {reactor_index} parameters set successfully.",
            "parameters": params
        }, indent=2)
    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in set_reactor_parameters: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)


@mcp.tool()
@capture_response
def run_simulation_tool() -> str:  # Renamed to avoid conflict with imported run_simulation
    """
    Run the ADM1 simulation(s) with the current parameters.

    Returns:
        Success/failure message for each simulation scenario.
    """
    sys.stderr.write("DEBUG: Tool run_simulation_tool called.\n")
    sys.stderr.flush()
    try:
        # Validate that we have influent values
        if not simulation_state.influent_values:
            sys.stderr.write("DEBUG: No influent values found in state.\n")
            sys.stderr.flush()
            return json.dumps({
                "success": False,
                "message": "Influent state variables are not set. Use describe_feedstock or describe_kinetics first."
            }, indent=2)

        # Run simulations for each reactor scenario
        results_summary = []
        simulation_state.sim_results = [None] * len(simulation_state.sim_params)  # Reset results

        for i, params in enumerate(simulation_state.sim_params):
            sys.stderr.write(f"DEBUG: Starting simulation for reactor scenario {i + 1} with params: {params}\n")
            sys.stderr.flush()
            try:
                # Call the simulation logic from simulation.py
                sim_result_tuple = run_simulation(
                    Q=simulation_state.Q,
                    Temp=params['Temp'],
                    HRT=params['HRT'],
                    concentrations=simulation_state.influent_values,
                    kinetic_params=simulation_state.kinetic_params,  # Pass current kinetics
                    simulation_time=simulation_state.simulation_time,
                    t_step=simulation_state.t_step,
                    method=params['method'],
                    use_kinetics=simulation_state.use_kinetics  # Use flag
                )

                # Store the full result tuple (sys, inf, eff, gas)
                simulation_state.sim_results[i] = sim_result_tuple
                sys.stderr.write(f"DEBUG: Simulation {i + 1} completed successfully.\n")
                sys.stderr.flush()
                results_summary.append({
                    "reactor_scenario": i + 1,
                    "success": True,
                    "parameters": params,
                    "message": "Simulation successful."
                })

            except Exception as e_sim:
                sys.stderr.write(f"DEBUG ERROR: Simulation scenario {i + 1} failed: {str(e_sim)}\n")
                sys.stderr.flush()
                traceback.print_exc(file=sys.stderr)  # Print detailed error to stderr
                simulation_state.sim_results[i] = None  # Ensure failed result is None
                results_summary.append({
                    "reactor_scenario": i + 1,
                    "success": False,
                    "parameters": params,
                    "error": f"Simulation failed: {str(e_sim)}"
                })

        # Check if any simulations succeeded
        overall_success = any(r["success"] for r in results_summary)

        return json.dumps({
            "success": overall_success,
            "message": "Simulations execution finished. Check results for individual scenario outcomes.",
            "results": results_summary
        }, indent=2)

    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in run_simulation_tool: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred during simulation execution: {str(e)}"
        }, indent=2)


@mcp.tool()
@capture_response
def get_stream_properties(stream_type: str) -> str:
    """
    Get detailed properties of a specified stream from the simulation results.

    Args:
        stream_type: Stream type ("influent", "effluent1", "effluent2", "effluent3", "biogas1", "biogas2", "biogas3")

    Returns:
        JSON string with detailed stream properties.
    """
    sys.stderr.write(f"DEBUG: Tool get_stream_properties called for type: {stream_type}\n")
    sys.stderr.flush()
    try:
        if stream_type == "influent":
            # Recreate influent stream based on current state for consistency
            if not simulation_state.influent_values:
                return json.dumps({"success": False, "message": "Influent state variables not set."}, indent=2)

            inf = create_influent_stream(
                Q=simulation_state.Q,
                Temp=simulation_state.sim_params[0]['Temp'],  # Use Temp from first scenario as default
                concentrations=simulation_state.influent_values
            )
            properties = analyze_liquid_stream(inf, include_components=True)  # Include components for influent
            message = "Influent properties retrieved successfully."

        elif stream_type.startswith("effluent") or stream_type.startswith("biogas"):
            is_effluent = stream_type.startswith("effluent")
            prefix_len = len("effluent") if is_effluent else len("biogas")
            try:
                reactor_idx = int(stream_type[prefix_len:]) - 1
                if not (0 <= reactor_idx < len(simulation_state.sim_results)):
                    raise ValueError("Invalid reactor index")
            except ValueError:
                valid_types = [f"{'effluent' if is_effluent else 'biogas'}{i + 1}" for i in
                               range(len(simulation_state.sim_params))]
                return json.dumps({
                    "success": False,
                    "message": f"Invalid stream type. Use one of: {', '.join(valid_types)}"
                }, indent=2)

            sim_result_tuple = simulation_state.sim_results[reactor_idx]
            if not sim_result_tuple:
                return json.dumps({
                    "success": False,
                    "message": f"Simulation scenario {reactor_idx + 1} has not been run successfully or results are missing."
                }, indent=2)

            _, inf, eff, gas = sim_result_tuple  # Unpack result

            if is_effluent:
                stream_to_analyze = eff
                properties = analyze_liquid_stream(stream_to_analyze, include_components=True)  # Include components for effluent
                # Calculate yields as well for effluent
                yields = analyze_biomass_yields(inf, eff)
                properties["yields"] = yields  # Add yields to the properties dict
                message = f"Effluent {reactor_idx + 1} properties retrieved successfully."
            else:  # Biogas
                stream_to_analyze = gas
                properties = analyze_gas_stream(stream_to_analyze)
                message = f"Biogas {reactor_idx + 1} properties retrieved successfully."

        else:
            valid_types = ["influent"] + [f"effluent{i + 1}" for i in range(len(simulation_state.sim_params))] + [
                f"biogas{i + 1}" for i in range(len(simulation_state.sim_params))]
            return json.dumps({
                "success": False,
                "message": f"Invalid stream type. Use one of: {', '.join(valid_types)}"
            }, indent=2)

        # Combine results into the final JSON output
        return json.dumps({
            "success": properties.get("success", False),
            "message": message if properties.get("success", False) else properties.get("message", "Error analyzing stream."),
            "stream_type": stream_type,
            "properties": properties  # Contains the detailed analysis
        }, indent=2, default=lambda x: str(x) if isinstance(x, (np.ndarray, np.generic)) else x)  # Handle numpy types

    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in get_stream_properties: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)


@mcp.tool()
@capture_response
def get_inhibition_analysis(simulation_index: int) -> str:
    """
    Get process health and inhibition analysis for a specific simulation scenario.

    Args:
        simulation_index: Simulation scenario index (1, 2, or 3)

    Returns:
        JSON string with detailed inhibition analysis and recommendations.
    """
    sys.stderr.write(f"DEBUG: Tool get_inhibition_analysis called for index: {simulation_index}\n")
    sys.stderr.flush()
    try:
        # Validate simulation index
        if not (1 <= simulation_index <= len(simulation_state.sim_params)):
            return json.dumps({"success": False, "message": f"Simulation index must be between 1 and {len(simulation_state.sim_params)}."}, indent=2)

        idx = simulation_index - 1

        # Check if the simulation has been run successfully
        sim_result_tuple = simulation_state.sim_results[idx]
        if not sim_result_tuple:
            return json.dumps({
                "success": False,
                "message": f"Simulation scenario {simulation_index} has not been run successfully or results are missing."
            }, indent=2)

        # Get inhibition analysis using the result tuple
        analysis = analyze_inhibition(sim_result_tuple)

        return json.dumps({
            "success": analysis.get("success", False),
            "message": "Inhibition analysis completed successfully." if analysis.get("success", False) else analysis.get("message", "Error analyzing inhibition."),
            "simulation_index": simulation_index,
            "analysis": analysis
        }, indent=2, default=lambda x: str(x) if isinstance(x, (np.ndarray, np.generic)) else x)  # Handle numpy types

    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in get_inhibition_analysis: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)


@mcp.tool()
@capture_response
def get_biomass_yields(simulation_index: int) -> str:
    """
    Calculate biomass yields from a specific simulation scenario.

    Args:
        simulation_index: Simulation scenario index (1, 2, or 3)

    Returns:
        JSON string with VSS and TSS yields.
    """
    sys.stderr.write(f"DEBUG: Tool get_biomass_yields called for index: {simulation_index}\n")
    sys.stderr.flush()
    try:
        # Validate simulation index
        if not (1 <= simulation_index <= len(simulation_state.sim_params)):
            return json.dumps({"success": False, "message": f"Simulation index must be between 1 and {len(simulation_state.sim_params)}."}, indent=2)

        idx = simulation_index - 1

        # Check if the simulation has been run successfully
        sim_result_tuple = simulation_state.sim_results[idx]
        if not sim_result_tuple:
            return json.dumps({
                "success": False,
                "message": f"Simulation scenario {simulation_index} has not been run successfully or results are missing."
            }, indent=2)

        # Get streams from the simulation results
        _, inf, eff, _ = sim_result_tuple  # Unpack result

        # Calculate yields
        yields = analyze_biomass_yields(inf, eff)

        return json.dumps({
            "success": yields.get("success", False),
            "message": "Biomass yields calculated successfully." if yields.get("success", False) else yields.get("message", "Error calculating biomass yields."),
            "simulation_index": simulation_index,
            "yields": yields
        }, indent=2, default=lambda x: str(x) if isinstance(x, (np.ndarray, np.generic)) else x)  # Handle numpy types

    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in get_biomass_yields: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)


@mcp.tool()
@capture_response
def reset_simulation() -> str:
    """
    Reset the simulation parameters and results to defaults.

    Returns:
        Confirmation message with default parameters.
    """
    sys.stderr.write("DEBUG: Tool reset_simulation called.\n")
    sys.stderr.flush()
    try:
        # Create a new state object, effectively resetting everything
        global simulation_state
        simulation_state = ADM1SimulationState()
        sys.stderr.write("DEBUG: Simulation state reset to defaults.\n")
        sys.stderr.flush()

        return json.dumps({
            "success": True,
            "message": "Simulation reset to default parameters.",
            "default_parameters": {
                "Q": simulation_state.Q,
                "simulation_time": simulation_state.simulation_time,
                "t_step": simulation_state.t_step,
                "sim_params": simulation_state.sim_params
            }
        }, indent=2)
    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in reset_simulation: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)

@mcp.tool()
@capture_response
def check_nutrient_balance(simulation_index: int, element: str, inhibition_threshold: float, mass_balance_tolerance: float) -> str:
    """
    Checks a specific simulation result for nutrient limitation based on
    inhibition metrics and input/output mass balance for the specified element.

    Args:
        simulation_index: Which simulation scenario to check (1, 2, or 3).
        element: The element symbol to check ("N" or "P").
        inhibition_threshold: Inhibition percentage above which limitation is flagged (default 80.0).
        mass_balance_tolerance: Ratio (Mass Out / Mass In) above which imbalance is flagged (default 1.05).

    Returns:
        JSON string indicating if limitation or imbalance was detected.
    """
    sys.stderr.write(f"DEBUG: Tool check_nutrient_balance called for index: {simulation_index}, element: {element}\n")
    sys.stderr.flush()
    try:
        # Apply default values if None or not provided
        if inhibition_threshold is None:
            inhibition_threshold = 80.0
        if mass_balance_tolerance is None:
            mass_balance_tolerance = 1.05
        # Validate simulation index
        if not (1 <= simulation_index <= len(simulation_state.sim_params)):
            return json.dumps({"success": False, "message": f"Simulation index must be between 1 and {len(simulation_state.sim_params)}."}, indent=2)
        idx = simulation_index - 1

        # Validate element
        if element not in ["N", "P"]:
             return json.dumps({"success": False, "message": "Element must be 'N' or 'P'."}, indent=2)

        # Check if the simulation has been run successfully
        sim_result_tuple = simulation_state.sim_results[idx]
        if not sim_result_tuple:
            return json.dumps({
                "success": False,
                "message": f"Simulation scenario {simulation_index} has not been run successfully or results are missing."
            }, indent=2)

        # Check if influent values exist
        if not simulation_state.influent_values:
             return json.dumps({"success": False, "message": "Influent state variables not set."}, indent=2)

        sys, inf_obj, eff_obj, gas_obj = sim_result_tuple

        # 1. Get Inhibition Analysis
        inhibition_results = analyze_inhibition(sim_result_tuple)
        limitation_detected = False
        inhibition_value = 0.0
        if inhibition_results.get("success"):
            element_key = f"{element} Limitation"
            # Find the specific inhibition factor
            for factor in inhibition_results.get("inhibition_factors", []):
                if factor.get("type") == element_key:
                    inhibition_value = factor.get("value", 0.0)
                    if inhibition_value >= inhibition_threshold:
                        limitation_detected = True
                    break # Found the element, no need to check further

        # 2. Get Stream Properties and Check Mass Balance
        mass_balance_issue = False
        mass_balance_ratio = 0.0
        try:
            # Analyze influent (use stored values for consistency)
            inf_props = analyze_liquid_stream(inf_obj) # Get flow from simulated obj

            # Analyze effluent
            eff_props = analyze_liquid_stream(eff_obj)

            if inf_props.get("success") and eff_props.get("success"):
                inf_flow = inf_props.get("basic", {}).get("flow", 0.0) # m3/d
                eff_flow = eff_props.get("basic", {}).get("flow", 0.0) # m3/d

                # Get total element concentrations (mg/L = g/m3)
                if element == "N":
                    inf_conc = inf_props.get("nitrogen", {}).get("TN", 0.0)
                    eff_conc = eff_props.get("nitrogen", {}).get("TN", 0.0)
                elif element == "P":
                    inf_conc = inf_props.get("other_nutrients", {}).get("TP", 0.0)
                    eff_conc = eff_props.get("other_nutrients", {}).get("TP", 0.0)
                else: # Should not happen due to validation above
                    inf_conc = 0.0
                    eff_conc = 0.0

                mass_in = inf_flow * inf_conc if inf_conc is not None else 0 # g/d
                mass_out = eff_flow * eff_conc if eff_conc is not None else 0 # g/d (ignoring gas)

                if mass_in is not None and mass_out is not None and mass_in > 1e-9: # Avoid division by zero or near-zero
                    mass_balance_ratio = mass_out / mass_in
                    if mass_balance_ratio > mass_balance_tolerance:
                        mass_balance_issue = True
                elif mass_out is not None and mass_out > 1e-9 and mass_in <= 1e-9:
                    # If N/P is generated from zero input, flag as issue
                    mass_balance_issue = True
                    mass_balance_ratio = float('inf')

        except Exception as e_mb:
            sys.stderr.write(f"DEBUG WARNING: Could not calculate mass balance for element {element}: {e_mb}\n")
            sys.stderr.flush()
            # Proceed without mass balance check if calculation fails

        # 3. Formulate Response Message
        messages = []
        if limitation_detected:
            messages.append(f"High {element} limitation ({inhibition_value:.1f}%) detected.")
        if mass_balance_issue:
            ratio_str = f"{mass_balance_ratio:.2f}" if mass_balance_ratio != float('inf') else "Inf"
            messages.append(f"Mass imbalance ({element} Out/In = {ratio_str}) detected.")

        final_message = " ".join(messages) if messages else f"No significant {element} limitation or mass balance issue detected."

        return json.dumps({
            "success": True,
            "simulation_index": simulation_index,
            "element": element,
            "limitation_detected": limitation_detected,
            "mass_balance_issue": mass_balance_issue,
            "inhibition_value": inhibition_value,
            "mass_balance_ratio": mass_balance_ratio if mass_balance_ratio != float('inf') else "inf",
            "message": final_message
        }, indent=2)

    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in check_nutrient_balance: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({"success": False, "error": f"An unexpected error occurred: {str(e)}"}, indent=2)

@mcp.tool()
@capture_response
def generate_report(simulation_index: int = 1, include_technical_details: bool = True) -> str:
    """
    Generates a professional ADM1 simulation report using results from previously executed tools.
    This tool preserves the educational multi-tool execution flow while providing comprehensive
    documentation of the process and results.

    Args:
        simulation_index: The index (1-3) of the simulation to be reported.
        include_technical_details: Whether to include detailed technical sections.

    Returns:
        Dictionary with success status and paths/URLs to the generated reports.
    """
    log_debug(f"Tool generate_report called for simulation index: {simulation_index}")
    try:
        # Validate simulation index
        if not (1 <= simulation_index <= len(simulation_state.sim_params)):
            return json.dumps({
                "success": False,
                "message": f"Simulation index must be between 1 and {len(simulation_state.sim_params)}."
            }, indent=2)

        # Check if required tools have been run
        required_tool_responses = ['run_simulation_tool']
        missing_tools = []

        for tool_name in required_tool_responses:
            if tool_name not in simulation_state.tool_responses or not simulation_state.tool_responses[tool_name]:
                missing_tools.append(tool_name)

        if missing_tools:
            return json.dumps({
                "success": False,
                "message": f"Cannot generate report. The following tools have not been executed: {', '.join(missing_tools)}."
            }, indent=2)

        # Check if the simulation has been run successfully
        idx = simulation_index - 1
        if simulation_state.sim_results[idx] is None:
            return json.dumps({
                "success": False,
                "message": f"Simulation scenario {simulation_index} has not been run successfully or results are missing."
            }, indent=2)

        # Generate unique ID for this report run
        report_uuid = str(uuid.uuid4())
        executed_notebook_path = os.path.join(OUTPUT_DIR, f"executed_report_{report_uuid}.ipynb")
        internal_report_path = os.path.join(OUTPUT_DIR, f"internal_report_{report_uuid}.html")
        client_report_path = os.path.join(OUTPUT_DIR, f"client_report_{report_uuid}.html")
        output_css_path = os.path.join(OUTPUT_DIR, "styles.css")

        # Copy the CSS file to the output directory if it doesn't exist
        if not os.path.exists(output_css_path) and os.path.exists(CSS_PATH):
            import shutil
            try:
                shutil.copy2(CSS_PATH, output_css_path)
                log_debug(f"CSS file copied to output directory: {output_css_path}")
            except Exception as e:
                log_debug(f"WARNING: Failed to copy CSS file: {e}")

        # Prepare data for the notebook
        # Prepare parameter dictionaries
        feedstock_params = simulation_state.influent_values.copy()
        kinetic_params = simulation_state.kinetic_params.copy() if simulation_state.use_kinetics else None

        flow_params = {
            "flow_rate": simulation_state.Q,
            "simulation_time": simulation_state.simulation_time,
            "time_step": simulation_state.t_step
        }

        reactor_params = simulation_state.sim_params[idx].copy()

        # --- Execute Notebook with Papermill ---
        log_debug(f"Executing professional template notebook: {PROFESSIONAL_TEMPLATE_PATH}")
        log_debug(f"Parameters being passed to notebook: simulation_index={simulation_index}, include_technical_details={include_technical_details}")

        # Convert datetime objects to strings to make them JSON serializable
        def convert_tool_responses(responses):
            serializable_responses = {}
            for tool_name, tool_responses in responses.items():
                serializable_responses[tool_name] = []
                for response in tool_responses:
                    resp_copy = response.copy()
                    if 'timestamp' in resp_copy and isinstance(resp_copy['timestamp'], datetime):
                        resp_copy['timestamp'] = resp_copy['timestamp'].isoformat()
                    serializable_responses[tool_name].append(resp_copy)
            return serializable_responses

        serializable_tool_responses = convert_tool_responses(simulation_state.tool_responses)

        # Import the output redirector to prevent debug messages from interfering with MCP protocol
        try:
            from output_redirector import OutputRedirector, suppress_notebook_output
            
            # Create a log file for this report
            log_file_path = os.path.join(OUTPUT_DIR, f"report_generation_{report_uuid}.log")
            log_debug(f"Redirecting output to log file: {log_file_path}")
            
            # CRITICAL FIX: Pre-validate module availability before notebook execution
            templates_dir = os.path.join(SERVER_ROOT, "templates")
            required_modules = ['data_parsers.py', 'enhanced_functions.py', 'enhanced_plot_functions.py']
            
            log_debug(f"Pre-validating required modules in: {templates_dir}")
            modules_valid = True
            for module_file in required_modules:
                module_path = os.path.join(templates_dir, module_file)
                if os.path.exists(module_path):
                    log_debug(f"✓ Found required module: {module_file}")
                else:
                    log_debug(f"✗ Missing required module: {module_file} at {module_path}")
                    modules_valid = False
            
            if not modules_valid:
                log_debug("⚠ WARNING: Not all required modules found - report will use fallback functions")
            else:
                log_debug("✓ All required modules validated - professional formatting will be available")
            
            # Use the redirector to capture all debug output during notebook execution
            with OutputRedirector(log_file=log_file_path, capture_stdout=True, capture_stderr=True):
                # CRITICAL FIX: Change working directory to server root for papermill execution
                original_cwd = os.getcwd()
                try:
                    os.chdir(SERVER_ROOT)
                    log_debug(f"Changed working directory to server root: {SERVER_ROOT}")
                    
                    # Execute the notebook using papermill (with output redirected)
                    pm.execute_notebook(
                        input_path=PROFESSIONAL_TEMPLATE_PATH,
                        output_path=executed_notebook_path,
                        parameters=dict(
                            feedstock_params=feedstock_params,
                            kinetic_params=kinetic_params,
                            flow_params=flow_params,
                            reactor_params=reactor_params,
                            simulation_index=simulation_index,
                            tool_responses=serializable_tool_responses,
                            include_technical_details=include_technical_details,
                            notebook_dir=os.path.abspath(os.path.join(SERVER_ROOT, "templates"))  # CRITICAL FIX: Pass absolute templates directory path
                        ),
                        kernel_name='python3',
                        log_output=False  # Changed to False to prevent output mixing with MCP protocol
                    )
                finally:
                    # CRITICAL: Always restore original working directory
                    os.chdir(original_cwd)
                    log_debug(f"Restored working directory to: {original_cwd}")
        except ImportError:
            # Fall back to suppressing output if redirector import fails
            log_debug("Warning: OutputRedirector not available, using fallback output suppression")
            
            # Use the suppress_notebook_output context manager as fallback
            try:
                with suppress_notebook_output():
                    pm.execute_notebook(
                        input_path=PROFESSIONAL_TEMPLATE_PATH,
                        output_path=executed_notebook_path,
                        parameters=dict(
                            feedstock_params=feedstock_params,
                            kinetic_params=kinetic_params,
                            flow_params=flow_params,
                            reactor_params=reactor_params,
                            simulation_index=simulation_index,
                            tool_responses=serializable_tool_responses,
                            include_technical_details=include_technical_details
                        ),
                        kernel_name='python3',
                        log_output=False  # Disabled to prevent MCP protocol interference
                    )
            except NameError:
                # Final fallback - just disable log_output
                pm.execute_notebook(
                    input_path=PROFESSIONAL_TEMPLATE_PATH,
                    output_path=executed_notebook_path,
                    parameters=dict(
                        feedstock_params=feedstock_params,
                        kinetic_params=kinetic_params,
                        flow_params=flow_params,
                        reactor_params=reactor_params,
                        simulation_index=simulation_index,
                        tool_responses=serializable_tool_responses,
                        include_technical_details=include_technical_details
                    ),
                    kernel_name='python3',
                    log_output=False  # Critical: Disabled to prevent MCP protocol interference
                )
        log_debug(f"Executed notebook saved to: {executed_notebook_path}")

        # --- Generate Internal Report (nbconvert) ---
        log_debug(f"Generating internal report (nbconvert): {internal_report_path}")
        
        # Generate internal report with output redirection
        try:
            if 'OutputRedirector' in locals():
                with OutputRedirector(log_file=log_file_path, capture_stdout=True, capture_stderr=True):
                    notebook_node = nbformat.read(executed_notebook_path, as_version=4)
                    exporter = HTMLExporter()
                    exporter.exclude_input = False  # Ensure code is included
                    (body, resources) = exporter.from_notebook_node(notebook_node)
                    with open(internal_report_path, 'w', encoding='utf-8') as f:
                        f.write(body)
            else:
                # Fall back if redirector wasn't imported
                notebook_node = nbformat.read(executed_notebook_path, as_version=4)
                exporter = HTMLExporter()
                exporter.exclude_input = False  # Ensure code is included
                (body, resources) = exporter.from_notebook_node(notebook_node)
                with open(internal_report_path, 'w', encoding='utf-8') as f:
                    f.write(body)
        except Exception as e:
            log_debug(f"Error generating internal report: {e}")
            raise
            
        log_debug(f"Internal report saved to: {internal_report_path}")

        # --- Post-process Internal Report to Clean Artifacts ---
        try:
            def clean_report_output(html_content):
                """
                Post-process HTML report to ensure professional presentation
                """
                import re
                
                # Replace scientific notation with formatted numbers
                def replace_scientific(match):
                    try:
                        value = float(match.group(0))
                        if 1000 <= value < 1000000:
                            return f"{value:,.0f}"
                        elif 0.1 <= value < 1000:
                            return f"{value:.2f}"
                        else:
                            return match.group(0)
                    except:
                        return match.group(0)
                
                html_content = re.sub(r'\d+\.\d+e[+-]?\d+', replace_scientific, html_content)
                
                # Remove debug artifacts
                debug_patterns = [
                    r'✓.*?imported.*?\n',
                    r'✗.*?failed.*?\n',
                    r'IMPORT FAILED.*?\n',
                    r'DEBUG:.*?\n',
                    r'Data processing unavailable',
                    r'Chart generation temporarily unavailable',
                    r'Enhanced .* plot temporarily unavailable'
                ]
                
                for pattern in debug_patterns:
                    html_content = re.sub(pattern, '', html_content, flags=re.IGNORECASE)
                
                return html_content
            
            # Apply post-processing to internal report
            with open(internal_report_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            cleaned_content = clean_report_output(html_content)
            
            with open(internal_report_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            log_debug("Applied post-processing cleanup to internal report")
        except Exception as e:
            log_debug(f"Warning: Post-processing cleanup failed: {e}")

        # --- Generate Client Report (Quarto) ---
        # Assumes Quarto CLI is in the system PATH
        log_debug(f"Generating client report (Quarto): {client_report_path}")
        
        # Setup Windows environment variables for Quarto
        setup_windows_env_for_quarto()
        
        quarto_command = [
            "quarto", "render", executed_notebook_path,
            "--to", "html",
            "--output", os.path.basename(client_report_path)  # Output file name
        ]
        
        # Run quarto in the output directory so it finds the notebook
        try:
            import subprocess
            
            # Use output redirection to prevent Quarto output from interfering with MCP protocol
            if 'OutputRedirector' in locals():
                with OutputRedirector(log_file=log_file_path, capture_stdout=True, capture_stderr=True):
                    result = subprocess.run(
                        quarto_command,
                        cwd=OUTPUT_DIR,
                        capture_output=True,
                        text=True,
                        check=False  # Don't raise exception on failure, check returncode instead
                    )
            else:
                result = subprocess.run(
                    quarto_command,
                    cwd=OUTPUT_DIR,
                    capture_output=True,
                    text=True,
                    check=False  # Don't raise exception on failure, check returncode instead
                )

            if result.returncode != 0:
                log_debug(f"Quarto failed: {result.stderr}")
                log_debug("Falling back to nbconvert for client report")
                
                # Use the redirector if available
                if 'StderrRedirector' in locals():
                    with StderrRedirector(log_file=log_file_path):
                        fallback_exporter = HTMLExporter()
                        fallback_exporter.exclude_input = True  # Hide code for client report
                        (body, resources) = fallback_exporter.from_notebook_node(notebook_node)
                        with open(client_report_path, 'w', encoding='utf-8') as f:
                            f.write(body)
                        
                        # Post-process the client report to clean artifacts
                        try:
                            with open(client_report_path, 'r', encoding='utf-8') as f:
                                client_html_content = f.read()
                            
                            cleaned_client_content = clean_report_output(client_html_content)
                            
                            with open(client_report_path, 'w', encoding='utf-8') as f:
                                f.write(cleaned_client_content)
                            
                            log_debug("Applied post-processing cleanup to client report (quarto fallback stderr)")
                        except Exception as cleanup_e:
                            log_debug(f"Warning: Client report quarto fallback stderr post-processing cleanup failed: {cleanup_e}")
                else:
                    fallback_exporter = HTMLExporter()
                    fallback_exporter.exclude_input = True  # Hide code for client report
                    (body, resources) = fallback_exporter.from_notebook_node(notebook_node)
                    with open(client_report_path, 'w', encoding='utf-8') as f:
                        f.write(body)
                    
                    # Post-process the client report to clean artifacts
                    try:
                        with open(client_report_path, 'r', encoding='utf-8') as f:
                            client_html_content = f.read()
                        
                        cleaned_client_content = clean_report_output(client_html_content)
                        
                        with open(client_report_path, 'w', encoding='utf-8') as f:
                            f.write(cleaned_client_content)
                        
                        log_debug("Applied post-processing cleanup to client report (quarto fallback direct)")
                    except Exception as cleanup_e:
                        log_debug(f"Warning: Client report quarto fallback direct post-processing cleanup failed: {cleanup_e}")
            else:
                log_debug(f"Client report saved to: {client_report_path}")
                
                # --- Post-process Client Report to Clean Artifacts ---
                try:
                    # Apply post-processing to client report
                    if os.path.exists(client_report_path):
                        with open(client_report_path, 'r', encoding='utf-8') as f:
                            client_html_content = f.read()
                        
                        cleaned_client_content = clean_report_output(client_html_content)
                        
                        with open(client_report_path, 'w', encoding='utf-8') as f:
                            f.write(cleaned_client_content)
                        
                        log_debug("Applied post-processing cleanup to client report")
                except Exception as e:
                    log_debug(f"Warning: Client report post-processing cleanup failed: {e}")
                
        except Exception as e:
            log_debug(f"ERROR: Failed to generate client report: {e}")
            
            # Use nbconvert as fallback
            try:
                # Use the redirector if available
                if 'StderrRedirector' in locals():
                    with StderrRedirector(log_file=log_file_path):
                        fallback_exporter = HTMLExporter()
                        fallback_exporter.exclude_input = True  # Hide code for client report
                        (body, resources) = fallback_exporter.from_notebook_node(notebook_node)
                        with open(client_report_path, 'w', encoding='utf-8') as f:
                            f.write(body)
                        
                        # Post-process the client report to clean artifacts
                        try:
                            with open(client_report_path, 'r', encoding='utf-8') as f:
                                client_html_content = f.read()
                            
                            cleaned_client_content = clean_report_output(client_html_content)
                            
                            with open(client_report_path, 'w', encoding='utf-8') as f:
                                f.write(cleaned_client_content)
                            
                            log_debug("Applied post-processing cleanup to client report (exception fallback stderr)")
                        except Exception as cleanup_e:
                            log_debug(f"Warning: Client report exception fallback stderr post-processing cleanup failed: {cleanup_e}")
                else:
                    fallback_exporter = HTMLExporter()
                    fallback_exporter.exclude_input = True  # Hide code for client report
                    (body, resources) = fallback_exporter.from_notebook_node(notebook_node)
                    with open(client_report_path, 'w', encoding='utf-8') as f:
                        f.write(body)
                    
                    # Post-process the client report to clean artifacts
                    try:
                        with open(client_report_path, 'r', encoding='utf-8') as f:
                            client_html_content = f.read()
                        
                        cleaned_client_content = clean_report_output(client_html_content)
                        
                        with open(client_report_path, 'w', encoding='utf-8') as f:
                            f.write(cleaned_client_content)
                        
                        log_debug("Applied post-processing cleanup to client report (exception fallback direct)")
                    except Exception as cleanup_e:
                        log_debug(f"Warning: Client report exception fallback direct post-processing cleanup failed: {cleanup_e}")
                        
                log_debug("Client report saved using fallback method")
                
                # --- Post-process Client Report Fallback to Clean Artifacts ---
                try:
                    # Apply post-processing to client report from fallback method
                    if os.path.exists(client_report_path):
                        with open(client_report_path, 'r', encoding='utf-8') as f:
                            client_html_content = f.read()
                        
                        cleaned_client_content = clean_report_output(client_html_content)
                        
                        with open(client_report_path, 'w', encoding='utf-8') as f:
                            f.write(cleaned_client_content)
                        
                        log_debug("Applied post-processing cleanup to client report (fallback)")
                except Exception as e:
                    log_debug(f"Warning: Client report fallback post-processing cleanup failed: {e}")
            except Exception as e2:
                log_debug(f"ERROR: Fallback client report generation failed: {e2}")

        # --- Launch Reports in Browser ---
        # Create relative paths for easier access
        base_url = "file://"

        # Convert paths to URLs
        internal_report_url = f"{base_url}{os.path.abspath(internal_report_path).replace(os.sep, '/')}"
        client_report_url = f"{base_url}{os.path.abspath(client_report_path).replace(os.sep, '/')}"

        # Launch both reports in browser tabs (suppress output to avoid JSON parsing issues)
        try:
            import webbrowser
            
            # Only log that we're opening the reports, but not the actual URLs
            log_debug("Opening client report in browser")
            log_debug("Opening internal report in browser")
            
            # Try to use the redirector if available
            if 'StderrRedirector' in locals():
                with StderrRedirector(log_file=log_file_path):
                    webbrowser.open_new_tab(client_report_url)
                    webbrowser.open_new_tab(internal_report_url)
            else:
                # Disable output before launching browsers to avoid JSON parse errors
                webbrowser.open_new_tab(client_report_url)
                webbrowser.open_new_tab(internal_report_url)
                
        except Exception as e:
            log_debug(f"WARNING: Failed to open reports in browser: {e}")

        return json.dumps({
            "success": True,
            "message": "Reports generated successfully.",
            "simulation_index": simulation_index,
            "internal_report_path": internal_report_path,
            "client_report_path": client_report_path,
            "internal_report_url": internal_report_url,
            "client_report_url": client_report_url
        }, indent=2)

    except FileNotFoundError as e:
        log_debug(f"ERROR: Required file not found. {e}")
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "message": f"ERROR: Required file not found. Check template path. {e}"
        }, indent=2)
    except pm.exceptions.PapermillExecutionError as e:
        log_debug(f"ERROR during notebook execution: {e}")
        
        # Extract and print notebook execution error details
        if hasattr(e, 'traceback'):
            log_debug(f"Notebook execution traceback: {e.traceback}")
        if hasattr(e, 'ename') and hasattr(e, 'evalue'):
            log_debug(f"Error type: {e.ename}")
            log_debug(f"Error value: {e.evalue}")

        # Try to save the partially executed notebook if it exists
        try:
            partial_path = os.path.join(OUTPUT_DIR, f"partial_executed_report_{report_uuid}.ipynb")
            if os.path.exists(executed_notebook_path):
                os.rename(executed_notebook_path, partial_path)
                log_debug(f"Partially executed notebook saved to: {partial_path}")
                return json.dumps({
                    "success": False,
                    "message": f"ERROR during notebook execution: {e}",
                    "error_details": f"Error type: {getattr(e, 'ename', 'Unknown')}, Error message: {getattr(e, 'evalue', 'Unknown')}",
                    "partial_notebook": partial_path
                }, indent=2)
        except Exception as rename_e:
            log_debug(f"Failed to save partial execution: {rename_e}")

        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "message": f"ERROR during notebook execution: {e}",
            "error_details": f"Error type: {getattr(e, 'ename', 'Unknown')}, Error message: {getattr(e, 'evalue', 'Unknown')}"
        }, indent=2)
    except Exception as e:
        log_debug(f"An unexpected error occurred: {e}")
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "message": f"An unexpected error occurred during report generation: {e}"
        }, indent=2)

@mcp.tool()
@capture_response
def get_parameter(parameter_type: str, parameter_name: str, reactor_index) -> str:
    """
    Get the value of a specific simulation parameter.

    Args:
        parameter_type: The category of the parameter ('feedstock', 'kinetic', 'reactor', 'flow').
        parameter_name: The specific name of the parameter to retrieve.
                        For 'feedstock': Any component ID (e.g., 'S_su', 'S_IN', 'S_cat').
                        For 'kinetic': Any kinetic parameter ID (e.g., 'k_dec_X_su', 'Y_su').
                        For 'reactor': 'Temp', 'HRT', or 'method'. Requires 'reactor_index'.
                        For 'flow': 'Q', 'simulation_time', or 't_step'.
        reactor_index: The index (1-based) of the reactor if parameter_type is 'reactor'.
                       Optional for other parameter types.

    Returns:
        JSON string containing the parameter type, name, and its current value or an error message.
    """
    sys.stderr.write(f"DEBUG: Tool get_parameter called for type='{parameter_type}', name='{parameter_name}', index={reactor_index}\n")
    sys.stderr.flush()

    # Handle reactor_index being None for non-reactor parameters
    # This preserves the optional behavior while avoiding default values in the signature

    value = None
    found = False
    message = ""
    try:
        if parameter_type == 'feedstock':
            if not simulation_state.influent_values:
                message = "Feedstock parameters not yet defined."
            else:
                value = simulation_state.influent_values.get(parameter_name)
                if value is not None:
                    found = True
                else:
                    # Check if it's a valid component in the loaded thermo package
                    if simulation_state.cmps and parameter_name in simulation_state.cmps.IDs:
                        value = 0.0 # Assume 0 if valid component but not explicitly set
                        found = True
                        message = f"Parameter '{parameter_name}' not explicitly set, returning default 0.0."
                    else:
                        message = f"Parameter '{parameter_name}' not found in feedstock values or known components."

        elif parameter_type == 'kinetic':
            if not simulation_state.kinetic_params:
                message = "Kinetic parameters not yet defined or using defaults."
                # Potentially check default kinetic params if accessible? For now, just report not set.
            else:
                value = simulation_state.kinetic_params.get(parameter_name)
                if value is not None:
                    found = True
                else:
                    message = f"Kinetic parameter '{parameter_name}' not found."
                    # TODO: Could potentially retrieve default value from pc.create_adm1_processes() if needed

        elif parameter_type == 'reactor':
            if reactor_index is None or not (1 <= reactor_index <= len(simulation_state.sim_params)):
                message = f"Invalid or missing reactor_index (must be between 1 and {len(simulation_state.sim_params)})."
            elif parameter_name not in ['Temp', 'HRT', 'method']:
                message = f"Invalid reactor parameter name '{parameter_name}'. Must be 'Temp', 'HRT', or 'method'."
            else:
                value = simulation_state.sim_params[reactor_index - 1].get(parameter_name)
                if value is not None:
                    found = True
                else:
                    # This case shouldn't happen if param name is valid, but handle defensively
                    message = f"Reactor parameter '{parameter_name}' not found for index {reactor_index} (internal error?)."

        elif parameter_type == 'flow':
            if hasattr(simulation_state, parameter_name) and parameter_name in ['Q', 'simulation_time', 't_step']:
                value = getattr(simulation_state, parameter_name)
                found = True
            else:
                message = f"Invalid flow parameter name '{parameter_name}'. Must be 'Q', 'simulation_time', or 't_step'."
        else:
            message = f"Invalid parameter_type '{parameter_type}'. Must be 'feedstock', 'kinetic', 'reactor', or 'flow'."

        if found:
            message = f"Parameter '{parameter_name}' retrieved successfully."
            return json.dumps({
                "success": True,
                "parameter_type": parameter_type,
                "parameter_name": parameter_name,
                "value": value,
                "message": message
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "parameter_type": parameter_type,
                "parameter_name": parameter_name,
                "message": message or f"Parameter '{parameter_name}' not found for type '{parameter_type}'."
            }, indent=2)

    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in get_parameter: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)


@mcp.tool()
@capture_response
def set_parameter(parameter_type: str, parameter_name: str, value, reactor_index) -> str:
    """
    Set the value of a specific simulation parameter. This will clear any previous simulation results.

    Args:
        parameter_type: The category of the parameter ('feedstock', 'kinetic', 'reactor', 'flow').
        parameter_name: The specific name of the parameter to set.
                        For 'feedstock': Any component ID (e.g., 'S_su', 'S_IN', 'S_cat'). Value should be numeric (concentration in kg/m³).
                        For 'kinetic': Any kinetic parameter ID (e.g., 'k_dec_X_su', 'Y_su'). Value should be numeric.
                        For 'reactor': 'Temp' (numeric, K), 'HRT' (numeric, days), or 'method' (string, e.g., 'BDF'). Requires 'reactor_index'.
                        For 'flow': 'Q' (numeric, m³/d), 'simulation_time' (numeric, days), or 't_step' (numeric, days).
        value: The new value for the parameter. Should be convertible to float for most parameters, string for 'method'.
        reactor_index: The index (1-based) of the reactor if parameter_type is 'reactor'.
                       Can be None for other parameter types.

    Returns:
        JSON string confirming the parameter update or reporting an error. Results are always cleared on success.
    """
    sys.stderr.write(f"DEBUG: Tool set_parameter called for type='{parameter_type}', name='{parameter_name}', index={reactor_index}, value='{value}'\n")
    sys.stderr.flush()

    # Your existing code can handle reactor_index being None for non-reactor parameters

    results_cleared = False
    message = ""
    success = False

    # Rest of your function implementation...
    try:
        original_value_type = type(value)
        processed_value = value # Keep original for potential string usage

        # Try converting to float if parameter type generally expects numeric input
        if parameter_type != 'reactor' or (parameter_type == 'reactor' and parameter_name != 'method'):
            if isinstance(value, str):
                try:
                    processed_value = float(value)
                except ValueError:
                    # Keep as string if conversion fails, will likely cause error later if number needed
                    pass
            elif not isinstance(value, Number): # Check if it's not already a number (int, float)
                # If it's not a string and not a number, it's an unsupported type for numeric params
                return json.dumps({
                    "success": False,
                    "message": f"Invalid value type '{original_value_type.__name__}' for numeric parameter '{parameter_name}'. Expected number or convertible string."
                }, indent=2)


        if parameter_type == 'feedstock':
            if not isinstance(processed_value, Number):
                message = f"Invalid value for feedstock parameter '{parameter_name}'. Must be numeric (concentration in kg/m³)."
            elif processed_value < 0:
                message = f"Invalid value for feedstock parameter '{parameter_name}'. Concentration cannot be negative."
            # Check if cmps is loaded and parameter_name is a valid component
            # elif simulation_state.cmps and parameter_name not in simulation_state.cmps.IDs:
            #      message = f"Warning: '{parameter_name}' is not a known component ID in the loaded thermo package."
            #      # Allow setting anyway, but warn? Or disallow? Let's allow for flexibility.
            #      simulation_state.influent_values[parameter_name] = processed_value
            #      simulation_state.sim_results = [None] * len(simulation_state.sim_params)
            #      results_cleared = True
            #      success = True
            #      message += f"\nParameter '{parameter_name}' set to {processed_value}. Results cleared."

            else:
                # Initialize influent_values if it doesn't exist
                if simulation_state.influent_values is None:
                    simulation_state.influent_values = {}
                simulation_state.influent_values[parameter_name] = processed_value
                simulation_state.sim_results = [None] * len(simulation_state.sim_params)
                results_cleared = True
                success = True
                message = f"Feedstock parameter '{parameter_name}' set to {processed_value}. Results cleared."

        elif parameter_type == 'kinetic':
            if not isinstance(processed_value, Number):
                message = f"Invalid value for kinetic parameter '{parameter_name}'. Must be numeric."
            else:
                # Initialize kinetic_params if it doesn't exist
                if simulation_state.kinetic_params is None:
                    simulation_state.kinetic_params = {}
                simulation_state.kinetic_params[parameter_name] = processed_value
                simulation_state.use_kinetics = True # Assume manual setting implies usage
                simulation_state.sim_results = [None] * len(simulation_state.sim_params)
                results_cleared = True
                success = True
                message = f"Kinetic parameter '{parameter_name}' set to {processed_value}. Results cleared."

        elif parameter_type == 'reactor':
            if reactor_index is None or not (1 <= reactor_index <= len(simulation_state.sim_params)):
                message = f"Invalid or missing reactor_index (must be between 1 and {len(simulation_state.sim_params)})."
            elif parameter_name not in ['Temp', 'HRT', 'method']:
                message = f"Invalid reactor parameter name '{parameter_name}'. Must be 'Temp', 'HRT', or 'method'."
            else:
                idx = reactor_index - 1
                target_param = simulation_state.sim_params[idx]

                if parameter_name == 'method':
                    if not isinstance(processed_value, str):
                        message = f"Invalid value for reactor parameter 'method'. Must be a string (e.g., 'BDF')."
                    else:
                        # Optional: Add validation against known methods
                        valid_methods = ["BDF", "RK45", "RK23", "DOP853", "Radau", "LSODA"]
                        if processed_value not in valid_methods:
                            message = f"Warning: Integration method '{processed_value}' is not in the standard list: {valid_methods}. Using it anyway."
                        target_param[parameter_name] = processed_value
                        success = True
                else: # Temp or HRT
                    if not isinstance(processed_value, Number):
                        message = f"Invalid value for reactor parameter '{parameter_name}'. Must be numeric."
                    elif parameter_name == 'Temp' and not (273.15 <= processed_value <= 373.15):
                        message = f"Temperature value {processed_value} K is outside the typical range (273.15K - 373.15K)."
                        # Allow setting anyway, but warn
                        target_param[parameter_name] = processed_value
                        success = True
                    elif parameter_name == 'HRT' and processed_value <= 0:
                        message = f"Invalid value for reactor parameter 'HRT'. Must be positive."
                    else:
                        target_param[parameter_name] = processed_value
                        success = True

                if success:
                    simulation_state.sim_results = [None] * len(simulation_state.sim_params)
                    results_cleared = True
                    message += f"\nReactor {reactor_index} parameter '{parameter_name}' set to {processed_value}. Results cleared."


        elif parameter_type == 'flow':
            if parameter_name not in ['Q', 'simulation_time', 't_step']:
                message = f"Invalid flow parameter name '{parameter_name}'. Must be 'Q', 'simulation_time', or 't_step'."
            elif not isinstance(processed_value, Number):
                message = f"Invalid value for flow parameter '{parameter_name}'. Must be numeric."
            elif processed_value <= 0:
                message = f"Invalid value for flow parameter '{parameter_name}'. Must be positive."
            else:
                setattr(simulation_state, parameter_name, processed_value)
                simulation_state.sim_results = [None] * len(simulation_state.sim_params)
                results_cleared = True
                success = True
                message = f"Flow parameter '{parameter_name}' set to {processed_value}. Results cleared."

        else:
            message = f"Invalid parameter_type '{parameter_type}'. Must be 'feedstock', 'kinetic', 'reactor', or 'flow'."

        return json.dumps({
            "success": success,
            "message": message,
            "results_cleared": results_cleared
        }, indent=2)

    except Exception as e:
        sys.stderr.write(f"DEBUG ERROR in set_parameter: {str(e)}\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        return json.dumps({
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }, indent=2)

if __name__ == "__main__":
    sys.stderr.write("Starting ADM1 Simulation MCP Server...\n")
    sys.stderr.flush()
    mcp.run(transport="stdio")
