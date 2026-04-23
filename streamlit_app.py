import streamlit as st
from hoist_calc_core import (
    REGIME_COEFFS,
    calc_mechanism,
    check_drive,
)
from hoist_drawing import generate_drum_pdf
from hoist_overlay import overlay_hoist_dimensions

st.set_page_config(page_title="Расчёт механизма подъёма", layout="wide")

st.title("Онлайн‑расчёт механизма подъёма по Иванченко")

st.markdown(
    "Приложение выполняет расчёт полиспаста, каната, блоков, барабана и мощности привода, "
    "а также проверку выбранного двигателя и редуктора и формирует эскиз барабана в формате A3 (PDF)."
)

# ============================================================
# 1. Форма исходных данных и расчёт механизма
# ============================================================

st.header("1. Исходные данные механизма подъёма")

regime_options = {
    "Легкий (light)": "light",
    "Средний (medium)": "medium",
    "Тяжёлый (heavy)": "heavy",
    "Очень тяжёлый (very_heavy)": "very_heavy",
}

with st.form("basic_data_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        Q_t = st.number_input("Грузоподъёмность Q, тс", min_value=0.1, value=12.5, step=0.1)
        H_m = st.number_input("Высота подъёма H, м", min_value=0.1, value=13.5, step=0.1)

    with col2:
        v_lift_m_s = st.number_input(
            "Скорость подъёма крюка v, м/с",
            min_value=0.01,
            value=0.15,
            step=0.01,
        )
        eta_mech = st.number_input(
            "КПД механизма η",
            min_value=0.5,
            max_value=0.99,
            value=0.85,
            step=0.01,
        )

    with col3:
        regime_label = st.selectbox(
            "Режим работы крана",
            list(regime_options.keys()),
            index=1,
        )
        regime_code = regime_options[regime_label]

    submitted_basic = st.form_submit_button("Рассчитать механизм")

if "mech_result" not in st.session_state:
    st.session_state["mech_result"] = None

if submitted_basic:
    mech_result = calc_mechanism(
        Q_t=Q_t,
        H_m=H_m,
        v_lift_m_s=v_lift_m_s,
        eta_mech=eta_mech,
        regime_code=regime_code,
    )
    st.session_state["mech_result"] = mech_result

mech_result = st.session_state["mech_result"]

if mech_result is not None:
    basic = mech_result["basic"]
    pol = mech_result["pol"]
    rope = mech_result["rope"]
    block = mech_result["block"]
    eqb = mech_result["eqb"]
    drum = mech_result["drum"]
    ref = mech_result["ref"]

    # ---------- Блок "1. Исходные данные и мощность" ----------
    st.subheader("1. Исходные данные и мощность")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"**Грузоподъёмность Q:** {basic['Q_t']:.2f} тс  \n"
            f"**Высота подъёма H:** {basic['H_m']:.2f} м  \n"
            f"**Скорость подъёма v:** {basic['v_lift_m_s']:.3f} м/с  \n"
            f"**КПД механизма η:** {basic['eta_mech']:.2f}"
        )

    with col2:
        st.markdown(
            f"**Режим работы:** {basic['regime']['name']} "
            f"(h1={basic['regime']['h1']}, h2={basic['regime']['h2']}, h3={basic['regime']['h3']})  \n"
            f"**Мощность механизма Np:** ≈ {ref['Np_kW']:.2f} кВт  \n"
            f"**Коэф. запаса по мощности K_N:** {ref['K_N']:.2f}  \n"
            f"**Требуемая мощность двигателя Nдв,расч:** ≈ {ref['N_motor_req_kW']:.2f} кВт"
        )

    st.info("Из каталога выберите стандартный двигатель с Nдв ≥ Nдв,расч.")

    # ---------- Блок "2. Полиспаст и канат" ----------
    st.subheader("2. Полиспаст и канат")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"**Полиспаст (сдвоенный):**  \n"
            f"a = {pol['a']} ветви на барабане  \n"
            f"z = {pol['z']} ветвей всего  \n"
            f"u = {pol['u']:.1f}"
        )
        st.markdown(
            f"**Максимальное натяжение ветви Smax:** ≈ {pol['Smax_kgf']:.0f} кгс"
        )

    with col2:
        st.markdown(
            f"**Рекомендуемый канат:**  \n"
            f"d = {rope['d_mm']} мм  \n"
            f"Тип = {rope['type']}  \n"
            f"Sp = {rope['S_break_kgf']} кгс  \n"
            f"Sразр ≥ {rope['S_required_kgf']:.0f} кгс (n_k = {rope['n_k']:.1f})"
        )

    # ---------- Блок "3. Блоки и барабан" ----------
    st.subheader("3. Блоки и барабан (геометрия)")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"**Блоки:**  \n"
            f"D_e ≈ {block['D_e_mm']:.1f} мм  \n"
            f"Принят D = {block['D_adopted_mm']:.1f} мм  \n"
            f"h2 ≈ {block['h2']:.1f}"
        )
        st.markdown(
            f"**Уравнительный блок:**  \n"
            f"Dy ≈ {eqb['Dy_mm']:.0f} мм (h3 ≈ {eqb['h3']:.1f})"
        )

    with col2:
        st.markdown(
            f"**Барабан:**  \n"
            f"D_req ≈ {drum['D_req_mm']:.1f} мм (h1 ≈ {drum['h1']:.1f})  \n"
            f"Принят стандартный D_ср = {drum['D_center_mm']:.1f} мм  \n"
            f"L каната ≈ {drum['L_m']:.2f} м  \n"
            f"Шаг навивки t = {drum['t_step_mm']:.1f} мм  \n"
            f"z_half ≈ {drum['z_turns_half']:.0f} "
            f"(расчётное ≈ {drum['z_turns_half_raw']:.1f})  \n"
            f"Длина навивки l_t ≈ {drum['l_t_mm']:.1f} мм  \n"
            f"Длина барабана L_b ≈ {drum['L_b_mm']:.1f} мм"
        )
    # ---------- Эскиз барабана с подписями на готовом чертеже ----------
    st.subheader("3.1 Эскиз барабана (подписи на шаблоне)")

    company_name = st.text_input("Название фирмы для штампа", value='Моя фирма')

    # путь к шаблону в папке templates
    template_path = "templates/Eskiz-barbana.png"  # подставь своё реальное имя файла

    try:
        out_path = overlay_hoist_dimensions(mech_result, template_path, company_name=company_name)
        st.markdown("### Просмотр эскиза (для удобства можно увеличить масштаб браузера)")
        st.image(out_path, caption="Эскиз барабана с размерами", use_column_width=True)
    except FileNotFoundError:
        st.error(
            f"Не найден файл шаблона эскиза: {template_path}. "
            f"Проверь, что он лежит в папке templates и имя совпадает."
        )

    # ---------- Блок "4. Ориентиры по частоте и u" ----------
    st.subheader("4. Ориентиры по частоте барабана и передаточному числу")

    st.markdown(
        f"**Кратность полиспаста u:** {pol['u']:.1f}  \n"
        f"**Расчётная частота вращения барабана nб:** ≈ {ref['n_b_rpm']:.2f} об/мин"
    )

    st.markdown("**Требуемые передаточные числа u_треб для ряда nдв:**")
    st.table(
        {
            "nдв, об/мин": [g["n_motor_rpm"] for g in ref["gear_list"]],
            "u_треб": [round(g["u_required"], 2) for g in ref["gear_list"]],
        }
    )

    st.info(
        "Из каталога редукторов выберите вариант с u_cat, максимально близким к u_треб "
        "для выбранной nдв, и с Nред ≥ выбранной Nдв."
    )

