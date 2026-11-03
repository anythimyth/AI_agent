import os
import json
import requests
from datetime import datetime
from groq import Groq
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Configuration API Keys & Telegram (Ganti dengan Key Anda)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "gsk_YOUR_GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")

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
    3. Buat konten ringkas namun padat produk digital tersebut (minimal 3 bab/bagian utama).
    4. Buat copywriting deskripsi penjualan untuk toko Lynk.id.

    Kembalikan output DALAM FORMAT JSON SANGAT KETAT dengan struktur persis seperti berikut:
    {{
        "judul": "Judul Produk Digital",
        "kategori": "Kategori",
        "alasan_tren": "Alasan singkat kenapa ini laris",
        "harga_rekomendasi": "Rp 15.000",
        "isi_ebook": "Isi materi lengkap dalam bentuk teks berpola rapi...",
        "deskripsi_lynk": "Teks deskripsi penjualan untuk Lynk.id"
    }}
    """

    # Menggunakan model Llama 3.3 70B resmi dari Groq dengan paksaan format JSON
    response = client.chat.completions.create(
        model="qwen-2.5-coder-32b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=4096,
        response_format={"type": "json_object"}  # Memaksa output JSON murni yang valid
    )
    
    output_text = response.choices[0].message.content.strip()
    return json.loads(output_text)

def create_pdf(filename, title, content):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, spaceAfter=12)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=8)

    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 12))

    for paragraph in content.split('\n'):
        if paragraph.strip():
            # Clean special characters for ReportLab standard font
            safe_text = paragraph.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story.append(Paragraph(safe_text, body_style))
            story.append(Spacer(1, 6))

    doc.build(story)

def send_to_telegram(pdf_path, data):
    caption = f"🚀 *PRODUK DIGITAL BARU SIAP UPLOAD*\n\n" \
              f"📌 *Judul:* {data['judul']}\n" \
              f"🏷️ *Kategori:* {data['kategori']}\n" \
              f"💡 *Alasan Tren:* {data['alasan_tren']}\n" \
              f"💰 *Harga:* {data['harga_rekomendasi']}\n\n" \
              f"📝 *Deskripsi Lynk.id (Copy-Paste):*\n{data['deskripsi_lynk']}"

    # Send Message
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": caption,
        "parse_mode": "Markdown"
    })

    # Send Document
    with open(pdf_path, 'rb') as f:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument", data={
            "chat_id": TELEGRAM_CHAT_ID
        }, files={"document": f})

if __name__ == "__main__":
    print("AI Agent sedang bekerja melakukan riset & generasi produk...")
    result = generate_market_research_and_content()
    
    pdf_filename = f"Produk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    create_pdf(pdf_filename, result['judul'], result['isi_ebook'])
    
    send_to_telegram(pdf_filename, result)
    save_topic_history(result['judul'])
    print("Selesai! File dan deskripsi telah dikirim ke Telegram.")
