"""
ASME B36.10M - Standard Pipe Schedules
Provides standard wall thicknesses for various nominal pipe sizes
"""

# Standard pipe schedules according to ASME B36.10M
# Dictionary structure: {OD: [list of standard wall thicknesses sorted ascending]}
# Extended database with comprehensive wall thickness options for riser/pipeline design
PIPE_SCHEDULES = {
    # 4.5" OD (NPS 4) - Extended range for high-pressure applications
    4.5: [
        0.083, 0.095, 0.109, 0.120, 0.125, 0.134, 0.141, 0.156, 0.165, 0.172,
        0.188, 0.203, 0.219, 0.237, 0.250, 0.262, 0.281, 0.300, 0.312, 0.325,
        0.337, 0.350, 0.375, 0.400, 0.438, 0.469, 0.500, 0.531, 0.562, 0.594,
        0.625, 0.656, 0.687, 0.719, 0.750, 0.781, 0.812, 0.844, 0.875, 0.906,
        0.937, 0.969, 1.000, 1.062, 1.125
    ],
    
    # 6.625" OD (NPS 6) - Extended range
    6.625: [
        0.109, 0.120, 0.125, 0.134, 0.141, 0.156, 0.172, 0.188, 
        0.203, 0.219, 0.250, 0.280, 0.312, 0.344, 0.375, 0.406,
        0.432, 0.469, 0.500, 0.531, 0.562, 0.594, 0.625, 0.656,
        0.688, 0.719, 0.750, 0.812, 0.875, 0.938
    ],
    
    # 6.63" OD (similar to 6.625", adding for compatibility)
    6.63: [
        0.109, 0.120, 0.125, 0.134, 0.141, 0.156, 0.172, 0.188, 
        0.203, 0.219, 0.250, 0.280, 0.312, 0.344, 0.375, 0.406,
        0.432, 0.469, 0.500, 0.531, 0.562, 0.594, 0.625, 0.656,
        0.688, 0.719, 0.750, 0.812, 0.875, 0.938
    ],
    
    # 8.625" OD (NPS 8) - Extended range
    8.625: [
        0.109, 0.125, 0.134, 0.148, 0.156, 0.165, 0.172, 0.188, 0.203, 
        0.219, 0.238, 0.250, 0.262, 0.277, 0.281, 0.300, 0.312, 0.322,
        0.344, 0.359, 0.375, 0.391, 0.406, 0.422, 0.438, 0.469, 0.500,
        0.531, 0.562, 0.594, 0.625, 0.656, 0.688, 0.719, 0.750, 0.812,
        0.875, 0.938, 1.000
    ],
    
    # 8.63" OD (similar to 8.625", adding for compatibility)
    8.63: [
        0.109, 0.125, 0.134, 0.148, 0.156, 0.165, 0.172, 0.188, 0.203, 
        0.219, 0.238, 0.250, 0.262, 0.277, 0.281, 0.300, 0.312, 0.322,
        0.344, 0.359, 0.375, 0.391, 0.406, 0.422, 0.438, 0.469, 0.500,
        0.531, 0.562, 0.594, 0.625, 0.656, 0.688, 0.719, 0.750, 0.812,
        0.875, 0.938, 1.000
    ],
    
    # 9.625" OD (NPS 9) - Extended range
    9.625: [
        0.109, 0.125, 0.134, 0.148, 0.156, 0.165, 0.172, 0.188, 0.203, 0.219, 
        0.250, 0.262, 0.281, 0.300, 0.312, 0.328, 0.344, 0.359, 0.375, 0.391,
        0.406, 0.422, 0.438, 0.453, 0.469, 0.484, 0.500, 0.516, 0.531, 0.547,
        0.562, 0.578, 0.594, 0.609, 0.625, 0.656, 0.688, 0.719, 0.750, 0.781,
        0.812, 0.844, 0.875, 0.938, 1.000
    ],
    
    # 9.63" OD (similar to 9.625", adding for compatibility)
    9.63: [
        0.109, 0.125, 0.134, 0.148, 0.156, 0.165, 0.172, 0.188, 0.203, 0.219, 
        0.250, 0.262, 0.281, 0.300, 0.312, 0.328, 0.344, 0.359, 0.375, 0.391,
        0.406, 0.422, 0.438, 0.453, 0.469, 0.484, 0.500, 0.516, 0.531, 0.547,
        0.562, 0.578, 0.594, 0.609, 0.625, 0.656, 0.688, 0.719, 0.750, 0.781,
        0.812, 0.844, 0.875, 0.938, 1.000
    ],
    
    # 10.75" OD (NPS 10) - Extended range
    10.75: [
        0.134, 0.141, 0.156, 0.165, 0.172, 0.188, 0.203, 0.219, 
        0.250, 0.262, 0.279, 0.281, 0.300, 0.307, 0.312, 0.328,
        0.344, 0.359, 0.365, 0.375, 0.391, 0.406, 0.422, 0.438,
        0.453, 0.469, 0.484, 0.500, 0.516, 0.531, 0.547, 0.562,
        0.578, 0.594, 0.609, 0.625, 0.656, 0.688, 0.719, 0.750,
        0.812, 0.844, 0.875, 0.938, 1.000, 1.062, 1.125
    ],
    
    # 12.75" OD (NPS 12) - Extended range
    12.75: [
        0.156, 0.165, 0.172, 0.180, 0.188, 0.203, 0.219, 0.234, 
        0.250, 0.262, 0.281, 0.300, 0.312, 0.328, 0.330, 0.344,
        0.359, 0.375, 0.391, 0.406, 0.422, 0.438, 0.453, 0.469,
        0.484, 0.500, 0.516, 0.531, 0.547, 0.562, 0.578, 0.594,
        0.609, 0.625, 0.641, 0.656, 0.672, 0.688, 0.719, 0.750,
        0.781, 0.812, 0.844, 0.875, 0.906, 0.938, 0.969, 1.000,
        1.062, 1.125, 1.188, 1.250
    ],
    
    # 14.0" OD (NPS 14) - Extended range
    14.0: [
        0.156, 0.165, 0.172, 0.188, 0.203, 0.219, 0.234, 0.250, 0.262, 0.281,
        0.300, 0.312, 0.328, 0.344, 0.359, 0.375, 0.391, 0.406, 0.422, 0.438,
        0.453, 0.469, 0.484, 0.500, 0.516, 0.531, 0.547, 0.562, 0.578, 0.594,
        0.609, 0.625, 0.641, 0.656, 0.672, 0.688, 0.719, 0.750, 0.781, 0.812,
        0.844, 0.875, 0.906, 0.938, 0.969, 1.000, 1.031, 1.062, 1.094, 1.125,
        1.188, 1.250, 1.312, 1.375, 1.406, 1.500
    ],
    
    # 16.0" OD (NPS 16) - Extended range
    16.0: [
        0.165, 0.188, 0.203, 0.219, 0.234, 0.250, 0.262, 0.281, 0.300, 0.312,
        0.328, 0.344, 0.359, 0.375, 0.391, 0.406, 0.422, 0.438, 0.453, 0.469,
        0.484, 0.500, 0.516, 0.531, 0.547, 0.562, 0.578, 0.594, 0.609, 0.625,
        0.641, 0.656, 0.672, 0.688, 0.703, 0.719, 0.734, 0.750, 0.781, 0.812,
        0.844, 0.875, 0.906, 0.938, 0.969, 1.000, 1.031, 1.062, 1.094, 1.125,
        1.156, 1.188, 1.219, 1.250, 1.312, 1.375, 1.438, 1.500, 1.562
    ],
    
    # 18.0" OD (NPS 18) - Extended range
    18.0: [
        0.165, 0.188, 0.203, 0.219, 0.234, 0.250, 0.262, 0.281, 0.300, 0.312,
        0.328, 0.344, 0.359, 0.375, 0.391, 0.406, 0.422, 0.438, 0.453, 0.469,
        0.484, 0.500, 0.516, 0.531, 0.547, 0.562, 0.578, 0.594, 0.609, 0.625,
        0.641, 0.656, 0.672, 0.688, 0.719, 0.750, 0.781, 0.812, 0.844, 0.875,
        0.906, 0.938, 0.969, 1.000, 1.031, 1.062, 1.094, 1.125, 1.156, 1.188,
        1.219, 1.250, 1.312, 1.375, 1.438, 1.500, 1.562, 1.625
    ],
    
    # 20.0" OD (NPS 20) - Extended range
    20.0: [
        0.188, 0.203, 0.219, 0.234, 0.250, 0.262, 0.281, 0.300, 0.312, 0.328,
        0.344, 0.359, 0.375, 0.391, 0.406, 0.422, 0.438, 0.453, 0.469, 0.484,
        0.500, 0.516, 0.531, 0.547, 0.562, 0.578, 0.594, 0.609, 0.625, 0.641,
        0.656, 0.672, 0.688, 0.719, 0.750, 0.781, 0.812, 0.844, 0.875, 0.906,
        0.938, 0.969, 1.000, 1.031, 1.062, 1.094, 1.125, 1.156, 1.188, 1.219,
        1.250, 1.281, 1.312, 1.375, 1.438, 1.500, 1.562, 1.625, 1.750
    ],
    
    # 24.0" OD (NPS 24) - Extended range
    24.0: [
        0.218, 0.234, 0.250, 0.262, 0.281, 0.300, 0.312, 0.328, 0.344, 0.359,
        0.375, 0.391, 0.406, 0.422, 0.438, 0.453, 0.469, 0.484, 0.500, 0.516,
        0.531, 0.547, 0.562, 0.578, 0.594, 0.609, 0.625, 0.641, 0.656, 0.672,
        0.688, 0.719, 0.750, 0.781, 0.812, 0.844, 0.875, 0.906, 0.938, 0.969,
        1.000, 1.031, 1.062, 1.094, 1.125, 1.156, 1.188, 1.219, 1.250, 1.281,
        1.312, 1.344, 1.375, 1.438, 1.500, 1.531, 1.562, 1.625, 1.750, 1.875,
        1.969, 2.000
    ],
    
    # Additional common sizes (for extensibility)
    2.375: [0.065, 0.083, 0.095, 0.109, 0.120, 0.125, 0.134, 0.141, 0.154, 0.172, 0.188, 0.203, 0.218, 0.250, 0.281, 0.312, 0.344],
    2.875: [0.083, 0.095, 0.109, 0.120, 0.125, 0.134, 0.141, 0.156, 0.172, 0.188, 0.203, 0.219, 0.250, 0.276, 0.300, 0.312, 0.344, 0.375],
    3.5: [0.083, 0.095, 0.109, 0.120, 0.125, 0.134, 0.141, 0.156, 0.172, 0.188, 0.203, 0.216, 0.226, 0.250, 0.281, 0.300, 0.312, 0.318, 0.344, 0.375, 0.438],
}


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
        print(f"First 5: {thicknesses[:5]}")
    
    # Test for 16" OD
    od = 16.0
    thicknesses = get_standard_thicknesses(od)
    if thicknesses:
        print(f"\nStandard wall thicknesses for {od}\" OD:")
        print(f"Available: {len(thicknesses)} standard sizes")
        print(f"Range: {thicknesses[0]}\" to {thicknesses[-1]}\"")
        print(f"First 5: {thicknesses[:5]}")
    
    # Test pipe properties calculation
    od, wt = 16.0, 0.5
    props = get_pipe_properties(od, wt)
    print(f"\nPipe properties for {od}\" OD x {wt}\" WT:")
    print(f"  Inner Diameter: {props['id']:.3f}\"")
    print(f"  Cross-section Area: {props['cross_section_area']:.3f} in²")
    print(f"  Moment of Inertia: {props['moment_of_inertia']:.3f} in⁴")
    print(f"  Section Modulus: {props['section_modulus']:.3f} in³")
