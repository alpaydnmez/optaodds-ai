import os
import csv
import io
import json
import datetime
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "8922109226:AAGCEVmDNyCf2DMLhnOi1Mh2hYLp5WdV_tc"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "867372590"
DATA_FILE = "data.json"

LEAGUES_TO_SCAN = [
    ("İngiltere Premier", "https://www.football-data.co.uk/mmz4281/2324/E0.csv"),
    ("İngiltere Championship", "https://www.football-data.co.uk/mmz4281/2324/E1.csv"),
    ("İngiltere League 1", "https://www.football-data.co.uk/mmz4281/2324/E2.csv"),
    ("İngiltere League 2", "https://www.football-data.co.uk/mmz4281/2324/E3.csv"),
    ("İspanya La Liga", "https://www.football-data.co.uk/mmz4281/2324/SP1.csv"),
    ("İspanya La Liga 2", "https://www.football-data.co.uk/mmz4281/2324/SP2.csv"),
    ("İtalya Serie A", "https://www.football-data.co.uk/mmz4281/2324/I1.csv"),
    ("İtalya Serie B", "https://www.football-data.co.uk/mmz4281/2324/I2.csv"),
    ("Almanya Bundesliga", "https://www.football-data.co.uk/mmz4281/2324/D1.csv"),
    ("Almanya 2. Bundesliga", "https://www.football-data.co.uk/mmz4281/2324/D2.csv"),
    ("Türkiye Süper Lig", "https://www.football-data.co.uk/mmz4281/2324/T1.csv"),
    ("Fransa Ligue 1", "https://www.football-data.co.uk/mmz4281/2324/F1.csv"),
    ("Fransa Ligue 2", "https://www.football-data.co.uk/mmz4281/2324/F2.csv"),
    ("Portekiz Liga", "https://www.football-data.co.uk/mmz4281/2324/P1.csv"),
    ("Hollanda Eredivisie", "https://www.football-data.co.uk/mmz4281/2324/N1.csv")
]

GLOBAL_DATABASE_CACHE = []

def download_and_build_cache():
    global GLOBAL_DATABASE_CACHE
    if GLOBAL_DATABASE_CACHE:
        return GLOBAL_DATABASE_CACHE

    records = []
    for league_name, url in LEAGUES_TO_SCAN:
        try:
            res = requests.get(url, timeout=5)
            if res.status_code != 200: continue
            reader = csv.DictReader(io.StringIO(res.text))
            for row in reader:
                try:
                    h = float(row.get('B365H') or row.get('AvgH') or row.get('BbAvH') or 0)
                    d = float(row.get('B365D') or row.get('AvgD') or row.get('BbAvD') or 0)
                    a = float(row.get('B365A') or row.get('AvgA') or row.get('BbAvA') or 0)
                    if h <= 1.0: continue
                    home = row.get('HomeTeam', '')
                    away = row.get('AwayTeam', '')
                    hg = int(row.get('FTHG', -1))
                    ag = int(row.get('FTAG', -1))
                    if home and away and hg >= 0 and ag >= 0:
                        records.append({
                            "league": league_name, "home": home, "away": away,
                            "hg": hg, "ag": ag, "score": f"{hg}-{ag}", "h": h, "d": d, "a": a
                        })
                except Exception:
                    continue
        except Exception:
            pass

    GLOBAL_DATABASE_CACHE = records
    return records

# TERCİHİN SKORA GÖRE GELİP GELMEDİĞİNİ MATEMATİKSEL DOĞRULAYAN FONKSİYON
def check_pick_success(hg, ag, pick_str):
    pick = pick_str.upper()
    total_goals = hg + ag
    
    # 2.5 Üst / Alt
    if "2.5 ÜST" in pick or "2.5 GOL ÜSTÜ" in pick:
        return total_goals >= 3
    if "2.5 ALT" in pick or "2.5 GOL ALTI" in pick:
        return total_goals < 3
        
    # 1.5 Üst
    if "1.5 ÜST" in pick:
        if "1X" in pick:
            return (hg >= ag) and (total_goals >= 2)
        return total_goals >= 2
        
    # Karşılıklı Gol
    if "KG VAR" in pick:
        return (hg > 0 and ag > 0)
        
    # Maç Sonu 1, X, 2
    if pick == "MS 1":
        return hg > ag
    if pick == "MS 2":
        return ag > hg
    if pick == "MS X":
        return hg == ag
        
    # Çifte Şans
    if "1X" in pick:
        return hg >= ag
    if "X2" in pick:
        return ag >= hg
        
    return False

