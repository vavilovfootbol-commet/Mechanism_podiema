import math
from PIL import Image, ImageDraw, ImageFont, ImageOps


def load_font(size=10000):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default()


FONT = load_font(5000)


def overlay_hoist_dimensions(mech_result, template_path, out_path="Eskiz-barbana_out.png", company_name=""):
    """
    Накладывает численные значения размеров и исходных данных
    на ГОТОВЫЙ эскиз барабана формата A3.

    template_path – путь к исходному чертежу (png/jpg) с буквами L_b, L_h, L_g, L_k, D_c, D_min, Z_r, t.
    out_path     – путь к сохранённому результату.
    """

    drum = mech_result["drum"]
    basic = mech_result["basic"]
    rope = mech_result["rope"]
    pol  = mech_result["pol"]
    d_k  = rope["d_mm"]     # d_k = диаметр каната
    pipe = drum.get("pipe")

    u = pol["u"]   # кратность полиспаста
    z = pol["z"]   # число ветвей у груза
    a = pol["a"]   # число ветвей на барабане (2 = сдвоенный)

    D_c   = drum["D_center_mm"]
    D_min = drum["D_min_mm"]
    L_b   = drum["L_b_mm"]
    L_h   = drum["L_h_mm"]
    L_g   = drum["L_g_mm"]
    L_k   = drum["L_k_mm"]
    t     = drum["t_step_mm"]
    Z_r   = drum["z_turns_half"]

    # Исходные данные
    Q_t    = basic["Q_t"]
    H_m    = basic["H_m"]
    v_lift = basic["v_lift_m_s"]
    regime = basic["regime"]

    # Масса трубы (кг/м) по наружному диаметру и толщине стенки
    rho_steel = 7850.0  # кг/м3

    if pipe is not None:
        D_out_mm = pipe["D_out_mm"]
        S_mm     = pipe["S_mm"]

        D_out_m = D_out_mm / 1000.0
        t_m     = S_mm / 1000.0
        D_in_m  = D_out_m - 2.0 * t_m

        A_m2 = math.pi / 4.0 * (D_out_m**2 - D_in_m**2)
        mass_per_m = A_m2 * rho_steel   # кг/м
        mass_total = mass_per_m * (L_b / 1000.0) # кг, полная масса трубы барабана
    else:
        mass_per_m = None
        mass_total = None

    # Открываем шаблон
    img = Image.open(template_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    # Координаты (ПРИМЕР! – подгони под свой эскиз)
    coords = {
        "L_b":       (500, 90),
        "L_h":       (100, 200),
        "L_g":       (100, 300),
        "L_k":       (100, 400),
        "D_c":       (200, 500),
        "D_min":     (300, 500),
        "d_k":       (400, 500),
        "Zrt":       (100, 600),
        "material":  (100, 700),
        "basic_box": (100, 800),
        "t":         (500, 500),
        "polispast": (100, 900),
        "pipe_mass": (100, 1000),
        "company":   (100, 1100),
    }

        # Тексты для подписей размеров
    txt_L_b = f"{L_b:.0f}"
    txt_L_h = f"{L_h:.0f}"
    txt_L_g = f"{L_g:.0f}"
    txt_L_k = f"{L_k:.0f}"
    txt_D_c = f"{D_c:.0f}"
    txt_D_min = f"{D_min:.0f}"
    txt_d_k = f"{d_k:.0f}"
    txt_Zrt = f"{Z_r}"
    txt_t = f"{t:.0f}"
    txt_polispast = f"Кратность u = {u:.1f}; ветвей z = {z}; сдвоенный a = {a}"

    if mass_total is not None:
        txt_pipe_mass = f"{mass_total:.1f}"
    else:
        txt_pipe_mass = ""

    txt_company = company_name or " "

    if pipe is not None:
        D_out = pipe["D_out_mm"]
        S     = pipe["S_mm"]
        steel = pipe["steel"]
        gost  = pipe["gost"]
        txt_material = f"{D_out:.0f}×{S:.0f}"
    else:
        txt_material = f"{D_c:.0f}"

    # Строка с исходными данными (можно корректировать формат под твой штамп)
    txt_basic = (
        f"Q = {Q_t:.1f} тс; H = {H_m:.1f} м; v = {v_lift:.3f} м/с; \n\n"
        f"{regime['name']} (h1={regime['h1']:.0f}, h2={regime['h2']:.0f}, h3={regime['h3']:.0f}); \n\n"
        f"d каната = {rope['d_mm']:.1f} мм, n_k = {rope['n_k']:.1f}"
    )

    def draw_text_with_bg(draw_obj, xy, text, font):
        x, y = xy
        # textbbox возвращает (left, top, right, bottom)
        bbox = draw_obj.textbbox((x, y), text, font=font)
        left, top, right, bottom = bbox
        padding = 4
        draw_obj.rectangle(
            (left - padding, top - padding, right + padding, bottom + padding),
            fill="white",
        )
        draw_obj.text((x, y), text, font=font, fill="black")
    def draw_rotated_text_with_bg(base_img, xy, text, font, angle):
        """
        Рисует текст на отдельном прозрачном слое,
        поворачивает его и приклеивает к base_img.
        angle в градусах, против часовой (90 = снизу-вверх).
        """
        x, y = xy

        # Подготовим временное изображение под текст (минимального размера)
        dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        d = ImageDraw.Draw(dummy_img)
        bbox = d.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        # 2. Запас по краям, чтобы при повороте ничего не срезалось
        padding = 12  # было мало, увеличиваем

        # Рисуем текст на маленьком слое
        text_img = Image.new("RGBA", (tw + 2 * padding, th + 2 * padding), (0, 0, 0, 0))
        d2 = ImageDraw.Draw(text_img)
        d2.rectangle((0, 0, tw + 2 * padding, th + 2 * padding), fill="white")
        d2.text((padding, padding), text, font=font, fill="black")

        # Поворачиваем
        text_img = text_img.rotate(angle, expand=True)

        # Координата вставки (центрируем относительно (x, y))
        tx, ty = text_img.size
        paste_x = int(x - tx / 2)
        paste_y = int(y - ty / 2)

        base_img.alpha_composite(text_img, (paste_x, paste_y))     

    # Рисуем все подписи
    draw_text_with_bg(draw, coords["L_b"],      txt_L_b,      FONT)
    draw_text_with_bg(draw, coords["L_h"],      txt_L_h,      FONT)
    draw_text_with_bg(draw, coords["L_g"],      txt_L_g,      FONT)
    draw_text_with_bg(draw, coords["L_k"],      txt_L_k,      FONT)
    # D_c и D_min — повернутые на 90°
    draw_rotated_text_with_bg(img, coords["D_c"],   txt_D_c,   FONT, angle=90)
    draw_rotated_text_with_bg(img, coords["D_min"], txt_D_min, FONT, angle=90)
    draw_text_with_bg(draw, coords["d_k"],      txt_d_k,      FONT)
    draw_text_with_bg(draw, coords["t"],      txt_t,      FONT)
    draw_text_with_bg(draw, coords["Zrt"],      txt_Zrt,      FONT)
    draw_text_with_bg(draw, coords["material"], txt_material, FONT)
    draw_text_with_bg(draw, coords["basic_box"], txt_basic,   FONT)
    draw_text_with_bg(draw, coords["polispast"], txt_polispast,   FONT)

    if txt_pipe_mass:
        draw_text_with_bg(draw, coords["pipe_mass"], txt_pipe_mass, FONT)

    draw_text_with_bg(draw, coords["company"], txt_company, FONT)

    img.save(out_path)
    return out_path
