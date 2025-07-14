import re
import fitz
import tabula
import pandas as pd
from PyPDF2 import PdfReader

# --- Adresse normalisieren ---
def normalize_address(text):
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', text.lower())).strip()

# --- Adresse matchen ---
def is_address_match(config_inhaber, detected_address):
    if not config_inhaber or not detected_address:
        return False
    norm_conf = normalize_address(config_inhaber)
    norm_addr = normalize_address(detected_address)
    return norm_conf in norm_addr or norm_addr in norm_conf

def is_bank_match(config_bank, detected_bank):
    if not config_bank or not detected_bank:
        return False
    norm_conf = normalize_address(config_bank)
    norm_bank = normalize_address(detected_bank)
    return norm_conf in norm_bank or norm_bank in norm_conf

def generate_booking_text(text_value):
    if not isinstance(text_value, str):
        return ""
    pattern = r"([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)?)"
    matches = re.findall(pattern, text_value)
    if len(matches) >= 2:
        return f"{matches[0]}, {matches[1]}"
    elif matches:
        return matches[0]
    fallback = " ".join(text_value.split()[:4])
    return fallback

def detect_address_for_postfinance(page):
    page_width = page.rect.width
    page_height = page.rect.height
    left_cutoff = page_width * 0.40
    top_cutoff = page_height * 0.30
    blocks = page.get_text("blocks")
    candidate_lines = []
    for b in blocks:
        x0, y0, x1, y1, text = b[:5]
        if x0 < left_cutoff and y0 < top_cutoff:
            for line in text.splitlines():
                line_stripped = line.strip()
                if line_stripped:
                    candidate_lines.append(line_stripped)
    ignore_keywords = ["postfinance", "roberto caruso", "www.postfinance.ch", "telefon +41", "sie werden betreut von"]
    filtered = [line for line in candidate_lines if not any(k in line.lower() for k in ignore_keywords)]
    address_text = "\n".join(filtered).strip()
    return address_text if address_text else "Keine Adresse gefunden (PostFinance)"

def detect_address_for_raiffeisen(page):
    blocks = page.get_text("blocks")
    target_x = 340
    target_y = 39
    tolerance = 5
    for b in blocks:
        x0, y0, x1, y1, text = b[:5]
        if abs(x0 - target_x) < tolerance and abs(y0 - target_y) < tolerance:
            lines = [l.strip() for l in text.splitlines()]
            for i, line in enumerate(lines):
                if "kontoinhaber" in line.lower():
                    candidate_lines = []
                    for follow_line in lines[i + 1:]:
                        if (
                            follow_line.lower().startswith("iban") or
                            follow_line.lower().startswith("kontoart") or
                            "ch" in follow_line.lower() or
                            "raiffeisen" in follow_line.lower()
                        ):
                            break
                        candidate_lines.append(follow_line.strip())
                    return " ".join(candidate_lines).strip()
    return "Keine Adresse gefunden (Raiffeisen)"

def detect_bank_and_address(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        page = doc[0]
        first_page_text = page.get_text().lower()
        if "postfinance" in first_page_text:
            bank = "PostFinance"
            address = detect_address_for_postfinance(page)
        elif "raiffeisen" in first_page_text:
            bank = "Raiffeisen"
            address = detect_address_for_raiffeisen(page)
        else:
            bank = "not found"
            address = "not found"
        doc.close()
        return bank, address
    except Exception as e:
        return ("Fehler", f"Fehler bei Bank- oder Adress-Erkennung: {e}")

def fallback_postfinance_tables(pdf_path):
    table_area_first_page = [400, 25, 800, 580]
    table_area_other_pages = [100, 25, 800, 580]
    table_columns = [100, 280, 400, 440, 500]
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    fallback_dfs = []
    for p in range(1, total_pages + 1):
        area = table_area_first_page if p == 1 else table_area_other_pages
        try:
            df_list = tabula.read_pdf(
                pdf_path,
                pages=p,
                area=[area],
                columns=table_columns,
                guess=False,
                multiple_tables=False,
                pandas_options={"header": None}
            )
            if df_list and df_list[0].shape[0] > 0:
                df = df_list[0]
                if len(df.columns) == 6:
                    df.columns = ["Date", "Text", "Credit", "Debit", "Value", "Balance"]
                    df.dropna(how="all", inplace=True)
                    fallback_dfs.append(df)
        except Exception:
            continue
    return fallback_dfs

def get_valid_dfs(dfs):
    return [df for df in dfs if isinstance(df, pd.DataFrame) and not df.empty]

def is_valid_table(df):
    if not isinstance(df, pd.DataFrame):
        return False
    cols = [str(c).lower() for c in df.columns if pd.notna(c)]
    return "datum" in cols and "text" in cols