"""
ASME B31.4/B31.8 - Hoop Stress Calculations
Circumferential stress due to internal pressure
"""

import math


def calculate_hoop_stress_barlow(p_internal, od, wt):
    """
    Calculate hoop stress using Barlow's formula (thin-wall approximation).
    
    Formula: S_h = P * D / (2 * t)
    
    This is the standard formula used in ASME B31.4 and B31.8 for pipelines.
    
    Parameters:
    -----------
    p_internal : float
        Internal pressure (psi or ksi)
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
        
    Returns:
    --------
    dict : Dictionary containing:
        - hoop_stress: Circumferential hoop stress (same units as pressure)
        - inner_diameter: Inner diameter (inches)
    """
    # Calculate inner diameter
    inner_diameter = od - 2 * wt
    
    # Barlow's formula: S_h = P * D / (2 * t)
    # Using outer diameter D
    hoop_stress = p_internal * od / (2 * wt)
    
    return {
        'hoop_stress': hoop_stress,
        'inner_diameter': inner_diameter
    }


def calculate_hoop_stress_lame(p_internal, p_external, od, wt, location='inner'):
    """
    Calculate hoop stress using Lame's equation (thick-wall theory).
    
    For thick-walled pipes, provides more accurate stress at inner or outer surface.
    
    At inner surface: S_h = (P_i * r_i² - P_o * r_o²) / (r_o² - r_i²) + (P_i - P_o) * r_i² * r_o² / [r² * (r_o² - r_i²)]
    Simplified at r = r_i (inner): S_h = [(P_i * r_i² - P_o * r_o²) - (P_i - P_o) * r_o²] / (r_o² - r_i²)
    
    For most pipeline applications, Barlow's formula is sufficient and conservative.
    
    Parameters:
    -----------
    p_internal : float
        Internal pressure (psi or ksi)
    p_external : float
        External pressure (psi or ksi)
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
    location : str
        'inner' or 'outer' surface (default 'inner')
        
    Returns:
    --------
    dict : Dictionary containing stress components
    """
    # Calculate radii
    r_o = od / 2
    r_i = (od - 2 * wt) / 2
    
    # Select radius for calculation
    if location == 'inner':
        r = r_i
    elif location == 'outer':
        r = r_o
    else:
        r = (r_i + r_o) / 2  # Mean radius
    
    # Lame's equation for hoop stress
    # S_h = (P_i*r_i² - P_o*r_o²)/(r_o² - r_i²) + (P_i - P_o)*r_i²*r_o² / [r²*(r_o² - r_i²)]
    
    term1 = (p_internal * r_i**2 - p_external * r_o**2) / (r_o**2 - r_i**2)
    
    if r > 0:
        term2 = (p_internal - p_external) * r_i**2 * r_o**2 / (r**2 * (r_o**2 - r_i**2))
    else:
        term2 = 0.0
    
    hoop_stress = term1 + term2
    
    return {
        'hoop_stress': hoop_stress,
        'inner_radius': r_i,
        'outer_radius': r_o,
        'location': location
    }


def get_design_factor_asme(code='B31.4', location='onshore'):
    """
    Get design factor for ASME codes.
    
    Parameters:
    -----------
    code : str
        ASME code: 'B31.4' (liquid), 'B31.8' (gas)
    location : str
        'onshore', 'offshore', 'class1', 'class2', 'class3', 'class4'
        
    Returns:
    --------
    float : Design factor F (or T for B31.4)
    """
    design_factors = {
        'B31.4': {
            'onshore': 0.72,
            'offshore': 0.72,
            'standard': 0.72
        },
        'B31.8': {
            'class1': 0.72,
            'class2': 0.60,
            'class3': 0.50,
            'class4': 0.40,
            'offshore': 0.72
        }
    }
    
    if code in design_factors:
        if location in design_factors[code]:
            return design_factors[code][location]
        else:
            # Default to most conservative
            return 0.72
    else:
        return 0.72


