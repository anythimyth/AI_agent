import os
import json
import urllib.parse
import requests
import random
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

def generate_image(prompt_text, filename, style_type="normal", width=800, height=500):
    """Menghasilkan gambar ilustrasi visual gratis via Pollinations"""
    if style_type == "coloring":
        base_prompt = (
            f"Simple black and white coloring page of {prompt_text}, "
            "vibrant clean outline vector, no shading, no colors, kid-friendly "
            "and adult-friendly bold lines, high resolution, coloring book style, on plain white background"
        )
    else:
        base_prompt = (
            f"Professional modern product cover illustration for '{prompt_text}', "
            "clean aesthetic, highly detailed, vibrant digital artwork"
        )
        
    encoded_prompt = urllib.parse.quote(base_prompt)
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

def create_pdf(filename, title, category, content, cover_img_path, is_coloring=False):
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

    # 1. HALAMAN COVER
    story.append(Spacer(1, 15))
    badge_text = "BUKU MEWARNAI DIGITAL" if is_coloring else f"PANDUAN DIGITAL • {category.upper()}"
    badge_p = Paragraph(f"<b>{badge_text}</b>", badge_style)
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

    sub_caption = "Buku Mewarnai Interaktif yang Bisa Diprint Berulang Kali" if is_coloring else "Panduan Praktis & Template Siap Pakai"
    story.append(Paragraph(f"<i>{sub_caption}</i>", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, textColor=TEXT_COLOR, alignment=1)))
    story.append(PageBreak())

    # 2. HALAMAN ISI
    chapter_count = 0
    for paragraph in content.split('\n'):
        text = paragraph.strip()
        if not text: continue
        safe_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        clean_upper = safe_text.upper()
        
        is_chapter = any(clean_upper.startswith(prefix) for prefix in ['BAB', 'CHAPTER', 'BAGIAN', 'HALAMAN', 'MODUL']) or (len(safe_text) > 2 and safe_text[0].isdigit() and safe_text[1] in ['.', ' '])

        if is_chapter:
            chapter_count += 1
            if chapter_count > 1: story.append(Spacer(1, 10))
            story.append(Paragraph(safe_text, heading_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=BORDER_COLOR, spaceAfter=10))

            img_filename = f"ch_img_{chapter_count}.jpg"
            img_style = "coloring" if is_coloring else "normal"
            img_w, img_h = (480, 480) if is_coloring else (540, 170)
            
            img_path = generate_image(f"{title} - {safe_text}", img_filename, style_type=img_style, width=img_w, height=img_h)
            if img_path and os.path.exists(img_path):
                story.append(Image(img_path, width=img_w, height=img_h))
                story.append(Spacer(1, 10))
                if is_coloring:
                    story.append(PageBreak())

        elif not is_coloring and safe_text.startswith(('-', 'Prompt:', 'Template:', 'Catatan:', 'Tips:', 'Langkah:')):
            p_box = Paragraph(safe_text, box_text_style)
            box_table = Table([[p_box]], colWidths=[540])
            box_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), BG_BOX_COLOR), ('BOX', (0,0), (-1,-1), 1, ACCENT_COLOR), ('PADDING', (0,0), (-1,-1), 8)]))
            story.append(box_table)
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(safe_text, body_style))

    doc.build(story)

# =============================================================================
# PRODUK 1: KREATIF / COLORING / EBOOK GENERAL
# =============================================================================
def generate_product_1():
    history = get_topic_history()
    past_topics = [h['topic'] for h in history]
    
    themes = ["buku_mewarnai", "work_hacks", "education", "digital_art"]
    selected_theme = random.choice(themes)

    prompt = f"""
    Kamu adalah pakar pembuatan produk digital kreatif.
    Riset ide berdasarkan tema: {selected_theme}.
    Hindari topik ini: {json.dumps(past_topics)}.

    - Jika 'buku_mewarnai': Buat minimal 4 Halaman Objek Mewarnai (contoh format: "HALAMAN 1: [Objek & Cerita Ringkas]").
    - Jika tema lain: Buat KONTEN LENGKAP 800-1200 KATA minimal 4 BAB.

    Format JSON ketat:
    {{
        "judul": "Judul Produk Kreatif",
        "kategori": "{selected_theme.replace('_', ' ').title()}",
        "alasan_tren": "Alasan singkat",
        "harga_rekomendasi": "Rp 15.000 - Rp 25.000",
        "isi_ebook": "Teks lengkap bab/halaman...",
        "deskripsi_lynk": "Teks deskripsi Lynk.id",
        "is_coloring_book": {"true" if selected_theme == "buku_mewarnai" else "false"}
    }}
    """
    response = client.models.generate_content(
        model='gemini-3.5-flash-lite', contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7)
    )
    return json.loads(response.text.strip())

# =============================================================================
# PRODUK 2: SPREADSHEET & CALCULATOR LOGIC
# =============================================================================
def generate_product_2():
    history = get_topic_history()
    past_topics = [h['topic'] for h in history]
    
    themes = ["keuangan_pribadi", "operasional_umkm", "planner_kreatif", "it_management"]
    selected_theme = random.choice(themes)

    prompt = f"""
    Kamu adalah pakar Template Spreadsheet & Kalkulator Bisnis.
    Riset 1 ide template di bawah sub-tema: {selected_theme}.
    Hindari topik ini: {json.dumps(past_topics)}.

    Buat Panduan Struktur Kolom + Rumus Formula Excel/Google Sheets Lengkap + Cara Menggunakannya.

    Format JSON ketat:
    {{
        "judul": "Judul Template Spreadsheet",
        "kategori": "{selected_theme.replace('_', ' ').title()}",
        "alasan_tren": "Alasan singkat",
        "harga_rekomendasi": "Rp 20.000 - Rp 35.000",
        "struktur_rumus": "Panduan struktur tabel dan rumus Excel...",
        "deskripsi_lynk": "Teks deskripsi Lynk.id"
    }}
    """
    response = client.models.generate_content(
        model='gemini-3.5-flash-lite', contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.6)
    )
    return json.loads(response.text.strip())

