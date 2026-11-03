import os
import json
import urllib.parse
import requests
from datetime import datetime
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image, Table, TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuration API Keys & Telegram
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

client = genai.Client(api_key=GEMINI_API_KEY)
LOG_FILE = "history_topics.json"

def get_topic_history():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_topic_history(topic, product_type):
    history = get_topic_history()
    history.append({"topic": topic, "type": product_type, "date": str(datetime.now())})
    with open(LOG_FILE, "w") as f:
        json.dump(history, f, indent=2)

def generate_image(prompt_text, filename, width=800, height=500):
    encoded_prompt = urllib.parse.quote(f"Professional modern product cover illustration for '{prompt_text}', clean tech aesthetic, 3d render style")
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
    
    try:
        response = requests.get(image_url, timeout=35)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"Gagal generate gambar ({filename}): {e}")
    return None

# =============================================================================
# PRODUK 1: GENERATE EBOOK / CHEATSHEET PDF
# =============================================================================
def generate_ebook_product():
    history = get_topic_history()
    past_topics = [h['topic'] for h in history]

    prompt = f"""
    Kamu adalah pakar pembuatan produk digital PDF premium.
    Tugasmu:
    1. Riset 1 ide Ebook / Cheatsheet laris untuk pekerja kantor/IT/produktivitas.
    2. Hindari topik ini: {json.dumps(past_topics)}
    3. Buat KONTEN LENGKAP & MENDALAM (800-1200 KATA), minimal 4 BAB lengkap dengan contoh prompt/template.
    4. Buat copywriting deskripsi Lynk.id.

    Format JSON ketat:
    {{
        "judul": "Judul Produk Ebook",
        "kategori": "Ebook / Guide",
        "alasan_tren": "Alasan singkat",
        "harga_rekomendasi": "Rp 25.000",
        "isi_ebook": "Isi materi lengkap mendalam...",
        "deskripsi_lynk": "Teks deskripsi Lynk.id"
    }}
    """
    response = client.models.generate_content(
        model='gemini-3.5-flash-lite', contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.5)
    )
    return json.loads(response.text.strip())

def create_pdf(filename, title, category, content, cover_img_path):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    PRIMARY_COLOR = colors.HexColor("#1E1B4B")
    ACCENT_COLOR = colors.HexColor("#4F46E5")
    TEXT_COLOR = colors.HexColor("#334155")
    BG_BOX_COLOR = colors.HexColor("#F1F5F9")
    BORDER_COLOR = colors.HexColor("#C7D2FE")

    cover_title_style = ParagraphStyle('CoverTitle', parent=styles['Heading1'], fontSize=22, leading=26, textColor=PRIMARY_COLOR, spaceAfter=12, alignment=1)
    badge_style = ParagraphStyle('CoverBadge', parent=styles['Normal'], fontSize=10, leading=12, textColor=colors.white, alignment=1)
    heading_style = ParagraphStyle('DocHeading', parent=styles['Heading2'], fontSize=13, leading=17, textColor=ACCENT_COLOR, spaceBefore=14, spaceAfter=8)
    body_style = ParagraphStyle('DocBody', parent=styles['Normal'], fontSize=9.5, leading=14.5, textColor=TEXT_COLOR, spaceAfter=8)
    box_text_style = ParagraphStyle('BoxBody', parent=styles['Normal'], fontSize=9, leading=13.5, textColor=PRIMARY_COLOR)

    # Cover
    story.append(Spacer(1, 15))
    badge_p = Paragraph(f"<b>PANDUAN DIGITAL • {category.upper()}</b>", badge_style)
    badge_table = Table([[badge_p]], colWidths=[280])
    badge_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), ACCENT_COLOR), ('PADDING', (0,0), (-1,-1), 6), ('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(badge_table)
    story.append(Spacer(1, 15))
    story.append(Paragraph(title, cover_title_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="60%", thickness=3, color=ACCENT_COLOR, spaceAfter=15, hAlign='CENTER'))

    if cover_img_path and os.path.exists(cover_img_path):
        story.append(Image(cover_img_path, width=460, height=260))
        story.append(Spacer(1, 15))

    story.append(PageBreak())

    # Content
    chapter_count = 0
    for paragraph in content.split('\n'):
        text = paragraph.strip()
        if not text: continue
        safe_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        clean_upper = safe_text.upper()
        
        is_chapter = any(clean_upper.startswith(prefix) for prefix in ['BAB', 'CHAPTER', 'BAGIAN']) or (len(safe_text) > 2 and safe_text[0].isdigit() and safe_text[1] in ['.', ' '])

        if is_chapter:
            chapter_count += 1
            if chapter_count > 1: story.append(Spacer(1, 10))
            story.append(Paragraph(safe_text, heading_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=BORDER_COLOR, spaceAfter=10))

            img_filename = f"ch_img_{chapter_count}.jpg"
            img_path = generate_image(f"{title} {safe_text}", img_filename, width=700, height=250)
            if img_path and os.path.exists(img_path):
                story.append(Image(img_path, width=540, height=170))
                story.append(Spacer(1, 10))

        elif safe_text.startswith(('-', 'Prompt:', 'Template:', 'Catatan:', 'Tips:')):
            p_box = Paragraph(safe_text, box_text_style)
            box_table = Table([[p_box]], colWidths=[540])
            box_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), BG_BOX_COLOR), ('BOX', (0,0), (-1,-1), 1, ACCENT_COLOR), ('PADDING', (0,0), (-1,-1), 8)]))
            story.append(box_table)
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(safe_text, body_style))

    doc.build(story)

