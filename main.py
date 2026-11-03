import os
import json
import urllib.parse
import requests
from datetime import datetime
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuration API Keys & Telegram
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

client = Groq(api_key=GROQ_API_KEY)
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
    Kamu adalah pakar pembuatan produk digital premium siap jual.
    Tugasmu:
    1. Riset 1 ide produk digital laris (Ebook / Cheatsheet / Guide) untuk segmen pekerja kantor, IT support, atau produktivitas.
    2. Hindari topik ini: {json.dumps(past_topics)}
    3. Buat KONTEN LENGKAP & MENDALAM (MINIMAL 600-900 KATA).
       - JANGAN HANYA MEMBUAT OUTLINE ATAU JUDUL BAB!
       - Berikan contoh prompt asli, template siap pakai, atau instruksi langkah demi langkah yang nyata dan solutif.
       - Tulis minimal 3 Bab lengkap dengan penjelasannya.
    4. Buat copywriting deskripsi penjualan untuk Lynk.id.

    Kembalikan output DALAM FORMAT JSON SANGAT KETAT dengan key persis seperti ini:
    {{
        "judul": "Judul Produk Digital",
        "kategori": "Kategori",
        "alasan_tren": "Alasan singkat kenapa laris",
        "harga_rekomendasi": "Rp 25.000",
        "isi_ebook": "Isi materi lengkap mendalam...",
        "deskripsi_lynk": "Teks deskripsi penjualan Lynk.id"
    }}
    """

    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=4096,
        response_format={"type": "json_object"}
    )
    
    output_text = response.choices[0].message.content.strip()
    return json.loads(output_text)

def generate_image(prompt_text, filename):
    """Menghasilkan gambar visual berbasis prompt AI secara gratis"""
    encoded_prompt = urllib.parse.quote(f"Minimalist modern illustration of {prompt_text}, clean design, professional infographic style, high quality")
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=700&height=350&nologo=true"
    
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"Gagal generate gambar: {e}")
    return None

def create_pdf(filename, title, content):
    doc = SimpleDocTemplate(
        filename, 
        pagesize=letter,
        rightMargin=36, leftMargin=36, 
        topMargin=36, bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    # Palette Warna Premium Produk Digital
    PRIMARY_COLOR = colors.HexColor("#0F172A")    # Deep Slate / Navy
    ACCENT_COLOR = colors.HexColor("#2563EB")     # Vibrant Royal Blue
    TEXT_COLOR = colors.HexColor("#334155")       # Charcoal Body Text
    BG_BOX_COLOR = colors.HexColor("#F8FAFC")     # Soft Gray background
    BORDER_COLOR = colors.HexColor("#CBD5E1")     # Light Border Gray

    # Typography Styling
    title_style = ParagraphStyle(
        'DocTitle', 
        parent=styles['Heading1'], 
        fontSize=22, 
        leading=26, 
        textColor=PRIMARY_COLOR, 
        spaceAfter=10
    )
    
    heading_style = ParagraphStyle(
        'DocHeading', 
        parent=styles['Heading2'], 
        fontSize=13, 
        leading=17, 
        textColor=ACCENT_COLOR, 
        spaceBefore=16,
        spaceAfter=8
    )

    body_style = ParagraphStyle(
        'DocBody', 
        parent=styles['Normal'], 
        fontSize=9.5, 
        leading=14.5, 
        textColor=TEXT_COLOR, 
        spaceAfter=8
    )

    box_text_style = ParagraphStyle(
        'BoxBody', 
        parent=styles['Normal'], 
        fontSize=9, 
        leading=13.5, 
        textColor=PRIMARY_COLOR
    )

    # 1. Header Judul + Line Accent
    story.append(Paragraph(title, title_style))
    story.append(HRFlowable(width="100%", thickness=3, color=ACCENT_COLOR, spaceAfter=15))

    chapter_count = 0

    # 2. Parse Content & Inject Dynamic Visuals
    for paragraph in content.split('\n'):
        text = paragraph.strip()
        if not text:
            continue
            
        safe_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Deteksi Header / Bab
        if safe_text.startswith(('Bab', 'BAB', 'Chapter', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            chapter_count += 1
            story.append(Spacer(1, 8))
            story.append(Paragraph(safe_text, heading_style))
            story.append(HRFlowable(width="100%", thickness=1, color=BORDER_COLOR, spaceAfter=10))

            # Sisipkan Gambar Ilustrasi Setiap Bab Baru
            img_filename = f"chapter_{chapter_count}.jpg"
            img_path = generate_image(f"{title} - {safe_text}", img_filename)
            if img_path and os.path.exists(img_path):
                story.append(Image(img_path, width=540, height=200))
                story.append(Spacer(1, 10))

        # Format Kotak Sorotan (Callout Box) untuk Prompt / Template Siap Pakai
        elif safe_text.startswith(('-', 'Prompt:', 'Template:', 'Catatan:', 'Tips:')):
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
    prompt = f"Professional ebook cover mockup for '{title}', minimalist modern tech style, 3d book presentation, high resolution"
    return generate_image(prompt, filename)

def send_to_telegram(pdf_path, cover_path, data):
    caption = f"🚀 *PRODUK DIGITAL BARU SIAP UPLOAD*\n\n" \
              f"📌 *Judul:* {data['judul']}\n" \
              f"🏷️ *Kategori:* {data['kategori']}\n" \
              f"💡 *Alasan Tren:* {data['alasan_tren']}\n" \
              f"💰 *Harga:* {data['harga_rekomendasi']}\n\n" \
              f"📝 *Deskripsi Lynk.id (Copy-Paste):*\n{data['deskripsi_lynk']}"

    # Send Info
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": caption,
        "parse_mode": "Markdown"
    })

    # Send Cover Photo
    if cover_path and os.path.exists(cover_path):
        with open(cover_path, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": "🖼️ Cover Mockup Lynk.id"
            }, files={"photo": f})

    # Send Full PDF
    with open(pdf_path, 'rb') as f:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument", data={
            "chat_id": TELEGRAM_CHAT_ID
        }, files={"document": f})

if __name__ == "__main__":
    print("AI Agent sedang bekerja melakukan riset, generasi materi & gambar visual...")
    result = generate_market_research_and_content()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_filename = f"Produk_{timestamp}.pdf"
    cover_filename = f"Cover_{timestamp}.jpg"
    
    # Generate Full PDF & Images
    create_pdf(pdf_filename, result['judul'], result['isi_ebook'])
    cover_file = generate_cover_image(result['judul'], cover_filename)
    
    # Send Output
    send_to_telegram(pdf_filename, cover_file, result)
    save_topic_history(result['judul'])
    
    print("Selesai! PDF Visual, Cover, dan Deskripsi telah dikirim ke Telegram.")
