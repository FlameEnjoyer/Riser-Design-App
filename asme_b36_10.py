"""
ASME B36.10M - Standard Pipe Schedules
Provides standard wall thicknesses for various nominal pipe sizes
Data extracted from official ASME B36.10/B36.19 specification

Structure: OD (inches) -> {schedule_name: wall_thickness_inches}
Version: 2.0 - Updated December 2025
"""

# ASME B36.10 Schedule Database
# OD (inches) -> {schedule_name: wall_thickness_inches}
# Data from ASME B36.10/B36.19 specification tables
PIPE_SCHEDULE_DATA = {
    0.405: {"5S": 0.035, "10S": 0.049, "10": 0.049, "40S": 0.068, "STD": 0.068, "40": 0.068, "80S": 0.095, "XS": 0.095, "80": 0.095},
    0.54: {"5S": 0.049, "10S": 0.065, "10": 0.065, "40S": 0.088, "STD": 0.088, "40": 0.088, "80S": 0.119, "XS": 0.119, "80": 0.119},
    0.675: {"5S": 0.049, "10S": 0.065, "10": 0.065, "40S": 0.091, "STD": 0.091, "40": 0.091, "80S": 0.126, "XS": 0.126, "80": 0.126},
    0.84: {"5S": 0.065, "5": 0.065, "10S": 0.083, "10": 0.083, "40S": 0.109, "STD": 0.109, "40": 0.109, "80S": 0.147, "XS": 0.147, "80": 0.147, "160": 0.187, "XXS": 0.294},
    1.05: {"5S": 0.065, "5": 0.065, "10S": 0.083, "10": 0.083, "40S": 0.113, "STD": 0.113, "40": 0.113, "80S": 0.154, "XS": 0.154, "80": 0.154, "160": 0.218, "XXS": 0.308},
    1.315: {"5S": 0.065, "5": 0.065, "10S": 0.109, "10": 0.109, "40S": 0.133, "STD": 0.133, "40": 0.133, "80S": 0.179, "XS": 0.179, "80": 0.179, "160": 0.25, "XXS": 0.358},
    1.66: {"5S": 0.065, "5": 0.065, "10S": 0.109, "10": 0.109, "40S": 0.14, "STD": 0.14, "40": 0.14, "80S": 0.191, "XS": 0.191, "80": 0.191, "160": 0.25, "XXS": 0.382},
    1.9: {"5S": 0.065, "5": 0.065, "10S": 0.109, "10": 0.109, "40S": 0.145, "STD": 0.145, "40": 0.145, "80S": 0.2, "XS": 0.2, "80": 0.2, "160": 0.281, "XXS": 0.4},
    2.375: {"5S": 0.065, "5": 0.065, "10S": 0.109, "10": 0.109, "40S": 0.154, "STD": 0.154, "40": 0.154, "80S": 0.218, "XS": 0.218, "80": 0.218, "160": 0.343, "XXS": 0.436},
    2.875: {"5S": 0.083, "5": 0.083, "10S": 0.12, "10": 0.12, "40S": 0.203, "STD": 0.203, "40": 0.203, "80S": 0.276, "XS": 0.276, "80": 0.276, "160": 0.375, "XXS": 0.552},
    3.5: {"5S": 0.083, "5": 0.083, "10S": 0.12, "10": 0.12, "40S": 0.216, "STD": 0.216, "40": 0.216, "80S": 0.3, "XS": 0.3, "80": 0.3, "160": 0.437, "XXS": 0.6},
    4.0: {"5S": 0.083, "5": 0.083, "10S": 0.12, "10": 0.12, "40S": 0.226, "STD": 0.226, "40": 0.226, "80S": 0.318, "XS": 0.318, "80": 0.318, "XXS": 0.636},
    4.5: {"5S": 0.083, "5": 0.083, "10S": 0.12, "10": 0.12, "40S": 0.237, "STD": 0.237, "40": 0.237, "60": 0.281, "80S": 0.337, "XS": 0.337, "80": 0.337, "120": 0.437, "160": 0.531, "XXS": 0.674},
    5.0: {"40S": 0.247, "STD": 0.247, "80S": 0.355, "XS": 0.355, "XXS": 0.71},
    5.563: {"5S": 0.109, "5": 0.109, "10S": 0.134, "10": 0.134, "40S": 0.258, "STD": 0.258, "40": 0.258, "80S": 0.375, "XS": 0.375, "80": 0.375, "120": 0.5, "160": 0.625, "XXS": 0.75},
    6.625: {"5S": 0.109, "5": 0.109, "10S": 0.134, "10": 0.134, "40S": 0.28, "STD": 0.28, "40": 0.28, "80S": 0.432, "XS": 0.432, "80": 0.432, "120": 0.562, "160": 0.718, "XXS": 0.864},
    7.625: {"40S": 0.301, "STD": 0.301, "80S": 0.5, "XS": 0.5, "XXS": 0.875},
    8.625: {"5S": 0.109, "5": 0.109, "10S": 0.148, "10": 0.148, "20": 0.25, "30": 0.277, "40S": 0.322, "STD": 0.322, "40": 0.322, "60": 0.406, "80S": 0.5, "XS": 0.5, "80": 0.5, "100": 0.593, "120": 0.718, "140": 0.812, "XXS": 0.875, "160": 0.906},
    9.63: {"40S": 0.342, "STD": 0.342, "80S": 0.5, "XS": 0.5},
    10.75: {"5S": 0.134, "5": 0.134, "10S": 0.165, "10": 0.165, "20": 0.25, "30": 0.307, "40S": 0.365, "STD": 0.365, "40": 0.365, "60": 0.5, "80S": 0.5, "XS": 0.5, "80": 0.593, "100": 0.718, "120": 0.843, "140": 1.0, "160": 1.125},
    11.75: {"40S": 0.375, "STD": 0.375, "80S": 0.5, "XS": 0.5},
    12.75: {"5S": 0.156, "5": 0.165, "10S": 0.18, "10": 0.18, "20": 0.25, "30": 0.307, "40S": 0.375, "STD": 0.375, "40": 0.406, "60": 0.5, "80S": 0.5, "XS": 0.5, "80": 0.593, "100": 0.718, "120": 0.843, "140": 1.0, "160": 1.125},
    14.0: {"5S": 0.156, "10S": 0.188, "10": 0.25, "20": 0.312, "30": 0.375, "40S": 0.375, "STD": 0.375, "40": 0.437, "80S": 0.5, "XS": 0.5, "60": 0.593, "80": 0.75, "100": 0.937, "120": 1.093, "140": 1.25, "160": 1.406},
    16.0: {"5S": 0.165, "10S": 0.188, "10": 0.25, "20": 0.312, "30": 0.375, "40S": 0.375, "STD": 0.375, "40": 0.5, "80S": 0.5, "XS": 0.5, "60": 0.656, "80": 0.843, "100": 1.031, "120": 1.218, "140": 1.427, "160": 1.593},
    18.0: {"5S": 0.165, "10S": 0.188, "10": 0.25, "20": 0.312, "40S": 0.375, "STD": 0.375, "30": 0.437, "80S": 0.5, "XS": 0.5, "40": 0.562, "60": 0.75, "80": 0.937, "100": 1.156, "120": 1.375, "140": 1.562, "160": 1.781},
    20.0: {"5S": 0.188, "10S": 0.218, "10": 0.25, "20": 0.375, "40S": 0.375, "STD": 0.375, "30": 0.5, "80S": 0.5, "XS": 0.5, "40": 0.593, "60": 0.812, "80": 1.031, "100": 1.28, "120": 1.5, "140": 1.75, "160": 1.968},
    22.0: {"5S": 0.188, "10S": 0.218, "10": 0.25, "20": 0.375, "40S": 0.375, "STD": 0.375, "30": 0.5, "80S": 0.5, "XS": 0.5, "60": 0.875, "80": 1.125, "100": 1.375, "120": 1.625, "140": 1.875},
    24.0: {"5S": 0.218, "10S": 0.25, "10": 0.25, "20": 0.375, "40S": 0.375, "STD": 0.375, "80S": 0.5, "XS": 0.5, "30": 0.562, "40": 0.687, "60": 0.968, "80": 1.218, "100": 1.531, "120": 1.812},
    26.0: {"10": 0.312, "40S": 0.375, "STD": 0.375, "20": 0.5, "80S": 0.5, "XS": 0.5},
    28.0: {"10": 0.312, "40S": 0.375, "STD": 0.375, "20": 0.5, "30": 0.625},
    30.0: {"5S": 0.25, "10S": 0.312, "10": 0.312, "40S": 0.375, "STD": 0.375, "20": 0.5, "80S": 0.5, "XS": 0.5, "30": 0.625},
    32.0: {"10": 0.312, "40S": 0.375, "STD": 0.375, "20": 0.5, "80S": 0.5, "XS": 0.5, "30": 0.625, "40": 0.688},
    34.0: {"10": 0.312, "40S": 0.375, "STD": 0.375, "20": 0.5, "30": 0.625, "40": 0.688},
    36.0: {"10": 0.312, "40S": 0.375, "STD": 0.375, "80S": 0.5, "XS": 0.5, "30": 0.625, "40": 0.75},
}

