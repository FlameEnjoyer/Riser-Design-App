"""
Streamlit UI for Riser Design Analysis Tool
API RP 1111 & ASME B31.4/B31.8 Compliance Checker

This application provides a web-based interface for the riser analysis tool,
using the same calculation modules as the command-line version.
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path

# Import calculation modules
import calcs_burst
import calcs_collapse
import calcs_propagation
import calcs_bending
import calcs_hoop
import asme_b36_10

# Page configuration
st.set_page_config(
    page_title="Riser Design Analysis Tool",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .summary-box {
        background-color: #f0f8ff;
        border-left: 5px solid #1f77b4;
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .pass-status {
        color: #28a745;
        font-weight: bold;
    }
    .fail-status {
        color: #dc3545;
        font-weight: bold;
    }
    .metric-container {
        background-color: #ffffff;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #e8e8e8;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
        color: #2c3e50;
        font-size: 1.1rem;
        padding: 0.5rem 1.5rem;
        border: 2px solid #d0d0d0;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #d4d4d4;
        color: #1a252f;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: 2px solid #5a67d8;
        font-weight: 700;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* Table heading justification */
    .dataframe thead th {
        text-align: center !important;
    }
</style>
""", unsafe_allow_html=True)


def load_default_config():
    """Load default configuration from input_data.json"""
    config_path = Path("input_data.json")
    if config_path.exists():
        with open(config_path, 'r') as f:
            data = json.load(f)
            return data
    return None


def load_riser_database():
    """Load riser database from riser_database.json"""
    db_path = Path("riser_database.json")
    if db_path.exists():
        with open(db_path, 'r') as f:
            data = json.load(f)
            return data.get('risers', {})
    return {}


def get_riser_display_name(riser_id, riser_data):
    """Generate display name for dropdown with color highlighting"""
    name = riser_data.get('name', f'Riser {riser_id}')
    if riser_data.get('highlight', False):
        return f"🔶 ID {riser_id}: {name}"
    return f"ID {riser_id}: {name}"


def apply_riser_config(riser_data):
    """Apply riser configuration to session state"""
    # Geometry
    st.session_state['od'] = riser_data['geometry']['od_inches']
    st.session_state['ovality'] = riser_data['geometry']['ovality']
    st.session_state['corrosion_allowance'] = riser_data['geometry']['corrosion_allowance_inches']
    st.session_state['mill_tolerance'] = riser_data['geometry']['mill_tolerance_percent']
    
    # Material
    st.session_state['grade'] = riser_data['material']['grade']
    st.session_state['smys_ksi'] = riser_data['material']['smys_ksi']
    st.session_state['uts_ksi'] = riser_data['material']['uts_ksi']
    st.session_state['E_ksi'] = riser_data['material']['modulus_of_elasticity_ksi']
    st.session_state['poisson'] = riser_data['material']['poisson_ratio']
    
    # Type and Manufacturing
    st.session_state['pipe_type'] = riser_data['type']
    st.session_state['riser_type'] = riser_data['riser_type']
    st.session_state['manufacturing'] = riser_data['manufacturing']
    
    # Loads
    st.session_state['p_internal_psi'] = riser_data['loads']['design_internal_pressure_psi']
    st.session_state['depth_lat_m'] = riser_data['loads']['depth_lat_m']
    st.session_state['depth_hat_m'] = riser_data['loads']['depth_hat_m']
    st.session_state['bending_strain'] = riser_data['loads']['bending_strain']
    st.session_state['bending_strain_installation'] = riser_data['loads']['bending_strain_installation']
    st.session_state['fluid_content'] = riser_data['loads']['fluid_content']
    st.session_state['use_annulus_pressure'] = riser_data['loads']['use_annulus_pressure']
    
    # Calculate external pressure if not provided
    if riser_data['loads']['design_external_pressure_psi'] is not None:
        st.session_state['p_external_psi'] = riser_data['loads']['design_external_pressure_psi']
    else:
        st.session_state['p_external_psi'] = None
    
    # Hydrotest pressure
    st.session_state['p_hydrotest_psi'] = riser_data['loads']['hydrotest_pressure_psi']


def calculate_external_pressure(depth_m, water_density=64.0):
    """Calculate hydrostatic pressure from water depth"""
    # Convert depth from meters to feet
    depth_ft = depth_m * 3.28084
    # Pressure (psi) = water_density (lb/ft³) * depth (ft) / 144 (in²/ft²)
    pressure_psi = water_density * depth_ft / 144
    return pressure_psi


def get_effective_wall_thickness(nominal_wt, corrosion_allowance, mill_tolerance,
                                 use_corrosion, use_mill_tol):
    """Calculate effective wall thickness based on condition"""
    effective_wt = nominal_wt
    
    if use_mill_tol:
        effective_wt = effective_wt * (1 - mill_tolerance / 100)
    
    if use_corrosion:
        effective_wt = effective_wt - corrosion_allowance
    
    return effective_wt


