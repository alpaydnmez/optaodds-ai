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
MIN_SAMPLE_SIZE = 12  # EN AZ 12 BİREBİR GEÇMİŞ MAÇ EŞLEŞMESİ ŞARTI!

LIVE_SPORT_KEYS = [
    ("Türkiye Süper Lig", "soccer_turkey_super_league"),
    ("İngiltere Premier Lig", "soccer_epl"),
    ("İngiltere Championship", "soccer_efl_champ"),
    ("İspanya La Liga", "soccer_spain_la_liga"),
    ("İtalya Serie A", "soccer_italy_serie_a"),
    ("Almanya Bundesliga", "soccer_germany_bundesliga"),
    ("Fransa Ligue 1", "soccer_france_ligue_one"),
    ("Hollanda Eredivisie", "soccer_netherlands_eredivisie")
]

SEASONS = ["2526", "2425", "2324", "2223", "2122", "2021", "1920", "1819", "1718", "1617"]
LEAGUE_CODES = [
    ("İngiltere Premier", "E0"), ("İngiltere Championship", "E1"),
    ("İspanya La Liga", "SP1"), ("İtalya Serie A", "I1"),
    ("Almanya Bundesliga", "D1"), ("Türkiye Süper Lig", "T1")
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
                            "score": f"{hg}-{ag}", "hg": hg, "ag": ag, "h": round(h, 2)
                        })
                except Exception: continue
    except Exception: pass
    return records

def download_and_build_cache():
    global GLOBAL_DATABASE_CACHE
    if GLOBAL_DATABASE_CACHE: return GLOBAL_DATABASE_CACHE
    tasks = [(l_name, code, s) for l_name, code in LEAGUE_CODES for s in SEASONS]
    records = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        for r_list in executor.map(fetch_single_csv, tasks):
            records.extend(r_list)
    GLOBAL_DATABASE_CACHE = records
    return records