# Legacy compatibility: OD -> [list of thicknesses]
# Convert schedule data to simple thickness lists for backward compatibility
PIPE_SCHEDULES = {}
for od, schedules in PIPE_SCHEDULE_DATA.items():
    PIPE_SCHEDULES[od] = sorted(set(schedules.values()))


def get_standard_thicknesses(od):
    """
    Get available standard wall thicknesses for a given outer diameter.
    
    Parameters:
    -----------
    od : float
        Outer diameter in inches
        
    Returns:
    --------
    list : List of standard wall thicknesses in inches (sorted ascending)
           Returns None if OD is not in the standard table
    """
    if od in PIPE_SCHEDULES:
        return sorted(PIPE_SCHEDULES[od])
    else:
        return None


def get_schedule_data(od):
    """
    Get schedule-to-thickness mapping for a given outer diameter.
    
    Parameters:
    -----------
    od : float
        Outer diameter in inches
        
    Returns:
    --------
    dict : Dictionary mapping schedule names to thicknesses
           Returns None if OD is not in the standard table
    """
    if od in PIPE_SCHEDULE_DATA:
        return PIPE_SCHEDULE_DATA[od]
    else:
        return None


def get_schedule_for_thickness(od, thickness, tolerance=0.001):
    """
    Get the schedule name(s) for a given OD and wall thickness.
    
    Parameters:
    -----------
    od : float
        Outer diameter in inches
    thickness : float
        Wall thickness in inches
    tolerance : float
        Tolerance for thickness matching (default 0.001")
        
    Returns:
    --------
    list : List of schedule names that match the thickness
           Returns empty list if no match found
    """
    if od not in PIPE_SCHEDULE_DATA:
        return []
    
    schedules = []
    for schedule_name, sched_thickness in PIPE_SCHEDULE_DATA[od].items():
        if abs(sched_thickness - thickness) <= tolerance:
            schedules.append(schedule_name)
    
    return schedules


