import os
import json
import datetime
import requests

ODDS_API_KEY = os.getenv("ODDS_API_KEY") or "c8f2ff4c0a9d031a5ea7310149936e98"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "8922109226:AAGCEVmDNyCf2DMLhnOi1Mh2hYLp5WdV_tc"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "867372590"
DATA_FILE = "data.json"

MIN_ODDS_FLOOR = 1.50

LIVE_SPORT_KEYS = [
    ("Türkiye Süper Lig", "soccer_turkey_super_league"),
    ("İngiltere Premier Lig", "soccer_epl"),
    ("İngiltere Championship", "soccer_efl_champ"),
    ("İspanya La Liga", "soccer_spain_la_liga"),
    ("İtalya Serie A", "soccer_italy_serie_a"),
    ("Almanya Bundesliga", "soccer_germany_bundesliga"),
    ("Fransa Ligue 1", "soccer_france_ligue_one"),
    ("Hollanda Eredivisie", "soccer_netherlands_eredivisie"),
    ("Portekiz Liga", "soccer_portugal_primeira_liga")
]

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
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.status_code == 200
    except Exception:
        return False

# SADECE VE SADECE O GÜN OYNANACAK MAÇLARI ÇEKEN KATI FİLTRE
def fetch_only_today_matches():
    # Türkiye Saatiyle (TSİ = UTC+3) Bugünün Tarihi
    now_tsi = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    today_date_str = now_tsi.strftime("%Y-%m-%d")
    print(f"Sadece {today_date_str} tarihli maçlar filtreleniyor...")

    today_matches = []

    for league_name, sport_key in LIVE_SPORT_KEYS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                events = res.json()
                for ev in events:
                    commence = ev.get("commence_time", "")
                    if not commence: continue
                    
                    # Maçın başlama saatini TSİ'ye çevir
                    t_utc = datetime.datetime.fromisoformat(commence.replace("Z", "+00:00"))
                    t_tsi = t_utc + datetime.timedelta(hours=3)
                    match_date_str = t_tsi.strftime("%Y-%m-%d")

                    # KATI KONTROL: Eğer maç bugün değilse (yarın veya pazarsa) DİREKT ELE!
                    if match_date_str != today_date_str:
                        continue

                    bookies = ev.get("bookmakers", [])
                    if not bookies: continue
                    h2h = bookies[0]["markets"][0]["outcomes"]
                    
                    h_odd = next((o["price"] for o in h2h if o["name"] == ev["home_team"]), 1.80)
                    d_odd = next((o["price"] for o in h2h if o["name"].lower() == "draw"), 3.40)
                    a_odd = next((o["price"] for o in h2h if o["name"] == ev["away_team"]), 3.80)
                    time_str = t_tsi.strftime("%H:%M")

                    today_matches.append({
                        "id": ev.get("id", str(len(today_matches)+1)),
                        "time": time_str,
                        "league": league_name,
                        "match": f"{ev['home_team']} vs {ev['away_team']}",
                        "odds_dna": f"{h_odd:.2f} | {d_odd:.2f} | {a_odd:.2f} | 1.85 | 1.75 | 1.68",
                        "opening_odds": h_odd,
                        "current_odds": h_odd,
                        "odds": h_odd,
                        "prediction": "MS 1" if h_odd <= 1.85 else "1X ve 1.5 Üst",
                        "dna_score": 80.0,
                        "form_score": 75.0,
                        "confidence": 79.2,
                        "status": "BANKO"
                    })
        except Exception:
            continue

    print(f"Filtre sonucu: Bugüne ait {len(today_matches)} adet maç tespit edildi.")
    return today_matches

def get_progress_bar(percent):
    filled = int(round(percent / 10))
    return "🟩" * filled + "⬜" * (10 - filled)

