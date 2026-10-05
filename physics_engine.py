import math

STANDARD_DIAMETERS = [
    10, 12, 14, 16, 18, 20, 22, 25, 28, 30, 32, 35, 40, 45, 50,
    55, 60, 65, 70, 75, 80, 85, 90, 95, 100, 110, 120, 130, 140, 150
]

MATERIALS_DB = {
    "C45 Carbon Steel": {"Sut": 600, "Syt": 380, "G": 79e3},
    "40Cr1 Alloy Steel": {"Sut": 700, "Syt": 460, "G": 80e3},
    "4140 High Tensile Steel": {"Sut": 1000, "Syt": 750, "G": 80e3},
    "Stainless Steel 304": {"Sut": 515, "Syt": 205, "G": 75e3}
}

SURFACE_FACTORS = {
    "Ground": 0.92,
    "Machined / Cold-Drawn": 0.80,
    "Hot-Rolled": 0.60,
    "As-Forged": 0.45,
    "Custom": None
}

RELIABILITY_FACTORS = {
    "50% (kc = 1.000)": 1.000,
    "90% (kc = 0.897)": 0.897,
    "95% (kc = 0.868)": 0.868,
    "99% (kc = 0.814)": 0.814,
    "99.9% (kc = 0.753)": 0.753,
    "Custom": None
}


def calculate_fatigue_factors(Sut, ka, kb, kc, Kt, Kts, q, q_s):
    """Calculates Endurance Limit (Se), Bending Fatigue Factor (Kf), and Shear Fatigue Factor (Kfs)."""
    Se_prime = 0.5 * Sut if Sut <= 1400 else 700.0
    Se = Se_prime * ka * kb * kc
    Kf = 1.0 + q * (Kt - 1.0)
    Kfs = 1.0 + q_s * (Kts - 1.0)
    return Se, Kf, Kfs


def _solve_single_state(length, loads, support_left, support_right, f_key, m_key, t_key):
    """Solves reaction forces, reaction torque, and max bending moment for a specific load component state ('a' or 'm')."""
    total_force = sum(load.get(f_key, 0.0) for load in loads)
    total_moment_loads = sum(load.get(f_key, 0.0) *
                             load['x'] + load.get(m_key, 0.0) for load in loads)

    total_applied_torque = sum(load.get(t_key, 0.0) for load in loads)
    T_R1 = total_applied_torque if support_left == "Fixed" else 0.0

    if support_left == "Fixed" and support_right == "Free":
        R1 = total_force
        R2 = 0.0
        M_max = max([abs(total_moment_loads)] + [abs(l.get(m_key, 0.0))
                    for l in loads] if loads else [0.0])
    else:
        R2 = total_moment_loads / length if length > 0 else 0.0
        R1 = total_force - R2

        eval_points = sorted(
            list(set([0.0, length] + [l['x'] for l in loads])))
        b_moments = []
        for x in eval_points:
            M_x = R1 * x - sum(l.get(f_key, 0.0) * (x - l['x']) for l in loads if l['x'] <= x) + sum(
                l.get(m_key, 0.0) for l in loads if l['x'] <= x)
            b_moments.append(abs(M_x))
        M_max = max(b_moments) if b_moments else 0.0

    return R1, R2, T_R1, M_max


def solve_reactions_and_moments(length, loads, support_left, support_right):
    """Computes separate alternating (a) and mean (m) reaction forces, reaction torques, and max bending moments."""
    R1_a, R2_a, T_R1_a, M_a = _solve_single_state(
        length, loads, support_left, support_right, 'F_a', 'M_a', 'T_a')
    R1_m, R2_m, T_R1_m, M_m = _solve_single_state(
        length, loads, support_left, support_right, 'F_m', 'M_m', 'T_m')

    return {
        "R1_a": R1_a, "R1_m": R1_m,
        "R2_a": R2_a, "R2_m": R2_m,
        "T_R1_a": T_R1_a, "T_R1_m": T_R1_m,
        "M_a": M_a, "M_m": M_m
    }


def compute_shaft_design(length, loads, support_left, support_right,
                         fos, d_max, theta_max, material_name,
                         ka, kb, kc, Kt, Kts, q, q_s):
    """
    Computes required shaft diameter under fully fluctuating Force, Moment, and Torque
    inputs using the ASME Elliptic Fatigue Criterion.
    """
    mat = MATERIALS_DB[material_name]
    Sut, Syt, G = mat["Sut"], mat["Syt"], mat["G"]

    # Solve statics separately for alternating and mean loads
    statics = solve_reactions_and_moments(
        length, loads, support_left, support_right)

    M_a = statics["M_a"]
    M_m = statics["M_m"]

    # Calculate net maximum fluctuating torques across all loads
    T_a = max([abs(l.get('T_a', 0.0)) for l in loads] if loads else [0.0])
    T_m = max([abs(l.get('T_m', 0.0)) for l in loads] if loads else [0.0])
    T_peak = T_m + T_a  # Peak torque for rigidity check

    Se, Kf, Kfs = calculate_fatigue_factors(Sut, ka, kb, kc, Kt, Kts, q, q_s)

    # ASME Elliptic Criterion for Fluctuating Bending & Fluctuating Torsion
    term_bending_alt = (Kf * M_a / Se) ** 2
    term_bending_mean = (Kf * M_m / Syt) ** 2
    term_torsion_alt = (Kfs * T_a / Se) ** 2
    term_torsion_mean = (Kfs * T_m / Syt) ** 2

    d_strength = ((16.0 * fos / math.pi) * math.sqrt(
        4.0 * (term_bending_alt + term_bending_mean) +
        3.0 * (term_torsion_alt + term_torsion_mean)
    )) ** (1.0 / 3.0)

    # Torsional Rigidity Criterion based on Peak Torque
    d_rigidity = ((584 * T_peak * length) / (G * theta_max)
                  ) ** (1.0 / 4.0) if theta_max > 0 else 0

    d_required = max(d_strength, d_rigidity)

    selected_std_d = None
    for d_std in STANDARD_DIAMETERS:
        if d_std >= d_required:
            selected_std_d = d_std
            break

    actual_theta = (584 * T_peak * length) / \
        (G * (selected_std_d ** 4)) if selected_std_d else 0.0
    is_valid = (selected_std_d is not None) and (
        selected_std_d <= d_max) and (actual_theta <= theta_max)

    return {
        "success": is_valid,
        "d_calculated": d_required,
        "d_standard": selected_std_d,
        "d_max": d_max,
        "actual_theta": actual_theta,
        "theta_max": theta_max,
        "material": material_name,
        "Sut": Sut,
        "Syt": Syt,
        "R1_a": statics["R1_a"],
        "R1_m": statics["R1_m"],
        "R2_a": statics["R2_a"],
        "R2_m": statics["R2_m"],
        "T_R1_a": statics["T_R1_a"],
        "T_R1_m": statics["T_R1_m"],
        "M_a": M_a,
        "M_m": M_m,
        "T_a": T_a,
        "T_m": T_m,
        "Kf": Kf,
        "Kfs": Kfs,
        "Se": Se
    }