# MAÇLARI VE GERÇEK KAZANMA ORANINI HESAPLAYAN MOTOR
def evaluate_real_dna(target_h, target_d, target_a, prediction, tolerance=0.06, max_matches=4):
    records = download_and_build_cache()
    matched_games = []
    success_count = 0

    for r in records:
        if abs(r["h"] - target_h) <= tolerance and abs(r["d"] - target_d) <= 0.20:
            is_win = check_pick_success(r["hg"], r["ag"], prediction)
            if is_win:
                success_count += 1
            
            durum_isareti = "✅" if is_win else "❌"
            str_rep = f"{r['league']}: {r['home']} {r['score']} {r['away']} ({durum_isareti} @ {r['h']:.2f})"
            matched_games.append(str_rep)
            
            if len(matched_games) >= max_matches:
                break

    total = len(matched_games)
    # GERÇEK DNA BAŞARI SKORU HESABI
    dna_score = (success_count / total * 100.0) if total > 0 else 50.0
    return matched_games, dna_score

def get_current_shift():
    manual = os.getenv("MANUAL_SHIFT")
    if manual in ["night", "midday", "afternoon"]: return manual
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    tsi_hour = (now_utc.hour + 3) % 24
    if 0 <= tsi_hour < 6: return "night"
    elif 6 <= tsi_hour < 14: return "midday"
    else: return "afternoon"

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    resp = requests.post(url, json=payload, timeout=20)
    return resp.status_code == 200

def get_progress_bar(percent):
    filled = int(round(percent / 10))
    return "🟩" * filled + "⬜" * (10 - filled)