def analyze_condition_streamlit(config, condition_key, nominal_wt):
    """
    Run analysis for a specific life cycle condition
    Returns: dict with all check results
    """
    # Life cycle condition definitions
    LIFE_CYCLE_CONDITIONS = {
        'installation': {
            'name': 'Installation',
            'description': 'Empty pipe during installation - nominal WT',
            'internal_pressure_factor': 0.0,
            'external_pressure_factor': 1.0,
            'bending_strain_key': 'bending_strain_installation',
            'use_corrosion_allowance': False,
            'use_mill_tolerance': False,
            'note': 'Empty pipe, external pressure + bending during lay operations'
        },
        'hydrotest': {
            'name': 'Hydrotest',
            'description': 'Pressure testing at 1.25x design pressure - nominal WT',
            'internal_pressure_factor': 1.25,
            'external_pressure_factor': 1.0,
            'bending_strain_key': 'bending_strain',
            'use_corrosion_allowance': False,
            'use_mill_tolerance': False,
            'note': 'Elevated internal pressure (1.25x), external pressure, bending'
        },
        'operation': {
            'name': 'Operation',
            'description': 'Normal operation with corroded wall thickness + mill tolerance',
            'internal_pressure_factor': 1.0,
            'external_pressure_factor': 1.0,
            'bending_strain_key': 'bending_strain',
            'use_corrosion_allowance': True,
            'use_mill_tolerance': True,
            'note': 'Mill tolerance + corrosion allowance deducted from wall thickness'
        }
    }
    
    condition = LIFE_CYCLE_CONDITIONS[condition_key]
    
    # Extract parameters
    od = config['od']
    ovality = config['ovality']
    corrosion_allowance = config['corrosion_allowance']
    mill_tolerance = config['mill_tolerance']
    
    smys_ksi = config['smys_ksi']
    uts_ksi = config['uts_ksi']
    E_ksi = config['E_ksi']
    poisson = config['poisson']
    
    design_p_i_psi = config['p_internal_psi']
    scenario_type = config['scenario_type']
    manufacturing = config['manufacturing']
    
    # Calculate effective wall thickness
    effective_wt = get_effective_wall_thickness(
        nominal_wt, 
        corrosion_allowance, 
        mill_tolerance,
        condition['use_corrosion_allowance'],
        condition['use_mill_tolerance']
    )
    
    # Determine internal pressure
    if condition_key == 'hydrotest':
        p_i_psi = config.get('hydrotest_pressure_psi', design_p_i_psi * 1.25)
    else:
        p_i_factor = condition['internal_pressure_factor']
        p_i_psi = design_p_i_psi * p_i_factor
    
    # Determine external pressures
    p_o_factor = condition['external_pressure_factor']
    p_o_hat_psi = config['p_external_hat_psi'] * p_o_factor
    p_o_lat_psi = config['p_external_lat_psi'] * p_o_factor
    
    # Determine bending strain
    bending_key = condition['bending_strain_key']
    bending_strain = config[bending_key]
    
    # Convert to ksi
    p_i_ksi = p_i_psi / 1000.0
    p_o_hat_ksi = p_o_hat_psi / 1000.0
    p_o_lat_ksi = p_o_lat_psi / 1000.0
    
    # Run all checks
    
    # 1. Burst (uses LAT - lower external pressure)
    burst_result = calcs_burst.check_burst_criteria(
        od, effective_wt, smys_ksi, uts_ksi, p_i_ksi, p_o_lat_ksi,
        scenario_type, manufacturing
    )
    
    # 2. Collapse (uses HAT - higher external pressure)
    collapse_result = calcs_collapse.check_collapse_criteria(
        od, effective_wt, smys_ksi, E_ksi, p_i_ksi, p_o_hat_ksi,
        manufacturing, poisson, ovality
    )
    
    # 3. Propagation (uses HAT)
    net_external_pressure_hat = p_o_hat_ksi - p_i_ksi
    propagation_result = calcs_propagation.check_propagation_criteria(
        od, effective_wt, smys_ksi, net_external_pressure_hat
    )
    
    # 4. Combined Bending (uses HAT)
    bending_result = calcs_bending.check_combined_bending_pressure(
        od, effective_wt, smys_ksi, E_ksi, p_i_ksi, p_o_hat_ksi,
        bending_strain, collapse_result['critical_collapse'], ovality
    )
    
    # 5. Hoop Stress (uses LAT - lower external pressure for conservatism)
    # Note: ASME B31.4 uses internal pressure only
    smys_psi = smys_ksi * 1000
    hoop_result = calcs_hoop.check_hoop_stress_criteria(
        od, effective_wt, p_i_psi, smys_psi, design_factor=0.72
    )
    
    # Check if all pass
    all_pass = (burst_result['pass_fail'] and 
                collapse_result['pass_fail'] and 
                propagation_result['pass_fail'] and 
                bending_result['pass_fail'] and 
                hoop_result['pass_fail'])
    
    return {
        'condition_name': condition['name'],
        'description': condition['description'],
        'note': condition['note'],
        'nominal_wt': nominal_wt,
        'effective_wt': effective_wt,
        'p_internal_psi': p_i_psi,
        'p_external_hat_psi': p_o_hat_psi,
        'p_external_lat_psi': p_o_lat_psi,
        'bending_strain': bending_strain,
        'burst': burst_result,
        'collapse': collapse_result,
        'propagation': propagation_result,
        'bending': bending_result,
        'hoop': hoop_result,
        'all_pass': all_pass
    }


def format_safety_factor(sf, is_reverse):
    """Format safety factor for display"""
    if sf == float('inf'):
        return "∞"
    elif sf > 999:
        return f">{999:.0f}"
    elif is_reverse:
        return "∞"
    else:
        return f"{sf:.2f}"


