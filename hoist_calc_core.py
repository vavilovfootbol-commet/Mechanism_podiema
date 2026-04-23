import math

# ============================================================
# 0. Табличные данные из приложений Иванченко
# ============================================================

ROPE_PITCH_BY_D = {
    7.4:  9.0,
    8.0:  10.0,
    9.0:  11.0,
    10.0: 12.0,
    12.5: 13.5,
    13.5: 14.0,
    15.0: 16.0,
    16.0: 18.0,
    17.0: 19.0,
    18.0: 20.0,
    19.0: 21.0,
    20.0: 22.0,
    22.0: 24.0,
    23.0: 25.0,
    24.0: 26.0,
    26.0: 28.0,
    28.0: 30.0,
    29.0: 31.0,
    32.0: 34.0,
    34.0: 36.0,
    36.0: 38.0,
    38.0: 40.0,
    40.0: 42.0,
    42.0: 44.0,
    44.0: 46.0,
    48.0: 50.0,
    50.0: 52.0,
}

STANDARD_DRUM_DIAMETERS_MM = [
    160, 200, 250, 320, 400, 450, 500, 560, 630, 710, 800, 900, 1000
]

REGIME_COEFFS = {
    "light": {
        "name": "Легкий",
        "h1": 18.0,
        "h2": 20.0,
        "h3": 16.0,
    },
    "medium": {
        "name": "Средний",
        "h1": 20.0,
        "h2": 22.0,
        "h3": 18.0,
    },
    "heavy": {
        "name": "Тяжелый",
        "h1": 22.0,
        "h2": 25.0,
        "h3": 20.0,
    },
    "very_heavy": {
        "name": "Очень тяжелый",
        "h1": 24.0,
        "h2": 28.0,
        "h3": 22.0,
    },
}

# ===== ДОБАВКА: усечённый сортамент труб ГОСТ 8732-78 (S >= 25 мм) =====
GOST_8732_PIPES = [
    {"D_out_mm": 273, "S_mm": 25},
    {"D_out_mm": 325, "S_mm": 25},
    {"D_out_mm": 351, "S_mm": 28},
    {"D_out_mm": 377, "S_mm": 28},
    {"D_out_mm": 406, "S_mm": 30},
    {"D_out_mm": 426, "S_mm": 30},
    {"D_out_mm": 457, "S_mm": 30},
    {"D_out_mm": 508, "S_mm": 30},
    {"D_out_mm": 530, "S_mm": 32},
    {"D_out_mm": 630, "S_mm": 36},
]


def select_rope_pitch(d_rope_mm):
    d_list = sorted(ROPE_PITCH_BY_D)
    for d in d_list:
        if d_rope_mm <= d:
            return ROPE_PITCH_BY_D[d]
    return ROPE_PITCH_BY_D[d_list[-1]]


def select_drum_diameter(d_rope_mm, h1):
    D_req = h1 * d_rope_mm
    D_std = STANDARD_DRUM_DIAMETERS_MM[-1]
    for D in STANDARD_DRUM_DIAMETERS_MM:
        if D >= D_req:
            D_std = D
            break
    return D_req, D_std


def select_polispast(Q_t):
    a = 2
    if Q_t <= 3.2:
        z = 2
    elif 5 <= Q_t <= 12:
        z = 4
    elif 12.5 <= Q_t <= 16:
        z = 6
    elif 16.5 < Q_t <= 50:
        z = 8
    else:
        z = 10
    u = z / a
    return a, z, u


def calc_Smax_kgf(Q_t, z, eta_polispast=0.985):
    Q_kgf = Q_t * 1000.0
    return Q_kgf / (z * eta_polispast)


def select_rope_ivanchenko(Smax_kgf, n_k=5.5):
    S_req = n_k * Smax_kgf
    rope_table = [
        {"d_mm": 12.0, "S_break_kgf":  9000},
        {"d_mm": 14.0, "S_break_kgf": 12000},
        {"d_mm": 16.0, "S_break_kgf": 15500},
        {"d_mm": 17.5, "S_break_kgf": 18600},
        {"d_mm": 19.0, "S_break_kgf": 21500},
        {"d_mm": 21.5, "S_break_kgf": 26000},
        {"d_mm": 24.0, "S_break_kgf": 30000},
    ]
    candidate = None
    for rope in rope_table:
        if rope["S_break_kgf"] >= S_req:
            candidate = rope
            break
    if candidate is None:
        candidate = rope_table[-1]
    result = candidate.copy()
    result["n_k"] = n_k
    result["S_required_kgf"] = S_req
    result["type"] = "6x36"
    return result


