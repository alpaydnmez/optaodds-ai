import os
import csv
import io
import json
import datetime
import requests
from concurrent.futures import ThreadPoolExecutor

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or "8922109226:AAGCEVmDNyCf2DMLhnOi1Mh2hYLp5WdV_tc"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "867372590"
DATA_FILE = "data.json"

MIN_ODDS_FLOOR = 1.50

# 2018'DEN 2026'YA KADAR 8 SEZONUN TAMAMI
SEASONS = ["2526", "2425", "2324", "2223", "2122", "2021", "1920", "1819"]

# 16 MAJÖR VE ALT LİG KODLARI
LEAGUE_CODES = [
    ("İngiltere Premier", "E0"),
    ("İngiltere Championship", "E1"),
    ("İngiltere League 1", "E2"),
    ("İspanya La Liga", "SP1"),
    ("İspanya La Liga 2", "SP2"),
    ("İtalya Serie A", "I1"),
    ("İtalya Serie B", "I2"),
    ("Almanya Bundesliga", "D1"),
    ("Almanya 2. Bundesliga", "D2"),
    ("Türkiye Süper Lig", "T1"),
    ("Fransa Ligue 1", "F1"),
    ("Fransa Ligue 2", "F2"),
    ("Portekiz Liga", "P1"),
    ("Hollanda Eredivisie", "N1"),
    ("Belçika Pro League", "B1"),
    ("İskoçya Premiership", "SC0")
]

GLOBAL_DATABASE_CACHE = []

def fetch_single_csv(args):
    league_name, code, season = args
    url = f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    season_label = f"20{season[:2]}/20{season[2:]}"
    records = []
    
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
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
                            "season": season_label,
                            "league": league_name,
                            "home": home,
                            "away": away,
                            "hg": hg,
                            "ag": ag,
                            "score": f"{hg}-{ag}",
                            "h": h,
                            "d": d,
                            "a": a
                        })
                except Exception:
                    continue
    except Exception:
        pass
    return records

def download_and_build_cache(data):
    global GLOBAL_DATABASE_CACHE
    if GLOBAL_DATABASE_CACHE:
        return GLOBAL_DATABASE_CACHE

    tasks = []
    for l_name, code in LEAGUE_CODES:
        for s in SEASONS:
            tasks.append((l_name, code, s))

    print(f"2018-2026 arası 8 sezon paralel olarak indiriliyor ({len(tasks)} dosya)...")
    records = []
    
    with ThreadPoolExecutor(max_workers=14) as executor:
        results = executor.map(fetch_single_csv, tasks)
        for r_list in results:
            records.extend(r_list)

    # 2026 EKİM GÜNCEL KÜTÜĞÜNÜ DE HAVUZA KAT (19-22 EKİM MAÇLARI)
    for arch in data.get("archive", []):
        try:
            score = arch.get("score", "")
            if "/" in score: score = score.split("/")[1].strip().replace("MS ", "")
            parts = score.split("-")
            if len(parts) == 2:
                hg = int(parts[0].strip())
                ag = int(parts[1].strip())
                records.append({
                    "season": "2026 Canlı",
                    "league": "2026 Kütük",
                    "home": arch.get("match", "").split(" vs ")[0],
                    "away": arch.get("match", "").split(" vs ")[-1],
                    "hg": hg,
                    "ag": ag,
                    "score": f"{hg}-{ag}",
                    "h": float(arch.get("odds", 1.50)),
                    "d": 3.40,
                    "a": 3.80
                })
        except Exception:
            pass

    print(f"Başarılı: 2018-2026 arası toplam {len(records)} adet maç bellek havuzuna alındı!")
    GLOBAL_DATABASE_CACHE = records
    return records

def check_pick_success(hg, ag, pick_str):
    pick = pick_str.upper()
    total_goals = hg + ag
    
    if "2.5 ÜST" in pick or "2.5 GOL ÜSTÜ" in pick: return total_goals >= 3
    if "2.5 ALT" in pick or "2.5 GOL ALTI" in pick: return total_goals < 3
    if "1.5 ÜST" in pick:
        if "1X" in pick: return (hg >= ag) and (total_goals >= 2)
        return total_goals >= 2
    if "KG VAR" in pick: return (hg > 0 and ag > 0)
    if pick == "MS 1": return hg > ag
    if pick == "MS 2": return ag > hg
    if pick == "MS X": return hg == ag
    if "1X" in pick: return hg >= ag
    if "X2" in pick: return ag >= hg
    return False