def create_results_dataframe(condition_result):
    """Create a DataFrame for displaying check results"""
    checks_data = []
    
    p_i = condition_result['p_internal_psi']
    
    # Burst
    burst = condition_result['burst']
    if p_i <= 0:
        sf_burst = "N/A"
        remark_burst = "P_i = 0"
    else:
        sf_burst = format_safety_factor(burst['safety_factor'], burst.get('is_reverse_load', False))
        remark_burst = "Reverse" if burst.get('is_reverse_load', False) else ""
    
    checks_data.append({
        'Check': '1. Burst Pressure',
        'Safety Factor': sf_burst,
        'Utilization': f"{burst['utilization']:.2%}" if p_i > 0 else "N/A",
        'Status': '✓ PASS' if burst['pass_fail'] else '✗ FAIL',
        'Remark': remark_burst
    })
    
    # Collapse
    collapse = condition_result['collapse']
    sf_collapse = format_safety_factor(collapse['safety_factor'], collapse.get('is_reverse_load', False))
    remark_collapse = "Reverse" if collapse.get('is_reverse_load', False) else ""
    
    checks_data.append({
        'Check': '2. External Collapse',
        'Safety Factor': sf_collapse,
        'Utilization': f"{collapse['utilization']:.2%}",
        'Status': '✓ PASS' if collapse['pass_fail'] else '✗ FAIL',
        'Remark': remark_collapse
    })
    
    # Propagation
    prop = condition_result['propagation']
    sf_prop = format_safety_factor(prop['safety_factor'], prop.get('is_reverse_load', False))
    remark_prop = "Reverse" if prop.get('is_reverse_load', False) else ""
    
    checks_data.append({
        'Check': '3. Propagation Buckling',
        'Safety Factor': sf_prop,
        'Utilization': f"{prop['utilization']:.2%}",
        'Status': '✓ PASS' if prop['pass_fail'] else '✗ FAIL',
        'Remark': remark_prop
    })
    
    # Bending
    bend = condition_result['bending']
    sf_bend = format_safety_factor(bend['safety_factor'], bend.get('is_reverse_load', False))
    remark_bend = "Reverse" if bend.get('is_reverse_load', False) else ""
    
    checks_data.append({
        'Check': '4. Combined Bending+Pressure',
        'Safety Factor': sf_bend,
        'Utilization': f"{bend['utilization']:.2%}",
        'Status': '✓ PASS' if bend['pass_fail'] else '✗ FAIL',
        'Remark': remark_bend
    })
    
    # Hoop
    hoop = condition_result['hoop']
    if p_i <= 0:
        sf_hoop = "N/A"
        remark_hoop = "P_i = 0"
    else:
        sf_hoop = format_safety_factor(hoop['safety_factor'], hoop.get('is_reverse_load', False))
        remark_hoop = "Reverse" if hoop.get('is_reverse_load', False) else ""
    
    checks_data.append({
        'Check': '5. Hoop Stress (ASME B31.4/B31.8)',
        'Safety Factor': sf_hoop,
        'Utilization': f"{hoop['utilization']:.2%}" if p_i > 0 else "N/A",
        'Status': '✓ PASS' if hoop['pass_fail'] else '✗ FAIL',
        'Remark': remark_hoop
    })
    
    return pd.DataFrame(checks_data)


def run_full_analysis(config):
    """Run full analysis for all standard thicknesses and conditions"""
    od = config['od']
    
    # Get standard thicknesses
    standard_thicknesses = asme_b36_10.get_standard_thicknesses(od)
    
    if standard_thicknesses is None:
        return None
    
    results = []
    least_thickness = None
    recommended_thickness = None
    
    condition_order = ['installation', 'hydrotest', 'operation']
    
    # Target utilization for recommended thickness (85% = 0.85)
    # This gives ~15% safety margin beyond the minimum passing
    TARGET_MAX_UTILIZATION = 0.85
    
    for wt in standard_thicknesses:
        condition_results = {}
        all_conditions_pass = True
        max_utilization = 0.0  # Track maximum utilization across all checks
        
        for cond_key in condition_order:
            cond_result = analyze_condition_streamlit(config, cond_key, wt)
            condition_results[cond_key] = cond_result
            if not cond_result['all_pass']:
                all_conditions_pass = False
            
            # Calculate max utilization from all 5 checks in this condition
            for check_name in ['burst', 'collapse', 'propagation', 'bending', 'hoop']:
                check_result = cond_result.get(check_name, {})
                util = check_result.get('utilization', 0.0)
                if util is not None and util != float('inf'):
                    max_utilization = max(max_utilization, util)
        
        result_entry = {
            'wall_thickness': wt,
            'all_pass': all_conditions_pass,
            'conditions': condition_results,
            'max_utilization': max_utilization
        }
        results.append(result_entry)
        
        # Find least thickness (first passing)
        if all_conditions_pass and least_thickness is None:
            least_thickness = wt
        
        # Find recommended thickness (first with utilization <= 85%)
        if all_conditions_pass and recommended_thickness is None:
            if max_utilization <= TARGET_MAX_UTILIZATION:
                recommended_thickness = wt
    
    # If no thickness meets the 85% target, use the least passing thickness
    if recommended_thickness is None and least_thickness is not None:
        recommended_thickness = least_thickness
    
    return {
        'results': results,
        'least_thickness': least_thickness,
        'recommended_thickness': recommended_thickness,
        'config': config
    }


# ========================================
# STREAMLIT UI LAYOUT
# ========================================

# Header
st.markdown('<div class="main-header">🔧 RISER DESIGN ANALYSIS TOOL</div>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">API RP 1111 & ASME B31.4/B31.8 Compliance Checker</p>', unsafe_allow_html=True)

# Load default configuration
default_config = load_default_config()

# ========================================
# SIDEBAR - Input Configuration
# ========================================

st.sidebar.title("⚙️ Configuration")

# Load riser database
riser_db = load_riser_database()

# Initialize session state for auto-fill
if 'current_riser_id' not in st.session_state:
    st.session_state['current_riser_id'] = None

