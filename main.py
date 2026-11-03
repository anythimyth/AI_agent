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
    SimpleDocTemplate, BaseDocTemplate, PageTemplate, Frame, 
    Paragraph, Spacer, HRFlowable, Image, Table, TableStyle, PageBreak
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

def generate_image(prompt_text, filename, style_type="normal", width=800, height=800):
    if style_type == "coloring_outline":
        # Prompt khusus sketsa hitam putih
        base_prompt = f"Black and white coloring book page of {prompt_text}, clean thick outline vector line art, no shading, pure white background, kid friendly"
    elif style_type == "coloring_reference":
        # Prompt khusus gambar referensi berwarna ceria
        base_prompt = f"Cute cartoon 2d vector flat color illustration of {prompt_text}, white background, vibrant colors, kids style design, high quality"
    else:
        # Prompt cover biasa
        base_prompt = f"Professional digital cover illustration for '{prompt_text}', modern clean design, high resolution 3d graphic"
        
    encoded_prompt = urllib.parse.quote(base_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
    
    try:
        response = requests.get(image_url, timeout=40)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"Gagal generate gambar ({filename}): {e}")
    return None

# =============================================================================
# ENGINE PDF KHUSUS BUKU MEWARNAI (WORKSHEET LAYOUT)
# =============================================================================
def draw_dashed_border(canvas, doc):
    """Fungsi untuk menggambar garis putus-putus di pinggir kertas (Worksheet style)"""
    canvas.saveState()
    canvas.setDash(6, 4) # Ukuran garis putus-putus
    canvas.setLineWidth(2)
    canvas.setStrokeColor(colors.black)
    # roundRect(x, y, width, height, radius)
    canvas.roundRect(20, 20, letter[0]-40, letter[1]-40, 15)
    canvas.restoreState()

def create_coloring_worksheet(filename, data):
    doc = BaseDocTemplate(filename, pagesize=letter)
    
    # Setup frame agar teks tidak menabrak garis border
    frame = Frame(40, 40, letter[0]-80, letter[1]-80, id='normal')
    template = PageTemplate(id='worksheet', frames=frame, onPage=draw_dashed_border)
    doc.addPageTemplates([template])
    
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', fontSize=32, alignment=1, spaceAfter=8)
    sub_style = ParagraphStyle('Sub', fontSize=12, alignment=1, spaceAfter=25, textColor=colors.HexColor("#333333"))
    desc_style = ParagraphStyle('Desc', fontSize=9, alignment=1, leading=12)
    
    # Generate Halaman Mewarnai Berdasarkan Data JSON
    for idx, page in enumerate(data.get('halaman_mewarnai', [])):
        # 1. HEADER
        story.append(Paragraph('<font color="#2CA02C"><b>MARI</b></font> <font color="#FFB300"><b>MEWARNAI !</b></font>', title_style))
        story.append(Paragraph('<b>Lanjutkan Huruf yang terpotong dibawah yaa!</b>', sub_style))
        
        # 2. GENERATE 2 GAMBAR (BERWARNA & OUTLINE)
        col_img_name = f"color_ref_{idx}.jpg"
        out_img_name = f"outline_bw_{idx}.jpg"
        
        generate_image(page['nama_objek'], col_img_name, "coloring_reference", 300, 300)
        generate_image(page['nama_objek'], out_img_name, "coloring_outline", 600, 600)
        
        # 3. TOP SECTION (Huruf, Deskripsi, dan Gambar Referensi)
        letter_p = Paragraph(f"<font size=42><b>{page['huruf']}</b></font>", styles['Normal'])
        desc_p = Paragraph(page['deskripsi'], desc_style)
        
        left_text_table = Table([[letter_p, desc_p]], colWidths=[60, 160])
        left_text_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
        
        img_col = Image(col_img_name, width=130, height=130) if os.path.exists(col_img_name) else Paragraph("Img Error")
        img_col_table = Table([[img_col]])
        img_col_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 1.5, colors.black), # Bingkai kotak untuk gambar referensi
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('TOPPADDING', (0,0), (-1,-1), 5),
        ]))
        
        top_layout = Table([[left_text_table, img_col_table]], colWidths=[310, 170])
        top_layout.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'RIGHT'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
        
        story.append(top_layout)
        story.append(Spacer(1, 15))
        
        # 4. MIDDLE SECTION (Gambar Sketsa Utama)
        img_out = Image(out_img_name, width=380, height=380) if os.path.exists(out_img_name) else Paragraph("Img Error")
        img_out_table = Table([[img_out]], colWidths=[480])
        img_out_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        story.append(img_out_table)
        story.append(Spacer(1, 15))
        
        # 5. BOTTOM SECTION (Kotak Tebak Kata)
        puzzle_p = Paragraph(f"<font size=32><b>{page['soal_kata']}</b></font>", ParagraphStyle('puz', alignment=1))
        puzzle_table = Table([[puzzle_p]], colWidths=[300], rowHeights=[70])
        puzzle_table.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 2.5, colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        
        wrapper = Table([[puzzle_table]], colWidths=[480])
        wrapper.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        story.append(wrapper)
        
        story.append(PageBreak())
        
    doc.build(story)