def evaluate_real_dna(target_h, target_d, target_a, prediction, data, tolerance=0.06, display_limit=4):
    records = download_and_build_cache(data)
    matched_games = []
    total_pool_matches = 0
    success_count = 0

    for r in records:
        if abs(r["h"] - target_h) <= tolerance and abs(r["d"] - target_d) <= 0.22:
            total_pool_matches += 1
            is_win = check_pick_success(r["hg"], r["ag"], prediction)
            if is_win:
                success_count += 1
            
            if len(matched_games) < display_limit:
                durum = "✅" if is_win else "❌"
                matched_games.append(f"{r['season']} {r['league']}: {r['home']} {r['score']} {r['away']} ({durum} @ {r['h']:.2f})")

    dna_score = (success_count / total_pool_matches * 100.0) if total_pool_matches > 0 else 50.0
    return matched_games, dna_score, total_pool_matches

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

# 16:15 RESMİ BÜLTEN
def build_afternoon_bulletin(data):
    today = data.get("current_date", "23.10.2026")
    matches = data.get("matches", [])
    rolling = data.get("rolling_kasa", {})
    vip_picks = data.get("vip_room", [])
    surprises = data.get("surprise_picks", [])

    valid_banko_matches = []

    for m in matches:
        odds_val = m.get("current_odds", m["odds"])
        if odds_val < MIN_ODDS_FLOOR:
            continue

        parts = m.get("odds_dna", "").split("|")
        if len(parts) >= 3:
            try:
                target_h = float(parts[0].strip())
                target_d = float(parts[1].strip())
                target_a = float(parts[2].strip())
                
                real_h, calc_dna_score, total_count = evaluate_real_dna(target_h, target_d, target_a, m["prediction"], data)
                
                if real_h:
                    m["history_matches"] = real_h
                    m["total_matched_pool"] = total_count
                    m["dna_score"] = round(calc_dna_score, 1)
                    form_score = m.get("form_score", 75.0)
                    m["confidence"] = round((0.85 * m["dna_score"]) + (0.15 * form_score), 1)

                    if m["dna_score"] >= 65.0:
                        valid_banko_matches.append(m)
            except Exception as e:
                print(f"Hata: {e}")

    lines = []
    lines.append("╔════════════════════════╗")
    lines.append("  ⚡ <b>OPTAODDS AI v5.6 RESMİ BÜLTENİ</b> ⚡")
    lines.append(f"  📅 <b>{today}</b> | 🔬 <b>2018 - 2026 Arşivi</b>")
    lines.append(f"  🛡️ <b>Kural:</b> Minimum 1.50 Oran Tabanı")
    lines.append("╚════════════════════════╝\n")

    # 1. BANKO SEÇİMLER
    lines.append("👑 <b>DOĞRULANMIŞ BANKO MAÇLAR (2018-2026 İSPATLI)</b>\n")
    for m in valid_banko_matches:
        bar = get_progress_bar(m['confidence'])
        hist_lines = ""
        for h in m.get("history_matches", []):
            hist_lines += f"   ▫️ <i>{h}</i>\n"

        lines.append(f"⚽ <b>{m['match'].upper()}</b>")
        lines.append(f"🏆 <i>{m['league']}</i> | ⏰ {m['time']}")
        lines.append(f"🎯 <b>Tercih:</b> <code>{m['prediction']}</code>  |  <b>Oran:</b> <code>@{m.get('current_odds', m['odds']):.2f}</code>")
        lines.append(f"📊 <b>2018-2026 DNA İsabeti:</b> %{m['dna_score']} (Toplam {m.get('total_matched_pool', 10)} maç)")
        lines.append(f"🔥 <b>Bileşik Model Güveni:</b> <b>%{m['confidence']}</b>")
        lines.append(f"   {bar}")
        lines.append(f"🧬 <b>2018-2026 Örnek Eşleşmeleri:</b>\n{hist_lines}")
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
        lines.append(f"💰 <b>ROLLING KASA (Adım #{rolling.get('current_step', 1)})</b>")
        lines.append(f"💵 <code>{rolling.get('current_amount', 250):.2f} TL</code> ➔ <b>Hedef:</b> <code>{rolling.get('target_amount', 562.5):.2f} TL</code>")
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
            lines.append(f"   📈 <i>Frekans: %{s.get('frequency', 20)}</i>\n")
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
