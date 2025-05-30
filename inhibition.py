"""
Inhibition analysis functions for ADM1 MCP server
"""
import numpy as np

def calculate_inhibition_factors(system_or_results):
    """
    Calculate inhibition and nutrient limitation factors from the simulation state or results
    
    Parameters
    ----------
    system_or_results : System or tuple
        The simulation system with results or a tuple containing (sys, inf, eff, gas)
        
    Returns
    -------
    dict
        Dictionary containing all inhibition factors
    """
    if isinstance(system_or_results, tuple) and len(system_or_results) >= 1:
        # Extract system from results tuple
        sys = system_or_results[0]
    else:
        # Use directly if it's a system
        sys = system_or_results
    
    if sys is None:
        return None
    
    # Try to access the inhibition data stored by the ADM1 model during the last simulation step
    try:
        # The ADM1 model in QSDsan stores inhibition data in the model's root attribute
        # This is stored during rate calculation in the _rhos_adm1 function
        root_data = sys._path[0].model.rate_function._params['root'].data
        
        if root_data is None:
            return None
        
        # Extract inhibition factors
        inhibition_factors = {
            'pH_Inhibition': root_data.get('Iph', [1, 1, 1, 1, 1, 1, 1, 1]),
            'H2_Inhibition': root_data.get('Ih2', [1, 1, 1, 1]),
            'Nitrogen_Limitation': root_data.get('Iin', 1),
            'Ammonia_Inhibition': root_data.get('Inh3', 1),
            'Substrate_Limitation': root_data.get('Monod', [1, 1, 1, 1, 1, 1, 1, 1]),
            'Process_Rates': root_data.get('rhos', [0, 0, 0, 0, 0, 0, 0, 0]),
            'pH_Value': root_data.get('pH', 7.0)
        }
        
        return inhibition_factors
    
    except (KeyError, AttributeError, IndexError) as e:
        # If the inhibition data isn't available, return None
        return None

