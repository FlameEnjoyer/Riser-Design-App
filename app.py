"""
Riser Design Calculation Web App
API RP 1111 + ASME B31.4/B31.8 checks

Manual-entry only. No AI integration.
"""

import math
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple

import pandas as pd
import streamlit as st

import asme_b36_10

# -----------------------------------------------------------------------------
# Constants and reference data
# -----------------------------------------------------------------------------
COLOR_PRIMARY = "#1e3a8a"
COLOR_SECONDARY = "#3b82f6"
COLOR_SUCCESS = "#10b981"
COLOR_ALERT = "#ef4444"

GRADE_PROPERTIES = {
    "X-52": {"smys_psi": 52000, "uts_psi": 66000},
    "X-60": {"smys_psi": 60000, "uts_psi": 75000},
    "X-65": {"smys_psi": 65000, "uts_psi": 77000},
}

MANUFACTURING_COLLAPSE_FACTOR = {
    "SMLS": 0.70,
    "ERW": 0.75,
    "DSAW": 0.60,
}

DEFAULT_E_PSI = 2.9e7
DEFAULT_POISSON = 0.30
DEFAULT_WATER_DENSITY = 64.0  # lb/ft^3

TEAM8_REFERENCE = {
    "Gas Riser (ID 3)": {
        "od": 20.0,
        "wt": 0.750,
        "grade": "X-52",
        "design_pressure": 211.0,
        "shut_in_pressure": 250.0,
        "water_depth": 700.0,
        "fluid_type": "Gas",
        "fluid_sg": 0.05,
        "manufacturing": "SMLS",
        "design_category": "Riser",
        "corrosion_allowance": 0.125,
    },
    "Oil Riser (ID 8)": {
        "od": 8.63,
        "wt": 0.500,
        "grade": "X-52",
        "design_pressure": 195.0,
        "shut_in_pressure": 230.0,
        "water_depth": 960.0,
        "fluid_type": "Oil",
        "fluid_sg": 0.82,
        "manufacturing": "SMLS",
        "design_category": "Riser",
        "corrosion_allowance": 0.125,
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
    corrosion_allowance_in: float
    grade: str
    manufacturing: str
    design_category: str  # "Pipeline" or "Riser"
    fluid_type: str  # Gas, Oil, Multiphase, Wet Gas
    fluid_sg: float
    smys_psi: float
    uts_psi: float
    E_psi: float = DEFAULT_E_PSI
    poisson: float = DEFAULT_POISSON


@dataclass
class LoadingCondition:
    design_pressure_psi: float
    shut_in_pressure_psi: float
    water_depth_m: float


# -----------------------------------------------------------------------------
# Core calculation engine
# -----------------------------------------------------------------------------
class RiserCalculator:
    def __init__(self, pipe: PipeProperties, load: LoadingCondition):
        self.pipe = pipe
        self.load = load

    @staticmethod
    def _ft_from_m(depth_m: float) -> float:
        return depth_m * 3.28084

    def external_pressure(self) -> float:
        depth_ft = self._ft_from_m(self.load.water_depth_m)
        return DEFAULT_WATER_DENSITY * depth_ft / 144.0

    def _hoop_design_factor(self) -> float:
        if self.pipe.design_category.lower() == "pipeline":
            return 0.72
        if self.pipe.fluid_type.lower() in ["gas", "wet gas"]:
            return 0.50
        if self.pipe.fluid_type.lower() in ["oil", "multiphase"]:
            return 0.60
        return 0.72

    @staticmethod
    def _burst_design_factor(design_category: str) -> float:
        return 0.90 if design_category.lower() == "pipeline" else 0.75

    def compute_burst(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        fd = self._burst_design_factor(self.pipe.design_category)
        fe = 1.0
        ft = 1.0
        od = self.pipe.od_in
        smys = self.pipe.smys_psi

        pb = 0.90 * smys * wt_eff / (od - wt_eff) if od > wt_eff else 0.0
        delta_p = p_internal - p_external
        if delta_p <= 0:
            sf = float("inf")
        else:
            sf = (fd * fe * ft * pb) / delta_p

        return {
            "name": "Burst",
            "pb": pb,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {
                "design_factor": fd,
                "joint_factor": fe,
                "temperature_factor": ft,
                "delta_p": delta_p,
            },
        }

    def compute_collapse(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        E = self.pipe.E_psi
        nu = self.pipe.poisson
        f_o = MANUFACTURING_COLLAPSE_FACTOR.get(self.pipe.manufacturing.upper(), 0.70)

        t_over_d = wt_eff / od
        py = 2 * smys * t_over_d
        pe = (2 * E * (t_over_d ** 3)) / (1 - nu ** 2)
        pc = (py * pe) / math.sqrt(py ** 2 + pe ** 2) if (py > 0 and pe > 0) else 0.0

        delta_p = p_external - p_internal
        if delta_p <= 0:
            sf = float("inf")
        else:
            sf = (f_o * pc) / delta_p

        return {
            "name": "Collapse",
            "py": py,
            "pe": pe,
            "pc": pc,
            "collapse_factor": f_o,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {"delta_p": delta_p},
        }

    def compute_propagation(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        fp = 0.80
        t_over_d = wt_eff / od
        pp = 35 * smys * (t_over_d ** 2.5)
        delta_p = p_external - p_internal

        if delta_p <= 0:
            sf = float("inf")
        else:
            sf = (fp * pp) / delta_p

        return {
            "name": "Propagation",
            "pp": pp,
            "design_factor": fp,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {"delta_p": delta_p},
        }

    def compute_hoop(self, p_internal: float, p_external: float, wt_eff: float) -> Dict[str, Any]:
        od = self.pipe.od_in
        smys = self.pipe.smys_psi
        design_factor = self._hoop_design_factor()
        delta_p = p_internal - p_external

        if wt_eff <= 0 or od <= wt_eff:
            hoop_stress = float("inf")
        else:
            hoop_stress = delta_p * od / (2 * wt_eff)

        allowable = design_factor * smys
        sf = allowable / hoop_stress if hoop_stress > 0 else float("inf")

        return {
            "name": "Hoop Stress",
            "hoop_stress": hoop_stress,
            "design_factor": design_factor,
            "allowable": allowable,
            "safety_factor": sf,
            "utilization": 0 if sf == float("inf") else 1 / sf,
            "pass_fail": sf >= 1.0,
            "details": {"delta_p": delta_p},
        }

    def run_all(self) -> Dict[str, Any]:
        p_internal = max(self.load.design_pressure_psi, self.load.shut_in_pressure_psi)
        p_external = self.external_pressure()
        wt_eff = max(self.pipe.wt_in - self.pipe.corrosion_allowance_in, 1e-6)

        burst = self.compute_burst(p_internal, p_external, wt_eff)
        collapse = self.compute_collapse(p_internal, p_external, wt_eff)
        propagation = self.compute_propagation(p_internal, p_external, wt_eff)
        hoop = self.compute_hoop(p_internal, p_external, wt_eff)

        checks = [burst, collapse, propagation, hoop]
        limiting = min(
            checks,
            key=lambda c: c["safety_factor"] if c["safety_factor"] != float("inf") else float("inf"),
        )
        all_pass = all(c["pass_fail"] for c in checks)

        return {
            "inputs": {
                "pipe": asdict(self.pipe),
                "loading": asdict(self.load),
                "p_internal_governing": p_internal,
                "p_external": p_external,
                "wt_effective": wt_eff,
            },
            "checks": checks,
            "all_pass": all_pass,
            "limiting": limiting,
        }


def evaluate_standard_thicknesses(base_pipe: PipeProperties, load: LoadingCondition) -> pd.DataFrame:
    thicknesses = asme_b36_10.get_standard_thicknesses(base_pipe.od_in)
    if not thicknesses:
        return pd.DataFrame()

    records: List[Dict[str, Any]] = []
    for wt in thicknesses:
        pipe_variant = PipeProperties(**{**asdict(base_pipe), "wt_in": wt})
        calc = RiserCalculator(pipe_variant, load)
        result = calc.run_all()
        limiting_sf = result["limiting"]["safety_factor"]
        records.append({
            "WT (in)": wt,
            "Schedule": schedule_name_for_thickness(base_pipe.od_in, wt),
            "Limiting Check": result["limiting"]["name"],
            "Safety Factor": limiting_sf,
            "Utilization (%)": 0 if limiting_sf == float("inf") else round(100 / limiting_sf, 1),
            "Status": "PASS" if result["all_pass"] else "FAIL",
        })

    return pd.DataFrame(records)


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
.subdued {{ color: #475569; font-size: 0.9rem; }}
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


def render_hero():
    st.markdown(
        """
        <div class='headline-card'>
            <div class='main-header'>Riser Design Analysis Tool</div>
            <div class='subdued'>API RP 1111 burst/collapse/propagation + ASME B31.4/B31.8 hoop checks</div>
            <div style='margin-top:12px; display:flex; gap:12px; flex-wrap:wrap;'>
                <span class='badge-pill' style='background:linear-gradient(120deg, #22c55e, #16a34a);'>Manual Entry Only</span>
                <span class='badge-pill' style='background:linear-gradient(120deg, #3b82f6, #1e3a8a);'>No AI Calls</span>
                <span class='badge-pill' style='background:linear-gradient(120deg, #f59e0b, #f97316);'>Design Factors per Standard</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(text: str, positive: bool) -> str:
    color = COLOR_SUCCESS if positive else COLOR_ALERT
    return f"<span class='badge-pill' style='background:{color};'>{text}</span>"


def info_chip(label: str, value: str) -> str:
    return f"<span class='metric-chip'>{label}: {value}</span>"


def initialize_state():
    defaults = TEAM8_REFERENCE["Gas Riser (ID 3)"]
    for key, value in {
        "od_in": defaults["od"],
        "wt_in": defaults["wt"],
        "design_pressure": defaults["design_pressure"],
        "shut_in_pressure": defaults["shut_in_pressure"],
        "water_depth": defaults["water_depth"],
        "corrosion_allowance": defaults["corrosion_allowance"],
        "fluid_sg": defaults["fluid_sg"],
        "grade": defaults["grade"],
        "manufacturing": defaults["manufacturing"],
        "fluid_type": defaults["fluid_type"],
        "design_category": defaults["design_category"],
    }.items():
        st.session_state.setdefault(key, value)


def apply_reference(name: str):
    ref = TEAM8_REFERENCE[name]
    st.session_state.od_in = ref["od"]
    st.session_state.wt_in = ref["wt"]
    st.session_state.design_pressure = ref["design_pressure"]
    st.session_state.shut_in_pressure = ref["shut_in_pressure"]
    st.session_state.water_depth = ref["water_depth"]
    st.session_state.corrosion_allowance = ref.get("corrosion_allowance", 0.0)
    st.session_state.fluid_sg = ref.get("fluid_sg", 1.0)
    st.session_state.grade = ref.get("grade", "X-52")
    st.session_state.manufacturing = ref.get("manufacturing", "SMLS")
    st.session_state.fluid_type = ref.get("fluid_type", "Gas")
    st.session_state.design_category = ref.get("design_category", "Riser")


def build_pipe_and_load() -> Tuple[PipeProperties, LoadingCondition]:
    grade_props = GRADE_PROPERTIES.get(st.session_state.grade, GRADE_PROPERTIES["X-52"])
    pipe = PipeProperties(
        od_in=st.session_state.od_in,
        wt_in=st.session_state.wt_in,
        corrosion_allowance_in=st.session_state.corrosion_allowance,
        grade=st.session_state.grade,
        manufacturing=st.session_state.manufacturing,
        design_category=st.session_state.design_category,
        fluid_type=st.session_state.fluid_type,
        fluid_sg=st.session_state.fluid_sg,
        smys_psi=grade_props["smys_psi"],
        uts_psi=grade_props["uts_psi"],
    )
    load = LoadingCondition(
        design_pressure_psi=st.session_state.design_pressure,
        shut_in_pressure_psi=st.session_state.shut_in_pressure,
        water_depth_m=st.session_state.water_depth,
    )
    return pipe, load


def render_input_sections():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.subheader("Design Inputs")
    st.caption("Manual data entry only. Reference buttons simply pre-fill the form; nothing is auto-loaded.")

    tabs = st.tabs(["Pipe Properties", "Pressures", "Environment"])

    with tabs[0]:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.session_state.od_in = st.number_input("Outer Diameter (in)", min_value=2.0, max_value=48.0, value=st.session_state.od_in, step=0.01)
            st.session_state.wt_in = st.number_input("Wall Thickness (in)", min_value=0.1, max_value=3.0, value=st.session_state.wt_in, step=0.01)
            st.session_state.corrosion_allowance = st.number_input("Corrosion Allowance (in)", min_value=0.0, max_value=0.5, value=st.session_state.corrosion_allowance, step=0.01)
        with col2:
            st.session_state.grade = st.selectbox("Pipe Grade", list(GRADE_PROPERTIES.keys()), index=list(GRADE_PROPERTIES.keys()).index(st.session_state.grade))
            st.session_state.manufacturing = st.selectbox("Pipe Type (Manufacturing)", ["SMLS", "ERW", "DSAW"], index=["SMLS", "ERW", "DSAW"].index(st.session_state.manufacturing))
            st.session_state.design_category = st.selectbox("Design Category", ["Riser", "Pipeline"], index=["Riser", "Pipeline"].index(st.session_state.design_category))
        with col3:
            st.session_state.fluid_type = st.selectbox("Fluid Type", ["Gas", "Oil", "Multiphase", "Wet Gas"], index=["Gas", "Oil", "Multiphase", "Wet Gas"].index(st.session_state.fluid_type))
            st.session_state.fluid_sg = st.number_input("Fluid Specific Gravity", min_value=0.02, max_value=1.50, value=st.session_state.fluid_sg, step=0.01)
            st.caption("SMYS/UTS auto-filled from selected grade.")

    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.design_pressure = st.number_input("Design Pressure (psi)", min_value=0.0, max_value=20000.0, value=st.session_state.design_pressure, step=10.0)
        with col2:
            st.session_state.shut_in_pressure = st.number_input("Shut-in Pressure (psi)", min_value=0.0, max_value=20000.0, value=st.session_state.shut_in_pressure, step=10.0)
        st.caption("Governing internal pressure = max(design, shut-in).")

    with tabs[2]:
        st.session_state.water_depth = st.number_input("Water Depth (m)", min_value=0.0, max_value=4000.0, value=st.session_state.water_depth, step=10.0)
        st.caption("External pressure uses seawater density 64 lb/ft³ and depth × 3.28084 ft/m.")

    st.markdown("</div>", unsafe_allow_html=True)


def render_reference_section():
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    with st.expander("Team 8 Reference (for manual use only)", expanded=False):
        st.write("Click a button to pre-fill the form. You can modify any value after loading.")
        cols = st.columns(2)
        if cols[0].button("Load Gas Riser (ID 3)"):
            apply_reference("Gas Riser (ID 3)")
        if cols[1].button("Load Oil Riser (ID 8)"):
            apply_reference("Oil Riser (ID 8)")
        st.json(TEAM8_REFERENCE, expanded=False)
    st.markdown("</div>", unsafe_allow_html=True)


def build_verification_notes(pipe: PipeProperties, load: LoadingCondition, result: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    d_over_t = pipe.od_in / max(pipe.wt_in, 1e-6)
    if pipe.wt_in <= pipe.corrosion_allowance_in:
        notes.append("Corrosion allowance exceeds or matches wall thickness.")
    if d_over_t > 120:
        notes.append("High D/t ratio; check ovality and fabrication tolerances.")
    if load.shut_in_pressure_psi > load.design_pressure_psi * 1.5:
        notes.append("Shut-in pressure is more than 1.5× design; confirm well control assumptions.")
    if pipe.fluid_sg < 0.02 or pipe.fluid_sg > 1.2:
        notes.append("Fluid specific gravity is outside typical range; validate input.")
    if pipe.corrosion_allowance_in > 0.25:
        notes.append("Corrosion allowance > 0.25 in; verify design life assumptions.")
    if result["limiting"]["safety_factor"] < 1.0:
        notes.append("Limiting check below SF 1.0; review governing load case or material grade.")
    return notes


def render_check_details(checks: List[Dict[str, Any]], p_internal: float, p_external: float, wt_eff: float):
    for chk in checks:
        with st.expander(f"{chk['name']} – SF {chk['safety_factor']:.2f}"):
            st.markdown(status_pill("PASS" if chk["pass_fail"] else "FAIL", chk["pass_fail"]), unsafe_allow_html=True)
            if chk["name"] == "Burst":
                st.write(f"Design ΔP (Pi-Po): {chk['details']['delta_p']:.2f} psi")
                st.write(f"Allowable (fd·fe·ft·Pb): {(chk['details']['design_factor']*chk['pb']):.2f} psi")
                st.write(f"Pb: {chk['pb']:.2f} psi | fd={chk['details']['design_factor']}, fe={chk['details']['joint_factor']}, ft={chk['details']['temperature_factor']}")
            elif chk["name"] == "Collapse":
                st.write(f"Design ΔP (Po-Pi): {chk['details']['delta_p']:.2f} psi")
                st.write(f"Py={chk['py']:.2f} psi | Pe={chk['pe']:.2f} psi | Pc={chk['pc']:.2f} psi | f_o={chk['collapse_factor']}")
            elif chk["name"] == "Propagation":
                st.write(f"Design ΔP (Po-Pi): {chk['details']['delta_p']:.2f} psi")
                st.write(f"Pp={chk['pp']:.2f} psi | fp={chk['design_factor']}")
            elif chk["name"] == "Hoop Stress":
                st.write(f"Hoop Stress: {chk['hoop_stress']:.2f} psi | Allowable: {chk['allowable']:.2f} psi | F={chk['design_factor']}")
            st.caption(f"Effective WT used: {wt_eff:.4f} in | Pi={p_internal:.2f} psi | Po={p_external:.2f} psi")


def render_results(result: Dict[str, Any], pipe: PipeProperties, load: LoadingCondition):
    checks = result["checks"]
    limiting = result["limiting"]
    all_pass = result["all_pass"]
    p_internal = result["inputs"]["p_internal_governing"]
    p_external = result["inputs"]["p_external"]
    wt_eff = result["inputs"]["wt_effective"]

    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    tabs = st.tabs(["Summary", "Check Details", "Standard Thicknesses", "Inputs & Verification"])

    with tabs[0]:
        st.subheader("Results Overview")
        status_html = status_pill("PASS" if all_pass else "FAIL", all_pass)
        st.markdown(f"Overall Status: {status_html}", unsafe_allow_html=True)
        st.markdown(f"Limiting Check: **{limiting['name']}** | SF = {limiting['safety_factor']:.2f}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Outer Diameter (in)", f"{pipe.od_in:.2f}")
        col2.metric("Wall Thickness (in)", f"{pipe.wt_in:.3f}")
        col3.metric("Water Depth (m)", f"{load.water_depth_m:.0f}")

        chips = [
            info_chip("Grade", pipe.grade),
            info_chip("Type", pipe.manufacturing),
            info_chip("Fluid", pipe.fluid_type),
            info_chip("Design Category", pipe.design_category),
        ]
        st.markdown(" ".join(chips), unsafe_allow_html=True)

        table_records = []
        for chk in checks:
            util_pct = 0 if chk["safety_factor"] == float("inf") else round(100 / chk["safety_factor"], 1)
            table_records.append({
                "Check": chk["name"],
                "Safety Factor": chk["safety_factor"],
                "Utilization (%)": util_pct,
                "Status": "PASS" if chk["pass_fail"] else "FAIL",
            })
        df = pd.DataFrame(table_records)
        st.dataframe(df, use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader("Detailed Checks")
        render_check_details(checks, p_internal, p_external, wt_eff)

    with tabs[2]:
        st.subheader("Standard Thickness Evaluation (ASME B36.10)")
        df_std = evaluate_standard_thicknesses(pipe, load)
        if df_std.empty:
            st.warning("No standard thicknesses found for this OD.")
        else:
            st.dataframe(df_std, use_container_width=True, hide_index=True)
            passing = df_std[df_std["Status"] == "PASS"]
            if not passing.empty:
                first_pass = passing.iloc[0]
                st.info(
                    f"Least passing thickness: {first_pass['WT (in)']:.4f} in (Sch. {first_pass['Schedule']}), "
                    f"limiting {first_pass['Limiting Check']} with SF {first_pass['Safety Factor']:.2f}."
                )
            else:
                st.error("No standard thickness meets all checks. Consider increasing OD, grade, or reducing pressures.")

    with tabs[3]:
        st.subheader("Inputs & Verification")
        st.markdown("Automated verification highlights potential data issues. Review before finalizing.")
        st.json(result["inputs"], expanded=False)
        notes = build_verification_notes(pipe, load, result)
        if notes:
            st.warning("\n".join(notes))
        else:
            st.success("No data range flags detected. Inputs look consistent with typical design values.")

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
    if st.button("Calculate", type="primary", use_container_width=True):
        pipe, load = build_pipe_and_load()
        calculator = RiserCalculator(pipe, load)
        result = calculator.run_all()

        render_results(result, pipe, load)
    else:
        st.info("Enter all values manually, then click Calculate. Use Team 8 buttons only to pre-fill the form.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("Built for API RP 1111 burst/collapse/propagation and ASME B31.4/B31.8 hoop checks. Safety factors target ≥ 1.0.")


if __name__ == "__main__":
    main()