# =============================================================================
# PRODUK 3: PROMPT PACK AI / CHEATSHEET SCRIPT (BARU)
# =============================================================================
def generate_product_3():
    history = get_topic_history()
    past_topics = [h['topic'] for h in history]
    
    themes = ["prompt_chatgpt_admin", "prompt_midjourney_desain", "script_otomatisasi_python", "cheatsheet_copywriting_sales"]
    selected_theme = random.choice(themes)

    prompt = f"""
    Kamu adalah pakar AI Engineering & Automation Scripting.
    Riset 1 ide Prompt Pack / Script Otomatisasi di bawah tema: {selected_theme}.
    Hindari topik ini: {json.dumps(past_topics)}.

    Tugasmu:
    - Buat KUMPULAN 15-20 PROMPT AI SIAP PAKAI atau SCRIPT OTOMATISASI LENGKAP dengan parameter variabel yang bisa di-copy-paste langsung.
    - Berikan instruksi cara menggunakannya.

    Format JSON ketat:
    {{
        "judul": "Judul Prompt Pack / Script",
        "kategori": "{selected_theme.replace('_', ' ').title()}",
        "alasan_tren": "Alasan singkat",
        "harga_rekomendasi": "Rp 25.000",
        "isi_prompt_script": "Daftar prompt / script siap pakai...",
        "deskripsi_lynk": "Teks deskripsi Lynk.id"
    }}
    """
    response = client.models.generate_content(
        model='gemini-3.5-flash-lite', contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.6)
    )
    return json.loads(response.text.strip())

# =============================================================================
# TELEGRAM SENDER
# =============================================================================
def send_to_telegram(pdf_path, cover_path, data, tag="PRODUK"):
    caption = f"🚀 *[{tag}] PRODUK DIGITAL BARU SIAP UPLOAD*\n\n" \
              f"📌 *Judul:* {data['judul']}\n" \
              f"🏷️ *Kategori:* {data['kategori']}\n" \
              f"💡 *Alasan:* {data['alasan_tren']}\n" \
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
    # PRODUK 1: KREATIF / COLORING / EBOOK GENERAL
    # -------------------------------------------------------------------------
    print("AI Agent membuat Produk 1 (Ebook / Kreatif)...")
    res_p1 = generate_product_1()
    pdf_p1 = f"Prod1_Kreatif_{timestamp}.pdf"
    cover_p1 = f"Cover_P1_{timestamp}.jpg"
    is_coloring_p1 = (res_p1.get("is_coloring_book") == True or res_p1.get("is_coloring_book") == "true")
    c_style1 = "coloring" if is_coloring_p1 else "normal"
    
    c_file1 = generate_image(res_p1['judul'], cover_p1, style_type=c_style1, width=800, height=500)
    create_pdf(pdf_p1, res_p1['judul'], res_p1['kategori'], res_p1['isi_ebook'], c_file1, is_coloring=is_coloring_p1)
    send_to_telegram(pdf_p1, c_file1, res_p1, tag="PRODUK 1: KREATIF")
    save_topic_history(res_p1['judul'], res_p1['kategori'])
    
    # -------------------------------------------------------------------------
    # PRODUK 2: SPREADSHEET & CALCULATOR LOGIC
    # -------------------------------------------------------------------------
    print("AI Agent membuat Produk 2 (Spreadsheet)...")
    res_p2 = generate_product_2()
    pdf_p2 = f"Prod2_Spreadsheet_{timestamp}.pdf"
    cover_p2 = f"Cover_P2_{timestamp}.jpg"
    
    c_file2 = generate_image(res_p2['judul'], cover_p2, style_type="normal", width=800, height=500)
    create_pdf(pdf_p2, res_p2['judul'], res_p2['kategori'], res_p2['struktur_rumus'], c_file2, is_coloring=False)
    send_to_telegram(pdf_p2, c_file2, res_p2, tag="PRODUK 2: SPREADSHEET")
    save_topic_history(res_p2['judul'], res_p2['kategori'])

    # -------------------------------------------------------------------------
    # PRODUK 3: PROMPT PACK AI / SCRIPT OTOMATISASI (BARU)
    # -------------------------------------------------------------------------
    print("AI Agent membuat Produk 3 (Prompt Pack / Script)...")
    res_p3 = generate_product_3()
    pdf_p3 = f"Prod3_PromptPack_{timestamp}.pdf"
    cover_p3 = f"Cover_P3_{timestamp}.jpg"
    
    c_file3 = generate_image(res_p3['judul'], cover_p3, style_type="normal", width=800, height=500)
    create_pdf(pdf_p3, res_p3['judul'], res_p3['kategori'], res_p3['isi_prompt_script'], c_file3, is_coloring=False)
    send_to_telegram(pdf_p3, c_file3, res_p3, tag="PRODUK 3: PROMPT & SCRIPT")
    save_topic_history(res_p3['judul'], res_p3['kategori'])

    print("Selesai! 3 Produk Digital berbeda berhasil dikirim ke Telegram.")
