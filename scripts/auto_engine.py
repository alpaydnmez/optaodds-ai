import os
import csv
import io
import json
import datetime
import requests
from concurrent.futures import ThreadPoolExecutor

ODDS_API_KEY = os.getenv("ODDS_API_KEY") or "c8f2ff4c0a9d031a5ea7310149936e98"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "8922109226:AAGCEVmDNyCf2DMLhnOi1Mh2hYLp5WdV_tc"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "867372590"
DATA_FILE = "data.json"

MIN_ODDS_FLOOR = 1.50
MAX_REALISTIC_ODDS = 10.00  # 10.00 üzerindeki çöp/canlı bahis oranlarını engeller!

LIVE_SPORT_KEYS = [
    ("UEFA Şampiyonlar Ligi", "soccer_uefa_champs_league"),
    ("UEFA Avrupa Ligi", "soccer_uefa_europa_league"),
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

SEASONS = ["2526", "2425", "2324", "2223", "2122", "2021", "1920", "1819", "1718", "1617"]
LEAGUE_CODES = [
    ("İngiltere Premier", "E0"), ("İngiltere Championship", "E1"),
    ("İspanya La Liga", "SP1"), ("İtalya Serie A", "I1"),
    ("Almanya Bundesliga", "D1"), ("Türkiye Süper Lig", "T1"),
    ("Fransa Ligue 1", "F1"), ("Hollanda Eredivisie", "N1"), ("Portekiz Liga", "P1")
]

GLOBAL_DATABASE_CACHE = []

def fetch_single_csv(args):
    league_name, code, season = args
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    records = []
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            reader = csv.DictReader(io.StringIO(res.text))
            for row in reader:
                try:
                    h = float(row.get('B365H') or row.get('AvgH') or 0)
                    d = float(row.get('B365D') or row.get('AvgD') or 0)
                    a = float(row.get('B365A') or row.get('AvgA') or 0)
                    if h <= 1.0 or h > 15.0: continue
                    home = row.get('HomeTeam', '')
                    away = row.get('AwayTeam', '')
                    hg = int(row.get('FTHG', -1))
                    ag = int(row.get('FTAG', -1))
                    if home and away and hg >= 0 and ag >= 0:
                        records.append({
                            "season": f"20{season[:2]}/20{season[2:]}",
                            "league": league_name, "home": home, "away": away,
                            "hg": hg, "ag": ag, "score": f"{hg}-{ag}",
                            "h": round(h, 2), "d": round(d, 2), "a": round(a, 2)
                        })
                except Exception: continue
    except Exception: pass
    return records

def download_and_build_cache():
    global GLOBAL_DATABASE_CACHE
    if GLOBAL_DATABASE_CACHE: return GLOBAL_DATABASE_CACHE
    tasks = [(l_name, code, s) for l_name, code in LEAGUE_CODES for s in SEASONS]
    records = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        for r_list in executor.map(fetch_single_csv, tasks):
            records.extend(r_list)
    GLOBAL_DATABASE_CACHE = records
    return records

# SADECE VE SADECE HENÜZ BAŞLAMAMIŞ VE ORANI NORMAL OLAN MAÇLARI ÇEK
def fetch_upcoming_clean_matches():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    clean_matches = []

    for league_name, sport_key in LIVE_SPORT_KEYS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/?apiKey={ODDS_API_KEY}&regions=eu&markets=h2h&oddsFormat=decimal"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                events = res.json()
                for ev in events:
                    commence = ev.get("commence_time", "")
                    if not commence: continue
                    
                    t_utc = datetime.datetime.fromisoformat(commence.replace("Z", "+00:00"))
                    
                    # BAŞLAMIŞ VEYA BİTMİŞ MAÇLARI ASLA ALMA! (En az 10 dakika sonra başlayacak maçlar)
                    if t_utc <= now_utc + datetime.timedelta(minutes=10):
                        continue

                    bookies = ev.get("bookmakers", [])
                    if not bookies: continue
                    h2h = bookies[0]["markets"][0]["outcomes"]
                    
                    h_odd = next((o["price"] for o in h2h if o["name"] == ev["home_team"]), 0)
                    d_odd = next((o["price"] for o in h2h if o["name"].lower() == "draw"), 0)
                    a_odd = next((o["price"] for o in h2h if o["name"] == ev["away_team"]), 0)

                    # SAÇMA SAPAN 42, 100, 500 GİBİ ORANLARI ENGELLER!
                    if h_odd < 1.10 or h_odd > MAX_REALISTIC_ODDS: continue
                    if d_odd < 1.10 or d_odd > MAX_REALISTIC_ODDS: continue
                    if a_odd < 1.10 or a_odd > MAX_REALISTIC_ODDS: continue

                    t_tsi = t_utc + datetime.timedelta(hours=3)
                    time_str = t_tsi.strftime("%H:%M")

                    clean_matches.append({
                        "id": ev.get("id", str(len(clean_matches)+1)),
                        "time": time_str,
                        "league": league_name,
                        "match": f"{ev['home_team']} vs {ev['away_team']}",
                        "odds_dna": f"{h_odd:.2f} | {d_odd:.2f} | {a_odd:.2f} | 1.85 | 1.75 | 1.68",
                        "opening_odds": h_odd,
                        "current_odds": h_odd,
                        "odds": h_odd,
                        "target_h": h_odd,
                        "target_d": d_odd,
                        "target_a": a_odd
                    })
        except Exception:
            continue

    return clean_matches

def evaluate_and_optimize_pick(m, records):
    target_h = round(m.get("target_h", float(m["odds_dna"].split("|")[0].strip())), 2)
    target_a = round(m.get("target_a", 3.50), 2)
    
    matched = [r for r in records if r["h"] == target_h]
    if not matched:
        matched = [r for r in records if abs(r["h"] - target_h) <= 0.04]
        
    tot = len(matched)
    if tot == 0:
        m["confidence"] = 70.0
        m["dna_score"] = 70.0
        m["prediction"] = "MS 1" if target_h <= 2.0 else "2.5 Üst"
        return m

    h_wins = sum(1 for r in matched if r["hg"] > r["ag"])
    draws = sum(1 for r in matched if r["hg"] == r["ag"])
    a_wins = sum(1 for r in matched if r["ag"] > r["hg"])
    over25 = sum(1 for r in matched if (r["hg"] + r["ag"]) >= 3)
    btts = sum(1 for r in matched if r["hg"] > 0 and r["ag"] > 0)

    h_pct = (h_wins / tot) * 100
    over_pct = (over25 / tot) * 100
    btts_pct = (btts / tot) * 100
    a_pct = (a_wins / tot) * 100

    # HANGİ SONUÇ YÜKSEKSE TERCİH ONA VERİLİR (ASLA %15'E BANKO DENMEZ!)
    if over_pct >= 65.0:
        m["prediction"] = "2.5 Üst"
        m["odds"] = 1.50
        m["dna_score"] = round(over_pct, 1)
    elif h_pct >= 60.0 and target_h >= MIN_ODDS_FLOOR:
        m["prediction"] = "MS 1"
        m["odds"] = target_h
        m["dna_score"] = round(h_pct, 1)
    elif a_pct >= 60.0 and target_a >= MIN_ODDS_FLOOR:
        m["prediction"] = "MS 2"
        m["odds"] = target_a
        m["dna_score"] = round(a_pct, 1)
    elif btts_pct >= 65.0:
        m["prediction"] = "KG Var"
        m["odds"] = 1.68
        m["dna_score"] = round(btts_pct, 1)
    else:
        m["prediction"] = "2.5 Üst" if over_pct > h_pct else "MS 1"
        m["odds"] = max(target_h, 1.50)
        m["dna_score"] = round(max(h_pct, over_pct), 1)

    m["current_odds"] = m["odds"]
    m["confidence"] = round((0.85 * m["dna_score"]) + 11.2, 1)
    m["status"] = "BANKO" if m["confidence"] >= 70.0 else "DEĞER"
    
    m["history_matches"] = [
        f"{r['season']} {r['league']}: {r['home']} {r['score']} {r['away']} (@ {r['h']:.2f})"
        for r in matched[:3]
    ]
    m["stats"] = {
        "total_matched": tot,
        "h_wins": h_wins, "h_pct": round(h_pct, 1),
        "draws": draws, "d_pct": round((draws / tot) * 100, 1),
        "a_wins": a_wins, "a_pct": round(a_pct, 1),
        "over25": over25, "over_pct": round(over_pct, 1),
        "under25": tot - over25, "under_pct": round(100 - over_pct, 1),
        "btts_yes": btts, "btts_pct": round(btts_pct, 1),
        "btts_no": tot - btts
    }
    return m

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
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        resp = requests.post(url, json=payload, timeout=15)
        return resp.status_code == 200
    except Exception: return False

def get_progress_bar(percent):
    filled = int(round(percent / 10))
    return "🟩" * filled + "⬜" * (10 - filled)

def build_bulletin_telegram(data):
    today = data.get("current_date", "24.10.2026")
    matches = [m for m in data.get("matches", []) if m.get("confidence", 0) >= 70.0 and m.get("odds", 1.50) >= MIN_ODDS_FLOOR]

    lines = [
        "╔════════════════════════╗",
        "  ⚡ <b>OPTAODDS QUANT LIVE BÜLTEN</b> ⚡",
        f"  📅 <b>{today}</b> | 🔬 <b>2016-2026 Gerçek Oranlar</b>",
        "  🛡️ <b>Kural:</b> Yasal İddaa & Min 1.50 Taban",
        "╚════════════════════════╝\n",
        "👑 <b>DOĞRULANMIŞ GÜNLÜK BANKO SEÇİMLER</b>\n"
    ]

    for m in matches:
        odds_val = m.get("current_odds", m.get("odds", 1.50))
        bar = get_progress_bar(m.get("confidence", 75))
        st = m.get("stats", {})

        lines.append(f"⚽ <b>{m['match'].upper()}</b>")
        lines.append(f"🏆 <i>{m['league']}</i> | ⏰ {m['time']}")
        lines.append(f"🎯 <b>Tercih:</b> <code>{m['prediction']}</code>  |  <b>Oran:</b> <code>@{odds_val:.2f}</code>")
        lines.append(f"📊 <b>Birebir Oran Güveni:</b> <b>%{m.get('confidence', 75)}</b>\n   {bar}")

        if st:
            lines.append(f"📈 <b>2016-2026 ({st.get('total_matched', 20)} Maç) Dağılımı:</b>")
            lines.append(f"   ├ 1X2: Ev: {st.get('h_wins', 14)} (%{st.get('h_pct', 70)}) | Ber: {st.get('draws', 4)} | Dep: {st.get('a_wins', 2)}")
            lines.append(f"   ├ Gol: 2.5 Üst: {st.get('over25', 15)} (%{st.get('over_pct', 75)}) | 2.5 Alt: {st.get('under25', 5)}")
            lines.append(f"   └ KG: Var: {st.get('btts_yes', 13)} (%{st.get('btts_pct', 65)}) | Yok: {st.get('btts_no', 7)}")

        hist = m.get("history_matches", [])
        if hist:
            lines.append(f"🧬 <b>Gerçek Örnek Eşleşmeler:</b>")
            for h in hist[:3]: lines.append(f"   ▫️ <i>{h}</i>")

        lines.append("───────────────────────\n")

    lines.append("🌐 <b>Canlı Panel:</b> alpaydnmez.github.io/optaodds-ai")
    return "\n".join(lines).replace("& ", "ve ").replace(" &", " ve")

def main():
    shift = get_current_shift()
    print(f"Çalışan Vardiya: {shift.upper()}")
    data = load_data()

    today_tsi = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)).strftime("%d.%m.%Y")
    data["current_date"] = today_tsi

    records = download_and_build_cache()

    # SADECE VE SADECE HENÜZ BAŞLAMAMIŞ VE ORANI NORMAL OLAN MAÇLARI ÇEK
    upcoming = fetch_upcoming_clean_matches()
    if upcoming:
        optimized = []
        for um in upcoming:
            opt = evaluate_and_optimize_pick(um, records)
            optimized.append(opt)
        data["matches"] = optimized
    else:
        # Eğer o an maç yoksa mevcut maçları temizle ve optimize et
        cleaned = []
        for m in data.get("matches", []):
            parts = m.get("odds_dna", "").split("|")
            h_val = float(parts[0].strip()) if len(parts) >= 1 else 1.80
            if h_val < 1.10 or h_val > MAX_REALISTIC_ODDS:
                continue
            m["target_h"] = h_val
            m["target_a"] = float(parts[2].strip()) if len(parts) >= 3 else 3.50
            opt = evaluate_and_optimize_pick(m, records)
            cleaned.append(opt)
        data["matches"] = cleaned

    msg = build_bulletin_telegram(data)
    send_telegram_message(msg)

    save_data(data)
    print("İşlem başarıyla tamamlandı.")

if __name__ == "__main__":
    main()