# ============================================================
# 2. Форма проверки выбранного двигателя и редуктора
# ============================================================

st.header("5–7. Проверка выбранного двигателя и редуктора")

if "drive_result" not in st.session_state:
    st.session_state["drive_result"] = None
if "motor" not in st.session_state:
    st.session_state["motor"] = None
if "reducer" not in st.session_state:
    st.session_state["reducer"] = None

if mech_result is None:
    st.warning("Сначала выполните расчёт механизма (форма выше).")
else:
    with st.form("drive_check_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Двигатель**")
            motor_type = st.text_input("Тип двигателя", value="F411-8")
            motor_N_kW = st.number_input(
                "Номинальная мощность Nдв, кВт",
                min_value=0.1,
                value=22.0,
                step=0.1,
            )
            motor_n_rpm = st.number_input(
                "Номинальная частота nдв, об/мин",
                min_value=1.0,
                value=750.0,
                step=10.0,
            )
            motor_phi_max = st.number_input(
                "Коэф. максимального момента φ_max",
                min_value=1.0,
                value=2.0,
                step=0.1,
            )
            motor_phi_min = st.number_input(
                "Коэф. минимального момента φ_min",
                min_value=0.0,
                value=0.8,
                step=0.1,
            )

        with col2:
            st.markdown("**Редуктор**")
            red_type = st.text_input("Тип редуктора", value="2-500-50,94-4")
            red_u_cat = st.number_input(
                "Каталожное передаточное число u_cat",
                min_value=0.1,
                value=50.94,
                step=0.01,
            )
            red_N_red_kW = st.number_input(
                "Допустимая мощность редуктора Nред, кВт",
                min_value=0.1,
                value=25.0,
                step=0.1,
            )

        submitted_drive = st.form_submit_button("Проверить двигатель и редуктор")

    if submitted_drive:
        motor = {
            "type": motor_type,
            "N_kW": motor_N_kW,
            "n_rpm": motor_n_rpm,
            "phi_max": motor_phi_max,
            "phi_min": motor_phi_min,
        }
        reducer = {
            "type": red_type,
            "u_cat": red_u_cat,
            "N_red_kW": red_N_red_kW,
        }

        drive_result = check_drive(mech_result, motor, reducer)

        # сохраняем в session_state, чтобы использовать ниже
        st.session_state["drive_result"] = drive_result
        st.session_state["motor"] = motor
        st.session_state["reducer"] = reducer

