import io
import math

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader  # для вставки PNG [web:246]


# Простой ряд типоразмеров трубы (используется только для массы / подписи на PNG, если нужно)
PIPE_SERIES = [
    {"D_mm": 325, "s_mm": 20, "label": "Труба 325x20 ГОСТ 8732-78"},
    {"D_mm": 377, "s_mm": 25, "label": "Труба 377x25 ГОСТ 8732-78"},
    {"D_mm": 426, "s_mm": 30, "label": "Труба 426x30 ГОСТ 8732-78"},
]


def select_pipe_for_drum(D_center_mm: float) -> dict:
    """Подбор трубы: первая с D >= D_center, иначе последняя."""
    for pipe in PIPE_SERIES:
        if pipe["D_mm"] >= D_center_mm:
            return pipe
    return PIPE_SERIES[-1]


def calc_pipe_mass_kg(D_mm: float, s_mm: float, L_mm: float, rho_kg_m3: float = 7850.0) -> float:
    """Масса трубы (цилиндрической оболочки)."""
    D_outer_m = D_mm / 1000.0
    D_inner_m = (D_mm - 2.0 * s_mm) / 1000.0
    L_m = L_mm / 1000.0
    V_m3 = math.pi * (D_outer_m**2 - D_inner_m**2) / 4.0 * L_m
    return V_m3 * rho_kg_m3


def _make_report_pdf(
    eskiz_png_path: str,
) -> bytes:
    """
    Создаёт PDF A3 (landscape), КУДА ПРОСТО ВСТАВЛЯЕТСЯ ГОТОВЫЙ PNG-эскиз
    на весь лист. Все подписи и таблицы уже должны быть нарисованы в PNG.
    """
    buf = io.BytesIO()
    page_size = landscape(A3)
    c = canvas.Canvas(buf, pagesize=page_size)
    width, height = page_size

    img = ImageReader(eskiz_png_path)
    # Вставляем картинку на весь лист
    img_x = 0 * mm
    img_y = 0 * mm
    img_w = width
    img_h = height
    c.drawImage(img, img_x, img_y, width=img_w, height=img_h,
                preserveAspectRatio=True, anchor='sw')

    c.showPage()
    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()
    return pdf_bytes


def generate_drum_pdf(
    mech_result: dict,
    drive_result: dict,
    company_name: str = 'ООО "Фирма"',
    eskiz_png_path: str = "Eskiz-barbana_out.png",
) -> bytes:
    """
    Итоговая функция:
    - (при желании) можно здесь считать трубу и массу, но выводить их нужно на PNG;
    - генерирует PDF A3, в который просто вкладывается готовый PNG-эскиз.
    """
    # Если хочешь, можешь здесь посчитать трубу и массу и положить их в mech_result["drum"]["pipe_mass_kg"]
    # а уже hoist_overlay.py нарисует текст на самом эскизе.

    pdf_bytes = _make_report_pdf(eskiz_png_path=eskiz_png_path)
    return pdf_bytes