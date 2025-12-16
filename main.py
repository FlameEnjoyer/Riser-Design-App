"""
Riser Design Analysis Tool
API RP 1111 and ASME B31.4/B31.8 Compliance Checker

This tool performs comprehensive riser design analysis including:
- Burst pressure check (API RP 1111 Section 4.3.1)
- External collapse check (API RP 1111 Section 4.3.2)
- Propagation buckling check (API RP 1111 Section 4.3.2.3)
- Combined bending and pressure check (API RP 1111 Section 4.3.2.2)
- Hoop stress check (ASME B31.4/B31.8)

Life Cycle Conditions:
- Installation: Full nominal WT, empty pipe (no internal pressure), installation bending
- Hydrotest: Full nominal WT, hydrotest pressure, no bending
- Operation/Decommissioning: WT minus corrosion allowance, design pressures, operational bending
"""

import json
import math
import sys
from pathlib import Path

# Import calculation modules
from reference_data import asme_b36_10
from calculations import calcs_burst, calcs_collapse, calcs_propagation, calcs_bending, calcs_hoop


# Life cycle condition definitions
# All conditions include: Burst, Collapse, Propagation, Bending, and Hoop checks
LIFE_CYCLE_CONDITIONS = {
    'installation': {
        'name': 'Installation',
        'description': 'Empty pipe during installation - nominal WT',
        'use_corrosion_allowance': False,
        'use_mill_tolerance': False,  # Use nominal WT for installation
        'internal_pressure_factor': 0.0,  # Empty pipe - no internal pressure
        'external_pressure_factor': 1.0,  # Full external pressure (hydrostatic/annulus)
        'bending_strain_key': 'bending_strain_installation',  # Higher bending during lay
        'notes': 'Empty pipe, external pressure + bending during lay operations'
    },
    'hydrotest': {
        'name': 'Hydrotest',
        'description': 'Pressure testing at 1.25x design pressure - nominal WT',
        'use_corrosion_allowance': False,
        'use_mill_tolerance': False,  # Use nominal WT for hydrotest
        'internal_pressure_factor': None,  # Uses hydrotest_pressure_psi from input (1.25x design)
        'external_pressure_factor': 1.0,  # Full external pressure (hydrostatic/annulus)
        'bending_strain_key': 'bending_strain',  # Same bending as operation
        'notes': 'Elevated internal pressure (1.25x), external pressure, bending'
    },
    'operation': {
        'name': 'Operation',
        'description': 'Normal operation with corroded wall thickness + mill tolerance',
        'use_corrosion_allowance': True,
        'use_mill_tolerance': True,  # Apply mill tolerance for design
        'internal_pressure_factor': 1.0,  # Design internal pressure
        'external_pressure_factor': 1.0,  # Full external pressure (hydrostatic/annulus)
        'bending_strain_key': 'bending_strain',  # Design bending strain
        'notes': 'Mill tolerance + corrosion allowance deducted from wall thickness'
    }
}


