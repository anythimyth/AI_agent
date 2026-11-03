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

def save_topic_history(topic):
    history = get_topic_history()
    history.append({"topic": topic, "date": str(datetime.now())})
    with open(LOG_FILE, "w") as f:
        json.dump(history, f, indent=2)

def generate_market_research_and_content():
    history = get_topic_history()
    past_topics = [h['topic'] for h in history]

    prompt = f"""
    Kamu adalah pakar pembuatan produk digital premium siap jual bernilai tinggi.
    Tugasmu:
    1. Riset 1 ide produk digital laris (Ebook / Cheatsheet / Guide) untuk segmen pekerja kantor, IT support, atau produktivitas.
    2. Hindari topik yang sudah pernah dibuat ini: {json.dumps(past_topics)}
    3. Buat KONTEN LENGKAP, MENDALAM, DAN STRUKTUR JELAS (MINIMAL 800-1200 KATA).
       - Tulis minimal 4 BAB/BAGIAN UTAMA. Gunakan penanda jelas seperti "BAB 1: ...", "BAB 2: ...", "BAB 3: ...", "BAB 4: ...".
       - Setiap bab HARUS berisi penjelasan mendalam, contoh prompt asli siap pakai, template, atau tabel instruksi.
    4. Buat copywriting deskripsi penjualan untuk toko Lynk.id.

    Kembalikan output DALAM FORMAT JSON SANGAT KETAT dengan key persis seperti ini:
    {{
        "judul": "Judul Produk Digital",
        "kategori": "Kategori",
        "alasan_tren": "Alasan singkat kenapa laris",
        "harga_rekomendasi": "Rp 35.000",
        "isi_ebook": "Isi materi lengkap mendalam...",
        "deskripsi_lynk": "Teks deskripsi penjualan Lynk.id"
    }}
    """

    response = client.models.generate_content(
        model='gemini-3.5-flash-lite',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.5
        )
    )
    
    return json.loads(response.text.strip())

def generate_image(prompt_text, filename, width=800, height=400):
    """Menghasilkan gambar ilustrasi AI visual gratis via Pollinations"""
    encoded_prompt = urllib.parse.quote(f"Minimalist modern digital artwork of {prompt_text}, vibrant tech aesthetic, high quality illustration, clean ui design")
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
    
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"Gagal generate gambar ({filename}): {e}")
    return None