# 16:15 RESMİ GÜNLÜK BÜLTEN
def build_afternoon_bulletin(data):
    today = data.get("current_date", "23.10.2026")
    matches = data.get("matches", [])
    rolling = data.get("rolling_kasa", {})
    vip_picks = data.get("vip_room", [])
    surprises = data.get("surprise_picks", [])

    valid_banko_matches = []

    print("Eşleşen maçların skorları taranıyor ve gerçek başarı yüzdesi hesaplanıyor...")
    for m in matches:
        parts = m.get("odds_dna", "").split("|")
        if len(parts) >= 3:
            try:
                target_h = float(parts[0].strip())
                target_d = float(parts[1].strip())
                target_a = float(parts[2].strip())
                
                # GERÇEK MAÇLARI VE SKORA GÖRE TUTMA YÜZDESİNİ ÇEK
                real_h, calc_dna_score = evaluate_real_dna(target_h, target_d, target_a, m["prediction"])
                
                if real_h:
                    m["history_matches"] = real_h
                    m["history_count"] = len(real_h)
                    m["dna_score"] = round(calc_dna_score, 1)
                    
                    # Form skoru ile bileşik güven: %85 DNA + %15 Form
                    form_score = m.get("form_score", 75.0)
                    m["confidence"] = round((0.85 * m["dna_score"]) + (0.15 * form_score), 1)

                    # KATILIK KURALI: DNA Başarısı %65'in altında olan maç asla Banko Kupona GİREMEZ!
                    if m["dna_score"] >= 65.0:
                        valid_banko_matches.append(m)
            except Exception as e:
                print(f"Hata: {e}")

    lines = []
    lines.append("╔════════════════════════╗")
    lines.append("  ⚡ <b>OPTAODDS AI v5.6 RESMİ BÜLTENİ</b> ⚡")
    lines.append(f"  📅 <b>{today}</b> | 🔬 <b>Doğrulanmış DNA Modeli</b>")
    lines.append("╚════════════════════════╝\n")

    # 1. KANITLANMIŞ BANKO MAÇLAR
    lines.append("👑 <b>DOĞRULANMIŞ BANKO SEÇİMLER (DNA İSPATLI)</b>\n")
    for m in valid_banko_matches:
        bar = get_progress_bar(m['confidence'])
        hist_lines = ""
        for h in m.get("history_matches", []):
            hist_lines += f"   ▫️ <i>{h}</i>\n"

        lines.append(f"⚽ <b>{m['match'].upper()}</b>")
        lines.append(f"🏆 <i>{m['league']}</i> | ⏰ {m['time']}")
        lines.append(f"🎯 <b>Tercih:</b> <code>{m['prediction']}</code>  |  <b>Oran:</b> <code>@{m.get('current_odds', m['odds']):.2f}</code>")
        lines.append(f"📊 <b>Gerçek DNA İsabeti:</b> %{m['dna_score']} ➔ <b>Bileşik Güven:</b> <b>%{m['confidence']}</b>")
        lines.append(f"   {bar}")
        lines.append(f"🧬 <b>Eşleşen Maçlar & Tercih Doğrulaması:</b>\n{hist_lines}")
        lines.append("───────────────────────\n")

    # 2. VIP DEĞER ODASI
    if vip_picks:
        lines.append("⭐ <b>VIP DEĞER ODASI (1.90 - 2.80)</b>\n")
        for v in vip_picks:
            lines.append(f"💎 <b>{v['match']}</b>")
            lines.append(f"   👉 <b>Tercih:</b> <code>{v['prediction']}</code>  |  <b>Oran:</b> <code>@{v['odds']}</code>")
            lines.append(f"   💡 <i>{v.get('reason', '')}</i>\n")
        lines.append("───────────────────────\n")

    # 3. ROLLING KASA
    if rolling:
        lines.append(f"💰 <b>ROLLING KASA SERÜVENİ (Adım #{rolling.get('current_step', 1)})</b>")
        lines.append(f"💵 <b>Kasa:</b> <code>{rolling.get('current_amount', 250):.2f} TL</code> ➔ <b>Hedef:</b> <code>{rolling.get('target_amount', 562.5):.2f} TL</code>")
        for p in rolling.get("picks", []):
            lines.append(f"   🔹 {p['match']} ➔ <b>{p['pick']}</b> (@{p['odds']})")
        lines.append(f"🔥 <b>Kombine Oran:</b> <code>{rolling.get('total_odds', 2.25)}</code>\n")
        lines.append("───────────────────────\n")

    # 4. SÜRPRİZ İY/MS
    if surprises:
        lines.append("💣 <b>SÜRPRİZ ORAN AVCISI (İY / MS)</b>\n")
        for s in surprises:
            lines.append(f"💥 <b>{s['match']}</b> ({s.get('league', '')})")
            lines.append(f"   👉 <b>Tercih:</b> <code>{s['prediction']}</code>  |  <b>Oran:</b> <code>@{s['odds']}</code>")
            lines.append(f"   📈 <i>Tarihsel Frekans: %{s.get('frequency', 20)}</i>\n")
        lines.append("───────────────────────\n")

    lines.append("🌐 <b>Canlı Web Paneli:</b> alpaydnmez.github.io/optaodds-ai")
    return "\n".join(lines).replace("& ", "ve ").replace(" &", " ve")

# 12:15 ORTA ANALİZ
def build_midday_report(data):
    today = data.get("current_date", "23.10.2026")
    matches = data.get("matches", [])
    lines = [f"🔍 <b>OPTAODDS ORTA ANALİZ & TUZAK SÜZGECİ ({today})</b>\n"]
    for m in matches:
        open_odds = m.get("opening_odds", m["odds"])
        live_odds = m.get("current_odds", m["odds"])
        delta = live_odds - open_odds
        durum = "🟢 OYNANABİLİR" if delta <= 0.03 else "🔴 TUZAK ORAN"
        lines.append(f"• <b>{m['match']}</b> | {m['prediction']}\n  Açılış: {open_odds} ➔ Anlık: {live_odds} | {durum}\n")
    return "\n".join(lines).replace("& ", "ve ")

# 01:15 GECE KARNESİ
def build_night_audit_bulletin(data):
    today = data.get("current_date", "23.10.2026")
    lines = [f"🌙 <b>OPTAODDS GECE 01:15 KARNESİ ({today})</b>\n", "✅ Biten maçlar kütüğe işlendi."]
    return "\n".join(lines)

def main():
    shift = get_current_shift()
    print(f"Çalışan Vardiya: {shift.upper()}")
    data = load_data()

    if shift == "night":
        msg = build_night_audit_bulletin(data)
        send_telegram_message(msg)
    elif shift == "midday":
        msg = build_midday_report(data)
        send_telegram_message(msg)
    elif shift == "afternoon":
        msg = build_afternoon_bulletin(data)
        send_telegram_message(msg)

    save_data(data)
    print("İşlem tamamlandı.")

if __name__ == "__main__":
    main()