def analyze_inhibition(simulation_results):
    """
    Analyze inhibition and process health based on inhibition factors
    
    Parameters
    ----------
    simulation_results : tuple
        Tuple containing (sys, inf, eff, gas)
    
    Returns
    -------
    dict
        Comprehensive analysis of inhibition and process health
    """
    # Process names for reference
    process_names = [
        "Sugar Uptake", 
        "Amino Acid Uptake", 
        "LCFA Uptake", 
        "Valerate Uptake",
        "Butyrate Uptake", 
        "Propionate Uptake", 
        "Acetate Uptake", 
        "H₂ Uptake"
    ]
    
    # Get inhibition factors
    inhibition_data = calculate_inhibition_factors(simulation_results)
    
    if inhibition_data is None:
        return {
            "success": False,
            "message": "No inhibition data available from simulation."
        }
    
    # Extract inhibition factors
    pH_inhibition = inhibition_data['pH_Inhibition']
    h2_inhibition = inhibition_data['H2_Inhibition']
    n_limitation = inhibition_data['Nitrogen_Limitation']
    nh3_inhibition = inhibition_data['Ammonia_Inhibition']
    substrate_limitation = inhibition_data['Substrate_Limitation']
    process_rates = inhibition_data['Process_Rates']
    pH_value = inhibition_data['pH_Value']
    
    # Create expanded inhibition factors to match process names length
    h2_inhibition_expanded = [1.0, 1.0, h2_inhibition[0], h2_inhibition[1], 
                              h2_inhibition[2], h2_inhibition[3], 1.0, 1.0]
    
    nh3_inhibition_expanded = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, nh3_inhibition, 1.0]
    
    # Calculate two sets of overall inhibition values
    # 1. With substrate limitation
    # 2. Without substrate limitation (for health assessment)
    overall_inhibition = []
    overall_inhibition_no_substrate = []
    
    for i, process in enumerate(process_names):
        # Each inhibition factor is between 0-1, where 1 means no inhibition
        # Calculate overall inhibition with substrate limitation
        if i == 6:  # Acetate uptake affected by ammonia
            with_substrate = pH_inhibition[i] * n_limitation * nh3_inhibition * substrate_limitation[i]
            no_substrate = pH_inhibition[i] * n_limitation * nh3_inhibition
        elif i in [2, 3, 4, 5]:  # LCFA, valerate, butyrate, propionate uptake affected by H2
            with_substrate = pH_inhibition[i] * n_limitation * h2_inhibition_expanded[i] * substrate_limitation[i]
            no_substrate = pH_inhibition[i] * n_limitation * h2_inhibition_expanded[i]
        else:  # Other processes
            with_substrate = pH_inhibition[i] * n_limitation * substrate_limitation[i]
            no_substrate = pH_inhibition[i] * n_limitation
        
        overall_inhibition.append(with_substrate)
        overall_inhibition_no_substrate.append(no_substrate)
    
    # Convert inhibition values to degrees of inhibition (0-100%)
    def inhibition_degree(factor):
        return (1 - factor) * 100
    
    # Calculate process-specific inhibition values
    process_inhibition = []
    
    for i, process in enumerate(process_names):
        process_inhibition.append({
            "process": process,
            "pH_inhibition": inhibition_degree(pH_inhibition[i]),
            "h2_inhibition": inhibition_degree(h2_inhibition_expanded[i]),
            "n_limitation": inhibition_degree(n_limitation),
            "nh3_inhibition": inhibition_degree(nh3_inhibition_expanded[i]),
            "substrate_limitation": inhibition_degree(substrate_limitation[i]),
            "overall_inhibition": inhibition_degree(overall_inhibition[i]),
            "without_substrate": inhibition_degree(overall_inhibition_no_substrate[i]),
            "process_rate": process_rates[i] if i < len(process_rates) else 0
        })
    
    # Calculate health assessment
    # Use maximum inhibition value instead of average (processes are in series)
    true_inhibition_values = [inhibition_degree(x) for x in overall_inhibition_no_substrate]
    max_inhibition = max(true_inhibition_values)
    max_inhibition_process = process_names[true_inhibition_values.index(max_inhibition)]
    
    # Define health status based on maximum inhibition (worst case)
    if max_inhibition < 10:
        health_status = "Excellent"
    elif max_inhibition < 20:
        health_status = "Good"
    elif max_inhibition < 40:
        health_status = "Fair"
    elif max_inhibition < 60:
        health_status = "Poor"
    else:
        health_status = "Critical"
    
    # Calculate maximum inhibition by type (excluding substrate limitation)
    max_ph_inhibition = max([inhibition_degree(x) for x in pH_inhibition])
    max_h2_inhibition = max([inhibition_degree(x) for x in h2_inhibition]) if len(h2_inhibition) > 0 else 0
    max_n_limitation = inhibition_degree(n_limitation)
    max_nh3_inhibition = inhibition_degree(nh3_inhibition)
    
    # Calculate safety margin directly from limitation percentages
    safety_margin_values = [inhibition_degree(x) for x in substrate_limitation]
    min_safety_margin = min(safety_margin_values) if safety_margin_values else 0
    min_safety_idx = safety_margin_values.index(min_safety_margin) if safety_margin_values else 0
    min_safety_margin_process = process_names[min_safety_idx]
    
    # Evaluate safety margin based on substrate limitation percentage
    if min_safety_margin > 60:
        safety_status = "High"
        safety_message = "The system has a high safety margin against shock loads and inhibitory conditions."
    elif min_safety_margin > 30:
        safety_status = "Good"
        safety_message = "The system has a good safety margin, providing adequate buffer against upsets."
    elif min_safety_margin > 10:
        safety_status = "Moderate"
        safety_message = "The system has a moderate safety margin. Consider monitoring closely."
    else:
        safety_status = "Low"
        safety_message = "The system has a low safety margin and may be operating near maximum substrate utilization rate."
    
    # Generate recommendations based on the most significant inhibition factor
    inhibition_factors = [
        {"type": "pH Inhibition", "value": max_ph_inhibition},
        {"type": "H₂ Inhibition", "value": max_h2_inhibition},
        {"type": "N Limitation", "value": max_n_limitation},
        {"type": "NH₃ Inhibition", "value": max_nh3_inhibition}
    ]
    
    # Sort by inhibition value (highest first)
    inhibition_factors.sort(key=lambda x: x["value"], reverse=True)
    
    top_inhibition = inhibition_factors[0]["type"]
    top_value = inhibition_factors[0]["value"]
    
    if top_value < 10:
        recommendations = ["The reactor is operating optimally. No adjustments needed."]
    else:
        recommendations = []
        if top_inhibition == "pH Inhibition":
            recommendations.extend([
                f"pH Inhibition Detected ({top_value:.1f}%)",
                f"Current pH: {pH_value:.2f}",
                "If pH is too low: Add alkalinity (e.g., sodium bicarbonate)",
                "If pH is too high: Consider adding CO₂ or reducing alkalinity",
                "Monitor VFA accumulation which can cause pH drops"
            ])
        elif top_inhibition == "H₂ Inhibition":
            recommendations.extend([
                f"H₂ Inhibition Detected ({top_value:.1f}%)",
                "Optimize mixing to enhance H₂ transfer to methanogens",
                "Ensure healthy hydrogenotrophic methanogen population",
                "Consider reducing organic loading rate temporarily"
            ])
        elif top_inhibition == "N Limitation":
            recommendations.extend([
                f"Nitrogen Limitation Detected ({top_value:.1f}%)",
                "Supplement feedstock with nitrogen-rich substrates",
                "Consider adding ammonium or urea as nitrogen source",
                "Maintain C:N ratio between 20:1 and 30:1"
            ])
        elif top_inhibition == "NH₃ Inhibition":
            recommendations.extend([
                f"Ammonia Inhibition Detected ({top_value:.1f}%)",
                "Reduce nitrogen-rich feedstocks",
                "Consider lowering pH slightly (within safe range) to reduce free ammonia",
                "Dilute reactor contents or increase HRT",
                "Investigate ammonia-tolerant methanogen species"
            ])
    
    # Safety margin recommendations
    safety_recommendations = []
    if min_safety_margin > 60:
        safety_recommendations.extend([
            f"High Safety Margin ({min_safety_margin:.1f}% substrate limitation)",
            "Your system has significant reserve capacity and is well-protected against shock organic loads, toxic inhibition, and temperature fluctuations",
            "Consider increasing organic loading rate to improve biogas production",
            "Evaluate if HRT can be reduced to increase throughput"
        ])
    elif min_safety_margin > 30:
        safety_recommendations.extend([
            f"Good Safety Margin ({min_safety_margin:.1f}% substrate limitation)",
            "Your system has adequate reserve capacity for normal operation",
            "Maintain current organic loading rate",
            "Gradually test higher loading rates if increased production is desired"
        ])
    elif min_safety_margin > 10:
        safety_recommendations.extend([
            f"Moderate Safety Margin ({min_safety_margin:.1f}% substrate limitation)",
            "Your system has limited buffer against upsets",
            "Monitor process closely",
            "Maintain consistent feeding patterns",
            "Avoid rapid changes in feedstock composition"
        ])
    else:
        safety_recommendations.extend([
            f"Low Safety Margin ({min_safety_margin:.1f}% substrate limitation)",
            "Your system is operating close to maximum substrate utilization rate with minimal safety margin",
            "Consider reducing HRT to introduce more substrate limitation",
            "Maintain consistent operating conditions",
            "Monitor for inhibitory compounds that could slow the process further",
            "Consider adding additional biomass to increase safety margin"
        ])
    
    # Compile the final analysis
    return {
        "success": True,
        "current_pH": float(f"{pH_value:.2f}"),
        "process_inhibition": process_inhibition,
        "health_assessment": {
            "status": health_status,
            "max_inhibition": float(f"{max_inhibition:.1f}"),
            "limiting_process": max_inhibition_process
        },
        "safety_assessment": {
            "status": safety_status,
            "min_safety_margin": float(f"{min_safety_margin:.1f}"),
            "limiting_process": min_safety_margin_process,
            "message": safety_message
        },
        "inhibition_factors": inhibition_factors,
        "recommendations": recommendations,
        "safety_recommendations": safety_recommendations
    }