# =============================================================================
# PRODUK 2: GENERATE SPREADSHEET / CALCULATOR LOGIC
# =============================================================================
def generate_spreadsheet_product():
    history = get_topic_history()
    past_topics = [h['topic'] for h in history]

    prompt = f"""
    Kamu adalah pakar pembuat Template Spreadsheet / Kalkulator Bisnis & Produktivitas.
    Tugasmu:
    1. Riset 1 ide Template Spreadsheet / Calculator Logic yang sangat dicari (Misal: Kalkulator HPP UMKM, Tracker Keuangan Pribadi, Dashboard KPI, Log Maintenance Server/IT).
    2. Hindari topik ini: {json.dumps(past_topics)}
    3. Buat Panduan Struktur Kolom + Rumus Formula Excel/Google Sheets Lengkap + Cara Menggunakannya.
    4. Buat copywriting deskripsi Lynk.id.

    Format JSON ketat:
    {{
        "judul": "Judul Template Spreadsheet",
        "kategori": "Spreadsheet / Logic Calculator",
        "alasan_tren": "Alasan singkat",
        "harga_rekomendasi": "Rp 20.000",
        "struktur_rumus": "Panduan struktur tabel, nama sheet, dan rumus Excel/Google Sheets (VLOOKUP, IF, QUERY, INDEX/MATCH)...",
        "deskripsi_lynk": "Teks deskripsi Lynk.id"
    }}
    """
    response = client.models.generate_content(
        model='gemini-3.5-flash-lite', contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.5)
    )
    return json.loads(response.text.strip())

# =============================================================================
# TELEGRAM SENDER
# =============================================================================
def send_to_telegram(pdf_path, cover_path, data, tag="PRODUK 1"):
    caption = f"🚀 *[{tag}] PRODUK DIGITAL BARU SIAP UPLOAD*\n\n" \
              f"📌 *Judul:* {data['judul']}\n" \
              f"🏷️ *Kategori:* {data['kategori']}\n" \
              f"💡 *Alasan Tren:* {data['alasan_tren']}\n" \
              f"💰 *Harga:* {data['harga_rekomendasi']}\n\n" \
              f"📝 *Deskripsi Lynk.id (Copy-Paste):*\n{data['deskripsi_lynk']}"

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
        "chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"
    })

    if cover_path and os.path.exists(cover_path):
        with open(cover_path, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={
                "chat_id": TELEGRAM_CHAT_ID, "caption": f"🖼️ Image Thumbnail [{tag}]", "parse_mode": "Markdown"
            }, files={"photo": f})

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument", data={
                "chat_id": TELEGRAM_CHAT_ID, "caption": f"📄 File Utama [{tag}]", "parse_mode": "Markdown"
            }, files={"document": f})

# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # -------------------------------------------------------------------------
    # EKSEKUSI PRODUK 1: EBOOK / CHEATSHEET PDF
    # -------------------------------------------------------------------------
    print("AI Agent sedang membuat Produk 1 (Ebook PDF)...")
    res_p1 = generate_ebook_product()
    pdf_p1 = f"Ebook_{timestamp}.pdf"
    cover_p1 = f"Cover_Ebook_{timestamp}.jpg"
    
    c_file1 = generate_image(res_p1['judul'], cover_p1, width=800, height=500)
    create_pdf(pdf_p1, res_p1['judul'], res_p1['kategori'], res_p1['isi_ebook'], c_file1)
    send_to_telegram(pdf_p1, c_file1, res_p1, tag="PRODUK 1: EBOOK")
    save_topic_history(res_p1['judul'], "Ebook")
    
    # -------------------------------------------------------------------------
    # EKSEKUSI PRODUK 2: SPREADSHEET / CALCULATOR LOGIC PDF
    # -------------------------------------------------------------------------
    print("AI Agent sedang membuat Produk 2 (Spreadsheet Logic)...")
    res_p2 = generate_spreadsheet_product()
    pdf_p2 = f"Spreadsheet_Logic_{timestamp}.pdf"
    cover_p2 = f"Cover_Spreadsheet_{timestamp}.jpg"
    
    c_file2 = generate_image(res_p2['judul'], cover_p2, width=800, height=500)
    # Merender panduan Spreadsheet menjadi PDF siap pakai
    create_pdf(pdf_p2, res_p2['judul'], res_p2['kategori'], res_p2['struktur_rumus'], c_file2)
    send_to_telegram(pdf_p2, c_file2, res_p2, tag="PRODUK 2: SPREADSHEET LOGIC")
    save_topic_history(res_p2['judul'], "Spreadsheet")

    print("Selesai! 2 Produk Digital berhasil dibuat dan dikirim ke Telegram.")