def calc_block_diameter(d_rope_mm, h2):
    D_e = h2 * d_rope_mm
    D_adopted = D_e
    return {
        "D_e_mm": D_e,
        "D_adopted_mm": D_adopted,
        "h2": h2,
    }


def calc_equalizing_block(d_rope_mm, h3):
    Dy = h3 * d_rope_mm
    return {"Dy_mm": Dy, "h3": h3}


# ===== ДОБАВКА: выбор трубы по ГОСТ =====
def select_pipe_gost_8732(D_req_mm, S_min_mm=25.0):
    """
    Подбор трубы по ГОСТ 8732-78 по расчётному наружному диаметру D_req_mm,
    с условием S >= S_min_mm.
    """
    candidate = None
    for row in GOST_8732_PIPES:
        if row["D_out_mm"] >= D_req_mm and row["S_mm"] >= S_min_mm:
            candidate = row
            break
    if candidate is None:
        candidate = GOST_8732_PIPES[-1]
    return {
        "D_out_mm": candidate["D_out_mm"],
        "S_mm": candidate["S_mm"],
        "gost": "8732-78",
        "steel": "20",
    }


# ===== ИЗМЕНЁННАЯ calc_drum_geometry (остальное как у тебя) =====
def calc_drum_geometry(H_m, d_rope_mm, regime):
    h1 = regime["h1"]
    L_m = 2.0 * H_m

    D_req_mm, D_std_mm = select_drum_diameter(d_rope_mm, h1=h1)
    D_center_m = D_std_mm / 1000.0

    # подбор трубы по ГОСТ по принятому D_std_mm
    pipe = select_pipe_gost_8732(D_std_mm, S_min_mm=25.0)

    z_half_raw = L_m / (math.pi * D_center_m) + 2.0
    z_half = math.ceil(z_half_raw)
    t_mm = select_rope_pitch(d_rope_mm)
    l_t_mm = z_half * t_mm

    a_anc_mm = 20.0
    c_gap_mm = 180.0

    # твоя исходная формула длины барабана:
    L_b_mm = 2.0 * (l_t_mm + 4.0 * a_anc_mm) + c_gap_mm

    # дополнительно вводим "разложение" на L_h, L_k, L_g:
    L_h_mm = l_t_mm                  # нарезка на половине
    L_k_mm = 4.0 * a_anc_mm          # зона крепления
    L_g_mm = c_gap_mm                # гладкая часть между половинами

    D_center_mm = D_std_mm           # D_c
    D_min_mm = D_center_mm - d_rope_mm  # по дну канавки (упрощённо)

    return {
        "D_req_mm": D_req_mm,
        "D_center_mm": D_center_mm,
        "D_min_mm": D_min_mm,
        "L_m": L_m,
        "z_turns_half_raw": z_half_raw,
        "z_turns_half": z_half,
        "t_step_mm": t_mm,
        "l_t_mm": l_t_mm,
        "a_anc_mm": a_anc_mm,
        "c_gap_mm": c_gap_mm,
        "L_b_mm": L_b_mm,
        "L_h_mm": L_h_mm,
        "L_k_mm": L_k_mm,
        "L_g_mm": L_g_mm,
        "h1": h1,
        "pipe": pipe,
    }


def calc_drum_speed_from_vk(v_rope_m_s, D_drum_mm):
    D_m = D_drum_mm / 1000.0
    return 60.0 * v_rope_m_s / (math.pi * D_m)


def calc_drum_speed_from_v_and_u(v_hook_m_s, u_polispast, D_drum_mm):
    v_rope = u_polispast * v_hook_m_s
    return calc_drum_speed_from_vk(v_rope_m_s=v_rope, D_drum_mm=D_drum_mm)


def calc_hoist_power(basic):
    Q_kgf = basic["Q_t"] * 1000.0
    v = basic["v_lift_m_s"]
    eta = basic["eta_mech"]
    Np = Q_kgf * v / (102.0 * eta)
    return Np


