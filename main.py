import os
import json
import urllib.parse
import requests
from datetime import datetime
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Configuration API Keys & Telegram (Membaca dari Environment / GitHub Secrets)
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
    Kamu adalah AI Agent Riset Pasar & Content Creator Produk Digital.
    Tugasmu:
    1. Cari 1 ide topik produk digital yang sedang laris (Ebook / Cheatsheet / Guide) untuk segmen pekerja kantor, IT support, atau produktivitas.
    2. Hindari topik yang sudah pernah dibuat ini: {json.dumps(past_topics)}
    3. Buat konten lengkap dan padat produk digital tersebut (minimal 3 bab/bagian utama).
    4. Buat copywriting deskripsi penjualan untuk toko Lynk.id.

    Kembalikan output DALAM FORMAT JSON SANGAT KETAT dengan key persis seperti berikut:
    {{
        "judul": "Judul Produk Digital",
        "kategori": "Kategori",
        "alasan_tren": "Alasan singkat kenapa ini laris",
        "harga_rekomendasi": "Rp 15.000",
        "isi_ebook": "Isi materi lengkap dalam bentuk teks berpola rapi...",
        "deskripsi_lynk": "Teks deskripsi penjualan untuk Lynk.id"
    }}
    """

    # Menggunakan model rekomendasi Groq terbaru
    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=4096,
        response_format={"type": "json_object"}
    )
    
    output_text = response.choices[0].message.content.strip()
    return json.loads(output_text)

def create_pdf(filename, title, content):
    doc = SimpleDocTemplate(
        filename, 
        pagesize=letter,
        rightMargin=40, leftMargin=40, 
        topMargin=40, bottomMargin=40
    )
    styles = getSampleStyleSheet()
    story = []

    # Palette Warna Elegan & Profesional
    PRIMARY_COLOR = colors.HexColor("#1A365D")  # Navy Blue
    TEXT_COLOR = colors.HexColor("#2D3748")     # Dark Slate

    title_style = ParagraphStyle(
        'DocTitle', 
        parent=styles['Heading1'], 
        fontSize=20, 
        leading=24, 
        textColor=PRIMARY_COLOR, 
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'DocHeading', 
        parent=styles['Heading2'], 
        fontSize=13, 
        leading=17, 
        textColor=PRIMARY_COLOR, 
        spaceBefore=14,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'DocBody', 
        parent=styles['Normal'], 
        fontSize=10, 
        leading=15, 
        textColor=TEXT_COLOR, 
        spaceAfter=8
    )

    # Header Judul + Pembatas
    story.append(Paragraph(title, title_style))
    story.append(HRFlowable(width="100%", thickness=2, color=PRIMARY_COLOR, spaceAfter=14))

    # Parse Isi Teks
    for paragraph in content.split('\n'):
        text = paragraph.strip()
        if not text:
            continue
            
        safe_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Format judul bab jika mendeteksi awalan Bab/Chapter/Angka
        if safe_text.startswith(('Bab', 'BAB', 'Chapter', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            story.append(Spacer(1, 4))
            story.append(Paragraph(safe_text, heading_style))
        else:
            story.append(Paragraph(safe_text, body_style))

    doc.build(story)

def generate_cover_image(title, filename="cover.jpg"):
    prompt = f"Professional ebook cover design for '{title}', minimalist modern style, high resolution, vector art"
    encoded_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=800&height=1000&nologo=true"
    
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            return filename
    except Exception as e:
        print(f"Gagal generate cover: {e}")
    return None

def send_to_telegram(pdf_path, cover_path, data):
    caption = f"🚀 *PRODUK DIGITAL BARU SIAP UPLOAD*\n\n" \
              f"📌 *Judul:* {data['judul']}\n" \
              f"🏷️ *Kategori:* {data['kategori']}\n" \
              f"💡 *Alasan Tren:* {data['alasan_tren']}\n" \
              f"💰 *Harga:* {data['harga_rekomendasi']}\n\n" \
              f"📝 *Deskripsi Lynk.id (Copy-Paste):*\n{data['deskripsi_lynk']}"

    # 1. Send Text Info
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": caption,
        "parse_mode": "Markdown"
    })

    # 2. Send Cover Image
    if cover_path and os.path.exists(cover_path):
        with open(cover_path, 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto", data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": "🖼️ Cover Mockup Lynk.id"
            }, files={"photo": f})

    # 3. Send PDF File
    with open(pdf_path, 'rb') as f:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument", data={
            "chat_id": TELEGRAM_CHAT_ID
        }, files={"document": f})

if __name__ == "__main__":
    print("AI Agent sedang bekerja melakukan riset & generasi produk...")
    result = generate_market_research_and_content()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pdf_filename = f"Produk_{timestamp}.pdf"
    cover_filename = f"Cover_{timestamp}.jpg"
    
    # 1. Create PDF
    create_pdf(pdf_filename, result['judul'], result['isi_ebook'])
    
    # 2. Create Cover Image
    cover_file = generate_cover_image(result['judul'], cover_filename)
    
    # 3. Send All to Telegram
    send_to_telegram(pdf_filename, cover_file, result)
    
    # 4. Save History
    save_topic_history(result['judul'])
    
    print("Selesai! PDF, Cover, dan Deskripsi telah dikirim ke Telegram.")