def check_hoop_stress_criteria(od, wt, p_internal, smys, 
                               design_factor=0.72):
    """
    Check hoop stress design criteria according to ASME B31.4 Section 402.3.
    
    Formula: S_H = P_i * D / (2 * t)
    Check: S_H <= Design_Factor * SMYS
    
    Note: Per ASME B31.4 Sec 402.3, hoop stress is calculated from
    internal design gage pressure only (not net pressure P_i - P_o).
    This equation may not be applicable for pipe D/t less than 20.
    
    Parameters:
    -----------
    od : float
        Outer diameter (inches)
    wt : float
        Wall thickness (inches)
    p_internal : float
        Internal design gage pressure (psi)
    smys : float
        Specified Minimum Yield Strength (psi)
    design_factor : float
        Design factor F (default 0.72 for offshore per ASME B31.4/B31.8)
        
    Returns:
    --------
    dict : Dictionary containing:
        - pass_fail: Boolean, True if passes criteria
        - hoop_stress: Calculated hoop stress
        - allowable_stress: Allowable hoop stress
        - utilization: Ratio of actual to allowable
        - margin: Safety margin (%)
        - design_factor: Applied design factor
        - safety_factor: SF = Allowable / Hoop Stress
    """
    # Use Barlow's formula per ASME B31.4 Sec 402.3: S_H = P_i * D / (2 * t)
    stress_result = calculate_hoop_stress_barlow(p_internal, od, wt)
    hoop_stress = stress_result['hoop_stress']
    
    # Calculate allowable stress per ASME B31.4: S_allowable = F × SMYS
    allowable_stress = design_factor * smys
    
    # Check criteria: S_H ≤ F × SMYS
    pass_fail = hoop_stress <= allowable_stress
    
    # Calculate utilization and safety factor
    # ASME B31.4 Sec 402.3: S_H = P_i × D / (2 × t)
    # Safety Factor = Allowable Stress / Hoop Stress = (F × SMYS) / S_H
    # SF > 1.0 means PASS
    
    if p_internal > 0 and hoop_stress > 0:
        # Normal hoop loading: positive internal pressure creates hoop stress
        utilization = hoop_stress / allowable_stress
        safety_factor = allowable_stress / hoop_stress
        is_reverse_load = False
    else:
        # No internal pressure (empty pipe) - no hoop stress concern
        utilization = 0.0
        safety_factor = float('inf')  # Infinite SF when no internal pressure
        is_reverse_load = True
    
    # Calculate safety margin
    if allowable_stress > 0:
        margin = ((allowable_stress - hoop_stress) / allowable_stress) * 100
    else:
        margin = 0.0
    
    return {
        'pass_fail': pass_fail,
        'hoop_stress': hoop_stress,
        'allowable_stress': allowable_stress,
        'utilization': utilization,
        'safety_factor': safety_factor,
        'is_reverse_load': is_reverse_load,
        'margin': margin,
        'design_factor': design_factor,
        'smys': smys,
        'p_internal': p_internal,
        'd_over_t': od / wt,
        'method': 'Barlow (ASME B31.4 Sec 402.3)'
    }


def calculate_required_thickness_barlow(p_internal, od, smys, design_factor=0.72):
    """
    Calculate required wall thickness using Barlow's formula.
    
    From: S_h = P * D / (2 * t) <= F * SMYS
    Solving for t: t >= P * D / (2 * F * SMYS)
    
    Parameters:
    -----------
    p_internal : float
        Internal pressure (psi or ksi)
    od : float
        Outer diameter (inches)
    smys : float
        Specified Minimum Yield Strength (same units as pressure)
    design_factor : float
        Design factor (default 0.72)
        
    Returns:
    --------
    float : Required minimum wall thickness (inches)
    """
    if smys > 0 and design_factor > 0:
        required_thickness = p_internal * od / (2 * design_factor * smys)
    else:
        required_thickness = 0.0
    
    return required_thickness