# Riser Selection Dropdown
st.sidebar.subheader("🎯 Select Riser Configuration")

if riser_db:
    # Create dropdown options with highlighting indicator
    riser_options = {}
    for riser_id in sorted(riser_db.keys(), key=lambda x: int(x)):
        display_name = get_riser_display_name(riser_id, riser_db[riser_id])
        riser_options[display_name] = riser_id
    
    # Add color styling for highlighted risers in the dropdown
    st.sidebar.markdown("""
    <style>
    .highlight-notice {
        background: linear-gradient(90deg, #ff9a00 0%, #ffd700 100%);
        color: #000;
        padding: 8px;
        border-radius: 5px;
        font-weight: 600;
        margin-bottom: 10px;
        text-align: center;
    }
    </style>
    <div class="highlight-notice">🔶 Highlighted: ID 3 & ID 20</div>
    """, unsafe_allow_html=True)
    
    selected_display = st.sidebar.selectbox(
        "Riser ID",
        options=list(riser_options.keys()),
        index=0,
        help="Select a pre-configured riser. IDs 3 and 20 are highlighted."
    )
    
    selected_riser_id = riser_options[selected_display]
    
    # Auto-fill if selection changed
    if st.session_state['current_riser_id'] != selected_riser_id:
        st.session_state['current_riser_id'] = selected_riser_id
        apply_riser_config(riser_db[selected_riser_id])
        st.rerun()
else:
    st.sidebar.error("⚠️ Riser database not found. Please ensure riser_database.json exists.")
    selected_riser_id = None

st.sidebar.markdown("---")

# Display current configuration (read-only display)
if selected_riser_id and riser_db:
    current_riser = riser_db[selected_riser_id]
    
    st.sidebar.subheader("📋 Current Configuration")
    
    # Basic Info - display only
    with st.sidebar.expander("ℹ️ Pre-configured Values", expanded=False):
        st.text(f"Base Type: {current_riser['type']}")
        st.text(f"Base Riser: {current_riser['riser_type']}")
        st.text(f"Base Manufacturing: {current_riser['manufacturing']}")
    
    # Geometry - display in expander
    with st.sidebar.expander("📐 Geometry", expanded=False):
        st.text(f"OD: {current_riser['geometry']['od_inches']:.3f} in")
        st.text(f"Ovality: {current_riser['geometry']['ovality']:.4f}")
        st.text(f"Corrosion: {current_riser['geometry']['corrosion_allowance_inches']:.4f} in")
        st.text(f"Mill Tol: {current_riser['geometry']['mill_tolerance_percent']:.1f}%")
    
    # Material Properties - display in expander
    with st.sidebar.expander("🔩 Material Properties", expanded=False):
        st.text(f"Grade: {current_riser['material']['grade']}")
        st.text(f"SMYS: {current_riser['material']['smys_ksi']:.1f} ksi")
        st.text(f"UTS: {current_riser['material']['uts_ksi']:.1f} ksi")
        st.text(f"E: {current_riser['material']['modulus_of_elasticity_ksi']:.0f} ksi")
        st.text(f"ν: {current_riser['material']['poisson_ratio']:.2f}")
    
    # Loading Conditions - display in expander
    with st.sidebar.expander("⚡ Loading Conditions", expanded=False):
        st.text(f"Internal P: {current_riser['loads']['design_internal_pressure_psi']:.0f} psi")
        if current_riser['loads']['design_external_pressure_psi'] is not None:
            st.text(f"External P: {current_riser['loads']['design_external_pressure_psi']:.0f} psi")
        st.text(f"Hydrotest P: {current_riser['loads']['hydrotest_pressure_psi']:.0f} psi")
        st.text(f"Depth LAT: {current_riser['loads']['depth_lat_m']:.1f} m")
        st.text(f"Depth HAT: {current_riser['loads']['depth_hat_m']:.1f} m")
        st.text(f"Bending ε: {current_riser['loads']['bending_strain']:.4f}")
        st.text(f"Bending ε (inst): {current_riser['loads']['bending_strain_installation']:.4f}")
        st.text(f"Fluid: {current_riser['loads']['fluid_content']}")
        st.text(f"Use Annulus P: {current_riser['loads']['use_annulus_pressure']}")
    
    st.sidebar.markdown("---")
    
    # ========================================
    # EDITABLE PARAMETERS (Affect Calculations)
    # ========================================
    st.sidebar.subheader("🔧 Override Parameters")
    st.sidebar.markdown("*Modify these to affect calculation results:*")
    
    # Pipe Type - affects design factor (f_d)
    scenario_type = st.sidebar.selectbox(
        "Pipe Type",
        ["Pipeline", "Flowline", "Riser"],
        index=["Pipeline", "Flowline", "Riser"].index(current_riser['type']) if current_riser['type'] in ["Pipeline", "Flowline", "Riser"] else 2,
        help="Pipeline (f_d=0.90), Flowline/Riser (f_d=0.75) - Affects wall thickness requirements"
    )
    
    # Riser Subtype - documentation only
    riser_subtype = st.sidebar.selectbox(
        "Riser Subtype",
        ["", "TTR", "SCR", "Rigid", "Flexible"],
        index=["", "TTR", "SCR", "Rigid", "Flexible"].index(current_riser['riser_type']) if current_riser['riser_type'] in ["", "TTR", "SCR", "Rigid", "Flexible"] else 0,
        help="Documentation only - does not affect calculations"
    )
    
    # Manufacturing Method - affects weld efficiency and collapse factor
    manufacturing = st.sidebar.selectbox(
        "Manufacturing Method",
        ["Seamless", "DSAW", "ERW", "SAW"],
        index=["Seamless", "DSAW", "ERW", "SAW"].index(current_riser['manufacturing']) if current_riser['manufacturing'] in ["Seamless", "DSAW", "ERW", "SAW"] else 1,
        help="Affects weld efficiency (E_w) and collapse factor (F_c) - Impacts required wall thickness"
    )
    
    od = current_riser['geometry']['od_inches']
    ovality = current_riser['geometry']['ovality']
    corrosion_allowance = current_riser['geometry']['corrosion_allowance_inches']
    mill_tolerance = current_riser['geometry']['mill_tolerance_percent']
    
    grade = current_riser['material']['grade']
    smys_ksi = current_riser['material']['smys_ksi']
    uts_ksi = current_riser['material']['uts_ksi']
    E_ksi = current_riser['material']['modulus_of_elasticity_ksi']
    poisson = current_riser['material']['poisson_ratio']
    
    p_internal_psi = current_riser['loads']['design_internal_pressure_psi']
    depth_lat_m = current_riser['loads']['depth_lat_m']
    depth_hat_m = current_riser['loads']['depth_hat_m']
    bending_strain = current_riser['loads']['bending_strain']
    bending_strain_installation = current_riser['loads']['bending_strain_installation']
    hydrotest_pressure_psi = current_riser['loads']['hydrotest_pressure_psi']
    
    use_annulus_pressure = current_riser['loads']['use_annulus_pressure']
    if use_annulus_pressure and current_riser['loads']['design_external_pressure_psi'] is not None:
        p_external_design_psi = current_riser['loads']['design_external_pressure_psi']
        p_external_hat_psi = p_external_design_psi
        p_external_lat_psi = p_external_design_psi
    else:
        water_density = 64.0  # seawater
        p_external_hat_psi = calculate_external_pressure(depth_hat_m, water_density)
        p_external_lat_psi = calculate_external_pressure(depth_lat_m, water_density)
    