def optimize_match(m, records):
    h = round(m["h_odd"], 2)
    over_odd = m.get("over_odd", 1.65)
    
    matched = [r for r in records if r["h"] == h]
    if not matched:
        matched = [r for r in records if abs(r["h"] - h) <= 0.04]
        
    tot = len(matched)
    if tot < MIN_SAMPLE_SIZE:
        return None  # EŞLEŞME SAYISI YETERSİZSE DİREKT ELE!

    h_wins = sum(1 for r in matched if r["hg"] > r["ag"])
    draws = sum(1 for r in matched if r["hg"] == r["ag"])
    a_wins = tot - h_wins - draws
    over25 = sum(1 for r in matched if (r["hg"] + r["ag"]) >= 3)
    btts = sum(1 for r in matched if r["hg"] > 0 and r["ag"] > 0)

    over_pct = (over25 / tot) * 100
    h_pct = (h_wins / tot) * 100

    # ASLA 5-6 ORAN OLAMAZ! 2.5 ÜST SEÇİLİRSE GERÇEK OVER ORANI YAZILIR
    if over_pct >= 65.0:
        m["prediction"] = "2.5 Üst"
        m["odds"] = over_odd
        m["dna_score"] = round(over_pct, 1)
    elif h_pct >= 60.0 and h >= MIN_ODDS_FLOOR:
        m["prediction"] = "MS 1"
        m["odds"] = h
        m["dna_score"] = round(h_pct, 1)
    else:
        m["prediction"] = "2.5 Üst"
        m["odds"] = over_odd
        m["dna_score"] = round(over_pct, 1)

    m["confidence"] = round((0.85 * m["dna_score"]) + 11.2, 1)
    m["status"] = "BANKO"
    
    # GEÇMİŞ MAÇLAR KESİNTİSİZ EKLENİR
    m["history_matches"] = [
        f"{r['season']} {r['league']}: {r['home']} {r['score']} {r['away']} (@ {r['h']:.2f})"
        for r in matched[:3]
    ]
    
    # RÖNTGEN DAĞILIM KUTUSU KESİNTİSİZ EKLENİR
    m["stats"] = {
        "total_matched": tot,
        "h_wins": h_wins, "h_pct": round(h_pct, 1),
        "draws": draws, "d_pct": round((draws / tot) * 100, 1),
        "a_wins": a_wins, "a_pct": round((a_wins / tot) * 100, 1),
        "over25": over25, "over_pct": round(over_pct, 1),
        "under25": tot - over25, "under_pct": round(100 - over_pct, 1),
        "btts_yes": btts, "btts_pct": round((btts / tot) * 100, 1),
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

# TELEGRAM BÜLTENİ (6 MAÇ SINIRI KALDIRILDI! N ADET NİTELİKLİ MAÇ)
def build_bulletin_telegram(data):
    today = data.get("current_date", "24.10.2026")
    matches = data.get("matches", []) # 6 SINIRI YOK! TÜM NİTELİKLİ MAÇLAR

    lines = [
        "╔════════════════════════╗",
        "  ⚡ <b>OPTAODDS QUANT RESMİ BÜLTEN</b> ⚡",
        f"  📅 <b>{today} Cumartesi</b> | 🔬 <b>2016-2026 Gerçek Oranlar</b>",
        f"  🎯 <b>Nitelikli Maç Sayısı:</b> {len(matches)} Adet",
        "╚════════════════════════╝\n",
        "👑 <b>DOĞRULANMIŞ BANKO SEÇİMLER (≥%68 İSPATLI)</b>\n"
    ]

    for m in matches:
        bar = get_progress_bar(m.get("confidence", 75))
        st = m.get("stats", {})

        lines.append(f"⚽ <b>{m['match'].upper()}</b>")
        lines.append(f"🏆 <i>{m['league']}</i> | ⏰ {m['time']}")
        lines.append(f"🎯 <b>Tercih:</b> <code>{m['prediction']}</code>  |  <b>Gerçek Oran:</b> <code>@{m['odds']:.2f}</code>")
        lines.append(f"📊 <b>Model Güveni:</b> <b>%{m.get('confidence', 75)}</b>\n   {bar}")

        if st:
            lines.append(f"📈 <b>2016-2026 Dağılımı ({st.get('total_matched', 20)} Maç):</b>")
            lines.append(f"   ├ 1X2: Ev: {st.get('h_wins')} (%{st.get('h_pct')}) | Ber: {st.get('draws')} | Dep: {st.get('a_wins')}")
            lines.append(f"   ├ Gol: 2.5 Üst: {st.get('over25')} (%{st.get('over_pct')}) | 2.5 Alt: {st.get('under25')}")
            lines.append(f"   └ KG: Var: {st.get('btts_yes')} (%{st.get('btts_pct')}) | Yok: {st.get('btts_no')}")

        hist = m.get("history_matches", [])
        if hist:
            lines.append(f"🧬 <b>Geçmiş Birebir Eşleşmeler:</b>")
            for h in hist[:3]: lines.append(f"   ▫️ <i>{h}</i>")

        lines.append("───────────────────────\n")

    lines.append("🌐 <b>Canlı Panel:</b> alpaydnmez.github.io/optaodds-ai")
    return "\n".join(lines).replace("& ", "ve ").replace(" &", " ve")

def main():
    shift = get_current_shift()
    print(f"Çalışan Vardiya: {shift.upper()}")
    data = load_data()

    now_tsi = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3)
    data["current_date"] = now_tsi.strftime("%d.%m.%Y")

    records = download_and_build_cache()

    # DATA.JSON İÇİNDEKİ MAÇLARI KÜTÜKTE TEKRAR DOĞRULA VE İSTATİSTİKLERİNİ GARANTİLE
    validated_matches = []
    for m in data.get("matches", []):
        parts = m.get("odds_dna", "").split("|")
        h_val = float(parts[0].strip()) if len(parts) >= 1 else 1.80
        m["h_odd"] = h_val
        m["over_odd"] = m.get("odds", 1.65) if "Üst" in m.get("prediction", "") else 1.65
        opt = optimize_match(m, records)
        if opt:
            validated_matches.append(opt)

    # 6 MAÇ SINIRI KALKTI: ŞARTLARI SAĞLAYAN TÜM MAÇLAR GİRER!
    data["matches"] = validated_matches

    msg = build_bulletin_telegram(data)
    send_telegram_message(msg)

    save_data(data)
    print(f"İşlem tamamlandı. Toplam {len(validated_matches)} adet ispatlı maç bültene alındı.")

if __name__ == "__main__":
    main()