if __name__ == "__main__":
    # Example test cases per ASME B31.4 Section 402.3
    print("ASME B31.4 Section 402.3 - Hoop Stress Check")
    print("Formula: S_H = P_i × D / (2 × t)")
    print("Note: External pressure is NOT subtracted per ASME B31.4 Sec 402.3")
    print("=" * 70)
    
    # Test Case 1: TTR PIP Inner Tube
    print("\nTest Case 1: TTR PIP Inner Tube (4.5\" OD, X-80)")
    od = 4.5
    wt = 0.337  # Example wall thickness
    p_i = 5000.0  # 5000 psi internal (design gage pressure)
    smys = 80000.0  # 80 ksi = 80000 psi
    design_factor = 0.72
    
    result = check_hoop_stress_criteria(od, wt, p_i, smys, design_factor)
    
    print(f"  OD: {od}\" | WT: {wt}\"")
    print(f"  SMYS: {smys/1000:.0f} ksi")
    print(f"  Internal Design Pressure (P_i): {p_i} psi")
    print(f"  Design Factor (F): {result['design_factor']}")
    print(f"  Method: {result['method']}")
    print(f"  Hoop Stress (S_H): {result['hoop_stress']:.0f} psi ({result['hoop_stress']/1000:.2f} ksi)")
    print(f"  Allowable Stress (F×SMYS): {result['allowable_stress']:.0f} psi ({result['allowable_stress']/1000:.2f} ksi)")
    print(f"  Safety Factor: {result['safety_factor']:.2f}")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
    
    # Calculate required thickness
    t_req = calculate_required_thickness_barlow(p_i, od, smys, design_factor)
    print(f"  Required Thickness (Barlow): {t_req:.4f}\"")
    
    # Test Case 2: Rigid Riser
    print("\n\nTest Case 2: Rigid Riser (16\" OD, X-52)")
    od = 16.0
    wt = 0.5     # Example wall thickness
    p_i = 1400.0  # 1400 psi internal (design gage pressure)
    smys = 52000.0  # 52 ksi = 52000 psi
    design_factor = 0.72
    
    result = check_hoop_stress_criteria(od, wt, p_i, smys, design_factor)
    
    print(f"  OD: {od}\" | WT: {wt}\"")
    print(f"  SMYS: {smys/1000:.0f} ksi")
    print(f"  Internal Design Pressure (P_i): {p_i} psi")
    print(f"  Design Factor (F): {result['design_factor']}")
    print(f"  Method: {result['method']}")
    print(f"  Hoop Stress (S_H): {result['hoop_stress']:.0f} psi ({result['hoop_stress']/1000:.2f} ksi)")
    print(f"  Allowable Stress (F×SMYS): {result['allowable_stress']:.0f} psi ({result['allowable_stress']/1000:.2f} ksi)")
    print(f"  Safety Factor: {result['safety_factor']:.2f}")
    print(f"  Utilization: {result['utilization']:.3f} ({result['utilization']*100:.1f}%)")
    print(f"  Safety Margin: {result['margin']:.1f}%")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'}")
    
    # Calculate required thickness
    t_req = calculate_required_thickness_barlow(p_i, od, smys, design_factor)
    print(f"  Required Thickness (Barlow): {t_req:.4f}\"")
    
    # Test different design factors
    print("\n\nTest Case 3: Design Factor Comparison (16\" OD, X-52, 1400 psi)")
    design_factors_test = [0.40, 0.50, 0.60, 0.72]
    print(f"  OD: {od}\" | WT: {wt}\" | SMYS: {smys/1000} ksi | P_i: {p_i} psi")
    print(f"  {'Factor':<10} {'Allowable (psi)':<20} {'SF':<10} {'Utilization':<15} {'Status':<10}")
    print(f"  {'-'*65}")
    
    for df in design_factors_test:
        result = check_hoop_stress_criteria(od, wt, p_i, smys, df)
        status = 'PASS' if result['pass_fail'] else 'FAIL'
        print(f"  {df:<10.2f} {result['allowable_stress']:<20.0f} {result['safety_factor']:<10.2f} {result['utilization']:<15.3f} {status:<10}")
    
    # Test Case 4: Empty pipe (Installation condition)
    print("\n\nTest Case 4: Empty Pipe During Installation")
    p_i_empty = 0.0  # Empty pipe
    result = check_hoop_stress_criteria(od, wt, p_i_empty, smys, design_factor)
    print(f"  Internal Pressure: {p_i_empty} psi (empty pipe)")
    print(f"  Hoop Stress: {result['hoop_stress']:.0f} psi")
    print(f"  Is Reverse Load: {result['is_reverse_load']}")
    print(f"  Safety Factor: {'∞' if result['safety_factor'] == float('inf') else result['safety_factor']:.2f}")
    print(f"  Status: {'PASS' if result['pass_fail'] else 'FAIL'} (No hoop stress concern when P_i = 0)")