# =============================================================================
# ENGINE PDF BIASA (UNTUK EBOOK & SPREADSHEET)
# =============================================================================
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

    chapter_count = 0
    for paragraph in content.split('\n'):
        text = paragraph.strip()
        if not text: continue
        clean_text = text.replace('*', '').replace('#', '').strip()
        safe_text = clean_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        clean_upper = safe_text.upper()
        
        is_chapter = any(clean_upper.startswith(prefix) for prefix in ['BAB ', 'CHAPTER ', 'BAGIAN ']) or (len(safe_text) > 2 and safe_text[0].isdigit() and safe_text[1] in ['.', ' '])

        if is_chapter:
            chapter_count += 1
            if chapter_count > 1: story.append(Spacer(1, 10))
            story.append(Paragraph(safe_text, heading_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=BORDER_COLOR, spaceAfter=10))

            img_filename = f"ch_img_{chapter_count}.jpg"
            short_prompt = safe_text[:40]
            img_path = generate_image(f"{title} - {short_prompt}", img_filename, style_type="normal", width=540, height=170)
            
            if img_path and os.path.exists(img_path):
                story.append(Spacer(1, 10))
                story.append(Image(img_path, width=540, height=170))
                story.append(Spacer(1, 15))

        elif safe_text.startswith(('-', 'Prompt:', 'Template:', 'Catatan:', 'Tips:', 'Langkah:')):
            p_box = Paragraph(safe_text, box_text_style)
            box_table = Table([[p_box]], colWidths=[540])
            box_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), BG_BOX_COLOR), ('BOX', (0,0), (-1,-1), 1, ACCENT_COLOR), ('PADDING', (0,0), (-1,-1), 8)]))
            story.append(box_table)
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(safe_text, body_style))

    doc.build(story)

# =============================================================================
# PRODUK 1 & 2: EBOOK & SPREADSHEET (Sama seperti sebelumnya)
# =============================================================================
def generate_ebook_product():
    history = get_topic_history()
    past_topics = [h['topic'] for h in history]
    themes = ["work_hacks", "it_support_guide", "education", "productivity_hacks"]
    selected_theme = random.choice(themes)

    prompt = f"""
    Kamu adalah penulis buku digital profesional.
    Buatlah Ebook/Panduan LENGKAP tentang: {selected_theme}.
    Hindari topik ini: {json.dumps(past_topics)}.
    Tulis minimal 5 BAB LENGKAP dan panjang minimal 1000 kata.

    Format JSON ketat:
    {{
        "judul": "Judul Ebook Lengkap",
        "kategori": "{selected_theme.replace('_', ' ').title()}",
        "alasan_tren": "Alasan singkat",
        "harga_rekomendasi": "Rp 25.000",
        "isi_ebook": "Teks naskah panjang mendalam...",
        "deskripsi_lynk": "Teks deskripsi Lynk.id"
    }}
    """
    response = client.models.generate_content(model='gemini-3.5-flash-lite', contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.6))
    return json.loads(response.text.strip())

def generate_spreadsheet_product():
    history = get_topic_history()
    past_topics = [h['topic'] for h in history]
    themes = ["keuangan_pribadi", "operasional_umkm", "planner_kreatif", "it_management"]
    selected_theme = random.choice(themes)

    prompt = f"""
    Kamu adalah pakar Template Spreadsheet.
    Riset 1 ide template di bawah sub-tema: {selected_theme}.
    Hindari topik ini: {json.dumps(past_topics)}.
    Jelaskan Struktur Sheet dan RUMUS KUNCI (VLOOKUP, IF, dll).

    Format JSON ketat:
    {{
        "judul": "Judul Template Spreadsheet",
        "kategori": "{selected_theme.replace('_', ' ').title()}",
        "alasan_tren": "Alasan singkat",
        "harga_rekomendasi": "Rp 25.000",
        "struktur_rumus": "Panduan rinci struktur tabel dan rumus Excel...",
        "deskripsi_lynk": "Teks deskripsi Lynk.id"
    }}
    """
    response = client.models.generate_content(model='gemini-3.5-flash-lite', contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.6))
    return json.loads(response.text.strip())