def get_thickness_with_schedule(od, thickness, tolerance=0.001):
    """
    Get a formatted string showing thickness and matching schedule(s).
    
    Parameters:
    -----------
    od : float
        Outer diameter in inches
    thickness : float
        Wall thickness in inches
    tolerance : float
        Tolerance for thickness matching (default 0.001")
        
    Returns:
    --------
    str : Formatted string like '0.500" (Schedule 40S/XS)'
          or '0.500"' if no schedule match
    """
    schedules = get_schedule_for_thickness(od, thickness, tolerance)
    
    if schedules:
        schedule_str = "/".join(schedules)
        return f'{thickness:.3f}" (Schedule {schedule_str})'
    else:
        return f'{thickness:.3f}"'


def get_available_od_sizes():
    """
    Get list of all available outer diameters in the standard table.
    
    Returns:
    --------
    list : Sorted list of available OD sizes in inches
    """
    return sorted(PIPE_SCHEDULES.keys())


def add_custom_od(od, wall_thicknesses):
    """
    Add a custom OD with associated wall thicknesses to the schedule.
    
    Parameters:
    -----------
    od : float
        Outer diameter in inches
    wall_thicknesses : list
        List of wall thicknesses in inches
    """
    PIPE_SCHEDULES[od] = sorted(wall_thicknesses)


