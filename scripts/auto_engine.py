import os
import json
import datetime
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "8922109226:AAGCEVmDNyCf2DMLhnOi1Mh2hYLp5WdV_tc"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "867372590"
DATA_FILE = "data.json"

def get_current_shift():
    manual = os.getenv("MANUAL_SHIFT")
    if manual in ["night", "midday", "afternoon"]:
        return manual
    
    # TSİ (UTC+3)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    tsi_hour = (now_utc.hour + 3) % 24

    if 0 <= tsi_hour < 6:
        return "night"
    elif 6 <= tsi_hour < 14:
        return "midday"
    else:
        return "afternoon"

def load_data():
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"{DATA_FILE} bulunamadı!")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram kimlik bilgileri eksik!")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    resp = requests.post(url, json=payload, timeout=15)
    if resp.status_code == 200:
        print("Telegram mesajı başarıyla iletildi.")
        return True
    else:
        print(f"Telegram API Hatası ({resp.status_code}): {resp.text}")
        return False

def build_telegram_bulletin(data):
    today = data.get("current_date", "23.10.2026")
    matches = data.get("matches", [])
    rolling = data.get("rolling_kasa", {})
    vip_picks = data.get("vip_room", [])
    surprises = data.get("surprise_picks", [])

    lines = []
    lines.append("⚡ <b>OPTAODDS AI v5.6 GÜNLÜK BÜLTENİ</b> ⚡")
    lines.append(f"📅 <b>Tarih:</b> {today} | 🔬 <b>6'lı Oran DNA + Form Hibrit</b>")
    lines.append("───────────────────────")
    
    # 1. Banko Kupon & Günün Seçimleri
    lines.append("🎯 <b>GÜNÜN RESMİ ANALİZ BÜLTENİ</b>")
    for m in matches:
        if m.get("status") == "banko" or m.get("confidence", 0) >= 75:
            hist_count = m.get("history_count", 0)
            lines.append(
                f"• <b>{m['league']}</b> | {m['time']}\n"
                f"  <b>{m['match']}</b>\n"
                f"  👉 <b>Tercih:</b> {m['prediction']} (Oran: {m['odds']})\n"
                f"  📊 Güven: %{m['confidence']} | DNA: {hist_count} Eşleşme\n"
            )
    lines.append("───────────────────────")

    # 2. VIP 1.90 - 2.80 Değer Odası
    if vip_picks:
        lines.append("⭐ <b>VIP DEĞER ODASI (1.90 - 2.80)</b>")
        for v in vip_picks:
            lines.append(
                f"• <b>{v['match']}</b> ({v['league']})\n"
                f"  🎯 <b>Değer Tercihi:</b> {v['prediction']} (Oran: {v['odds']})\n"
                f"  💡 <i>{v.get('reason', 'Pozitif Değer Beklentisi')}</i>\n"
            )
        lines.append("───────────────────────")

    # 3. Rolling Kasa
    if rolling:
        step = rolling.get("current_step", 1)
        base = rolling.get("current_amount", 250.0)
        target = rolling.get("target_amount", 562.5)
        lines.append(f"💰 <b>ROLLING KASA SERÜVENİ (Adım {step})</b>")
        lines.append(f"• <b>Mevcut Kasa:</b> {base:.2f} TL ➔ <b>Hedef:</b> {target:.2f} TL")
        for r_pick in rolling.get("picks", []):
            lines.append(f"• {r_pick['match']} ➔ <b>{r_pick['pick']}</b> ({r_pick['odds']})")
        lines.append(f"🔥 <b>Kombine Toplam Oran:</b> {rolling.get('total_odds', 2.25)}")
        lines.append("───────────────────────")

    # 4. Sürpriz İY/MS
    if surprises:
        lines.append("💣 <b>SÜRPRİZ ORAN AVCISI (İY / MS)</b>")
        for s in surprises:
            lines.append(f"• <b>{s['match']}</b> ➔ {s['prediction']} (Oran: {s['odds']}) [Frekans: %{s.get('frequency', 20)}]")
        lines.append("───────────────────────")

    lines.append("<i>Bol şanslar dileriz. Disiplinli kasa yönetimi esastır.</i>")
    
    return "\n".join(lines).replace("& ", "ve ").replace(" &", " ve")

def run_night_shift(data):
    print("Gece vardiyası: Skorlar kütüğe işleniyor...")

def run_midday_shift(data):
    print("Öğlen vardiyası: Oran hareketleri izleniyor...")

def run_afternoon_shift(data):
    print("İkindi vardiyası: Analiz tamamlanıyor ve Telegram yayını yapılıyor...")
    msg = build_telegram_bulletin(data)
    send_telegram_message(msg)

def main():
    shift = get_current_shift()
    print(f"Çalışan Vardiya: {shift.upper()}")
    data = load_data()

    if shift == "night":
        run_night_shift(data)
    elif shift == "midday":
        run_midday_shift(data)
    elif shift == "afternoon":
        run_afternoon_shift(data)

    save_data(data)
    print("İşlem tamamlandı.")

if __name__ == "__main__":
    main()