def calc_motor_and_gear_reference(basic, drum, u_polispast, K_N=1.3, n_motor_series=None):
    if n_motor_series is None:
        n_motor_series = [500, 600, 750, 1000, 1500]
    Np = calc_hoist_power(basic)
    N_motor_req = K_N * Np
    n_b_rpm = calc_drum_speed_from_v_and_u(
        v_hook_m_s=basic["v_lift_m_s"],
        u_polispast=u_polispast,
        D_drum_mm=drum["D_center_mm"],
    )
    gear_list = []
    for n_m in n_motor_series:
        u_req = n_m / n_b_rpm
        gear_list.append({
            "n_motor_rpm": n_m,
            "u_required": u_req,
        })
    return {
        "Np_kW": Np,
        "K_N": K_N,
        "N_motor_req_kW": N_motor_req,
        "n_b_rpm": n_b_rpm,
        "gear_list": gear_list,
    }


def calc_motor_moments_kgfm(motor):
    M_nom = 975.0 * motor["N_kW"] / motor["n_rpm"]
    M_max = motor["phi_max"] * M_nom
    M_min = motor["phi_min"] * M_nom
    M_avg = 0.5 * (M_max + M_min)
    return {
        "M_nom_kgfm": M_nom,
        "M_max_kgfm": M_max,
        "M_min_kgfm": M_min,
        "M_avg_kgfm": M_avg,
    }


def calc_reducer_moments_kgfm(reducer, motor):
    M_red_nom = 975.0 * reducer["N_red_kW"] / motor["n_rpm"]
    return {
        "M_red_nom_kgfm": M_red_nom,
    }


def check_reducer_overload_ivanchenko(motor_mom_kgfm, red_mom_kgfm):
    M_avg = motor_mom_kgfm["M_avg_kgfm"]
    M_allow = red_mom_kgfm["M_red_nom_kgfm"]
    return M_avg < M_allow


def check_gear_ratio(u_required, u_cat, tolerance_rel=0.02):
    rel_dev = abs(u_cat - u_required) / u_required
    return rel_dev <= tolerance_rel, rel_dev


def check_motor_power(ref, motor, safety_factor=1.0):
    return motor["N_kW"] >= safety_factor * ref["N_motor_req_kW"]


# ====== ОБЁРТКИ ДЛЯ WEB =======

def calc_mechanism(Q_t, H_m, v_lift_m_s, eta_mech, regime_code):
    regime = REGIME_COEFFS[regime_code]

    basic = {
        "Q_t": Q_t,
        "H_m": H_m,
        "v_lift_m_s": v_lift_m_s,
        "eta_mech": eta_mech,
        "regime_code": regime_code,
        "regime": regime,
    }

    a, z, u = select_polispast(Q_t)
    Smax_kgf = calc_Smax_kgf(Q_t, z, eta_polispast=0.985)
    rope = select_rope_ivanchenko(Smax_kgf, n_k=5.5)

    h2 = regime["h2"]
    h3 = regime["h3"]

    block = calc_block_diameter(rope["d_mm"], h2=h2)
    eqb = calc_equalizing_block(rope["d_mm"], h3=h3)
    drum = calc_drum_geometry(H_m, rope["d_mm"], regime=regime)

    pol = {"a": a, "z": z, "u": u, "Smax_kgf": Smax_kgf}

    ref = calc_motor_and_gear_reference(basic, drum, u_polispast=u, K_N=1.3)

    result = {
        "basic": basic,
        "pol": pol,
        "rope": rope,
        "block": block,
        "eqb": eqb,
        "drum": drum,
        "ref": ref,
    }
    return result


def check_drive(mech_result, motor, reducer, tol_u_rel=0.02):
    basic = mech_result["basic"]
    pol = mech_result["pol"]
    drum = mech_result["drum"]
    ref = mech_result["ref"]

    motor_mom = calc_motor_moments_kgfm(motor)
    red_mom = calc_reducer_moments_kgfm(reducer, motor)

    n_b_rpm = calc_drum_speed_from_v_and_u(
        v_hook_m_s=basic["v_lift_m_s"],
        u_polispast=pol["u"],
        D_drum_mm=drum["D_center_mm"],
    )

    u_required = motor["n_rpm"] / n_b_rpm
    u_ok, u_rel_dev = check_gear_ratio(u_required, reducer["u_cat"], tolerance_rel=tol_u_rel)
    motor_ok = check_motor_power(ref, motor, safety_factor=1.0)
    red_ok = check_reducer_overload_ivanchenko(motor_mom, red_mom)

    drive_result = {
        "motor": motor,
        "reducer": reducer,
        "motor_moments": motor_mom,
        "reducer_moments": red_mom,
        "n_b_rpm": n_b_rpm,
        "u_required": u_required,
        "u_ok": u_ok,
        "u_rel_dev": u_rel_dev,
        "motor_ok": motor_ok,
        "reducer_ok": red_ok,
    }
    return drive_result