"""
Riser Design Calculation Web App
API RP 1111 + ASME B31.4/B31.8 checks

Three Life Cycle Conditions with Multiple Wall Thickness Cases:
- Installation: 2 WT types (Nominal, Nominal-Tolerance)
- Hydrotest: 2 WT types (Nominal, Nominal-Tolerance)
- Operation: 4 WT types (all combinations of tolerance and corrosion)

Each WT type can be checked at Top and Bottom positions.
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple

import pandas as pd
import streamlit as st

from reference_data import asme_b36_10
from calculations import calcs_weight

# -----------------------------------------------------------------------------
# Constants and reference data
# -----------------------------------------------------------------------------
COLOR_PRIMARY = "#1e3a8a"
COLOR_SECONDARY = "#3b82f6"
COLOR_SUCCESS = "#10b981"
COLOR_ALERT = "#ef4444"

GRADE_PROPERTIES = {
    # API 5L Grades (Specification for Line Pipe)
    # Format: Grade: {SMYS (ksi), UTS (ksi)}
    "A25": {"smys_psi": 25000, "uts_psi": 45000},
    "A": {"smys_psi": 30000, "uts_psi": 48000},
    "B": {"smys_psi": 35000, "uts_psi": 60000},
    "X-42": {"smys_psi": 42000, "uts_psi": 60000},
    "X-46": {"smys_psi": 46000, "uts_psi": 63000},
    "X-52": {"smys_psi": 52000, "uts_psi": 66000},
    "X-56": {"smys_psi": 56000, "uts_psi": 71000},
    "X-60": {"smys_psi": 60000, "uts_psi": 75000},
    "X-65": {"smys_psi": 65000, "uts_psi": 77000},
    "X-70": {"smys_psi": 70000, "uts_psi": 82000},
    "X-80": {"smys_psi": 80000, "uts_psi": 90000},
    "X-90": {"smys_psi": 90000, "uts_psi": 100000},
    "X-100": {"smys_psi": 100000, "uts_psi": 110000},
    "X-120": {"smys_psi": 120000, "uts_psi": 130000},
}

MANUFACTURING_COLLAPSE_FACTOR = {
    "SMLS": 0.70,
    "ERW": 0.75,
    "DSAW": 0.60,
}

DEFAULT_E_PSI = 2.9e7
DEFAULT_POISSON = 0.30
DEFAULT_WATER_DENSITY = 64.0  # lb/ft^3

# Design life and corrosion parameters (from Team 8 data)
DESIGN_LIFE_YEARS = 20
CORROSION_RATE_PER_YEAR = 0.004  # inch/year
MILL_TOLERANCE = 0.125  # 12.5% = wall thickness factor 0.875
HYDROTEST_FACTOR = 1.25

TEAM8_REFERENCE = {
    "Multiphase Riser (ID 3)": {
        "od": 16.0,
        "wt": 0.750,
        "grade": "X-52",
        "design_pressure": 1400.0,  # Design pressure for sizing
        "shut_in_pressure": 1236.0,  # Shut-in pressure = internal pressure (Pi)
        "shut_in_location": "Subsea Wellhead",
        "water_depth": 920.0,  # Kedalam Laut (m)
        "fluid_type": "Multiphase",
        "fluid_sg": 0.57,
        "manufacturing": "SMLS",
        "design_category": "Riser",
        "ovality_type": "Other Type",
        "ovality": 0.005,  # 0.5%
    },
    "Oil Riser (ID 8)": {
        "od": 8.63,
        "wt": 0.500,
        "grade": "X-52",
        "design_pressure": 230.0,  # Design pressure for sizing
        "shut_in_pressure": 195.0,  # Shut-in pressure = internal pressure (Pi)
        "shut_in_location": "Subsea Wellhead",
        "water_depth": 960.0,  # Kedalam Laut (m)
        "fluid_type": "Oil",
        "fluid_sg": 0.82,
        "manufacturing": "SMLS",
        "design_category": "Riser",
        "ovality_type": "Other Type",
        "ovality": 0.005,
    },
}


def schedule_name_for_thickness(od: float, wt: float) -> str:
    names = asme_b36_10.get_schedule_for_thickness(od, wt)
    if not names:
        return "Custom"
    return "/".join(names)


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------
@dataclass
class PipeProperties:
    od_in: float
    wt_in: float
    grade: str
    manufacturing: str
    design_category: str  # "Pipeline" or "Riser"
    fluid_type: str  # Gas, Oil, Multiphase, Wet Gas
    fluid_sg: float
    smys_psi: float
    uts_psi: float
    ovality_type: str  # "Reel-lay" or "Other Type"
    ovality: float
    E_psi: float = DEFAULT_E_PSI
    poisson: float = DEFAULT_POISSON


@dataclass
class LoadingCondition:
    design_pressure_psi: float
    shut_in_pressure_psi: float
    shut_in_location: str  # "Subsea Wellhead" or "Top of Riser"
    water_depth_m: float
    riser_length_m: float  # For longitudinal tension calculation


# -----------------------------------------------------------------------------
# Life Cycle Analyzer
# -----------------------------------------------------------------------------
class LifeCycleAnalyzer:
    """Analyzes all three life cycle conditions: Installation, Hydrotest, Operation"""
    
    def __init__(self, pipe: PipeProperties, load: LoadingCondition):
        self.pipe = pipe
        self.load = load

    @staticmethod
    def _ft_from_m(depth_m: float) -> float:
        return depth_m * 3.28084

    def external_pressure_psi(self) -> float:
        """Calculate hydrostatic external pressure"""
        depth_ft = self._ft_from_m(self.load.water_depth_m)
        return DEFAULT_WATER_DENSITY * depth_ft / 144.0

    def external_pressure_psi_for_position(self, position: str) -> float:
        """
        Calculate external pressure based on riser position

        Parameters:
        -----------
        position : str
            "Top" or "Bottom"

        Returns:
        --------
        float : External pressure in psi

        Top Position: Atmospheric only (14.7 psi)
        Bottom Position: Atmospheric + Hydrostatic

        Physical Basis:
        - Top of riser is at sea surface → atmospheric pressure
        - Bottom of riser is at water depth → atmospheric + hydrostatic
        """
        ATMOSPHERIC_PSI = 14.7

        if position.lower() == "top":
            return ATMOSPHERIC_PSI
        else:  # bottom
            depth_ft = self._ft_from_m(self.load.water_depth_m)
            hydrostatic_psi = DEFAULT_WATER_DENSITY * depth_ft / 144.0
            return ATMOSPHERIC_PSI + hydrostatic_psi

    def calculate_mop(self) -> float:
        """
        Calculate MOP (Maximum Operating Pressure) per API RP 1111

        MOP = Shut-in Pressure - Hydrostatic Head of Riser Contents

        The hydrostatic head is the pressure exerted by the fluid column
        inside the riser from bottom to top.

        Formula:
        Hydrostatic Head (psi) = (fluid_sg × water_density_pcf) × riser_length_ft / 144

        Where:
        - fluid_sg: Fluid specific gravity (dimensionless)
        - water_density_pcf: 64 lb/ft³ (seawater)
        - riser_length_ft: Riser vertical length in feet
        - 144: Conversion factor from lb/ft² to psi

        Returns:
        --------
        float : MOP in psi

        Notes:
        - MOP is only different from shut-in when shut-in location is at Subsea Wellhead
        - When shut-in is at Top of Riser, MOP = shut-in pressure (no adjustment)
        - MOP represents the pressure at top of riser when shut-in valve closes at bottom
        """
        # If shut-in location is at top, MOP = shut-in (no adjustment needed)
        if self.load.shut_in_location == "Top of Riser":
            return self.load.shut_in_pressure_psi

        # Calculate hydrostatic head of riser contents
        riser_length_ft = self._ft_from_m(self.load.riser_length_m)
        fluid_density_pcf = self.pipe.fluid_sg * DEFAULT_WATER_DENSITY  # lb/ft³
        hydrostatic_head_psi = (fluid_density_pcf * riser_length_ft) / 144.0

        # MOP = Shut-in pressure at bottom - hydrostatic head
        mop = self.load.shut_in_pressure_psi - hydrostatic_head_psi

        return max(mop, 0.0)  # Ensure non-negative

    def calculate_hydrotest_pressure(self, position: str = "Top") -> float:
        """
        Calculate Hydrotest Pressure per API RP 1111 Appendix C and Table C.3

        Per API RP 1111 Appendix C:
        - Hydrotest pressure accounts for hydrostatic head of test fluid
        - Test pressure at top of riser = (Design × 1.25) - Hydrostatic Head
        - Test pressure at bottom = Design × 1.25 (full test pressure)

        Formula (from Appendix C Table C.3):
        Pt_top = (Pd × 1.25) - (ρ × g × H / 144)

        Where:
        - Pd: Design pressure (psi)
        - 1.25: Hydrotest factor (inverse of 0.8 design factor)
        - ρ: Test fluid density (lb/ft³)
        - g: Gravitational constant (included in density)
        - H: Riser height (ft)
        - 144: Conversion from lb/ft² to psi

        Parameters:
        -----------
        position : str
            "Top" or "Bottom" - riser position being tested

        Returns:
        --------
        float : Hydrotest pressure in psi

        Notes:
        - TOP position: Pressure reduced by hydrostatic head of test fluid column
        - BOTTOM position: Full test pressure (1.25 × design)
        - Test fluid assumed same as operating fluid (fluid_sg)
        - Follows API RP 1111 Appendix C Example Calculation methodology
        """
        # Base hydrotest pressure (1.25 × design pressure)
        base_hydrotest_pressure = self.load.design_pressure_psi * HYDROTEST_FACTOR

        # For BOTTOM position, use full test pressure
        if position.lower() == "bottom":
            return base_hydrotest_pressure

        # For TOP position, subtract hydrostatic head of test fluid
        # (similar to MOP calculation but for test fluid)
        riser_length_ft = self._ft_from_m(self.load.riser_length_m)

        # Test fluid density (assuming test fluid same as operating fluid)
        test_fluid_density_pcf = self.pipe.fluid_sg * DEFAULT_WATER_DENSITY  # lb/ft³

        # Hydrostatic head of test fluid column
        hydrostatic_head_psi = (test_fluid_density_pcf * riser_length_ft) / 144.0

        # Hydrotest pressure at top = Base test pressure - Hydrostatic head
        hydrotest_top = base_hydrotest_pressure - hydrostatic_head_psi

        return max(hydrotest_top, 0.0)  # Ensure non-negative

    def calculate_internal_pressure_at_position(self, position: str) -> float:
        """
        Calculate internal pressure at a specific riser position based on wellhead location.

        This handles the hydrostatic pressure variation along the riser.

        Parameters:
        -----------
        position : str
            "Top" or "Bottom" - riser position being analyzed

        Returns:
        --------
        float : Internal pressure in psi at the specified position

        Logic:
        ------
        Case 1: Wellhead at "Subsea Wellhead" (Bottom of Riser)
            - Bottom: Pi = Shut-in Pressure (full pressure at wellhead)
            - Top: Pi = Shut-in Pressure - Hydrostatic Head of Riser Contents (MOP)

        Case 2: Wellhead at "Top of Riser"
            - Top: Pi = Shut-in Pressure (full pressure at wellhead)
            - Bottom: Pi = Shut-in Pressure + Hydrostatic Head of Riser Contents
        """
        riser_length_ft = self._ft_from_m(self.load.riser_length_m)
        fluid_density_pcf = self.pipe.fluid_sg * DEFAULT_WATER_DENSITY  # lb/ft³
        hydrostatic_head_psi = (fluid_density_pcf * riser_length_ft) / 144.0

        if self.load.shut_in_location == "Top of Riser":
            # Wellhead at top: pressure increases going down
            if position.lower() == "top":
                return self.load.shut_in_pressure_psi
            else:  # bottom
                return self.load.shut_in_pressure_psi + hydrostatic_head_psi
        else:  # "Subsea Wellhead" - Wellhead at bottom
            # Wellhead at bottom: pressure decreases going up
            if position.lower() == "bottom":
                return self.load.shut_in_pressure_psi
            else:  # top
                return max(self.load.shut_in_pressure_psi - hydrostatic_head_psi, 0.0)

    def get_internal_pressure_for_check(self, condition_name: str, check_type: str, position: str = "Top") -> float:
        """
        Determine internal pressure based on condition, check type, and position

        Parameters:
        -----------
        condition_name : str
            "Installation", "Hydrotest", or "Operation"
        check_type : str
            "burst", "collapse", "propagation", "hoop", "longitudinal", "combined"
        position : str
            "Top" or "Bottom" - riser position being analyzed

        Returns:
        --------
        float : Internal pressure in psi

        CRITICAL LOGIC FOR OPERATION CONDITION:

        Wellhead Location affects internal pressure distribution:

        Case 1: Wellhead at "Subsea Wellhead" (Bottom)
            - Bottom Position: Higher internal pressure (at wellhead)
            - Top Position: Lower internal pressure (MOP = shut-in - hydrostatic head)

        Case 2: Wellhead at "Top of Riser"
            - Top Position: Shut-in pressure (at wellhead)
            - Bottom Position: Higher internal pressure (shut-in + hydrostatic head)

        Pressure Selection by Check Type at Bottom Position:
        - Strength checks (burst, hoop, longitudinal, combined) → Use DESIGN PRESSURE
        - Stability checks (collapse, propagation) → Use position-dependent internal pressure
        """
        if condition_name == "Installation":
            # Empty pipe during installation
            return 0.0

        elif condition_name == "Hydrotest":
            # Position-dependent hydrotest pressure per API RP 1111 Appendix C
            # TOP: (Design × 1.25) - Hydrostatic Head of Test Fluid
            # BOTTOM: Design × 1.25 (full test pressure)
            return self.calculate_hydrotest_pressure(position)

        elif condition_name == "Operation":
            # CRITICAL: Position and wellhead-location dependent pressure logic

            # Calculate position-dependent internal pressure
            position_pressure = self.calculate_internal_pressure_at_position(position)

            # TOP POSITION: Always use position-dependent pressure (MOP or shut-in based on wellhead loc)
            if position.lower() == "top":
                return position_pressure

            # BOTTOM POSITION: Check-type dependent
            else:
                # Strength checks (burst, hoop, longitudinal, combined) - use design pressure
                if check_type in ["burst", "hoop", "longitudinal", "combined"]:
                    return self.load.design_pressure_psi

                # Stability checks (collapse, propagation) - use position-dependent pressure
                elif check_type in ["collapse", "propagation"]:
                    return position_pressure

        return 0.0

    def calculate_longitudinal_load(self, wt_eff: float, p_internal: float,
                                     p_external: float, condition_name: str,
                                     position: str) -> Dict[str, Any]:
        """
        Calculate longitudinal tension per API RP 1111 Section 4.3.1.1

        CRITICAL CHANGE: Position-dependent applied tension

        Longitudinal Load Design:
        T_eff = T_a - P_i × A_i + P_o × A_o

        Acceptance Criterion:
        T_eff ≤ 0.60 × T_y

        Position Effects:
        - Top: T_a = void_submerged_weight × riser_length (maximum tension)
        - Bottom: T_a = 0 (supported by mudline/seabed)

        Where:
        - T_a: Applied axial tension from self-weight (lb)
        - T_eff: Effective tension accounting for pressure end-cap forces
        - T_y: Yield tension = SMYS × A_steel
        - P_i: Internal pressure (position-specific)
        - P_o: External pressure (position-specific)
        - A_i: Internal cross-sectional area
        - A_o: External cross-sectional area

        BUOYANCY NOTE: void_submerged_weight already accounts for buoyancy
        void_submerged = dry_weight - (water_density × displaced_volume)
        """
        # Calculate cross-sectional areas (in²)
        od = self.pipe.od_in
        id_val = od - 2 * wt_eff

        a_outer = math.pi / 4 * od**2  # External area
        a_inner = math.pi / 4 * id_val**2  # Internal area
        a_steel = a_outer - a_inner  # Steel cross-section

        # Calculate pipe weights using effective WT
        weights = calcs_weight.calculate_pipe_weights(
            od_inches=od,
            wt_inches=wt_eff,
            fluid_sg=self.pipe.fluid_sg,
            use_seawater=True
        )

        # Applied tension T_a from self-weight - POSITION DEPENDENT
        # BUOYANCY is accounted for in void_submerged_weight_plf
        void_submerged_plf = weights['void_submerged_weight_plf']

        if position.lower() == "top":
            # Top of riser: Full tension from entire suspended weight
            riser_length_ft = self._ft_from_m(self.load.riser_length_m)
            t_a_lb = void_submerged_plf * riser_length_ft
            riser_length_ft_display = riser_length_ft
        else:  # bottom
            # Bottom of riser: Supported by mudline/seabed
            t_a_lb = 0.0
            riser_length_ft_display = 0.0
        
        # Pressure end-cap forces
        # Internal pressure creates upward force (reduces tension)
        # External pressure creates downward force (increases tension)
        force_internal_lb = p_internal * a_inner  # lb (reduces tension)
        force_external_lb = p_external * a_outer  # lb (increases tension)
        
        # Effective tension (lb)
        t_eff_lb = t_a_lb - force_internal_lb + force_external_lb
        
        # Yield tension (lb)
        t_y_lb = self.pipe.smys_psi * a_steel
        
        # Allowable tension per API RP 1111: 0.60 × T_y
        allowable_tension_lb = 0.60 * t_y_lb
        
        # Safety factor
        if t_eff_lb <= 0:
            # Compression case (not covered by this check)
            safety_factor = float('inf')
            passes = True
            status = "Compression (N/A)"
        else:
            safety_factor = allowable_tension_lb / t_eff_lb
            passes = safety_factor >= 1.0
            status = "PASS" if passes else "FAIL"
        
        # Axial stress in pipe wall (psi)
        axial_stress_psi = t_eff_lb / a_steel if a_steel > 0 else 0
        
        return {
            "condition": condition_name,
            "position": position,
            "t_a_applied_lb": t_a_lb,
            "t_a_applied_kips": t_a_lb / 1000,
            "force_internal_lb": force_internal_lb,
            "force_external_lb": force_external_lb,
            "t_eff_effective_lb": t_eff_lb,
            "t_eff_effective_kips": t_eff_lb / 1000,
            "t_y_yield_lb": t_y_lb,
            "t_y_yield_kips": t_y_lb / 1000,
            "allowable_tension_lb": allowable_tension_lb,
            "allowable_tension_kips": allowable_tension_lb / 1000,
            "axial_stress_psi": axial_stress_psi,
            "axial_stress_ksi": axial_stress_psi / 1000,
            "safety_factor": safety_factor,
            "passes": passes,
            "status": status,
            "criterion": "T_eff ≤ 0.60 × T_y (API RP 1111 Section 4.3.1.1)",
            "a_outer_in2": a_outer,
            "a_inner_in2": a_inner,
            "a_steel_in2": a_steel,
            "void_submerged_plf": void_submerged_plf,
            "riser_length_ft": riser_length_ft_display,
        }
    
    def calculate_combined_load(self, wt_eff: float, p_internal: float,
                                 p_external: float, condition_name: str,
                                 position: str) -> Dict[str, Any]:
        """
        Calculate combined loading per API RP 1111 Section 4.3.1.2

        Combined Load Design:
        √[(P_i - P_o)² / P_b²] + (T_eff / T_y)² ≤ Design Factor

        Design Factors:
        - 0.90 for operational loads
        - 0.96 for extreme loads (storm, earthquake)
        - 0.96 for hydrotest loads

        Position affects longitudinal component through T_eff calculation.

        This is the most comprehensive check that combines:
        1. Pressure loading (burst/collapse)
        2. Longitudinal tension (from weight and pressure end-caps, position-dependent)
        """
        # Get longitudinal load results with position
        longitudinal = self.calculate_longitudinal_load(
            wt_eff, p_internal, p_external, condition_name, position
        )
        
        # Get burst pressure using class method
        burst_result = self.compute_burst(p_internal, p_external, wt_eff)
        p_b = burst_result["pb"]  # Burst pressure capacity
        
        # Differential pressure (positive = burst, negative = collapse)
        p_diff = p_internal - p_external
        
        # Pressure component: (P_i - P_o) / P_b
        # For collapse cases (negative p_diff), we still use absolute value
        # per API RP 1111 interpretation
        pressure_component = (p_diff / p_b) if p_b > 0 else 0
        
        # Tension component: T_eff / T_y
        t_eff = longitudinal["t_eff_effective_lb"]
        t_y = longitudinal["t_y_yield_lb"]
        tension_component = (t_eff / t_y) if t_y > 0 else 0
        
        # Combined load ratio
        combined_ratio = math.sqrt(pressure_component**2 + tension_component**2)
        
        # Determine design factor based on condition
        if condition_name == "Operation":
            design_factor = 0.90  # Operational loads
            factor_description = "0.90 (Operational)"
        elif condition_name == "Hydrotest":
            design_factor = 0.96  # Hydrotest loads
            factor_description = "0.96 (Hydrotest)"
        else:  # Installation
            design_factor = 0.96  # Extreme loads (conservative)
            factor_description = "0.96 (Extreme)"
        
        # Safety factor (design_factor / combined_ratio)
        if combined_ratio > 0:
            safety_factor = design_factor / combined_ratio
        else:
            safety_factor = float('inf')
        
        passes = combined_ratio <= design_factor
        status = "PASS" if passes else "FAIL"
        
        return {
            "condition": condition_name,
            "position": position,
            "p_internal_psi": p_internal,
            "p_external_psi": p_external,
            "p_diff_psi": p_diff,
            "p_b_burst_psi": p_b,
            "pressure_component": pressure_component,
            "t_eff_lb": t_eff,
            "t_y_lb": t_y,
            "tension_component": tension_component,
            "combined_ratio": combined_ratio,
            "design_factor": design_factor,
            "factor_description": factor_description,
            "safety_factor": safety_factor,
            "passes": passes,
            "status": status,
            "criterion": f"√[(P/Pb)² + (T/Ty)²] ≤ {design_factor} (API RP 1111 Section 4.3.1.2)",
        }

    def effective_wall_thickness(self, use_mill_tolerance: bool, use_corrosion: bool) -> float:
        """
        Calculate effective wall thickness per life cycle condition
        - Installation/Hydrotest: WT × 0.875 (mill tolerance only)
        - Operation: (WT × 0.875) - (corrosion_rate × design_life)
        """
        wt = self.pipe.wt_in
        
        # Apply mill tolerance (12.5% reduction = 0.875 factor)
        if use_mill_tolerance:
            wt = wt * (1.0 - MILL_TOLERANCE)
        
        # Apply corrosion (only for operation: rate × design life)
        if use_corrosion:
            corrosion_total = CORROSION_RATE_PER_YEAR * DESIGN_LIFE_YEARS
            wt = wt - corrosion_total
        
        return max(wt, 0.001)  # Ensure positive

    def _hoop_design_factor(self) -> float:
        """Design factor per ASME B31.4/B31.8 based on category and fluid type"""
        if self.pipe.design_category.lower() == "pipeline":
            return 0.72
        # Riser design factors
        if self.pipe.fluid_type.lower() in ["gas", "wet gas"]:
            return 0.50
        if self.pipe.fluid_type.lower() in ["oil", "multiphase"]:
            return 0.60
        return 0.72

    @staticmethod
    def _burst_design_factor(design_category: str) -> float:
        """Burst design factor per API RP 1111 Section 4.3.1"""
        return 0.90 if design_category.lower() == "pipeline" else 0.75

    def compute_burst(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        """
        Burst pressure check per API RP 1111 Section 4.3.1

        Formula (Barlow thin-wall approximation):
        P_b = 0.90 × (SMYS + UTS) × t / (D - t)

        Criterion: (P_i - P_o) ≤ f_d × f_e × f_t × P_b

        Where:
        - f_d = Design factor (0.75 for Riser/Flowline, 0.90 for Pipeline)
        - f_e = Weld joint factor (1.0 for seamless)
        - f_t = Temperature derating factor (1.0 for ambient)
        """
        fd = self._burst_design_factor(self.pipe.design_category)
        fe = 1.0  # Weld joint factor
        ft = 1.0  # Temperature factor
        od = self.pipe.od_in
        id_val = od - 2 * wt_eff
        smys = self.pipe.smys_psi
        uts = self.pipe.uts_psi

        # Burst pressure: P_b = 0.90 × (SMYS + UTS) × t / (D - t)
        pb = 0.90 * (smys + uts) * wt_eff / (od - wt_eff) if od > wt_eff else 0.0

        # Allowable burst pressure
        allowable_burst = fd * fe * ft * pb

        # Net internal pressure
        delta_p = p_internal - p_external

        if delta_p <= 0:
            sf = float("inf")
        else:
            sf = allowable_burst / delta_p

        return {
            "name": "Burst",
            "pb": pb,
            "allowable_burst": allowable_burst,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {
                "design_factor": fd,
                "joint_factor": fe,
                "temperature_factor": ft,
                "delta_p": delta_p,
                "p_internal": p_internal,
                "p_external": p_external,
                "od": od,
                "id": id_val,
                "wt_eff": wt_eff,
                "smys": smys,
                "uts": uts,
            },
        }

    def compute_collapse(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        """
        External collapse check per API RP 1111 Section 4.3.2

        Formulas:
        - Yield Collapse: P_y = 2 × SMYS × (t/D)
        - Elastic Collapse: P_e = 2 × E × (t/D)³ / [(1 - ν²) × (1 + δ)]
        - Critical Collapse: P_c = P_y × P_e / √(P_y² + P_e²)

        Criterion: (P_o - P_i) ≤ f_o × P_c

        Where:
        - f_o = Collapse factor (0.70 for SMLS/ERW, 0.60 for DSAW)
        - δ = Ovality (0.5% for Other Type, 1.0% for Reel-lay)
        """
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        E = self.pipe.E_psi
        nu = self.pipe.poisson
        ovality = self.pipe.ovality
        f_o = MANUFACTURING_COLLAPSE_FACTOR.get(self.pipe.manufacturing.upper(), 0.70)

        t_over_d = wt_eff / od
        d_over_t = od / wt_eff if wt_eff > 0 else float('inf')

        # Yield collapse: P_y = 2 × SMYS × (t/D)
        py = 2 * smys * t_over_d

        # Elastic collapse adjusted for ovality: P_e = 2 × E × (t/D)³ / [(1 - ν²) × (1 + δ)]
        pe = (2 * E * (t_over_d ** 3)) / ((1 - nu ** 2) * (1 + ovality))

        # Critical collapse: P_c = P_y × P_e / √(P_y² + P_e²)
        pc = (py * pe) / math.sqrt(py ** 2 + pe ** 2) if (py > 0 and pe > 0) else 0.0

        # Allowable collapse pressure
        allowable_collapse = f_o * pc

        # Determine collapse mode
        if py > 0 and pe > 0:
            py_pe_ratio = py / pe
            if py_pe_ratio < 1.5:
                collapse_mode = "Elastic"
            elif py_pe_ratio < 4.0:
                collapse_mode = "Plastic"
            else:
                collapse_mode = "Yield"
        else:
            py_pe_ratio = 0.0
            collapse_mode = "N/A"

        # Net external pressure
        delta_p = p_external - p_internal
        if delta_p <= 0:
            sf = float("inf")
        else:
            sf = allowable_collapse / delta_p

        return {
            "name": "Collapse",
            "py": py,
            "pe": pe,
            "pc": pc,
            "allowable_collapse": allowable_collapse,
            "collapse_factor": f_o,
            "collapse_mode": collapse_mode,
            "ovality": ovality,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {
                "delta_p": delta_p,
                "p_internal": p_internal,
                "p_external": p_external,
                "od": od,
                "wt_eff": wt_eff,
                "t_over_d": t_over_d,
                "d_over_t": d_over_t,
                "smys": smys,
                "E": E,
                "poisson": nu,
                "py_pe_ratio": py_pe_ratio,
            },
        }

    def compute_propagation(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        """
        Propagation buckling check per API RP 1111 Section 4.3.2.3

        Formula: P_p = 35 × SMYS × (t/D)^2.5

        Criterion: (P_o - P_i) ≤ f_p × P_p

        Where:
        - f_p = 0.80 (Propagation buckling design factor)
        - P_p = Propagation pressure (the pressure at which a buckle propagates)

        Note: Propagation buckling arrestors may be required if net external
        pressure exceeds this limit.
        """
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        fp = 0.80
        t_over_d = wt_eff / od
        d_over_t = od / wt_eff if wt_eff > 0 else float('inf')

        # Propagation pressure: P_p = 35 × SMYS × (t/D)^2.5
        pp = 35 * smys * (t_over_d ** 2.5)

        # Allowable propagation pressure
        allowable_prop = fp * pp

        # Net external pressure
        delta_p = p_external - p_internal

        if delta_p <= 0:
            sf = float("inf")
        else:
            sf = allowable_prop / delta_p

        return {
            "name": "Propagation",
            "pp": pp,
            "allowable_prop": allowable_prop,
            "design_factor": fp,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {
                "delta_p": delta_p,
                "p_internal": p_internal,
                "p_external": p_external,
                "od": od,
                "wt_eff": wt_eff,
                "t_over_d": t_over_d,
                "d_over_t": d_over_t,
                "smys": smys,
            },
        }

    def compute_hoop(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        """
        Hoop stress check per ASME B31.4 Section 402.3

        Formula (Barlow for thin-wall): S_H = (P_i - P_o) × D / (2 × t)

        Where:
        - S_H = Hoop stress (psi)
        - P_i = Internal pressure (psi)
        - P_o = External pressure (psi)
        - D = Outside diameter (inches)
        - t = Wall thickness (inches)

        Criterion: S_H ≤ F × SMYS

        SPECIAL CASE: For Installation condition (empty pipe, Pi=0),
        the hoop stress is caused by external pressure (compressive):
        S_H = P_o × D / (2 × t)

        This equation is applicable for D/t ≥ 20 (thin-wall assumption).
        """
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        design_factor = self._hoop_design_factor()
        d_over_t = od / wt_eff if wt_eff > 0 else float('inf')

        # Calculate differential pressure (always needed for details)
        delta_p = p_internal - p_external

        # Calculate hoop stress based on pressure conditions
        if wt_eff <= 0 or od <= wt_eff:
            hoop_stress = float("inf")
        elif p_internal <= 0:
            # Installation condition: empty pipe (Pi = 0)
            # Hoop stress from external pressure (compressive)
            # S_H = P_o × D / (2 × t)
            hoop_stress = p_external * od / (2 * wt_eff)
        else:
            # Normal operation: differential pressure
            # S_H = (P_i - P_o) × D / (2 × t)
            if delta_p <= 0:
                # External pressure exceeds internal - use absolute external pressure
                hoop_stress = abs(delta_p) * od / (2 * wt_eff)
            else:
                hoop_stress = delta_p * od / (2 * wt_eff)

        # Allowable stress: S_allowable = F × SMYS
        allowable = design_factor * smys

        # Safety factor: SF = S_allowable / S_H
        if hoop_stress > 0:
            sf = allowable / hoop_stress
        else:
            sf = float("inf")

        return {
            "name": "Hoop Stress",
            "hoop_stress": hoop_stress,
            "design_factor": design_factor,
            "allowable": allowable,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {
                "delta_p": delta_p,
                "p_internal": p_internal,
                "p_external": p_external,
                "od": od,
                "wt_eff": wt_eff,
                "d_over_t": d_over_t,
                "smys": smys,
            },
        }

    def analyze_condition(self, condition_name: str, p_internal: float, 
                          use_mill_tolerance: bool, use_corrosion: bool) -> Dict[str, Any]:
        """Analyze one life cycle condition"""
        p_external = self.external_pressure_psi()
        wt_eff = self.effective_wall_thickness(use_mill_tolerance, use_corrosion)
        
        # Calculate pipe weights for this condition
        weights = calcs_weight.calculate_pipe_weights(
            od_inches=self.pipe.od_in,
            wt_inches=wt_eff,  # Use effective WT for this condition
            fluid_sg=self.pipe.fluid_sg,
            use_seawater=True
        )

        burst = self.compute_burst(p_internal, p_external, wt_eff)
        collapse = self.compute_collapse(p_internal, p_external, wt_eff)
        propagation = self.compute_propagation(p_internal, p_external, wt_eff)
        hoop = self.compute_hoop(p_internal, p_external, wt_eff)
        
        # NEW: Calculate longitudinal tension (Section 4.3.1.1)
        longitudinal = self.calculate_longitudinal_load(wt_eff, p_internal, condition_name)
        
        # NEW: Calculate combined loading (Section 4.3.1.2)
        combined = self.calculate_combined_load(wt_eff, p_internal, condition_name)

        checks = [burst, collapse, propagation, hoop]
        limiting = min(
            checks,
            key=lambda c: c["safety_factor"] if c["safety_factor"] != float("inf") else float("inf"),
        )
        # Update all_pass to include longitudinal and combined checks
        all_pass = all(c["pass_fail"] for c in checks) and longitudinal["passes"] and combined["passes"]

        return {
            "condition_name": condition_name,
            "p_internal_psi": p_internal,
            "p_external_psi": p_external,
            "wt_nominal": self.pipe.wt_in,
            "wt_effective": wt_eff,
            "mill_tolerance_applied": use_mill_tolerance,
            "corrosion_applied": use_corrosion,
            "weights": weights,
            "checks": checks,
            "longitudinal": longitudinal,
            "combined": combined,
            "all_pass": all_pass,
            "limiting": limiting,
        }

    def analyze_condition_at_position(
        self,
        condition_name: str,  # "Installation", "Hydrotest", "Operation"
        position: str,        # "Top" or "Bottom"
        use_mill_tolerance: bool,
        use_corrosion: bool
    ) -> Dict[str, Any]:
        """
        Analyze one life cycle condition at a specific riser position

        This is the NEW core analysis method that replaces analyze_condition()
        for the 6-condition analysis (3 stages × 2 positions).

        Key Differences from Old Method:
        1. Position-dependent external pressure (Po)
        2. Check-type-dependent internal pressure (Pi) for Operation
        3. Position-dependent axial loading (T_a)

        Parameters:
        -----------
        condition_name : str
            "Installation", "Hydrotest", or "Operation"
        position : str
            "Top" or "Bottom"
        use_mill_tolerance : bool
            Apply 12.5% mill tolerance to WT
        use_corrosion : bool
            Apply corrosion allowance to WT

        Returns:
        --------
        Dict containing:
        - Position-specific pressures for each check
        - All 7 check results
        - Overall pass/fail status
        """
        # Calculate position-specific external pressure
        p_external = self.external_pressure_psi_for_position(position)

        # Calculate effective wall thickness (unchanged logic)
        wt_eff = self.effective_wall_thickness(use_mill_tolerance, use_corrosion)

        # Calculate pipe weights for this condition
        weights = calcs_weight.calculate_pipe_weights(
            od_inches=self.pipe.od_in,
            wt_inches=wt_eff,
            fluid_sg=self.pipe.fluid_sg,
            use_seawater=True
        )

        # Run pressure-only checks with check-type-specific internal pressure
        # NOW WITH MOP SUPPORT: position affects collapse/propagation pressures

        # 1. Burst check - uses design pressure (no MOP)
        p_i_burst = self.get_internal_pressure_for_check(condition_name, "burst", position)
        burst = self.compute_burst(p_i_burst, p_external, wt_eff)

        # 2. Collapse check - uses shut-in/MOP depending on position
        p_i_collapse = self.get_internal_pressure_for_check(condition_name, "collapse", position)
        collapse = self.compute_collapse(p_i_collapse, p_external, wt_eff)

        # 3. Propagation check - uses shut-in/MOP depending on position
        p_i_propagation = self.get_internal_pressure_for_check(condition_name, "propagation", position)
        propagation = self.compute_propagation(p_i_propagation, p_external, wt_eff)

        # 4. Hoop check - uses design pressure (no MOP)
        p_i_hoop = self.get_internal_pressure_for_check(condition_name, "hoop", position)
        hoop = self.compute_hoop(p_i_hoop, p_external, wt_eff)

        # 5. Longitudinal tension - uses design pressure, POSITION-AWARE
        p_i_longitudinal = self.get_internal_pressure_for_check(condition_name, "longitudinal", position)
        longitudinal = self.calculate_longitudinal_load(
            wt_eff, p_i_longitudinal, p_external, condition_name, position
        )

        # 6. Combined loading - uses design pressure, POSITION-AWARE
        p_i_combined = self.get_internal_pressure_for_check(condition_name, "combined", position)
        combined = self.calculate_combined_load(
            wt_eff, p_i_combined, p_external, condition_name, position
        )

        # Collect pressure-only checks
        checks = [burst, collapse, propagation, hoop]

        # Find limiting check among pressure-only checks
        limiting = min(
            checks,
            key=lambda c: c["safety_factor"] if c["safety_factor"] != float("inf") else float("inf"),
        )

        # Overall pass/fail includes all 6 checks (4 pressure + longitudinal + combined)
        all_pass = (
            all(c["pass_fail"] for c in checks) and
            longitudinal["passes"] and
            combined["passes"]
        )

        # Calculate MOP for information display
        mop_psi = self.calculate_mop()
        mop_active = (
            condition_name == "Operation" and
            self.load.shut_in_location == "Subsea Wellhead" and
            position.lower() == "top"
        )

        return {
            "condition_name": condition_name,
            "position": position,
            # Store pressures used for each check type (for UI display)
            "p_internal_burst": p_i_burst,      # Used by: burst, hoop, longitudinal, combined
            "p_internal_collapse": p_i_collapse,  # Used by: collapse, propagation
            "p_external_psi": p_external,
            "wt_nominal": self.pipe.wt_in,
            "wt_effective": wt_eff,
            "mill_tolerance_applied": use_mill_tolerance,
            "corrosion_applied": use_corrosion,
            "weights": weights,
            "checks": checks,
            "longitudinal": longitudinal,
            "combined": combined,
            "all_pass": all_pass,
            "limiting": limiting,
            # MOP information
            "mop_psi": mop_psi,
            "mop_active": mop_active,
            "shut_in_location": self.load.shut_in_location,
        }

    def get_wt_type_description(self, use_mill_tolerance: bool, use_corrosion: bool) -> str:
        """Generate description for wall thickness type"""
        if not use_mill_tolerance and not use_corrosion:
            return "Nominal"
        elif use_mill_tolerance and not use_corrosion:
            return "Nominal - Tolerance"
        elif not use_mill_tolerance and use_corrosion:
            return "Nominal - Corrosion"
        else:  # both
            return "Nominal - Tolerance - Corrosion"

    def get_wt_type_short(self, use_mill_tolerance: bool, use_corrosion: bool) -> str:
        """Generate short key for wall thickness type"""
        if not use_mill_tolerance and not use_corrosion:
            return "nominal"
        elif use_mill_tolerance and not use_corrosion:
            return "with_tol"
        elif not use_mill_tolerance and use_corrosion:
            return "with_corr"
        else:  # both
            return "with_tol_corr"

    def run_all_conditions(self) -> Dict[str, Any]:
        """
        Analyze all life cycle conditions with multiple wall thickness types:

        Installation (2 WT types × 2 positions = 4 sub-conditions):
        - Nominal WT (no tolerance, no corrosion)
        - Nominal - Tolerance (with mill tolerance)

        Hydrotest (2 WT types × 2 positions = 4 sub-conditions):
        - Nominal WT (no tolerance, no corrosion)
        - Nominal - Tolerance (with mill tolerance)

        Operation (4 WT types × 2 positions = 8 sub-conditions):
        - Nominal WT (no tolerance, no corrosion)
        - Nominal - Tolerance (with mill tolerance only)
        - Nominal - Corrosion (with corrosion only)
        - Nominal - Tolerance - Corrosion (with both)

        Total: 16 sub-conditions

        Returns:
        --------
        Dict with keys:
        - pipe: Pipe properties
        - loading: Loading conditions
        - conditions: Nested dict organized by stage -> wt_type -> position
        - all_conditions_pass: Boolean (True if all pass)
        """
        # Define wall thickness types for each life cycle stage
        # Format: (use_mill_tolerance, use_corrosion)
        installation_wt_types = [
            (False, False),  # Nominal
            (True, False),   # Nominal - Tolerance
        ]

        hydrotest_wt_types = [
            (False, False),  # Nominal
            (True, False),   # Nominal - Tolerance
        ]

        operation_wt_types = [
            (False, False),  # Nominal
            (True, False),   # Nominal - Tolerance
            (False, True),   # Nominal - Corrosion
            (True, True),    # Nominal - Tolerance - Corrosion
        ]

        positions = ["Top", "Bottom"]

        results = {
            "installation": {},
            "hydrotest": {},
            "operation": {},
        }

        # Analyze Installation conditions
        for use_mill, use_corr in installation_wt_types:
            wt_key = self.get_wt_type_short(use_mill, use_corr)
            wt_desc = self.get_wt_type_description(use_mill, use_corr)
            results["installation"][wt_key] = {
                "description": wt_desc,
                "positions": {}
            }
            for position in positions:
                result = self.analyze_condition_at_position(
                    condition_name="Installation",
                    position=position,
                    use_mill_tolerance=use_mill,
                    use_corrosion=use_corr
                )
                result["wt_type_description"] = wt_desc
                results["installation"][wt_key]["positions"][position.lower()] = result

        # Analyze Hydrotest conditions
        for use_mill, use_corr in hydrotest_wt_types:
            wt_key = self.get_wt_type_short(use_mill, use_corr)
            wt_desc = self.get_wt_type_description(use_mill, use_corr)
            results["hydrotest"][wt_key] = {
                "description": wt_desc,
                "positions": {}
            }
            for position in positions:
                result = self.analyze_condition_at_position(
                    condition_name="Hydrotest",
                    position=position,
                    use_mill_tolerance=use_mill,
                    use_corrosion=use_corr
                )
                result["wt_type_description"] = wt_desc
                results["hydrotest"][wt_key]["positions"][position.lower()] = result

        # Analyze Operation conditions
        for use_mill, use_corr in operation_wt_types:
            wt_key = self.get_wt_type_short(use_mill, use_corr)
            wt_desc = self.get_wt_type_description(use_mill, use_corr)
            results["operation"][wt_key] = {
                "description": wt_desc,
                "positions": {}
            }
            for position in positions:
                result = self.analyze_condition_at_position(
                    condition_name="Operation",
                    position=position,
                    use_mill_tolerance=use_mill,
                    use_corrosion=use_corr
                )
                result["wt_type_description"] = wt_desc
                results["operation"][wt_key]["positions"][position.lower()] = result

        # Check if ALL conditions pass (iterate through all nested results)
        all_pass = True
        for stage_name, stage_data in results.items():
            for wt_key, wt_data in stage_data.items():
                for pos_key, pos_result in wt_data["positions"].items():
                    if not pos_result["all_pass"]:
                        all_pass = False

        return {
            "pipe": asdict(self.pipe),
            "loading": asdict(self.load),
            "conditions": results,
            "all_conditions_pass": all_pass,
        }


def evaluate_standard_thicknesses(base_pipe: PipeProperties, load: LoadingCondition) -> pd.DataFrame:
    """Evaluate all standard thicknesses per ASME B36.10"""
    thicknesses = asme_b36_10.get_standard_thicknesses(base_pipe.od_in)
    if not thicknesses:
        return pd.DataFrame()

    records: List[Dict[str, Any]] = []
    for wt in thicknesses:
        pipe_variant = PipeProperties(**{**asdict(base_pipe), "wt_in": wt})
        analyzer = LifeCycleAnalyzer(pipe_variant, load)
        result = analyzer.run_all_conditions()

        # Find worst safety factor across ALL conditions (new nested structure)
        min_sf = float("inf")
        limiting_condition = ""
        limiting_check = ""

        for stage_name, stage_data in result["conditions"].items():
            for wt_key, wt_data in stage_data.items():
                for pos_key, pos_result in wt_data["positions"].items():
                    if pos_result["limiting"]["safety_factor"] < min_sf:
                        min_sf = pos_result["limiting"]["safety_factor"]
                        # Create display name: "Installation - Nominal - Top"
                        stage = pos_result["condition_name"]
                        wt_desc = pos_result.get("wt_type_description", wt_data["description"])
                        position = pos_result["position"]
                        limiting_condition = f"{stage} ({wt_desc}) - {position}"
                        limiting_check = pos_result["limiting"]["name"]

        records.append({
            "WT (in)": wt,
            "Schedule": schedule_name_for_thickness(base_pipe.od_in, wt),
            "Limiting Condition": limiting_condition,
            "Limiting Check": limiting_check,
            "Safety Factor": format_safety_factor(min_sf),
            "Utilization (%)": 0 if min_sf == float("inf") else round(100 / min_sf, 1),
            "Status": "PASS" if result["all_conditions_pass"] else "FAIL",
        })

    return pd.DataFrame(records)


def find_closest_passing_standard_wt(base_pipe: PipeProperties, load: LoadingCondition, 
                                      input_wt: float) -> Tuple[float, str]:
    """
    Find closest standard thickness >= input_wt that passes all conditions.
    Uses floor-to-up approach (round up from input).
    """
    thicknesses = asme_b36_10.get_standard_thicknesses(base_pipe.od_in)
    if not thicknesses:
        return None, "No standard thicknesses available"
    
    # Filter thicknesses >= input_wt
    candidates = [wt for wt in thicknesses if wt >= input_wt]
    if not candidates:
        return None, "No standard thickness >= input thickness"
    
    # Test each candidate starting from smallest
    for wt in sorted(candidates):
        pipe_variant = PipeProperties(**{**asdict(base_pipe), "wt_in": wt})
        analyzer = LifeCycleAnalyzer(pipe_variant, load)
        result = analyzer.run_all_conditions()
        
        if result["all_conditions_pass"]:
            schedule = schedule_name_for_thickness(base_pipe.od_in, wt)
            return wt, schedule
    
    return None, "No passing standard thickness found"


# -----------------------------------------------------------------------------
# UI helpers
# -----------------------------------------------------------------------------

def badge(label: str, color: str) -> str:
    return f"<span style='background:{color}; color:#ffffff; padding:4px 10px; border-radius:999px; font-weight:700;'>{label}</span>"


def render_styles():
    style = f"""