# ------ вывод результатов проверки (5–7), если они есть ------
drive_result = st.session_state.get("drive_result", None)

if drive_result is not None and mech_result is not None:
    motor = st.session_state["motor"]
    reducer = st.session_state["reducer"]
    ref = mech_result["ref"]

    # ---------- Блок "5. Проверка выбранного двигателя" ----------
    st.subheader("5. Проверка выбранного двигателя")

    mm = drive_result["motor_moments"]
    motor_ok = drive_result["motor_ok"]

    st.markdown(
        f"**Двигатель:** {motor['type']}  \n"
        f"Nдв = {motor['N_kW']:.2f} кВт, nдв = {motor['n_rpm']:.0f} об/мин  \n"
        f"φ_max = {motor['phi_max']:.2f}, φ_min = {motor['phi_min']:.2f}  \n"
        f"Mном ≈ {mm['M_nom_kgfm']:.2f} кгс·м  \n"
        f"Mmax ≈ {mm['M_max_kgfm']:.2f} кгс·м  \n"
        f"Mmin ≈ {mm['M_min_kgfm']:.2f} кгс·м  \n"
        f"Mср ≈ {mm['M_avg_kgfm']:.2f} кгс·м  \n"
        f"Nдв,расч ≈ {ref['N_motor_req_kW']:.2f} кВт  \n"
        f"Запас по мощности ≈ {100*(motor['N_kW']/ref['N_motor_req_kW']-1):.1f} %"
    )
    # не забудь здесь исправить N_KW -> N_kW:
    # f"Запас по мощности ≈ {100*(motor['N_kW']/ref['N_motor_req_kW']-1):.1f} %"

    if motor_ok:
        st.success("Вывод по мощности двигателя: ПОДХОДИТ")
    else:
        st.error("Вывод по мощности двигателя: НЕ ПОДХОДИТ")

    # ---------- Блок "6. Проверка редуктора" ----------
    st.subheader("6. Проверка выбранного редуктора")

    red_m = drive_result["reducer_moments"]
    red_ok = drive_result["reducer_ok"]

    st.markdown(
        f"**Редуктор:** {reducer['type']}  \n"
        f"u_cat = {reducer['u_cat']:.2f}  \n"
        f"Nред (допустимая) = {reducer['N_red_kW']:.2f} кВт  \n"
        f"Mдоп редуктора ≈ {red_m['M_red_nom_kgfm']:.2f} кгс·м  \n"
        f"Mср двигателя ≈ {mm['M_avg_kgfm']:.2f} кгс·м"
    )

    if red_ok:
        st.success("Проверка по моменту: ПОДХОДИТ (Mср < Mдоп)")
    else:
        st.error("Проверка по моменту: НЕ ПОДХОДИТ (Mср ≥ Mдоп)")

    # ---------- Блок "7. Согласование по передаточному числу" ----------
    st.subheader("7. Согласование по передаточному числу")

    u_required = drive_result["u_required"]
    u_ok = drive_result["u_ok"]
    u_rel_dev = drive_result["u_rel_dev"] * 100.0
    n_b_rpm = drive_result["n_b_rpm"]

    st.markdown(
        f"**nб:** ≈ {n_b_rpm:.2f} об/мин  \n"
        f"u_треб ≈ {u_required:.2f}  \n"
        f"u_cat = {reducer['u_cat']:.2f}  \n"
        f"Относительное отклонение ≈ {u_rel_dev:.2f} %"
    )

    if u_ok:
        st.success("Согласование по u (допуск ~2%): ПОДХОДИТ")
    else:
        st.error("Согласование по u (допуск ~2%): НЕ ПОДХОДИТ")

        # ---------- Блок "8. Эскиз барабана (PDF)" ----------
    st.subheader("8. Эскиз барабана (PDF)")


    if st.button("Сформировать эскиз А3 (PDF)"):
        # out_path получен выше при overlay_hoist_dimensions
        pdf_bytes = generate_drum_pdf(
            mech_result,
            drive_result,
            company_name=company_name,
            eskiz_png_path=out_path,
        )
        st.download_button(
            label="Скачать эскиз барабана (A3, PDF)",
            data=pdf_bytes,
            file_name="eskiz_barbana_A3.pdf",
            mime="application/pdf",
        )