def create_pdf(filename, title, category, content, cover_img_path):
    doc = SimpleDocTemplate(
        filename, 
        pagesize=letter,
        rightMargin=36, leftMargin=36, 
        topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    # Palette Warna Premium Ebook (Indigo Slate Theme)
    PRIMARY_COLOR = colors.HexColor("#1E1B4B")   # Dark Indigo
    ACCENT_COLOR = colors.HexColor("#4F46E5")    # Vibrant Indigo/Violet
    TEXT_COLOR = colors.HexColor("#334155")      # Charcoal Body
    BG_BOX_COLOR = colors.HexColor("#F1F5F9")    # Slate Soft Gray
    BORDER_COLOR = colors.HexColor("#C7D2FE")    # Light Indigo Border

    # Typography Styling
    cover_title_style = ParagraphStyle(
        'CoverTitle', parent=styles['Heading1'], fontSize=24, leading=28, 
        textColor=PRIMARY_COLOR, spaceAfter=12, alignment=1
    )
    badge_style = ParagraphStyle(
        'CoverBadge', parent=styles['Normal'], fontSize=10, leading=12, 
        textColor=colors.white, alignment=1
    )
    heading_style = ParagraphStyle(
        'DocHeading', parent=styles['Heading2'], fontSize=14, leading=18, 
        textColor=ACCENT_COLOR, spaceBefore=14, spaceAfter=8
    )
    body_style = ParagraphStyle(
        'DocBody', parent=styles['Normal'], fontSize=9.5, leading=14.5, 
        textColor=TEXT_COLOR, spaceAfter=8
    )
    box_text_style = ParagraphStyle(
        'BoxBody', parent=styles['Normal'], fontSize=9, leading=13.5, 
        textColor=PRIMARY_COLOR
    )

    # -------------------------------------------------------------------------
    # 1. HALAMAN COVER KHUSUS (COVER PAGE)
    # -------------------------------------------------------------------------
    story.append(Spacer(1, 20))
    
    # Badge Kategori
    badge_p = Paragraph(f"<b>EBOOK PANDUAN DIGITAL • {category.upper()}</b>", badge_style)
    badge_table = Table([[badge_p]], colWidths=[280])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), ACCENT_COLOR),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 20))

    # Judul Ebook
    story.append(Paragraph(title, cover_title_style))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="60%", thickness=3, color=ACCENT_COLOR, spaceAfter=20, hAlign='CENTER'))

    # Gambar Cover Utuh
    if cover_img_path and os.path.exists(cover_img_path):
        story.append(Image(cover_img_path, width=480, height=280))
        story.append(Spacer(1, 20))

    story.append(Paragraph("<i>Panduan Praktis & Template Siap Pakai untuk Produktivitas Kerja</i>", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=11, textColor=TEXT_COLOR, alignment=1)))
    story.append(PageBreak()) # Pindah ke Halaman Isi

    # -------------------------------------------------------------------------
    # 2. HALAMAN ISI DENGAN ILUSTRASI PER BAB
    # -------------------------------------------------------------------------
    chapter_count = 0

    for paragraph in content.split('\n'):
        text = paragraph.strip()
        if not text:
            continue
            
        safe_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        clean_upper = safe_text.upper()
        
        # Deteksi Header / Bab (Lebih Fleksibel)
        is_chapter = any(clean_upper.startswith(prefix) for prefix in ['BAB', 'CHAPTER', 'BAGIAN']) or \
                     (len(safe_text) > 2 and safe_text[0].isdigit() and safe_text[1] in ['.', ' '])

        if is_chapter:
            chapter_count += 1
            if chapter_count > 1:
                story.append(Spacer(1, 10))

            story.append(Paragraph(safe_text, heading_style))
            story.append(HRFlowable(width="100%", thickness=1.5, color=BORDER_COLOR, spaceAfter=10))

            # Generate Gambar Ilustrasi Banner untuk Setiap Bab Baru
            img_filename = f"chapter_banner_{chapter_count}.jpg"
            img_path = generate_image(f"{title} {safe_text}", img_filename, width=700, height=250)
            if img_path and os.path.exists(img_path):
                story.append(Image(img_path, width=540, height=180))
                story.append(Spacer(1, 12))

        # Format Kotak Sorotan (Callout Box) untuk Prompt / Template / Tips
        elif safe_text.startswith(('-', 'Prompt:', 'Template:', 'Catatan:', 'Tips:', 'Langkah:')):
            p_box = Paragraph(safe_text, box_text_style)
            box_table = Table([[p_box]], colWidths=[540])
            box_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), BG_BOX_COLOR),
                ('BOX', (0,0), (-1,-1), 1, ACCENT_COLOR),
                ('PADDING', (0,0), (-1,-1), 8),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(box_table)
            story.append(Spacer(1, 6))

        else:
            story.append(Paragraph(safe_text, body_style))

    doc.build(story)

def generate_cover_image(title, filename="cover.jpg"):
    prompt = f"Modern professional book cover mockup for '{title}', minimalist tech aesthetic, vibrant color gradient, 3d render"
    return generate_image(prompt, filename, width=800, height=500)

def send_to_telegram(pdf_path, cover_path, data):
    caption = f"🚀 *PRODUK DIGITAL BARU SIAP UPLOAD*\n\n" \
              f"📌 *Judul:* {data['judul']}\n" \
              f"🏷️ *Kategori:* {data['kategori']}\n" \
              f"💡 *Alasan Tren:* {data['alasan_tren']}\n" \
              f"💰 *Harga:* {data['harga_rekomendasi']}\n\n" \
              f"📝 *Deskripsi Lynk.id (Copy-Paste):*\n{data['deskripsi_lynk']}"

    # 1. Kirim Pesan Teks
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": caption,
        "parse_mode": "Markdown"
    })

    # 2. Kirim Gambar Cover
    if cover_path and os.path.exists(cover_path):
        with open(cover_path, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": "🖼️ Cover Mockup Lynk.id"
            }, files={"photo": f})

    # 3. Kirim File PDF Utama
    with open(pdf_path, 'rb') as f:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument", data={
            "chat_id": TELEGRAM_CHAT_ID
        }, files={"document": f})

if __name__ == "__main__":
    print("AI Agent sedang bekerja membuat produk digital visual...")
    result = generate_market_research_and_content()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_filename = f"Produk_{timestamp}.pdf"
    cover_filename = f"Cover_{timestamp}.jpg"
    
    # 1. Generate Cover Image Utama
    cover_file = generate_cover_image(result['judul'], cover_filename)
    
    # 2. Generate PDF Visual Lengkap (dengan Cover Page + Gambar per Bab)
    create_pdf(pdf_filename, result['judul'], result['kategori'], result['isi_ebook'], cover_file)
    
    # 3. Send All to Telegram
    send_to_telegram(pdf_filename, cover_file, result)
    save_topic_history(result['judul'])
    
    print("Selesai! PDF Visual Premium, Cover Page, dan Deskripsi telah dikirim ke Telegram.")