def get_pipe_properties(od, wt):
    """
    Calculate basic pipe geometric properties.
    
    Parameters:
    -----------
    od : float
        Outer diameter in inches
    wt : float
        Wall thickness in inches
        
    Returns:
    --------
    dict : Dictionary containing:
        - id: Inner diameter (inches)
        - cross_section_area: Cross-sectional area of metal (in²)
        - moment_of_inertia: Second moment of area (in⁴)
        - section_modulus: Section modulus (in³)
    """
    import math
    
    inner_diameter = od - 2 * wt
    
    # Cross-sectional area of metal
    area = math.pi / 4 * (od**2 - inner_diameter**2)
    
    # Second moment of area (I)
    I = math.pi / 64 * (od**4 - inner_diameter**4)
    
    # Section modulus (Z)
    Z = I / (od / 2)
    
    return {
        'id': inner_diameter,
        'cross_section_area': area,
        'moment_of_inertia': I,
        'section_modulus': Z
    }


if __name__ == "__main__":
    # Example usage
    print("ASME B36.10M Pipe Schedule Library")
    print("=" * 60)
    
    # Test for 4.5" OD
    od = 4.5
    thicknesses = get_standard_thicknesses(od)
    if thicknesses:
        print(f"\nStandard wall thicknesses for {od}\" OD:")
        print(f"Available: {len(thicknesses)} standard sizes")
        print(f"Range: {thicknesses[0]}\" to {thicknesses[-1]}\"")
    
    # Test for 16" OD
    od = 16.0
    thicknesses = get_standard_thicknesses(od)
    if thicknesses:
        print(f"\nStandard wall thicknesses for {od}\" OD:")
        print(f"Available: {len(thicknesses)} standard sizes")
        print(f"Range: {thicknesses[0]}\" to {thicknesses[-1]}\"")
    
    # Test schedule lookup
    print(f"\nSchedule lookup tests for OD = 16.0\":")
    test_thicknesses = [0.375, 0.5, 0.656, 0.843]
    for t in test_thicknesses:
        schedules = get_schedule_for_thickness(16.0, t)
        formatted = get_thickness_with_schedule(16.0, t)
        print(f"  {t}\" -> Schedules: {schedules} -> {formatted}")
    
    # Test pipe properties calculation
    od, wt = 16.0, 0.5
    props = get_pipe_properties(od, wt)
    print(f"\nPipe properties for {od}\" OD x {wt}\" WT:")
    print(f"  Inner Diameter: {props['id']:.3f}\"")
    print(f"  Cross-section Area: {props['cross_section_area']:.3f} in²")
    print(f"  Moment of Inertia: {props['moment_of_inertia']:.3f} in⁴")
    print(f"  Section Modulus: {props['section_modulus']:.3f} in³")
    
    # Show all available OD sizes
    print(f"\nAll available OD sizes ({len(get_available_od_sizes())} sizes):")
    print(get_available_od_sizes())