<style>
:root {{
    --primary: {COLOR_PRIMARY};
    --secondary: {COLOR_SECONDARY};
    --success: {COLOR_SUCCESS};
    --alert: {COLOR_ALERT};
}}
[data-testid="stAppViewContainer"] {{
    background: radial-gradient(circle at 10% 20%, rgba(30,58,138,0.15), rgba(59,130,246,0)) ,
                linear-gradient(135deg, {COLOR_PRIMARY} 0%, {COLOR_SECONDARY} 35%, #0f172a 100%);
}}
.main-header {{
    font-size: 2.4rem;
    font-weight: 800;
    color: #ffffff;
    text-align: left;
    padding: 0.4rem 0 0.4rem 0;
}}
.headline-card {{
    background: #0b1224cc;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 1.2rem;
    box-shadow: 0 20px 45px rgba(0,0,0,0.35);
    color: #e2e8f0;
}}
.section-card {{
    background: #ffffff;
    border-radius: 14px;
    padding: 1rem 1rem 0.5rem 1rem;
    box-shadow: 0 15px 35px rgba(0,0,0,0.08);
    border: 1px solid rgba(15,23,42,0.06);
}}
.metric-chip {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    border-radius: 12px;
    font-weight: 700;
    color: #0f172a;
    background: linear-gradient(120deg, rgba(59,130,246,0.12), rgba(30,58,138,0.1));
}}
.status-pass {{ color: {COLOR_SUCCESS}; font-weight: 700; }}
.status-fail {{ color: {COLOR_ALERT}; font-weight: 700; }}
.badge-pill {{
    padding: 6px 12px;
    border-radius: 999px;
    font-weight: 700;
    color: #fff;
    display: inline-block;
}}
.subdued {{ color: #cbd5e1; font-size: 0.9rem; }}
.stTabs [data-baseweb="tab-list"] button {{
    gap: 8px;
    padding: 10px 16px;
    border-radius: 10px 10px 0 0;
    font-weight: 700;
}}
.stTabs [data-baseweb="tab"]:hover {{
    background: rgba(59,130,246,0.08);
}}
@media (max-width: 768px) {{
    .main-header {{
        font-size: 1.6rem;
        text-align: center;
    }}
    .headline-card {{
        padding: 1rem;
    }}
    .metric-chip {{
        width: 100%;
        justify-content: center;
    }}
}}
</style>
"""
    st.markdown(style, unsafe_allow_html=True)


def status_pill(text: str, positive: bool) -> str:
    color = COLOR_SUCCESS if positive else COLOR_ALERT
    return f"<span class='badge-pill' style='background:{color};'>{text}</span>"


def info_chip(label: str, value: str) -> str:
    return f"<span class='metric-chip'>{label}: {value}</span>"


def render_hero():
    st.markdown(
        """
        <div class='headline-card'>
            <div class='main-header'>Riser Design Analysis Tool</div>
            <div class='subdued'>API RP 1111 burst/collapse/propagation + ASME B31.4/B31.8 hoop checks</div>
            <div class='subdued' style='margin-top:8px;'>Three life cycle conditions: Installation, Hydrotest, Operation</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def initialize_state():
    """Initialize session state with Multiphase Riser defaults"""
    defaults = TEAM8_REFERENCE["Multiphase Riser (ID 3)"]
    for key, value in {
        "od_in": defaults["od"],
        "wt_in": defaults["wt"],
        "design_pressure": defaults["design_pressure"],
        "shut_in_pressure": defaults["shut_in_pressure"],
        "shut_in_location": defaults["shut_in_location"],
        "water_depth": defaults["water_depth"],
        "riser_length": defaults["water_depth"],  # Initialize with water depth
        "fluid_sg": defaults["fluid_sg"],
        "grade": defaults["grade"],
        "manufacturing": defaults["manufacturing"],
        "fluid_type": defaults["fluid_type"],
        "design_category": defaults["design_category"],
        "ovality_type": defaults["ovality_type"],
        "ovality": defaults["ovality"],
    }.items():
        st.session_state.setdefault(key, value)


def apply_reference(name: str):
    """Load Team 8 reference data into form"""
    ref = TEAM8_REFERENCE[name]
    st.session_state.od_in = ref["od"]
    st.session_state.wt_in = ref["wt"]
    st.session_state.design_pressure = ref["design_pressure"]
    st.session_state.shut_in_pressure = ref["shut_in_pressure"]
    st.session_state.shut_in_location = ref["shut_in_location"]
    st.session_state.water_depth = ref["water_depth"]
    st.session_state.riser_length = ref["water_depth"]  # Default to water depth
    st.session_state.fluid_sg = ref["fluid_sg"]
    st.session_state.grade = ref["grade"]
    st.session_state.manufacturing = ref["manufacturing"]
    st.session_state.fluid_type = ref["fluid_type"]
    st.session_state.design_category = ref["design_category"]
    st.session_state.ovality_type = ref["ovality_type"]
    st.session_state.ovality = ref["ovality"]
    st.success(f"Loaded {name} data. You can modify any values.")


def build_pipe_and_load() -> Tuple[PipeProperties, LoadingCondition]:
    """Build pipe and loading objects from session state"""
    grade_props = GRADE_PROPERTIES.get(st.session_state.grade, GRADE_PROPERTIES["X-52"])
    
    # Get ovality based on type
    if st.session_state.ovality_type == "Reel-lay":
        ovality_value = 0.01  # 1%
    else:  # Other Type
        ovality_value = 0.005  # 0.5%
    
    pipe = PipeProperties(
        od_in=st.session_state.od_in,
        wt_in=st.session_state.wt_in,
        grade=st.session_state.grade,
        manufacturing=st.session_state.manufacturing,
        design_category=st.session_state.design_category,
        fluid_type=st.session_state.fluid_type,
        fluid_sg=st.session_state.fluid_sg,
        smys_psi=grade_props["smys_psi"],
        uts_psi=grade_props["uts_psi"],
        ovality_type=st.session_state.ovality_type,
        ovality=ovality_value,
    )
    load = LoadingCondition(
        design_pressure_psi=st.session_state.design_pressure,
        shut_in_pressure_psi=st.session_state.shut_in_pressure,
        shut_in_location=st.session_state.get("shut_in_location", "Subsea Wellhead"),
        water_depth_m=st.session_state.water_depth,
        riser_length_m=st.session_state.get("riser_length", st.session_state.water_depth),
    )
    return pipe, load


def render_input_sections():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("Design Inputs")
    st.caption("Enter all values manually. Team 8 reference buttons pre-fill the form for convenience.")

    tabs = st.tabs(["Pipe Properties", "Pressures & Loading", "Environment"])

    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.od_in = st.number_input("Outer Diameter (in)", min_value=2.0, max_value=48.0, value=st.session_state.od_in, step=0.01, format="%.3f")
            st.session_state.wt_in = st.number_input("Wall Thickness (in)", min_value=0.1, max_value=3.0, value=st.session_state.wt_in, step=0.01, format="%.4f")
            st.caption(f"Mill tolerance: {MILL_TOLERANCE*100}% | Corrosion: {CORROSION_RATE_PER_YEAR*DESIGN_LIFE_YEARS:.3f}\" over {DESIGN_LIFE_YEARS} years")
        with col2:
            st.session_state.grade = st.selectbox("Pipe Grade", list(GRADE_PROPERTIES.keys()), index=list(GRADE_PROPERTIES.keys()).index(st.session_state.grade))
            st.session_state.manufacturing = st.selectbox("Manufacturing Type", ["SMLS", "ERW", "DSAW"], index=["SMLS", "ERW", "DSAW"].index(st.session_state.manufacturing))
            st.session_state.design_category = st.selectbox("Design Category", ["Riser", "Pipeline"], index=["Riser", "Pipeline"].index(st.session_state.design_category))
        with col3:
            st.session_state.fluid_type = st.selectbox("Fluid Type", ["Gas", "Oil", "Multiphase", "Wet Gas"], index=["Gas", "Oil", "Multiphase", "Wet Gas"].index(st.session_state.fluid_type))
            st.session_state.fluid_sg = st.number_input("Fluid Specific Gravity", min_value=0.02, max_value=1.50, value=st.session_state.fluid_sg, step=0.01)
            st.session_state.ovality_type = st.selectbox("Ovality Type", ["Other Type", "Reel-lay"], index=["Other Type", "Reel-lay"].index(st.session_state.ovality_type))
            st.caption("Ovality: 0.5% (Other Type) or 1.0% (Reel-lay) per API RP 1111")

    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.design_pressure = st.number_input("Design Pressure (psi)", min_value=0.0, max_value=20000.0, value=st.session_state.design_pressure, step=10.0)
            st.session_state.shut_in_pressure = st.number_input("Shut-in Pressure (psi)", min_value=0.0, max_value=20000.0, value=st.session_state.shut_in_pressure, step=10.0)
        with col2:
            st.session_state.shut_in_location = st.selectbox(
                "Shut-in Location",
                ["Subsea Wellhead", "Top of Riser"],
                index=["Subsea Wellhead", "Top of Riser"].index(st.session_state.get("shut_in_location", "Subsea Wellhead")),
                help="Location where shut-in pressure is measured. Affects MOP calculation."
            )
            st.caption("**MOP (Maximum Operating Pressure)** is calculated when shut-in is at Subsea Wellhead:\nMOP = Shut-in Pressure - Hydrostatic Head of Riser Contents")

    with tabs[2]:
        col1, col2 = st.columns([1, 2])
        with col1:
             depth_unit = st.radio("Depth Unit", ["Meters (m)", "Feet (ft)"], horizontal=True)
        
        with col2:
            # Display appropriate input based on unit
            if "Meters" in depth_unit:
                input_depth = st.number_input("💧 Water Depth", min_value=0.0, max_value=4000.0, value=st.session_state.water_depth, step=10.0)
                st.session_state.water_depth = input_depth
            else:
                # Convert current stored meters to feet for display/input
                current_feet = st.session_state.water_depth * 3.28084
                input_depth_ft = st.number_input("💧 Water Depth", min_value=0.0, max_value=13000.0, value=current_feet, step=30.0)
                # Convert back to meters for storage/calculation
                st.session_state.water_depth = input_depth_ft / 3.28084

        # Automatically set riser length to water depth
        st.session_state.riser_length = st.session_state.water_depth
        
        st.info(f"📏 Riser Length automatically set to Water Depth: {st.session_state.water_depth:.2f} m")
        st.caption(f"External pressure calculated at depth: {st.session_state.water_depth:.2f} m ({st.session_state.water_depth * 3.28084:.2f} ft)")
        st.caption(f"Seawater density: {DEFAULT_WATER_DENSITY} lb/ft³")

    st.markdown("</div>", unsafe_allow_html=True)


def render_reference_section():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    with st.expander("Team 8 Reference Data (Auto-Load)", expanded=False):
        st.write("Click a button to automatically load Team 8 data into the form. Modify values after loading if needed.")
        cols = st.columns(2)
        if cols[0].button("🔄 Load Multiphase Riser (ID 3)", use_container_width=True):
            apply_reference("Multiphase Riser (ID 3)")
            st.rerun()
        if cols[1].button("🔄 Load Oil Riser (ID 8)", use_container_width=True):
            apply_reference("Oil Riser (ID 8)")
            st.rerun()
        
        st.markdown("**Reference Values:**")
        df_ref = pd.DataFrame({
            "Parameter": ["OD (in)", "WT (in)", "Grade", "Design P (psi)", "Shut-in P (psi)", "Depth (m)", "Fluid Type", "SG"],
            "Gas Riser (ID 3)": [16.0, 0.750, "X-52", 1400, 1236, 920, "Multiphase", 0.57],
            "Oil Riser (ID 8)": [8.63, 0.500, "X-52", 230, 195, 960, "Oil", 0.82],
        })
        st.dataframe(df_ref, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def build_verification_notes(pipe: PipeProperties, load: LoadingCondition, result: Dict[str, Any]) -> List[str]:
    """Build automated verification warnings"""
    notes: List[str] = []
    d_over_t = pipe.od_in / max(pipe.wt_in, 1e-6)

    # Check operation condition WT (use operation with_tol_corr top as representative - worst case)
    if "operation" in result["conditions"]:
        op_data = result["conditions"]["operation"]
        if "with_tol_corr" in op_data and "positions" in op_data["with_tol_corr"]:
            op_wt = op_data["with_tol_corr"]["positions"]["top"]["wt_effective"]
            if op_wt < 0.1:
                notes.append(f"⚠️ Operation WT very thin ({op_wt:.4f} in) after corrosion and mill tolerance")

    if d_over_t > 120:
        notes.append(f"⚠️ High D/t ratio ({d_over_t:.1f}); check fabrication tolerances")

    if load.shut_in_pressure_psi > load.design_pressure_psi * 1.5:
        notes.append("⚠️ Shut-in pressure > 1.5× design; confirm well control assumptions")

    if pipe.fluid_sg < 0.02 or pipe.fluid_sg > 1.2:
        notes.append(f"⚠️ Fluid SG ({pipe.fluid_sg}) outside typical range")

    # Check if any condition fails (new nested structure)
    for stage_name, stage_data in result["conditions"].items():
        for wt_key, wt_data in stage_data.items():
            for pos_key, pos_result in wt_data["positions"].items():
                if not pos_result["all_pass"]:
                    # Format condition name nicely
                    stage = pos_result["condition_name"]
                    wt_desc = pos_result.get("wt_type_description", wt_data["description"])
                    position = pos_result["position"]
                    notes.append(f"❌ {stage} ({wt_desc}) - {position} fails")

    return notes


def format_safety_factor(sf: float, check_name: str = "", p_internal: float = 0.0) -> str:
    """
    Format safety factor for display with descriptive text for infinite values

    Parameters:
    -----------
    sf : float
        Safety factor value
    check_name : str
        Name of check (for context)
    p_internal : float
        Internal pressure (for determining N/A reason)

    Returns:
    --------
    str : Formatted safety factor text

    Replaces float('inf') with user-friendly descriptions:
    - "N/A (No internal pressure)" for burst/hoop during installation
    - "N/A (Favorable loading)" for reverse loading cases
    - ">999" for extremely high safety factors
    """
    if sf == float('inf'):
        # Determine reason for infinite safety factor
        if p_internal <= 0 and check_name in ["Burst", "Hoop Stress"]:
            return "N/A (No internal pressure)"
        else:
            return "N/A (Favorable loading)"
    elif sf > 999:
        return ">999"
    else:
        return f"{sf:.2f}"


def render_position_results(position_name: str, cond_result: Dict[str, Any]):
    """
    Render results for one position (Top or Bottom) within a lifecycle condition

    Displays:
    - Position-specific external pressure
    - Check-specific internal pressures (Operation shows both design and shut-in)
    - All 7 checks with formatted safety factors
    - Detailed expandable sections

    Parameters:
    -----------
    position_name : str
        "Top" or "Bottom"
    cond_result : Dict
        Result dictionary from analyze_condition_at_position()
    """
    st.markdown(f"#### {position_name} Position")

    # Status badge
    status_html = status_pill("PASS" if cond_result["all_pass"] else "FAIL", cond_result["all_pass"])
    st.markdown(f"**Status:** {status_html}", unsafe_allow_html=True)

    # Pressure summary card
    st.markdown("**Pressures:**")

    condition_name = cond_result['condition_name']

    if condition_name == "Operation":
        # Operation uses different Pi for different checks - show design, shut-in, and MOP
        # Check if MOP is being used (collapse pressure differs from shut-in)
        shut_in_used = cond_result.get('p_internal_collapse', 0)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("External (Po)", f"{cond_result['p_external_psi']:.0f} psi")
        with col2:
            st.metric("Design Pressure", f"{cond_result['p_internal_burst']:.0f} psi")
            st.caption("For: Burst, Hoop, Longitudinal, Combined")
        with col3:
            st.metric("Shut-in/MOP", f"{shut_in_used:.0f} psi")
            st.caption("For: Collapse, Propagation")
        with col4:
            # Show MOP indicator if applicable
            if cond_result.get('mop_active', False):
                st.metric("MOP Active", "✓ Yes")
                st.caption(f"MOP = {cond_result['mop_psi']:.0f} psi")
                st.caption("(Shut-in at Subsea Wellhead)")
            else:
                st.metric("MOP Active", "✗ No")
                if cond_result.get('shut_in_location') == "Top of Riser":
                    st.caption("Shut-in at Top")
                elif position_name == "Bottom":
                    st.caption("Bottom position uses full shut-in")
                else:
                    st.caption("Using shut-in pressure")
    else:
        # Installation and Hydrotest use same Pi for all checks
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Internal (Pi)", f"{cond_result['p_internal_burst']:.0f} psi")
        with col2:
            st.metric("External (Po)", f"{cond_result['p_external_psi']:.0f} psi")
        with col3:
            p_diff = cond_result['p_internal_burst'] - cond_result['p_external_psi']
            st.metric("Differential (Pi-Po)", f"{p_diff:+.0f} psi")

    # Wall thickness
    col1, col2 = st.columns(2)
    col1.metric("Nominal WT", f"{cond_result['wt_nominal']:.4f} in")
    col2.metric("Effective WT", f"{cond_result['wt_effective']:.4f} in")

    # Pipe weights
    st.markdown("**Pipe Weights:**")
    weights = cond_result["weights"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Empty Pipe:**")
        st.write(f"Dry: {weights['void_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['void_submerged_weight_plf']:.2f} lb/ft")
    with col2:
        st.markdown("**Flooded (Water):**")
        st.write(f"Dry: {weights['flooded_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['flooded_submerged_weight_plf']:.2f} lb/ft")
    with col3:
        st.markdown("**Product-Filled:**")
        st.write(f"Dry: {weights['product_filled_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['product_filled_submerged_weight_plf']:.2f} lb/ft")

    # Checks table with formatted safety factors
    st.markdown("**Analysis Results:**")
    table_records = []
    for chk in cond_result["checks"]:
        sf_formatted = format_safety_factor(
            chk["safety_factor"],
            chk["name"],
            cond_result.get('p_internal_burst', 0)
        )
        util_pct = 0 if chk["safety_factor"] == float("inf") else round(100 / chk["safety_factor"], 1)
        table_records.append({
            "Check": chk["name"],
            "Safety Factor": sf_formatted,
            "Utilization (%)": util_pct,
            "Status": "PASS" if chk["pass_fail"] else "FAIL",
        })

    # Add longitudinal tension
    long_check = cond_result["longitudinal"]
    sf_formatted = format_safety_factor(long_check["safety_factor"], "Longitudinal")
    long_util = 0 if long_check["safety_factor"] == float("inf") else round(100 / long_check["safety_factor"], 1)
    table_records.append({
        "Check": "Longitudinal Tension",
        "Safety Factor": sf_formatted,
        "Utilization (%)": long_util,
        "Status": long_check["status"],
    })

    # Add combined loading
    comb_check = cond_result["combined"]
    sf_formatted = format_safety_factor(comb_check["safety_factor"], "Combined")
    comb_util = 0 if comb_check["safety_factor"] == float("inf") else round(100 / comb_check["safety_factor"], 1)
    table_records.append({
        "Check": "Combined Loading",
        "Safety Factor": sf_formatted,
        "Utilization (%)": comb_util,
        "Status": comb_check["status"],
    })

    df = pd.DataFrame(table_records)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detailed Results Table (Burst Pressures, Resistances, Hoop Stress, Collapse Pressures)
    st.markdown("**Detailed Pressure & Resistance Results:**")

    # Extract values from check results
    burst_chk = cond_result["checks"][0]  # Burst
    collapse_chk = cond_result["checks"][1]  # Collapse
    hoop_chk = cond_result["checks"][3]  # Hoop

    # Get burst pressure values
    pb = burst_chk.get("pb", 0)
    d_burst = burst_chk.get("details", {})
    f_d = d_burst.get("design_factor", 0.75)
    f_e = d_burst.get("joint_factor", 1.0)
    f_t = d_burst.get("temperature_factor", 1.0)
    allowable_burst = f_d * f_e * f_t * pb

    # Get collapse pressure values
    py = collapse_chk.get("py", 0)
    pe = collapse_chk.get("pe", 0)
    pc = collapse_chk.get("pc", 0)

    # Get hoop stress values
    hoop_stress = hoop_chk.get("hoop_stress", 0)
    d_hoop = hoop_chk.get("details", {})
    delta_p_hoop = d_hoop.get("delta_p", 0)

    # Calculate pressure resistances
    # Pt = burst_pressure (theoretical)
    hydro_test_resistance = allowable_burst  # fd × fe × ft × Pb
    incidental_overpressure = 0.9 * pb  # 0.9 × Pt
    design_pressure_resistance = 0.8 * pb  # 0.8 × Pt

    detailed_records = [
        {
            "Parameter": "Burst Pressure (Pb)",
            "Value": f"{pb:,.0f} psi",
            "Description": "Theoretical burst pressure"
        },
        {
            "Parameter": "Hydrostatic Test Pressure Resistance",
            "Value": f"{hydro_test_resistance:,.0f} psi",
            "Description": f"fd × fe × ft × Pb = {f_d:.2f} × {f_e:.2f} × {f_t:.2f} × {pb:,.0f}"
        },
        {
            "Parameter": "Incidental Overpressure Resistance",
            "Value": f"{incidental_overpressure:,.0f} psi",
            "Description": f"0.9 × Pb = 0.9 × {pb:,.0f}"
        },
        {
            "Parameter": "Design Pressure Resistance",
            "Value": f"{design_pressure_resistance:,.0f} psi",
            "Description": f"0.8 × Pb = 0.8 × {pb:,.0f}"
        },
        {
            "Parameter": "Differential Pressure Hoop Stress",
            "Value": f"{hoop_stress:,.0f} psi",
            "Description": f"SH = (Pi - Po) × D / (2t) with ΔP = {delta_p_hoop:,.0f} psi"
        },
        {
            "Parameter": "Yield Pressure at Collapse (Py)",
            "Value": f"{py:,.0f} psi",
            "Description": "Py = 2 × SMYS × (t/D)"
        },
        {
            "Parameter": "Elastic Collapse Pressure (Pe)",
            "Value": f"{pe:,.0f} psi",
            "Description": "Pe = 2E(t/D)³ / (1-ν²)"
        },
        {
            "Parameter": "Collapse Pressure (Pc)",
            "Value": f"{pc:,.0f} psi",
            "Description": f"Pc = Py×Pe / sqrt(Py²+Pe²) [{collapse_chk.get('collapse_mode', 'N/A')} mode]"
        }
    ]

    df_detailed = pd.DataFrame(detailed_records)
    st.dataframe(df_detailed, use_container_width=True, hide_index=True)

    # Limiting check
    limiting_sf_text = format_safety_factor(cond_result['limiting']['safety_factor'])
    st.info(f"**Limiting Check:** {cond_result['limiting']['name']} with SF = {limiting_sf_text}")

    # Detailed expandable sections
    with st.expander("📊 Longitudinal Tension Details"):
        long = long_check
        st.markdown(f"""
        **Position:** {cond_result['position']}
        **Applied Tension (T_a):** {long['t_a_applied_kips']:.2f} kips
        *{"Full riser weight (submerged)" if position_name == "Top" else "Zero (supported by mudline)"}*

        **Effective Tension (T_eff):** {long['t_eff_effective_kips']:.2f} kips
        **Allowable (0.60 × T_y):** {long['allowable_tension_kips']:.2f} kips

        **Safety Factor:** {format_safety_factor(long['safety_factor'])}
        **Status:** {long['status']}

        **Note:** Buoyancy is accounted for in submerged weight calculation.
        """)

    with st.expander("🔄 Combined Loading Details"):
        comb = comb_check
        st.markdown(f"""
        **Position:** {cond_result['position']}
        **Combined Ratio:** {comb['combined_ratio']:.4f}
        **Design Factor:** {comb['design_factor']} ({comb['factor_description']})

        **Pressure Component:** {comb['pressure_component']:.4f}
        **Tension Component:** {comb['tension_component']:.4f}

        **Safety Factor:** {format_safety_factor(comb['safety_factor'])}
        **Status:** {"PASS" if comb['passes'] else "FAIL"}
        """)

    # Get individual check results for detailed expanders
    burst_chk = cond_result["checks"][0]  # Burst
    collapse_chk = cond_result["checks"][1]  # Collapse
    prop_chk = cond_result["checks"][2]  # Propagation
    hoop_chk = cond_result["checks"][3]  # Hoop

    with st.expander("💥 Burst Pressure Details (API RP 1111 Section 4.3.1)"):
        d = burst_chk.get("details", {})
        pb = burst_chk.get("pb", 0)
        allow_burst = burst_chk.get("allowable_burst", d.get("design_factor", 0.75) * pb)

        st.markdown(f"""
**Formula (Barlow Thin-Wall):**
```
P_b = 0.90 × (SMYS + UTS) × t / (D - t)
```

**Input Parameters:**
- OD (D): {d.get('od', 0):.3f} in
- Wall Thickness (t): {d.get('wt_eff', 0):.4f} in
- ID: {d.get('id', 0):.3f} in
- SMYS: {d.get('smys', 0):,.0f} psi
- UTS: {d.get('uts', 0):,.0f} psi

**Calculation:**
- Burst Pressure (P_b): {pb:,.0f} psi
- Design Factor (f_d): {d.get('design_factor', 0.75):.2f}
- Weld Factor (f_e): {d.get('joint_factor', 1.0):.2f}
- Temperature Factor (f_t): {d.get('temperature_factor', 1.0):.2f}

**Criterion:** (P_i - P_o) ≤ f_d × f_e × f_t × P_b
- Internal Pressure (P_i): {d.get('p_internal', 0):,.0f} psi
- External Pressure (P_o): {d.get('p_external', 0):,.0f} psi
- Net Differential (P_i - P_o): {d.get('delta_p', 0):,.0f} psi
- Allowable (f_d × f_e × f_t × P_b): {allow_burst:,.0f} psi

**Result:**
- Safety Factor: {format_safety_factor(burst_chk['safety_factor'])}
- Utilization: {burst_chk['utilization']*100:.1f}%
- Status: **{"PASS" if burst_chk['pass_fail'] else "FAIL"}**
        """)

    with st.expander("🔧 Collapse Pressure Details (API RP 1111 Section 4.3.2)"):
        d = collapse_chk.get("details", {})
        py = collapse_chk.get("py", 0)
        pe = collapse_chk.get("pe", 0)
        pc = collapse_chk.get("pc", 0)
        allow_collapse = collapse_chk.get("allowable_collapse", collapse_chk.get("collapse_factor", 0.7) * pc)

        st.markdown(f"""
**Formulas:**
```
P_y = 2 × SMYS × (t/D)                  (Yield Collapse)
P_e = 2E × (t/D)³ / (1 - ν²)            (Elastic Collapse)
P_c = (P_y × P_e) / sqrt(P_y² + P_e²)   (Critical Collapse - Murphy-Langner)
```

**Input Parameters:**
- OD (D): {d.get('od', 0):.3f} in
- Wall Thickness (t): {d.get('wt_eff', 0):.4f} in
- t/D Ratio: {d.get('t_over_d', 0):.6f}
- D/t Ratio: {d.get('d_over_t', 0):.1f}
- SMYS: {d.get('smys', 0):,.0f} psi
- Elastic Modulus (E): {d.get('E', 0):,.0f} psi
- Poisson's Ratio (ν): {d.get('poisson', 0.3):.2f}

**Calculation:**
- Yield Collapse (P_y): {py:,.0f} psi
- Elastic Collapse (P_e): {pe:,.0f} psi
- P_y/P_e Ratio: {d.get('py_pe_ratio', 0):.2f}
- Collapse Mode: {collapse_chk.get('collapse_mode', 'N/A')}
- Critical Collapse (P_c): {pc:,.0f} psi
- Collapse Factor (f_o): {collapse_chk.get('collapse_factor', 0.7):.2f}

**Criterion:** (P_o - P_i) ≤ f_o × P_c
- External Pressure (P_o): {d.get('p_external', 0):,.0f} psi
- Internal Pressure (P_i): {d.get('p_internal', 0):,.0f} psi
- Net External (P_o - P_i): {d.get('delta_p', 0):,.0f} psi
- Allowable (f_o × P_c): {allow_collapse:,.0f} psi

**Result:**
- Safety Factor: {format_safety_factor(collapse_chk['safety_factor'])}
- Utilization: {collapse_chk['utilization']*100:.1f}%
- Status: **{"PASS" if collapse_chk['pass_fail'] else "FAIL"}**
        """)

    with st.expander("🌊 Propagation Buckling Details (API RP 1111 Section 4.3.2.3)"):
        d = prop_chk.get("details", {})
        pp = prop_chk.get("pp", 0)
        allow_prop = prop_chk.get("allowable_prop", prop_chk.get("design_factor", 0.8) * pp)

        st.markdown(f"""
**Formula:**
```
P_p = 35 × SMYS × (t/D)^2.5
```

**Input Parameters:**
- OD (D): {d.get('od', 0):.3f} in
- Wall Thickness (t): {d.get('wt_eff', 0):.4f} in
- t/D Ratio: {d.get('t_over_d', 0):.6f}
- D/t Ratio: {d.get('d_over_t', 0):.1f}
- SMYS: {d.get('smys', 0):,.0f} psi

**Calculation:**
- Propagation Pressure (P_p): {pp:,.0f} psi
- Design Factor (f_p): {prop_chk.get('design_factor', 0.8):.2f}
- Allowable (f_p × P_p): {allow_prop:,.0f} psi

**Criterion:** (P_o - P_i) ≤ f_p × P_p
- External Pressure (P_o): {d.get('p_external', 0):,.0f} psi
- Internal Pressure (P_i): {d.get('p_internal', 0):,.0f} psi
- Net External (P_o - P_i): {d.get('delta_p', 0):,.0f} psi

**Result:**
- Safety Factor: {format_safety_factor(prop_chk['safety_factor'])}
- Utilization: {prop_chk['utilization']*100:.1f}%
- Status: **{"PASS" if prop_chk['pass_fail'] else "FAIL"}**

**Note:** Propagation buckling arrestors may be required if this check fails.
        """)

    with st.expander("⭕ Hoop Stress Details (ASME B31.4 Section 402.3)"):
        d = hoop_chk.get("details", {})
        hoop_stress = hoop_chk.get("hoop_stress", 0)
        allowable = hoop_chk.get("allowable", 0)

        st.markdown(f"""
**Formula (Barlow for Thin-Wall):**
```
S_H = (P_i - P_o) × D / (2 × t)
```

**Physical Basis:** Hoop stress is the circumferential stress in the pipe wall caused by
the **pressure differential** across the wall. External pressure reduces the hoop stress.

**Input Parameters:**
- OD (D): {d.get('od', 0):.3f} in
- Wall Thickness (t): {d.get('wt_eff', 0):.4f} in
- D/t Ratio: {d.get('d_over_t', 0):.1f}
- Internal Pressure (P_i): {d.get('p_internal', 0):,.0f} psi
- External Pressure (P_o): {d.get('p_external', 0):,.0f} psi
- SMYS: {d.get('smys', 0):,.0f} psi

**Calculation:**
- Differential Pressure (P_i - P_o): {d.get('delta_p', 0):,.0f} psi
- Hoop Stress (S_H): {hoop_stress:,.0f} psi ({hoop_stress/1000:.2f} ksi)
- Design Factor (F): {hoop_chk.get('design_factor', 0.72):.2f}
- Allowable Stress (F × SMYS): {allowable:,.0f} psi ({allowable/1000:.2f} ksi)

**Criterion:** S_H ≤ F × SMYS

**Result:**
- Safety Factor: {format_safety_factor(hoop_chk['safety_factor'])}
- Utilization: {hoop_chk['utilization']*100:.1f}%
- Status: **{"PASS" if hoop_chk['pass_fail'] else "FAIL"}**

**Note:** Equation applicable for D/t ≥ 20 (thin-wall assumption).
        """)


def render_condition_results(cond_name: str, cond_result: Dict[str, Any]):
    """Render one life cycle condition results"""
    st.markdown(f"### {cond_name.capitalize()} Condition")
    
    status_html = status_pill("PASS" if cond_result["all_pass"] else "FAIL", cond_result["all_pass"])
    st.markdown(f"Status: {status_html}", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Nominal WT", f"{cond_result['wt_nominal']:.4f} in")
    col2.metric("Effective WT", f"{cond_result['wt_effective']:.4f} in")
    col3.metric("Pi", f"{cond_result['p_internal_psi']:.0f} psi")
    col4.metric("Po", f"{cond_result['p_external_psi']:.0f} psi")
    
    # Display pipe weights
    st.markdown("#### Pipe Weights")
    weights = cond_result["weights"]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Empty Pipe:**")
        st.write(f"Dry: {weights['void_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['void_submerged_weight_plf']:.2f} lb/ft")
    with col2:
        st.markdown("**Flooded (Water):**")
        st.write(f"Dry: {weights['flooded_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['flooded_submerged_weight_plf']:.2f} lb/ft")
    with col3:
        st.markdown("**Product-Filled:**")
        st.write(f"Dry: {weights['product_filled_dry_weight_plf']:.2f} lb/ft")
        st.write(f"Submerged: {weights['product_filled_submerged_weight_plf']:.2f} lb/ft")
    
    st.caption(f"Pipe Specific Gravity: {weights['pipe_specific_gravity']:.2f} | Steel: {weights['steel_density_pcf']:.0f} pcf | Water: {weights['water_density_pcf']:.0f} pcf")
    
    # Adjustments applied
    adjustments = []
    if cond_result["mill_tolerance_applied"]:
        adjustments.append("Mill Tolerance (×0.875)")
    if cond_result["corrosion_applied"]:
        adjustments.append(f"Corrosion ({CORROSION_RATE_PER_YEAR*DESIGN_LIFE_YEARS:.3f} in)")
    st.caption("Applied: " + ", ".join(adjustments) if adjustments else "Applied: None (nominal WT)")
    
    # Checks table
    table_records = []
    for chk in cond_result["checks"]:
        util_pct = 0 if chk["safety_factor"] == float("inf") else round(100 / chk["safety_factor"], 1)
        table_records.append({
            "Check": chk["name"],
            "Safety Factor": f"{chk['safety_factor']:.2f}" if chk["safety_factor"] != float("inf") else "∞",
            "Utilization (%)": util_pct,
            "Status": "PASS" if chk["pass_fail"] else "FAIL",
        })
    
    # Add longitudinal tension check
    long_check = cond_result["longitudinal"]
    long_util = 0 if long_check["safety_factor"] == float("inf") else round(100 / long_check["safety_factor"], 1)
    table_records.append({
        "Check": "Longitudinal Tension",
        "Safety Factor": f"{long_check['safety_factor']:.2f}" if long_check["safety_factor"] != float("inf") else "∞",
        "Utilization (%)": long_util,
        "Status": long_check["status"],
    })
    
    # Add combined loading check
    comb_check = cond_result["combined"]
    comb_util = 0 if comb_check["safety_factor"] == float("inf") else round(100 / comb_check["safety_factor"], 1)
    table_records.append({
        "Check": "Combined Loading",
        "Safety Factor": f"{comb_check['safety_factor']:.2f}" if comb_check["safety_factor"] != float("inf") else "∞",
        "Utilization (%)": comb_util,
        "Status": comb_check["status"],
    })
    
    df = pd.DataFrame(table_records)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Detailed information for new checks
    with st.expander("📊 Longitudinal Tension Details (API RP 1111 Section 4.3.1.1)"):
        st.markdown(f"""
        **Applied Tension (T_a):** {long_check['t_a_applied_kips']:.2f} kips ({long_check['t_a_applied_lb']:.0f} lb)  
        *From self-weight: {long_check['void_submerged_plf']:.2f} lb/ft × {long_check['riser_length_ft']:.0f} ft*
        
        **Pressure End-Cap Forces:**
        - Internal (P_i × A_i): {long_check['force_internal_lb']/1000:.2f} kips (reduces tension)
        - External (P_o × A_o): {long_check['force_external_lb']/1000:.2f} kips (increases tension)
        
        **Effective Tension (T_eff):** {long_check['t_eff_effective_kips']:.2f} kips  
        *T_eff = T_a - P_i×A_i + P_o×A_o*
        
        **Yield Tension (T_y):** {long_check['t_y_yield_kips']:.2f} kips  
        *T_y = SMYS × A_steel = {cond_result["checks"][0].get("smys", "N/A")} psi × {long_check['a_steel_in2']:.2f} in²*
        
        **Allowable (0.60 × T_y):** {long_check['allowable_tension_kips']:.2f} kips
        
        **Axial Stress:** {long_check['axial_stress_ksi']:.2f} ksi  
        **Criterion:** T_eff ≤ 0.60 × T_y (per API RP 1111 Section 4.3.1.1)
        """)
    
    with st.expander("🔄 Combined Loading Details (API RP 1111 Section 4.3.1.2)"):
        st.markdown(f"""
        **Formula:** √[(P/P_b)² + (T/T_y)²] ≤ Design Factor
        
        **Pressure Component (P/P_b):** {comb_check['pressure_component']:.4f}  
        *P_i - P_o = {comb_check['p_diff_psi']:.0f} psi, P_b = {comb_check['p_b_burst_psi']:.0f} psi*
        
        **Tension Component (T/T_y):** {comb_check['tension_component']:.4f}  
        *T_eff = {comb_check['t_eff_lb']/1000:.2f} kips, T_y = {comb_check['t_y_lb']/1000:.2f} kips*
        
        **Combined Ratio:** {comb_check['combined_ratio']:.4f}  
        **Design Factor:** {comb_check['design_factor']} ({comb_check['factor_description']})
        
        **Status:** Combined Ratio {'≤' if comb_check['passes'] else '>'} Design Factor
        """)
    
    # Limiting check
    st.info(f"Limiting: **{cond_result['limiting']['name']}** with SF = {cond_result['limiting']['safety_factor']:.2f}")


def render_wt_type_results(wt_key: str, wt_data: Dict[str, Any], stage_name: str):
    """Render results for a wall thickness type with Top/Bottom position tabs"""
    wt_desc = wt_data["description"]

    # Check if both positions pass
    top_pass = wt_data["positions"]["top"]["all_pass"]
    bottom_pass = wt_data["positions"]["bottom"]["all_pass"]
    both_pass = top_pass and bottom_pass

    st.markdown(f"##### {wt_desc}")
    status_html = status_pill("PASS" if both_pass else "FAIL", both_pass)
    st.markdown(f"**Status:** {status_html}", unsafe_allow_html=True)

    # Show effective WT
    eff_wt = wt_data["positions"]["top"]["wt_effective"]
    nom_wt = wt_data["positions"]["top"]["wt_nominal"]
    st.caption(f"Effective WT: {eff_wt:.4f} in (Nominal: {nom_wt:.4f} in)")

    # Position tabs
    position_tabs = st.tabs(["Top Position", "Bottom Position"])

    with position_tabs[0]:
        render_position_results("Top", wt_data["positions"]["top"])

    with position_tabs[1]:
        render_position_results("Bottom", wt_data["positions"]["bottom"])


def render_results(result: Dict[str, Any], pipe: PipeProperties, load: LoadingCondition):
    """Render complete results with all life cycle conditions and WT types"""
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)

    tabs = st.tabs(["Summary", "Installation", "Hydrotest", "Operation", "Standard Thicknesses", "Verification"])

    with tabs[0]:
        st.subheader("Life Cycle Analysis Summary")

        all_pass = result["all_conditions_pass"]
        total_conditions = sum(
            len(stage_data) * 2  # 2 positions per WT type
            for stage_data in result["conditions"].values()
        )
        status_html = status_pill(f"ALL {total_conditions} CONDITIONS PASS" if all_pass else "SOME CONDITIONS FAIL", all_pass)
        st.markdown(f"Overall: {status_html}", unsafe_allow_html=True)

        st.markdown("---")

        # Summary table - organized by stage, WT type, position
        summary_records = []

        for stage_name in ["installation", "hydrotest", "operation"]:
            stage_data = result["conditions"][stage_name]
            for wt_key, wt_data in stage_data.items():
                for pos_key, pos_result in wt_data["positions"].items():
                    stage_display = pos_result["condition_name"]
                    wt_desc = wt_data["description"]
                    position = pos_result["position"]
                    display_name = f"{stage_display} - {wt_desc} - {position}"

                    summary_records.append({
                        "Stage": stage_display,
                        "Wall Thickness Type": wt_desc,
                        "Position": position,
                        "Effective WT (in)": f"{pos_result['wt_effective']:.4f}",
                        "Po (psi)": f"{pos_result['p_external_psi']:.0f}",
                        "Pi Burst (psi)": f"{pos_result['p_internal_burst']:.0f}",
                        "Pi Collapse (psi)": f"{pos_result['p_internal_collapse']:.0f}",
                        "Limiting Check": pos_result["limiting"]["name"],
                        "Min SF": format_safety_factor(pos_result["limiting"]["safety_factor"]),
                        "Status": "PASS" if pos_result["all_pass"] else "FAIL",
                    })

        df_summary = pd.DataFrame(summary_records)
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        if all_pass:
            st.success(f"✅ The selected wall thickness satisfies all design criteria for all {total_conditions} conditions.")
        else:
            st.error("❌ Wall thickness does NOT meet all criteria. Review failed conditions and consider increasing thickness.")

    with tabs[1]:
        st.markdown("### Installation Condition")
        st.info("""
        **Installation:** Empty pipe (Pi=0), external pressure + bending during lay.

        **Wall Thickness Types:**
        - **Nominal:** Full wall thickness (as manufactured)
        - **Nominal - Tolerance:** Wall thickness with mill tolerance (-12.5%) applied
        """)

        installation_data = result["conditions"]["installation"]

        # Create tabs for each WT type
        wt_types = list(installation_data.keys())
        wt_tabs = st.tabs([installation_data[wt]["description"] for wt in wt_types])

        for i, wt_key in enumerate(wt_types):
            with wt_tabs[i]:
                render_wt_type_results(wt_key, installation_data[wt_key], "Installation")

    with tabs[2]:
        st.markdown("### Hydrotest Condition")

        # Get hydrotest pressure values
        ht_nominal = result["conditions"]["hydrotest"]["nominal"]["positions"]["top"]
        ht_top_pressure = ht_nominal.get("p_internal_burst", load.design_pressure_psi * HYDROTEST_FACTOR)
        ht_bottom_pressure = result["conditions"]["hydrotest"]["nominal"]["positions"]["bottom"].get(
            "p_internal_burst", load.design_pressure_psi * HYDROTEST_FACTOR
        )

        st.info(f"""
        **Hydrotest Pressure Strategy (Per API RP 1111 Appendix C, Table C.3):**

        **🔵 TOP Position:** Pt = (Design × 1.25) - Hydrostatic Head = **{ht_top_pressure:.0f} psi**
        **🔴 BOTTOM Position:** Pt = Design × 1.25 = **{ht_bottom_pressure:.0f} psi**

        **Wall Thickness Types:**
        - **Nominal:** Full wall thickness (new pipe)
        - **Nominal - Tolerance:** With mill tolerance (-12.5%) applied
        """)

        hydrotest_data = result["conditions"]["hydrotest"]
        wt_types = list(hydrotest_data.keys())
        wt_tabs = st.tabs([hydrotest_data[wt]["description"] for wt in wt_types])

        for i, wt_key in enumerate(wt_types):
            with wt_tabs[i]:
                render_wt_type_results(wt_key, hydrotest_data[wt_key], "Hydrotest")

    with tabs[3]:
        st.markdown("### Operation Condition")

        # Get pressure info
        op_top = result["conditions"]["operation"]["with_tol_corr"]["positions"]["top"]
        shut_in_loc = op_top.get("shut_in_location", "Subsea Wellhead")

        # Calculate internal pressures based on wellhead location
        analyzer = LifeCycleAnalyzer(pipe, load)
        top_pressure = analyzer.calculate_internal_pressure_at_position("Top")
        bottom_pressure = analyzer.calculate_internal_pressure_at_position("Bottom")

        st.info(f"""
        **Operation Pressure Strategy (Wellhead Location: {shut_in_loc}):**

        {"**🔵 TOP Position:** Pi = Shut-in Pressure (wellhead at top)" if shut_in_loc == "Top of Riser" else f"**🔵 TOP Position:** Pi = MOP = {top_pressure:.0f} psi (shut-in - hydrostatic head)"}
        {"**🔴 BOTTOM Position:** Pi = Shut-in + Hydrostatic Head = " + f"{bottom_pressure:.0f} psi" if shut_in_loc == "Top of Riser" else f"**🔴 BOTTOM Position:** Pi = Shut-in = {bottom_pressure:.0f} psi (wellhead at bottom)"}

        **Wall Thickness Types (4 combinations):**
        - **Nominal:** Full wall thickness
        - **Nominal - Tolerance:** With mill tolerance (-12.5%)
        - **Nominal - Corrosion:** With corrosion allowance ({CORROSION_RATE_PER_YEAR*DESIGN_LIFE_YEARS:.3f} in)
        - **Nominal - Tolerance - Corrosion:** Both applied (worst case)
        """)

        operation_data = result["conditions"]["operation"]
        wt_types = list(operation_data.keys())
        wt_tabs = st.tabs([operation_data[wt]["description"] for wt in wt_types])

        for i, wt_key in enumerate(wt_types):
            with wt_tabs[i]:
                render_wt_type_results(wt_key, operation_data[wt_key], "Operation")

    with tabs[4]:
        st.subheader("Standard Thickness Evaluation (ASME B36.10)")
        df_std = evaluate_standard_thicknesses(pipe, load)
        if df_std.empty:
            st.warning("No standard thicknesses found for this OD.")
        else:
            st.dataframe(df_std, use_container_width=True, hide_index=True)
            passing = df_std[df_std["Status"] == "PASS"]
            if not passing.empty:
                first_pass = passing.iloc[0]
                st.success(
                    f"✅ Least passing thickness: **{first_pass['WT (in)']:.4f} in** (Schedule: {first_pass['Schedule']})"
                )
                st.info(
                    f"Limiting: {first_pass['Limiting Condition']} - {first_pass['Limiting Check']} with SF {first_pass['Safety Factor']}"
                )

                # Find closest standard >= input WT
                closest_wt, closest_sch = find_closest_passing_standard_wt(pipe, load, pipe.wt_in)
                if closest_wt:
                    if closest_wt == pipe.wt_in:
                        st.success(f"✅ Input WT ({pipe.wt_in:.4f} in) matches standard thickness (Sch. {closest_sch}) and passes all conditions.")
                    else:
                        st.info(f"📊 Closest standard thickness ≥ input ({pipe.wt_in:.4f} in): **{closest_wt:.4f} in** (Sch. {closest_sch})")
                else:
                    st.warning(f"⚠️ {closest_sch}")
            else:
                st.error("❌ No standard thickness meets all criteria. Consider:")
                st.markdown("- Increasing pipe grade (X-60, X-65)")
                st.markdown("- Reducing design/shut-in pressures")
                st.markdown("- Decreasing water depth")
                st.markdown("- Using custom (non-standard) wall thickness")

    with tabs[5]:
        st.subheader("Input Verification")
        notes = build_verification_notes(pipe, load, result)
        if notes:
            for note in notes:
                st.warning(note)
        else:
            st.success("✅ All inputs within typical design ranges. No flags detected.")

        with st.expander("Detailed Input Summary", expanded=False):
            st.json({"pipe": result["pipe"], "loading": result["loading"]}, expanded=False)

    st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Streamlit app
# -----------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="Riser Design Analysis", layout="wide")
    render_styles()
    render_hero()
    initialize_state()

    render_input_sections()
    render_reference_section()

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    if st.button("🔍 Calculate All Life Cycle Conditions", type="primary", use_container_width=True):
        pipe, load = build_pipe_and_load()
        analyzer = LifeCycleAnalyzer(pipe, load)
        result = analyzer.run_all_conditions()

        render_results(result, pipe, load)
    else:
        st.info("📝 Enter all design parameters manually, then click Calculate. Use Team 8 auto-load buttons for quick reference data entry.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.caption(
        f"API RP 1111 (3rd Ed 1999) + ASME B31.4/B31.8 | "
        f"Mill Tolerance: {MILL_TOLERANCE*100}% | "
        f"Corrosion: {CORROSION_RATE_PER_YEAR} in/year × {DESIGN_LIFE_YEARS} years | "
        f"Hydrotest Factor: {HYDROTEST_FACTOR}×"
    )


if __name__ == "__main__":
    main()