# =============================================================================
# PRODUK 3: BUKU MEWARNAI (FORMAT JSON TERSTRUKTUR UNTUK WORKSHEET)
# =============================================================================
def generate_coloring_product():
    history = get_topic_history()
    past_topics = [h['topic'] for h in history]

    prompt = f"""
    Kamu adalah pembuat Buku Mewarnai Digital Anak.
    Pilih 1 tema Mewarnai edukatif (Hewan, Kendaraan, Sayuran, Dll).
    Hindari topik ini: {json.dumps(past_topics)}.

    Buat 5 soal halaman mewarnai. Kembalikan data dalam struktur ARRAY objek JSON ketat.
    
    Format JSON:
    {{
        "judul": "Buku Mewarnai Interaktif",
        "kategori": "Buku Mewarnai Digital",
        "alasan_tren": "Melatih motorik dan huruf anak",
        "harga_rekomendasi": "Rp 15.000",
        "deskripsi_lynk": "Buku mewarnai edukatif interaktif",
        "halaman_mewarnai": [
            {{
                "huruf": "Aa",
                "nama_objek": "Ayam",
                "deskripsi": "Ayam adalah salah satu binatang bersayap namun ia lebih suka berjalan dengan kaki.",
                "soal_kata": "AY_ _ _"
            }},
            {{
                "huruf": "Bb",
                "nama_objek": "Bebek",
                "deskripsi": "Bebek suka berenang di air dan memiliki paruh pipih.",
                "soal_kata": "BE_ _ _"
            }}
        ]
    }}
    """
    response = client.models.generate_content(model='gemini-3.5-flash-lite', contents=prompt, config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.7))
    return json.loads(response.text.strip())

# =============================================================================
# TELEGRAM SENDER
# =============================================================================
def send_to_telegram(pdf_path, cover_path, data, tag="PRODUK"):
    caption = f"🚀 *[{tag}] PRODUK DIGITAL BARU SIAP UPLOAD*\n\n📌 *Judul:* {data['judul']}\n🏷️ *Kategori:* {data['kategori']}\n💰 *Harga:* {data['harga_rekomendasi']}\n\n📝 *Deskripsi Lynk.id:*\n{data['deskripsi_lynk']}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"})
    if cover_path and os.path.exists(cover_path):
        with open(cover_path, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"🖼️ Image Thumbnail [{tag}]"}, files={"photo": f})
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument", data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"📄 File Utama [{tag}]"}, files={"document": f})

# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print("AI Agent membuat Produk 1 (PDF Ebook Panjang)...")
    res_p1 = generate_ebook_product()
    pdf_p1 = f"Prod1_Ebook_{timestamp}.pdf"
    cover_p1 = f"Cover_P1_{timestamp}.jpg"
    c_file1 = generate_image(res_p1['judul'], cover_p1, style_type="normal", width=800, height=500)
    create_pdf(pdf_p1, res_p1['judul'], res_p1['kategori'], res_p1['isi_ebook'], c_file1)
    send_to_telegram(pdf_p1, c_file1, res_p1, tag="PRODUK 1: PDF EBOOK")
    save_topic_history(res_p1['judul'], res_p1['kategori'])
    
    print("AI Agent membuat Produk 2 (PDF Spreadsheet Logic)...")
    res_p2 = generate_spreadsheet_product()
    pdf_p2 = f"Prod2_Spreadsheet_{timestamp}.pdf"
    cover_p2 = f"Cover_P2_{timestamp}.jpg"
    c_file2 = generate_image(res_p2['judul'], cover_p2, style_type="normal", width=800, height=500)
    create_pdf(pdf_p2, res_p2['judul'], res_p2['kategori'], res_p2['struktur_rumus'], c_file2)
    send_to_telegram(pdf_p2, c_file2, res_p2, tag="PRODUK 2: SPREADSHEET")
    save_topic_history(res_p2['judul'], res_p2['kategori'])

    print("AI Agent membuat Produk 3 (PDF Worksheet Mewarnai)...")
    res_p3 = generate_coloring_product()
    pdf_p3 = f"Prod3_Worksheet_{timestamp}.pdf"
    cover_p3 = f"Cover_P3_{timestamp}.jpg"
    c_file3 = generate_image(res_p3['judul'], cover_p3, style_type="normal", width=800, height=500)
    
    # MENGGUNAKAN ENGINE WORKSHEET KHUSUS
    create_coloring_worksheet(pdf_p3, res_p3)
    
    send_to_telegram(pdf_p3, c_file3, res_p3, tag="PRODUK 3: PDF MEWARNAI")
    save_topic_history(res_p3['judul'], res_p3['kategori'])

    print("Selesai! 3 Produk PDF dengan layout Worksheet Premium berhasil dibuat.")