else:
    # Fallback if no riser selected
    scenario_type = "Riser"
    riser_subtype = ""
    manufacturing = "DSAW"
    od = 16.0
    ovality = 0.005
    corrosion_allowance = 0.125
    mill_tolerance = 12.5
    grade = "X-65"
    smys_ksi = 65.0
    uts_ksi = 77.0
    E_ksi = 30000.0
    poisson = 0.3
    p_internal_psi = 2500.0
    depth_lat_m = 100.0
    depth_hat_m = 105.0
    bending_strain = 0.0002
    bending_strain_installation = 0.0003
    hydrotest_pressure_psi = 3125.0
    water_density = 64.0
    p_external_hat_psi = calculate_external_pressure(depth_hat_m, water_density)
    p_external_lat_psi = calculate_external_pressure(depth_lat_m, water_density)

st.sidebar.markdown("---")

# Run Analysis Button
run_analysis = st.sidebar.button("🚀 Run Analysis", type="primary", use_container_width=True)

# ========================================
# MAIN AREA - Results Display
# ========================================

if run_analysis:
    # Prepare configuration dictionary
    config = {
        'scenario_type': scenario_type,
        'riser_subtype': riser_subtype,
        'manufacturing': manufacturing,
        'od': od,
        'ovality': ovality,
        'corrosion_allowance': corrosion_allowance,
        'mill_tolerance': mill_tolerance,
        'grade': grade,
        'smys_ksi': smys_ksi,
        'uts_ksi': uts_ksi,
        'E_ksi': E_ksi,
        'poisson': poisson,
        'p_internal_psi': p_internal_psi,
        'p_external_hat_psi': p_external_hat_psi,
        'p_external_lat_psi': p_external_lat_psi,
        'depth_hat_m': depth_hat_m,
        'depth_lat_m': depth_lat_m,
        'bending_strain': bending_strain,
        'bending_strain_installation': bending_strain_installation,
        'hydrotest_pressure_psi': hydrotest_pressure_psi
    }
    
    # Run full analysis
    with st.spinner("Running analysis for all standard wall thicknesses..."):
        analysis_result = run_full_analysis(config)
    
    if analysis_result is None:
        st.error(f"❌ No standard wall thicknesses available for OD {od}\"")
        st.info("Available OD sizes: " + ", ".join([f"{od}\"" for od in asme_b36_10.get_available_od_sizes()]))
    else:
        # ========================================
        # EXECUTIVE SUMMARY - Wall Thickness Results
        # ========================================
        st.markdown("## 📊 Executive Summary - Wall Thickness Results")
        
        least_thickness = analysis_result['least_thickness']
        recommended_thickness = analysis_result['recommended_thickness']
        
        if least_thickness is not None:
            # Get schedule name for recommended thickness
            schedule_names = asme_b36_10.get_schedule_for_thickness(od, recommended_thickness)
            schedule_str = "/".join(schedule_names) if schedule_names else "Custom"
            
            # Get utilization for both thicknesses
            least_util = None
            recommended_util = None
            for res in analysis_result['results']:
                if res['wall_thickness'] == least_thickness:
                    least_util = res.get('max_utilization', 0)
                if res['wall_thickness'] == recommended_thickness:
                    recommended_util = res.get('max_utilization', 0)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                least_util_pct = (least_util * 100) if least_util else 0
                st.markdown("""
                <div class="metric-container" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: 3px solid #5a67d8;">
                    <h3 style="color: #ffffff; margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">Least Thickness</h3>
                    <p style="font-size: 2.5rem; font-weight: bold; margin: 0.5rem 0; color: #ffffff;">{:.4f}"</p>
                    <p style="color: #f0f0f0; margin: 0; font-weight: 500;">Utilization: {:.1f}%</p>
                </div>
                """.format(least_thickness, least_util_pct), unsafe_allow_html=True)
            
            with col2:
                recommended_util_pct = (recommended_util * 100) if recommended_util else 0
                st.markdown("""
                <div class="metric-container" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border: 3px solid #e14d5a;">
                    <h3 style="color: #ffffff; margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">Recommended Thickness</h3>
                    <p style="font-size: 2.5rem; font-weight: bold; margin: 0.5rem 0; color: #ffffff;">{:.4f}"</p>
                    <p style="color: #f0f0f0; margin: 0; font-weight: 500;">Schedule {} | Util: {:.1f}%</p>
                </div>
                """.format(recommended_thickness, schedule_str, recommended_util_pct), unsafe_allow_html=True)
            
            with col3:
                d_over_t = od / recommended_thickness
                st.markdown("""
                <div class="metric-container" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); border: 3px solid #00d4e6;">
                    <h3 style="color: #ffffff; margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">D/t Ratio</h3>
                    <p style="font-size: 2.5rem; font-weight: bold; margin: 0.5rem 0; color: #ffffff;">{:.2f}</p>
                    <p style="color: #f0f0f0; margin: 0; font-weight: 500;">At Recommended WT</p>
                </div>
                """.format(d_over_t), unsafe_allow_html=True)
            
            st.success("✅ **Analysis Complete**: Design meets all API RP 1111 and ASME B31.4/B31.8 criteria for all life cycle conditions.")
            
            # Explanation of Least vs Recommended
            if least_thickness != recommended_thickness:
                st.info(f"ℹ️ **Note**: Least Thickness ({least_thickness:.4f}\") is the minimum passing wall thickness. "
                       f"Recommended Thickness ({recommended_thickness:.4f}\") provides additional margin with utilization ≤ 85%.")
            else:
                st.info(f"ℹ️ **Note**: Least and Recommended are the same because the minimum passing thickness already has utilization ≤ 85%.")
            
        else:
            st.error("❌ **No suitable wall thickness found!** All standard thicknesses failed one or more design criteria.")
            st.warning("Consider: Increasing OD, upgrading material grade, or reducing design pressures/bending strains.")
        
        st.markdown("---")
        
        # ========================================
        # DETAILED RESULTS - Tabbed by Condition
        # ========================================
        st.markdown("## 📋 Detailed Results by Life Cycle Condition")
        
        if least_thickness is not None:
            # Find the result entry for recommended thickness
            recommended_result = None
            for res in analysis_result['results']:
                if res['wall_thickness'] == recommended_thickness:
                    recommended_result = res
                    break
            
            if recommended_result:
                # Display input summary
                with st.expander("📝 Input Summary", expanded=False):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**Geometry**")
                        st.write(f"OD: {od}\"")
                        st.write(f"Nominal WT: {recommended_thickness}\" (Sch. {schedule_str})")
                        st.write(f"Ovality: {ovality:.4f}")
                        st.write(f"Corrosion: {corrosion_allowance}\"")
                        st.write(f"Mill Tol: {mill_tolerance}%")
                    
                    with col2:
                        st.markdown("**Material**")
                        st.write(f"Grade: {grade}")
                        st.write(f"SMYS: {smys_ksi} ksi")
                        st.write(f"UTS: {uts_ksi} ksi")
                        st.write(f"Type: {scenario_type}")
                        st.write(f"Mfg: {manufacturing}")
                    
                    with col3:
                        st.markdown("**Loading**")
                        st.write(f"P_internal: {p_internal_psi:.0f} psi")
                        st.write(f"LAT Depth: {depth_lat_m:.1f} m → {p_external_lat_psi:.1f} psi")
                        st.write(f"HAT Depth: {depth_hat_m:.1f} m → {p_external_hat_psi:.1f} psi")
                        st.write(f"Bending: {bending_strain:.6f}")
                
                # Create tabs for each condition
                tab1, tab2, tab3 = st.tabs(["🔧 Installation", "🧪 Hydrotest", "⚙️ Operation"])
                
                conditions = recommended_result['conditions']
                
                # Installation Tab
                with tab1:
                    inst_result = conditions['installation']
                    
                    st.markdown(f"### {inst_result['condition_name']}")
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 1rem; 
                                border-radius: 8px; 
                                border-left: 5px solid #5a67d8;
                                margin: 1rem 0;">
                        <p style="color: #ffffff; margin: 0; font-size: 1.1rem;">
                            <strong>📌 Note:</strong> {inst_result['note']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown("**Wall Thickness**")
                        st.write(f"Nominal WT: {inst_result['nominal_wt']:.4f}\"")
                        st.write(f"Effective WT: {inst_result['effective_wt']:.4f}\"")
                        st.write(f"D/t: {od/inst_result['effective_wt']:.2f}")
                    
                    with col2:
                        st.markdown("**Load Conditions**")
                        st.write(f"Internal Pressure: {inst_result['p_internal_psi']:.1f} psi")
                        st.write(f"External Pressure (HAT): {inst_result['p_external_hat_psi']:.1f} psi")
                        st.write(f"Bending Strain: {inst_result['bending_strain']:.6f} ({inst_result['bending_strain']*100:.3f}%)")
                    
                    st.markdown("**Design Check Results**")
                    df_inst = create_results_dataframe(inst_result)
                    
                    # Style the dataframe
                    def color_status(val):
                        if '✓' in val:
                            return 'background-color: #d4edda; color: #155724'
                        elif '✗' in val:
                            return 'background-color: #f8d7da; color: #721c24'
                        return ''
                    
                    styled_df = df_inst.style.map(color_status, subset=['Status'])
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                    
                    if inst_result['all_pass']:
                        st.success("✅ **OVERALL STATUS: PASS** - All checks satisfied")
                    else:
                        st.error("❌ **OVERALL STATUS: FAIL** - One or more checks failed")
                
                # Hydrotest Tab
                with tab2:
                    hydro_result = conditions['hydrotest']
                    
                    st.markdown(f"### {hydro_result['condition_name']}")
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); 
                                padding: 1rem; 
                                border-radius: 8px; 
                                border-left: 5px solid #f95d6a;
                                margin: 1rem 0;">
                        <p style="color: #2c3e50; margin: 0; font-size: 1.1rem; font-weight: 600;">
                            <strong>📌 Note:</strong> {hydro_result['note']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown("**Wall Thickness**")
                        st.write(f"Nominal WT: {hydro_result['nominal_wt']:.4f}\"")
                        st.write(f"Effective WT: {hydro_result['effective_wt']:.4f}\"")
                        st.write(f"D/t: {od/hydro_result['effective_wt']:.2f}")
                    
                    with col2:
                        st.markdown("**Load Conditions**")
                        st.write(f"Internal Pressure: {hydro_result['p_internal_psi']:.1f} psi")
                        st.write(f"External Pressure (HAT): {hydro_result['p_external_hat_psi']:.1f} psi")
                        st.write(f"Bending Strain: {hydro_result['bending_strain']:.6f} ({hydro_result['bending_strain']*100:.3f}%)")
                    
                    st.markdown("**Design Check Results**")
                    df_hydro = create_results_dataframe(hydro_result)
                    styled_df = df_hydro.style.map(color_status, subset=['Status'])
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                    
                    if hydro_result['all_pass']:
                        st.success("✅ **OVERALL STATUS: PASS** - All checks satisfied")
                    else:
                        st.error("❌ **OVERALL STATUS: FAIL** - One or more checks failed")
                
                # Operation Tab
                with tab3:
                    oper_result = conditions['operation']
                    
                    st.markdown(f"### {oper_result['condition_name']}")
                    st.markdown(f"""
                    <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); 
                                padding: 1rem; 
                                border-radius: 8px; 
                                border-left: 5px solid #0d9488;
                                margin: 1rem 0;">
                        <p style="color: #ffffff; margin: 0; font-size: 1.1rem;">
                            <strong>📌 Note:</strong> {oper_result['note']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown("**Wall Thickness**")
                        st.write(f"Nominal WT: {oper_result['nominal_wt']:.4f}\"")
                        st.write(f"Effective WT: {oper_result['effective_wt']:.4f}\"")
                        st.write(f"D/t: {od/oper_result['effective_wt']:.2f}")
                        st.caption(f"Deductions: Mill Tol ({mill_tolerance}%) + Corrosion ({corrosion_allowance}\")")
                    
                    with col2:
                        st.markdown("**Load Conditions**")
                        st.write(f"Internal Pressure: {oper_result['p_internal_psi']:.1f} psi")
                        st.write(f"External Pressure (HAT): {oper_result['p_external_hat_psi']:.1f} psi")
                        st.write(f"Bending Strain: {oper_result['bending_strain']:.6f} ({oper_result['bending_strain']*100:.3f}%)")
                    
                    st.markdown("**Design Check Results**")
                    df_oper = create_results_dataframe(oper_result)
                    styled_df = df_oper.style.map(color_status, subset=['Status'])
                    st.dataframe(styled_df, use_container_width=True, hide_index=True)
                    
                    if oper_result['all_pass']:
                        st.success("✅ **OVERALL STATUS: PASS** - All checks satisfied")
                    else:
                        st.error("❌ **OVERALL STATUS: FAIL** - One or more checks failed")
                    
                    # Detailed calculation breakdown for Operation
                    with st.expander("🔬 Detailed Calculation Breakdown (Operation)", expanded=False):
                        st.markdown("#### 1. Burst Pressure Check (API RP 1111 Sec 4.3.1)")
                        burst = oper_result['burst']
                        st.write(f"Burst Pressure (P_b): {burst['burst_pressure']:.2f} ksi")
                        st.write(f"Design Factors: f_d={burst['f_d']:.2f}, f_e={burst['f_e']:.2f}, f_t={burst['f_t']:.2f}")
                        st.write(f"Allowable Burst: {burst['allowable_burst']:.2f} ksi")
                        st.write(f"Design Pressure (P_i - P_o): {burst['design_pressure_diff']:.2f} ksi")
                        st.write(f"Check: {burst['design_pressure_diff']:.2f} ≤ {burst['allowable_burst']:.2f} → {'PASS' if burst['pass_fail'] else 'FAIL'}")
                        
                        st.markdown("#### 2. External Collapse Check (API RP 1111 Sec 4.3.2)")
                        collapse = oper_result['collapse']
                        st.write(f"Yield Collapse (P_y): {collapse['yield_collapse']:.2f} ksi")
                        st.write(f"Elastic Collapse (P_e): {collapse['elastic_collapse']:.2f} ksi")
                        st.write(f"Critical Collapse (P_c): {collapse['critical_collapse']:.2f} ksi")
                        st.write(f"Collapse Mode: {collapse['collapse_mode']} (P_y/P_e = {collapse['py_pe_ratio']:.2f})")
                        st.write(f"Collapse Factor (f_o): {collapse['f_o']:.1f}")
                        st.write(f"Allowable Collapse: {collapse['allowable_collapse']:.2f} ksi")
                        st.write(f"Net External Pressure (P_o - P_i): {collapse['design_pressure_diff']:.4f} ksi")
                        st.write(f"Check: {collapse['design_pressure_diff']:.4f} ≤ {collapse['allowable_collapse']:.2f} → {'PASS' if collapse['pass_fail'] else 'FAIL'}")
                        
                        st.markdown("#### 3. Propagation Buckling Check (API RP 1111 Sec 4.3.2.3)")
                        prop = oper_result['propagation']
                        st.write(f"Propagation Pressure (P_p): {prop['propagation_pressure']:.2f} ksi")
                        st.write(f"Allowable (0.80 × P_p): {prop['allowable_pressure']:.2f} ksi")
                        st.write(f"Net External (P_o - P_i): {prop['external_pressure']:.4f} ksi")
                        st.write(f"Check: {prop['external_pressure']:.4f} ≤ {prop['allowable_pressure']:.2f} → {'PASS' if prop['pass_fail'] else 'FAIL'}")
                        
                        st.markdown("#### 4. Combined Bending and Pressure (API RP 1111 Sec 4.3.2.2)")
                        bend = oper_result['bending']
                        st.write(f"Applied Bending Strain (ε): {bend['applied_bending_strain']:.6f} ({bend['applied_bending_strain']*100:.3f}%)")
                        st.write(f"Allowable Bending Strain (ε_b): {bend['allowable_bending_strain']:.6f} ({bend['allowable_bending_strain']*100:.3f}%)")
                        st.write(f"Bending Component (ε/ε_b): {bend['bending_component']:.3f}")
                        st.write(f"Pressure Component: {bend['pressure_component']:.3f}")
                        st.write(f"Ovality Function g(δ): {bend['g_delta']:.3f}")
                        st.write(f"Interaction Ratio: {bend['interaction_ratio']:.3f}")
                        st.write(f"Check: {bend['interaction_ratio']:.3f} ≤ {bend['g_delta']:.3f} → {'PASS' if bend['pass_fail'] else 'FAIL'}")
                        
                        st.markdown("#### 5. Hoop Stress Check (ASME B31.4/B31.8)")
                        hoop = oper_result['hoop']
                        st.write(f"Hoop Stress (S_H): {hoop['hoop_stress']:.0f} psi ({hoop['hoop_stress']/1000:.2f} ksi)")
                        st.write(f"Design Factor (F): {hoop['design_factor']:.2f}")
                        st.write(f"Allowable Stress (F × SMYS): {hoop['allowable_stress']:.0f} psi ({hoop['allowable_stress']/1000:.2f} ksi)")
                        st.write(f"Check: {hoop['hoop_stress']:.0f} ≤ {hoop['allowable_stress']:.0f} → {'PASS' if hoop['pass_fail'] else 'FAIL'}")
                
                st.markdown("---")
                
                # Additional information
                st.markdown("### 📌 Notes")
                st.info("""
                - **Infinite SF (∞)**: Indicates reverse loading or favorable condition where the failure mode cannot occur
                - **N/A**: Not applicable (e.g., burst/hoop checks when pipe is empty during installation)
                - **Conservative Loading**: HAT used for collapse/propagation/bending; LAT used for burst/hoop
                - **Type Impact**: Design factor f_d varies by type (Pipeline: 0.90, Flowline/Riser: 0.75)
                """)

else:
    # Initial state - show instructions
    st.info("""
    ### 👈 Configure your design parameters in the sidebar
    
    **Steps to run analysis:**
    1. **Select Riser ID** from the dropdown menu (24 pre-configured risers available)
       - 🔶 IDs 3 & 20 are highlighted for reference
    2. **Review Pre-configured Values** in the collapsible sections (Geometry, Material, Loading)
    3. **Override Parameters** (optional):
       - Pipe Type (Pipeline/Flowline/Riser) - affects design factor
       - Riser Subtype (TTR/SCR/Rigid/Flexible) - for documentation
       - Manufacturing Method (Seamless/DSAW/ERW/SAW) - affects weld efficiency & collapse factor
    4. Click **"🚀 Run Analysis"** button
    
    The tool will analyze all standard wall thicknesses and identify the minimum required thickness
    that satisfies API RP 1111 and ASME B31.4/B31.8 criteria for all three life cycle conditions:
    - **Installation** (empty pipe with bending)
    - **Hydrotest** (1.25× design pressure)
    - **Operation** (corroded state with mill tolerance)
    """)
    
    st.markdown("---")
    
    # Display some reference information
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📖 Design Factors (API RP 1111)")
        df_factors = pd.DataFrame({
            'Type': ['Pipeline', 'Flowline', 'Riser'],
            'Design Factor (f_d)': [0.90, 0.75, 0.75],
            'Application': ['Buried/Protected', 'Subsea/Seabed', 'Dynamic/Vertical']
        })
        st.dataframe(df_factors, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("### 🔧 Manufacturing Factors")
        df_mfg = pd.DataFrame({
            'Method': ['Seamless', 'ERW', 'DSAW', 'SAW'],
            'Weld Efficiency (f_e)': [1.00, 1.00, 0.85, 0.85],
            'Collapse Factor (f_o)': [0.70, 0.70, 0.60, 0.60]
        })
        st.dataframe(df_mfg, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p><strong>Riser Design Analysis Tool v1.0</strong></p>
    <p>Compliant with API RP 1111 (4th Ed.) & ASME B31.4/B31.8</p>
    <p>© 2025 | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)