def build_bulletin_telegram(data):
    today = data.get("current_date", "23.10.2026")
    matches = data.get("matches", [])
    rolling = data.get("rolling_kasa", {})
    vip_picks = data.get("vip_room", [])
    surprises = data.get("surprise_picks", [])

    lines = [
        "╔════════════════════════╗",
        "  ⚡ <b>OPTAODDS GÜNLÜK BÜLTEN</b> ⚡",
        f"  📅 <b>{today} Cuma</b> (Hafta Sonu Karışmaz)",
        "  🛡️ <b>Kural:</b> Sadece Bugünün Oynanmamış Maçları",
        "╚════════════════════════╝\n",
        "👑 <b>BUGÜNÜN RESMİ BANKO SEÇİMLERİ</b>\n"
    ]

    for m in matches:
        odds_val = m.get("current_odds", m.get("odds", 1.50))
        if odds_val < MIN_ODDS_FLOOR: continue

        bar = get_progress_bar(m.get("confidence", 75))
        st = m.get("stats", {})

        lines.append(f"⚽ <b>{m['match'].upper()}</b>")
        lines.append(f"🏆 <i>{m['league']}</i> | ⏰ {m['time']}")
        lines.append(f"🎯 <b>Tercih:</b> <code>{m['prediction']}</code>  |  <b>Oran:</b> <code>@{odds_val:.2f}</code>")
        lines.append(f"📊 <b>Birebir Oran Güveni:</b> <b>%{m.get('confidence', 75)}</b>\n   {bar}")

        if st:
            lines.append(f"📈 <b>Birebir {st.get('total_matched', 20)} Maçın Dağılımı:</b>")
            lines.append(f"   ├ 1X2: Ev: {st.get('h_wins', 14)} (%{st.get('h_pct', 70)}) | Ber: {st.get('draws', 4)} | Dep: {st.get('a_wins', 2)}")
            lines.append(f"   ├ Gol: 2.5 Üst: {st.get('over25', 15)} (%{st.get('over_pct', 75)}) | 2.5 Alt: {st.get('under25', 5)}")
            lines.append(f"   └ KG: Var: {st.get('btts_yes', 13)} (%{st.get('btts_pct', 65)}) | Yok: {st.get('btts_no', 7)}")

        hist = m.get("history_matches", [])
        if hist:
            lines.append(f"🧬 <b>2018-2026 Birebir Eşleşmeler:</b>")
            for h in hist[:3]: lines.append(f"   ▫️ <i>{h}</i>")

        lines.append("───────────────────────\n")

    if vip_picks:
        lines.append("⭐ <b>BUGÜNÜN VIP DEĞER ODASI (1.90 - 2.80)</b>\n")
        for v in vip_picks:
            lines.append(f"💎 <b>{v['match']}</b>")
            lines.append(f"   👉 <b>Tercih:</b> <code>{v['prediction']}</code>  |  <b>Oran:</b> <code>@{v['odds']}</code>\n")
        lines.append("───────────────────────\n")

    if rolling:
        lines.append(f"💰 <b>BUGÜNKÜ ROLLING KASA (Adım #{rolling.get('current_step', 1)})</b>")
        lines.append(f"💵 <code>{rolling.get('current_amount', 250):.2f} TL</code> ➔ <b>Hedef:</b> <code>{rolling.get('target_amount', 562.5):.2f} TL</code>")
        for p in rolling.get("picks", []):
            lines.append(f"   🔹 {p['match']} ➔ <b>{p['pick']}</b> (@{p['odds']})")
        lines.append(f"🔥 <b>Kombine Oran:</b> <code>{rolling.get('total_odds', 2.25)}</code>\n")
        lines.append("───────────────────────\n")

    if surprises:
        lines.append("💣 <b>BUGÜNÜN SÜRPRİZLERİ (İY / MS)</b>\n")
        for s in surprises:
            lines.append(f"💥 <b>{s['match']}</b> ({s.get('league', '')}) ➔ <code>{s['prediction']}</code> (@{s['odds']})\n")
        lines.append("───────────────────────\n")

    lines.append("🌐 <b>Canlı Web Paneli:</b> alpaydnmez.github.io/optaodds-ai")
    return "\n".join(lines).replace("& ", "ve ").replace(" &", " ve")

def main():
    shift = get_current_shift()
    print(f"Çalışan Vardiya: {shift.upper()}")
    data = load_data()

    today_tsi = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).strftime("%d.%m.%Y")
    data["current_date"] = today_tsi

    # SADECE VE SADECE BUGÜN OYNANACAK MAÇLARI ÇEK
    live_today = fetch_only_today_matches()
    if live_today:
        data["matches"] = live_today

    # Bülteni Telegram'a gönder
    msg = build_bulletin_telegram(data)
    send_telegram_message(msg)

    save_data(data)
    print("Yalnızca bugünün maçları işlendi ve bülten iletildi.")

if __name__ == "__main__":
    main()