def load_input_data(filename='reference_data/input_data.json'):
    """Load design parameters from JSON configuration file."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"Error: Configuration file '{filename}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{filename}': {e}")
        sys.exit(1)


def calculate_external_pressure(depth_m, water_density_lb_ft3=64.0):
    """
    Calculate hydrostatic external pressure at given depth.
    
    Parameters:
    -----------
    depth_m : float
        Water depth in meters
    water_density_lb_ft3 : float
        Water density in lb/ft³ (default 64 for seawater)
        
    Returns:
    --------
    float : External pressure in psi
    """
    # Convert depth from meters to feet
    depth_ft = depth_m * 3.28084
    
    # Calculate hydrostatic pressure: p = ρ * h / 144 (psi)
    # 144 converts from lb/ft² to psi
    p_external_psi = water_density_lb_ft3 * depth_ft / 144.0
    
    return p_external_psi


def get_effective_wall_thickness(nominal_wt, corrosion_allowance, mill_tolerance_percent, apply_corrosion, apply_mill_tolerance):
    """
    Calculate effective wall thickness considering corrosion and mill tolerance.
    
    Parameters:
    -----------
    nominal_wt : float
        Nominal wall thickness in inches
    corrosion_allowance : float
        Corrosion allowance in inches
    mill_tolerance_percent : float
        Mill tolerance as percentage (e.g., 12.5 for -12.5%)
    apply_corrosion : bool
        Whether to apply corrosion allowance
    apply_mill_tolerance : bool
        Whether to apply mill tolerance
        
    Returns:
    --------
    float : Effective wall thickness in inches
    """
    effective_wt = nominal_wt
    
    # Apply mill tolerance (negative tolerance reduces thickness)
    if apply_mill_tolerance:
        effective_wt = effective_wt * (1.0 - mill_tolerance_percent / 100.0)
    
    # Apply corrosion allowance if required
    if apply_corrosion:
        effective_wt = effective_wt - corrosion_allowance
    
    # Ensure positive thickness
    return max(effective_wt, 0.001)


def analyze_condition(scenario, project_info, condition_key, nominal_wt):
    """
    Analyze a single life cycle condition for a given wall thickness.
    Uses conservative loading:
    - HAT (Highest Astronomical Tide) for external-dominated checks (Collapse, Propagation, Bending)
    - LAT (Lowest Astronomical Tide) for burst checks (less external to counteract internal)
    
    Parameters:
    -----------
    scenario : dict
        Scenario configuration
    project_info : dict
        Project-level information
    condition_key : str
        Key for life cycle condition ('installation', 'hydrotest', 'operation')
    nominal_wt : float
        Nominal wall thickness in inches
        
    Returns:
    --------
    dict : Analysis results for this condition
    """
    condition = LIFE_CYCLE_CONDITIONS[condition_key]
    
    # Extract scenario parameters
    scenario_type = scenario['type']
    manufacturing = scenario['manufacturing']
    
    od = scenario['geometry']['od_inches']
    ovality = scenario['geometry']['ovality']
    corrosion_allowance = scenario['geometry'].get('corrosion_allowance_inches', 0.0)
    mill_tolerance = scenario['geometry'].get('mill_tolerance_percent', 0.0)
    
    smys_ksi = scenario['material']['smys_ksi']
    uts_ksi = scenario['material']['uts_ksi']
    E_ksi = scenario['material']['modulus_of_elasticity_ksi']
    poisson = scenario['material']['poisson_ratio']
    
    design_p_i_psi = scenario['loads']['design_internal_pressure_psi']
    
    # Get HAT and LAT depths (use depth_m as fallback for backward compatibility)
    depth_hat_m = scenario['loads'].get('depth_hat_m', scenario['loads'].get('depth_m', 40.0))
    depth_lat_m = scenario['loads'].get('depth_lat_m', scenario['loads'].get('depth_m', 40.0))
    use_annulus = scenario['loads']['use_annulus_pressure']
    
    # Calculate external pressures for both HAT and LAT
    # For annulus pressure (PIP systems), use design external pressure directly
    if scenario['loads']['design_external_pressure_psi'] is not None and use_annulus:
        # For PIP (Pipe-in-Pipe), annulus pressure is design external pressure
        base_p_o_hat_psi = scenario['loads']['design_external_pressure_psi']
        base_p_o_lat_psi = scenario['loads']['design_external_pressure_psi']
    else:
        # For conventional risers, calculate hydrostatic pressure from water depth
        water_density = project_info.get('water_density_seawater', 64.0)
        base_p_o_hat_psi = calculate_external_pressure(depth_hat_m, water_density)  # Higher external (HAT)
        base_p_o_lat_psi = calculate_external_pressure(depth_lat_m, water_density)  # Lower external (LAT)
    
    # Calculate effective wall thickness for this condition
    effective_wt = get_effective_wall_thickness(
        nominal_wt, 
        corrosion_allowance, 
        mill_tolerance,
        condition['use_corrosion_allowance'],
        condition['use_mill_tolerance']
    )
    
    # Determine internal pressure for this condition
    if condition_key == 'hydrotest':
        # Hydrotest: elevated internal pressure (1.25x design)
        hydrotest_factor = project_info.get('hydrotest_factor', 1.25)
        p_i_psi = scenario['loads'].get('hydrotest_pressure_psi', design_p_i_psi * hydrotest_factor)
    else:
        # Installation or Operation
        p_i_factor = condition['internal_pressure_factor']
        p_i_psi = design_p_i_psi * p_i_factor
    
    # Determine external pressures using CONSERVATIVE loading approach:
    # - HAT (higher depth) → Higher external pressure → Conservative for Collapse, Propagation, Bending
    # - LAT (lower depth) → Lower external pressure → Conservative for Burst (less to counteract internal)
    p_o_factor = condition['external_pressure_factor']
    p_o_hat_psi = base_p_o_hat_psi * p_o_factor  # External pressure at HAT (for Collapse/Propagation/Bending)
    p_o_lat_psi = base_p_o_lat_psi * p_o_factor  # External pressure at LAT (for Burst)
    
    # Determine bending strain for this condition
    bending_key = condition['bending_strain_key']
    bending_strain = scenario['loads'].get(bending_key, scenario['loads'].get('bending_strain', 0.001))
    
    # Convert pressures to ksi
    p_i_ksi = p_i_psi / 1000.0
    p_o_hat_ksi = p_o_hat_psi / 1000.0  # HAT external (for collapse/propagation/bending)
    p_o_lat_ksi = p_o_lat_psi / 1000.0  # LAT external (for burst)
    
    # Run all design checks with CONSERVATIVE loading
    
    # 1. Burst pressure check - Use LAT (lower external pressure is conservative)
    #    Less external pressure means less to counteract internal burst pressure
    burst_result = calcs_burst.check_burst_criteria(
        od, effective_wt, smys_ksi, uts_ksi, p_i_ksi, p_o_lat_ksi, 
        scenario_type, manufacturing
    )
    burst_result['depth_used'] = 'LAT'
    burst_result['external_pressure_psi'] = p_o_lat_psi
    
    # 2. Collapse check - Use HAT (higher external pressure is conservative)
    #    Higher external pressure is more severe for collapse
    collapse_result = calcs_collapse.check_collapse_criteria(
        od, effective_wt, smys_ksi, E_ksi, p_i_ksi, p_o_hat_ksi,
        manufacturing, poisson, ovality
    )
    collapse_result['depth_used'] = 'HAT'
    collapse_result['external_pressure_psi'] = p_o_hat_psi
    
    # 3. Propagation buckling check - Use HAT (higher external pressure is conservative)
    #    Higher net external pressure is more severe for propagation
    net_external_pressure_hat = p_o_hat_ksi - p_i_ksi
    propagation_result = calcs_propagation.check_propagation_criteria(
        od, effective_wt, smys_ksi, net_external_pressure_hat
    )
    propagation_result['depth_used'] = 'HAT'
    propagation_result['external_pressure_psi'] = p_o_hat_psi
    
    # 4. Combined bending and pressure check - Use HAT (higher external is conservative for bending interaction)
    #    External pressure contribution to bending interaction is more severe at HAT
    collapse_result_for_bending = calcs_collapse.check_collapse_criteria(
        od, effective_wt, smys_ksi, E_ksi, p_i_ksi, p_o_hat_ksi,
        manufacturing, poisson, ovality
    )
    p_c = collapse_result_for_bending['critical_collapse']
    bending_result = calcs_bending.check_combined_bending_pressure(
        od, effective_wt, smys_ksi, E_ksi, p_i_ksi, p_o_hat_ksi,
        bending_strain, p_c, ovality
    )
    bending_result['depth_used'] = 'HAT'
    bending_result['external_pressure_psi'] = p_o_hat_psi
    
    # 5. Hoop stress check per ASME B31.4 Section 402.3
    #    S_H = P_i × D / (2 × t) - uses internal pressure only per code
    #    Note: External pressure is NOT subtracted per ASME B31.4 Sec 402.3
    design_factor = 0.72
    smys_psi = smys_ksi * 1000.0
    hoop_result = calcs_hoop.check_hoop_stress_criteria(
        od, effective_wt, p_i_psi, smys_psi, design_factor
    )
    hoop_result['depth_used'] = 'N/A (Internal P only)'
    hoop_result['external_pressure_psi'] = 0.0  # Not used per ASME B31.4 Sec 402.3
    
    # Check if all criteria pass
    all_pass = (
        burst_result['pass_fail'] and
        collapse_result['pass_fail'] and
        propagation_result['pass_fail'] and
        bending_result['pass_fail'] and
        hoop_result['pass_fail']
    )
    
    return {
        'condition_key': condition_key,
        'condition_name': condition['name'],
        'condition_description': condition['description'],
        'notes': condition['notes'],
        'nominal_wt': nominal_wt,
        'effective_wt': effective_wt,
        'corrosion_applied': condition['use_corrosion_allowance'],
        'corrosion_allowance': corrosion_allowance if condition['use_corrosion_allowance'] else 0.0,
        'mill_tolerance_applied': condition['use_mill_tolerance'],
        'mill_tolerance_percent': mill_tolerance,
        'p_internal_psi': p_i_psi,
        'p_external_hat_psi': p_o_hat_psi,
        'p_external_lat_psi': p_o_lat_psi,
        'depth_hat_m': depth_hat_m,
        'depth_lat_m': depth_lat_m,
        'bending_strain': bending_strain,
        'all_pass': all_pass,
        'burst': burst_result,
        'collapse': collapse_result,
        'propagation': propagation_result,
        'bending': bending_result,
        'hoop': hoop_result
    }


def analyze_scenario(scenario, project_info):
    """
    Analyze a single design scenario across all life cycle conditions.
    
    Parameters:
    -----------
    scenario : dict
        Scenario configuration
    project_info : dict
        Project-level information
        
    Returns:
    --------
    dict : Analysis results including least and recommended thickness
    """
    # Extract scenario parameters
    name = scenario['name']
    scenario_type = scenario['type']  # Pipeline, Flowline, or Riser
    riser_type = scenario.get('riser_type', '')  # Optional: TTR, Rigid, SCR, etc.
    manufacturing = scenario['manufacturing']
    
    od = scenario['geometry']['od_inches']
    ovality = scenario['geometry']['ovality']
    corrosion_allowance = scenario['geometry'].get('corrosion_allowance_inches', 0.0)
    mill_tolerance = scenario['geometry'].get('mill_tolerance_percent', 0.0)
    
    grade = scenario['material']['grade']
    smys_ksi = scenario['material']['smys_ksi']
    uts_ksi = scenario['material']['uts_ksi']
    E_ksi = scenario['material']['modulus_of_elasticity_ksi']
    poisson = scenario['material']['poisson_ratio']
    
    p_i_psi = scenario['loads']['design_internal_pressure_psi']
    depth_hat_m = scenario['loads'].get('depth_hat_m', scenario['loads'].get('depth_m', 40.0))
    depth_lat_m = scenario['loads'].get('depth_lat_m', scenario['loads'].get('depth_m', 40.0))
    bending_strain = scenario['loads']['bending_strain']
    use_annulus = scenario['loads']['use_annulus_pressure']
    
    # Calculate external pressures for HAT and LAT
    if scenario['loads']['design_external_pressure_psi'] is not None and use_annulus:
        p_o_hat_psi = scenario['loads']['design_external_pressure_psi']
        p_o_lat_psi = scenario['loads']['design_external_pressure_psi']
    else:
        water_density = project_info.get('water_density_seawater', 64.0)
        p_o_hat_psi = calculate_external_pressure(depth_hat_m, water_density)
        p_o_lat_psi = calculate_external_pressure(depth_lat_m, water_density)
    
    # Get standard wall thicknesses for this OD
    standard_thicknesses = asme_b36_10.get_standard_thicknesses(od)
    
    if standard_thicknesses is None:
        print(f"\nError: No standard thicknesses available for OD {od}\"")
        return None
    
    # Results storage
    results = []
    least_thickness = None
    recommended_thickness = None
    
    # Define condition order
    condition_order = ['installation', 'hydrotest', 'operation']
    
    # Iterate through all standard thicknesses
    for wt in standard_thicknesses:
        # Analyze all three life cycle conditions for this thickness
        condition_results = {}
        all_conditions_pass = True
        
        for cond_key in condition_order:
            cond_result = analyze_condition(scenario, project_info, cond_key, wt)
            condition_results[cond_key] = cond_result
            if not cond_result['all_pass']:
                all_conditions_pass = False
        
        # Store results
        result_entry = {
            'wall_thickness': wt,
            'all_pass': all_conditions_pass,
            'conditions': condition_results
        }
        results.append(result_entry)
        
        # Find least thickness (first passing thickness for ALL conditions)
        if all_conditions_pass and least_thickness is None:
            least_thickness = wt
            recommended_thickness = wt
    
    return {
        'scenario_name': name,
        'scenario_type': scenario_type,
        'riser_type': riser_type,
        'manufacturing': manufacturing,
        'od': od,
        'grade': grade,
        'smys_ksi': smys_ksi,
        'uts_ksi': uts_ksi,
        'p_internal_psi': p_i_psi,
        'p_external_hat_psi': p_o_hat_psi,
        'p_external_lat_psi': p_o_lat_psi,
        'depth_hat_m': depth_hat_m,
        'depth_lat_m': depth_lat_m,
        'bending_strain': bending_strain,
        'ovality': ovality,
        'corrosion_allowance': corrosion_allowance,
        'mill_tolerance_percent': mill_tolerance,
        'results': results,
        'least_thickness': least_thickness,
        'recommended_thickness': recommended_thickness
    }


def print_condition_results(cond_result, od):
    """
    Print detailed results for a single life cycle condition.
    
    Parameters:
    -----------
    cond_result : dict
        Condition analysis results
    od : float
        Outer diameter in inches
    """
    print(f"\n{'─'*90}")
    print(f"  CONDITION: {cond_result['condition_name'].upper()}")
    print(f"{'─'*90}")
    print(f"  Description: {cond_result['condition_description']}")
    print(f"  Note: {cond_result['notes']}")
    print()
    
    # Wall thickness info
    print(f"  Wall Thickness:")
    print(f"    Nominal WT:                {cond_result['nominal_wt']:.4f} inches")
    if cond_result['mill_tolerance_applied']:
        print(f"    Mill Tolerance:            -{cond_result['mill_tolerance_percent']:.1f}%")
    else:
        print(f"    Mill Tolerance:            Not Applied (Use Nominal)")
    if cond_result['corrosion_applied']:
        print(f"    Corrosion Allowance:       -{cond_result['corrosion_allowance']:.4f} inches")
    else:
        print(f"    Corrosion Allowance:       Not Applied")
    print(f"    Effective WT:              {cond_result['effective_wt']:.4f} inches")
    
    print(f"    Inner Diameter:            {od - 2*cond_result['effective_wt']:.4f} inches")
    print(f"    D/t Ratio:                 {od/cond_result['effective_wt']:.2f}")
    print()
    
    # Load conditions
    print(f"  Load Conditions:")
    print(f"    Internal Pressure:         {cond_result['p_internal_psi']:.1f} psi")
    print(f"    Ext. Pressure @ HAT:       {cond_result['p_external_hat_psi']:.1f} psi  (Depth: {cond_result['depth_hat_m']:.1f} m - for Collapse/Prop/Bend)")
    print(f"    Ext. Pressure @ LAT:       {cond_result['p_external_lat_psi']:.1f} psi  (Depth: {cond_result['depth_lat_m']:.1f} m - for Burst/Hoop)")
    print(f"    Bending Strain:            {cond_result['bending_strain']:.6f} ({cond_result['bending_strain']*100:.3f}%)")
    print()
    
    # Design check summary table with Safety Factor per API RP 1111 / ASME B31.4/B31.8
    print(f"  {'Check':<32} {'Safety Factor':<15} {'Status':<8} {'Remark':<25}")
    print(f"  {'-'*80}")
    
    def format_sf(sf, is_reverse, check_type="", p_internal=0):
        """Format safety factor for display per API RP 1111 convention.

        Burst/hoop show N/A only when the pipe is empty during installation.
        Reverse loading cases report an infinite SF to highlight favorable demand.
        """
        if p_internal <= 0 and check_type in ['burst', 'hoop']:
            return "N/A", "P_i = 0 (empty pipe)"
        if is_reverse:
            return "∞", "Reverse (favorable)"
        if sf == float('inf'):
            return "∞", "No demand"
        if sf > 999:
            return f">{999:.0f}", "Very high margin"
        return f"{sf:.2f}", ""
    
    # Get internal pressure for this condition
    p_i = cond_result['p_internal_psi']
    
    # 1. Burst Pressure - API RP 1111 Sec 4.3.1
    burst = cond_result['burst']
    sf_burst, remark_burst = format_sf(burst['safety_factor'], burst.get('is_reverse_load', False), 'burst', p_i)
    print(f"  {'1. Burst Pressure':<32} {sf_burst:<15} {'PASS' if burst['pass_fail'] else 'FAIL':<8} {remark_burst:<25}")
    
    # 2. External Collapse - API RP 1111 Sec 4.3.2
    collapse = cond_result['collapse']
    sf_collapse, remark_collapse = format_sf(collapse['safety_factor'], collapse.get('is_reverse_load', False), 'collapse', p_i)
    print(f"  {'2. External Collapse':<32} {sf_collapse:<15} {'PASS' if collapse['pass_fail'] else 'FAIL':<8} {remark_collapse:<25}")
    
    # 3. Propagation Buckling - API RP 1111 Sec 4.3.2.3
    prop = cond_result['propagation']
    sf_prop, remark_prop = format_sf(prop['safety_factor'], prop.get('is_reverse_load', False), 'propagation', p_i)
    print(f"  {'3. Propagation Buckling':<32} {sf_prop:<15} {'PASS' if prop['pass_fail'] else 'FAIL':<8} {remark_prop:<25}")
    
    # 4. Combined Bending+Pressure - API RP 1111 Sec 4.3.2.2
    bend = cond_result['bending']
    sf_bend, remark_bend = format_sf(bend['safety_factor'], bend.get('is_reverse_load', False), 'bending', p_i)
    print(f"  {'4. Combined Bending+Pressure':<32} {sf_bend:<15} {'PASS' if bend['pass_fail'] else 'FAIL':<8} {remark_bend:<25}")
    
    # 5. Hoop Stress - ASME B31.4/B31.8
    hoop = cond_result['hoop']
    sf_hoop, remark_hoop = format_sf(hoop['safety_factor'], hoop.get('is_reverse_load', False), 'hoop', p_i)
    print(f"  {'5. Hoop Stress':<32} {sf_hoop:<15} {'PASS' if hoop['pass_fail'] else 'FAIL':<8} {remark_hoop:<25}")
    
    print(f"  {'-'*80}")
    status = "PASS" if cond_result['all_pass'] else "FAIL"
    print(f"  {'OVERALL STATUS':<32} {'':<15} {status:<8}")
    print(f"  Note: Reverse loading cases show SF = ∞ (favorable)")


def print_results(analysis_result):
    """
    Print professional analysis report to console.
    
    Parameters:
    -----------
    analysis_result : dict
        Complete analysis results for a scenario
    """
    if analysis_result is None:
        return
    
    # Header
    print("\n" + "="*90)
    print(f"RISER DESIGN ANALYSIS REPORT")
    print("="*90)
    print(f"Scenario: {analysis_result['scenario_name']}")
    print(f"Type: {analysis_result['scenario_type']}")
    if analysis_result['riser_type']:
        print(f"Riser Subtype: {analysis_result['riser_type']}")
    print(f"Manufacturing: {analysis_result['manufacturing']}")
    print("-"*90)
    
    # Input parameters
    print(f"\nINPUT PARAMETERS:")
    print(f"  Outer Diameter (OD):        {analysis_result['od']:.3f} inches")
    print(f"  Material Grade:             {analysis_result['grade']}")
    print(f"  SMYS:                       {analysis_result['smys_ksi']:.1f} ksi")
    print(f"  UTS:                        {analysis_result['uts_ksi']:.1f} ksi")
    print(f"  Design Internal Pressure:   {analysis_result['p_internal_psi']:.1f} psi ({analysis_result['p_internal_psi']/1000:.2f} ksi)")
    print(f"")
    print(f"  WATER DEPTH & EXTERNAL PRESSURE (Conservative Loading):")
    print(f"    LAT (Lowest Astronomical Tide):   {analysis_result['depth_lat_m']:.1f} m  →  {analysis_result['p_external_lat_psi']:.1f} psi (for Burst/Hoop)")
    print(f"    HAT (Highest Astronomical Tide):  {analysis_result['depth_hat_m']:.1f} m  →  {analysis_result['p_external_hat_psi']:.1f} psi (for Collapse/Prop/Bend)")
    print(f"")
    print(f"  Design Bending Strain:      {analysis_result['bending_strain']:.6f} ({analysis_result['bending_strain']*100:.2f}%)")
    print(f"  Ovality:                    {analysis_result['ovality']:.4f} ({analysis_result['ovality']*100:.2f}%)")
    print(f"  Corrosion Allowance:        {analysis_result['corrosion_allowance']:.4f} inches")
    print(f"  Mill Tolerance:             {analysis_result['mill_tolerance_percent']:.1f}%")
    
    # Find the least thickness result for detailed display
    least_thickness = analysis_result['least_thickness']
    recommended_thickness = analysis_result['recommended_thickness']
    
    if least_thickness is not None:
        # Find the result entry for least thickness
        least_result = None
        for res in analysis_result['results']:
            if res['wall_thickness'] == least_thickness:
                least_result = res
                break
        
        if least_result:
            print(f"\n{'='*90}")
            print(f"LIFE CYCLE CONDITION ANALYSIS - NOMINAL WT: {least_thickness:.4f} inches")
            print(f"{'='*90}")
            
            # Print results for each condition
            for cond_key in ['installation', 'hydrotest', 'operation']:
                cond_result = least_result['conditions'][cond_key]
                print_condition_results(cond_result, analysis_result['od'])
            
            # Detailed results for Operation condition (most critical)
            print(f"\n{'='*90}")
            print(f"DETAILED CALCULATIONS - OPERATION CONDITION (Corroded State)")
            print(f"{'='*90}")
            
            op_result = least_result['conditions']['operation']
            burst = op_result['burst']
            collapse = op_result['collapse']
            prop = op_result['propagation']
            bend = op_result['bending']
            hoop = op_result['hoop']
            
            print(f"\n1. Burst Pressure Check (API RP 1111 Section 4.3.1):")
            print(f"   Burst Pressure (P_b):       {burst['burst_pressure']:.2f} ksi")
            print(f"   Design Factors: f_d={burst['f_d']}, f_e={burst['f_e']}, f_t={burst['f_t']}")
            print(f"   Allowable Burst:            {burst['allowable_burst']:.2f} ksi")
            print(f"   Design Pressure (P_i-P_o):  {burst['design_pressure_diff']:.2f} ksi")
            print(f"   Check: {burst['design_pressure_diff']:.2f} <= {burst['allowable_burst']:.2f} → {'PASS' if burst['pass_fail'] else 'FAIL'}")
            
            print(f"\n2. External Collapse Check (API RP 1111 Section 4.3.2):")
            print(f"   Yield Collapse (P_y):       {collapse['yield_collapse']:.2f} ksi")
            print(f"   Elastic Collapse (P_e):     {collapse['elastic_collapse']:.2f} ksi")
            print(f"   Critical Collapse (P_c):    {collapse['critical_collapse']:.2f} ksi")
            print(f"   Collapse Mode:              {collapse['collapse_mode']} (P_y/P_e = {collapse['py_pe_ratio']:.2f})")
            print(f"   Collapse Factor (f_o):      {collapse['f_o']}")
            print(f"   Allowable Collapse:         {collapse['allowable_collapse']:.2f} ksi")
            print(f"   Design Pressure (P_o-P_i):  {collapse['design_pressure_diff']:.4f} ksi")
            print(f"   Check: {collapse['design_pressure_diff']:.4f} <= {collapse['allowable_collapse']:.2f} → {'PASS' if collapse['pass_fail'] else 'FAIL'}")
            
            print(f"\n3. Propagation Buckling Check (API RP 1111 Section 4.3.2.3):")
            print(f"   Propagation Pressure (P_p): {prop['propagation_pressure']:.2f} ksi")
            print(f"   Allowable (0.80*P_p):       {prop['allowable_pressure']:.2f} ksi")
            print(f"   Net External (P_o-P_i):     {prop['external_pressure']:.4f} ksi")
            print(f"   Check: {prop['external_pressure']:.4f} <= {prop['allowable_pressure']:.2f} → {'PASS' if prop['pass_fail'] else 'FAIL'}")
            
            print(f"\n4. Combined Bending and Pressure (API RP 1111 Section 4.3.2.2):")
            print(f"   Applied Bending Strain (ε): {bend['applied_bending_strain']:.6f} ({bend['applied_bending_strain']*100:.2f}%)")
            print(f"   Allowable Strain (ε_b):     {bend['allowable_bending_strain']:.6f} ({bend['allowable_bending_strain']*100:.2f}%)")
            print(f"   Bending Component (ε/ε_b):  {bend['bending_component']:.3f}")
            print(f"   Pressure Component:         {bend['pressure_component']:.3f}")
            print(f"   Ovality Function g(δ):      {bend['g_delta']:.3f}")
            print(f"   Interaction Ratio:          {bend['interaction_ratio']:.3f}")
            print(f"   Check: {bend['interaction_ratio']:.3f} <= {bend['g_delta']:.3f} → {'PASS' if bend['pass_fail'] else 'FAIL'}")
            
            print(f"\n5. Hoop Stress Check (ASME B31.4/B31.8):")
            print(f"   Hoop Stress:                {hoop['hoop_stress']:.0f} psi ({hoop['hoop_stress']/1000:.2f} ksi)")
            print(f"   Design Factor:              {hoop['design_factor']}")
            print(f"   Allowable Stress:           {hoop['allowable_stress']:.0f} psi ({hoop['allowable_stress']/1000:.2f} ksi)")
            print(f"   Check: {hoop['hoop_stress']:.0f} <= {hoop['allowable_stress']:.0f} → {'PASS' if hoop['pass_fail'] else 'FAIL'}")
    
    else:
        print("\nNO PASSING THICKNESS FOUND!")
        print("None of the standard wall thicknesses satisfy all design criteria")
        print("for ALL life cycle conditions (Installation, Hydrotest, Operation).")
        
        if analysis_result['results']:
            # Show which conditions fail for first thickness
            first_result = analysis_result['results'][0]
            wt = first_result['wall_thickness']
            print(f"\nFirst thickness analyzed: {wt:.4f} inches")
            print("-"*60)
            for cond_key in ['installation', 'hydrotest', 'operation']:
                cond = first_result['conditions'][cond_key]
                status = "PASS" if cond['all_pass'] else "FAIL"
                print(f"  {cond['condition_name']:<25} {status}")
                if not cond['all_pass']:
                    if not cond['burst']['pass_fail']: print(f"    - Burst: FAIL")
                    if not cond['collapse']['pass_fail']: print(f"    - Collapse: FAIL")
                    if not cond['propagation']['pass_fail']: print(f"    - Propagation: FAIL")
                    if not cond['bending']['pass_fail']: print(f"    - Bending: FAIL")
                    if not cond['hoop']['pass_fail']: print(f"    - Hoop: FAIL")
    
    # Summary
    print(f"\n{'='*90}")
    print(f"THICKNESS SELECTION SUMMARY")
    print("="*90)
    
    if least_thickness is not None:
        print(f"\n  NOMINAL WALL THICKNESS:     {least_thickness:.4f} inches")
        print(f"  RECOMMENDED THICKNESS:      {recommended_thickness:.4f} inches")
        
        # Calculate effective thickness for operation
        eff_op = least_thickness * (1 - analysis_result['mill_tolerance_percent']/100) - analysis_result['corrosion_allowance']
        print(f"\n  EFFECTIVE THICKNESSES:")
        print(f"    Installation/Hydrotest:   {least_thickness:.4f} inches (Nominal WT)")
        print(f"    Operation:                {eff_op:.4f} inches (After Mill Tol + {analysis_result['corrosion_allowance']:.4f}\" Corrosion)")
        
        print(f"\n  STATUS: All design criteria SATISFIED for all life cycle conditions")
        print(f"          ✓ Installation")
        print(f"          ✓ Hydrotest")
        print(f"          ✓ Operation")
    else:
        print(f"\n  LEAST THICKNESS:        NOT FOUND")
        print(f"  RECOMMENDED THICKNESS:  NOT FOUND")
        print(f"\n  STATUS: No standard thickness satisfies all criteria")
        print(f"          for all life cycle conditions.")
        print(f"          Consider:")
        print(f"          - Using a thicker non-standard size")
        print(f"          - Reducing corrosion allowance")
        print(f"          - Reviewing the design parameters")
    
    print("="*90)


def main():
    """Main execution function."""
    print("\n" + "="*90)
    print("RISER DESIGN ANALYSIS TOOL")
    print("API RP 1111 & ASME B31.4/B31.8 Compliance Checker")
    print("="*90)
    
    # Load input data
    print("\nLoading configuration from 'reference_data/input_data.json'...")
    data = load_input_data()
    
    project_info = data['project_info']
    scenarios = data['scenarios']
    
    print(f"Loaded {len(scenarios)} scenario(s) for analysis.")
    
    # Analyze each scenario
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n\n{'='*90}")
        print(f"ANALYZING SCENARIO {i} of {len(scenarios)}")
        print(f"{'='*90}")
        
        # Run analysis
        result = analyze_scenario(scenario, project_info)
        
        # Print results
        print_results(result)
    
    print("\n\n" + "="*90)
    print("ANALYSIS COMPLETE")
    print("="*90)
    print("\nAll scenarios have been analyzed.")
    print("Review the results above for design compliance.\n")


if __name__ == "__main__":
    main()
