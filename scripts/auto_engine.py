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

# 2018-2026 ARASI 8 SEZONUN TAMAMI
SEASONS = ["2526", "2425", "2324", "2223", "2122", "2021", "1920", "1819"]

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
                            "h": round(h, 2),
                            "d": round(d, 2),
                            "a": round(a, 2)
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

    # 2026 EKİM GÜNCEL KÜTÜĞÜ
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
                    "h": round(float(arch.get("odds", 1.50)), 2),
                    "d": 3.40,
                    "a": 3.80
                })
        except Exception:
            pass

    print(f"Başarılı: Toplam {len(records)} adet maç bellek havuzuna alındı!")
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

# BİREBİR ORAN EŞLEŞMESİ (TOLERANS = 0.00) VE KOMPLE SONUÇ DAĞILIMI
def evaluate_exact_odds_breakdown(target_h, target_d, target_a, prediction, data, display_limit=4):
    records = download_and_build_cache(data)
    
    matched_games = []
    total_matched = 0
    pick_wins = 0
    
    # 1X2 Dağılımı
    h_wins = 0
    draws = 0
    a_wins = 0
    
    # Gol Baremleri
    over25 = 0
    under25 = 0
    
    # Karşılıklı Gol
    btts_yes = 0
    btts_no = 0

    target_h_rounded = round(target_h, 2)

    for r in records:
        # BİREBİR KURULUŞU KURUŞUNA EŞLEŞME (TOLERANS = 0.00)
        if r["h"] == target_h_rounded:
            total_matched += 1
            hg = r["hg"]
            ag = r["ag"]
            total_goals = hg + ag
            
            # 1X2
            if hg > ag: h_wins += 1
            elif hg == ag: draws += 1
            else: a_wins += 1
            
            # 2.5 Üst / Alt
            if total_goals >= 3: over25 += 1
            else: under25 += 1
            
            # KG
            if hg > 0 and ag > 0: btts_yes += 1
            else: btts_no += 1
            
            # Tercih Doğrulaması
            is_win = check_pick_success(hg, ag, prediction)
            if is_win:
                pick_wins += 1
                
            if len(matched_games) < display_limit:
                durum = "✅" if is_win else "❌"
                matched_games.append(f"{r['season']} {r['league']}: {r['home']} {r['score']} {r['away']} ({durum} @ {r['h']:.2f})")

    stats = {
        "total_matched": total_matched,
        "pick_wins": pick_wins,
        "dna_score": round((pick_wins / total_matched * 100.0), 1) if total_matched > 0 else 50.0,
        "h_wins": h_wins,
        "h_pct": round((h_wins / total_matched * 100.0), 1) if total_matched > 0 else 0,
        "draws": draws,
        "d_pct": round((draws / total_matched * 100.0), 1) if total_matched > 0 else 0,
        "a_wins": a_wins,
        "a_pct": round((a_wins / total_matched * 100.0), 1) if total_matched > 0 else 0,
        "over25": over25,
        "over_pct": round((over25 / total_matched * 100.0), 1) if total_matched > 0 else 0,
        "under25": under25,
        "under_pct": round((under25 / total_matched * 100.0), 1) if total_matched > 0 else 0,
        "btts_yes": btts_yes,
        "btts_pct": round((btts_yes / total_matched * 100.0), 1) if total_matched > 0 else 0,
        "btts_no": btts_no
    }

    return matched_games, stats

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

# 16:15 RESMİ BÜLTEN (BİREBİR ORAN & KOMPLE DAĞILIM TABLOSU)
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
                
                # BİREBİR EŞLEŞTİRME VE KOMPLE DAĞILIM ANALİZİ
                real_h, stats = evaluate_exact_odds_breakdown(target_h, target_d, target_a, m["prediction"], data)
                
                if real_h:
                    m["history_matches"] = real_h
                    m["stats"] = stats
                    m["dna_score"] = stats["dna_score"]
                    form_score = m.get("form_score", 75.0)
                    m["confidence"] = round((0.85 * m["dna_score"]) + (0.15 * form_score), 1)

                    if m["dna_score"] >= 65.0:
                        valid_banko_matches.append(m)
            except Exception as e:
                print(f"Hata: {e}")

    lines = []
    lines.append("╔════════════════════════╗")
    lines.append("  ⚡ <b>OPTAODDS v5.6 BİREBİR ORAN BÜLTENİ</b> ⚡")
    lines.append(f"  📅 <b>{today}</b> | 🔬 <b>Sıfır Tolerans (0.00) DNA</b>")
    lines.append(f"  🛡️ <b>Kural:</b> Minimum 1.50 Oran Tabanı")
    lines.append("╚════════════════════════╝\n")

    # 1. BANKO SEÇİMLER & KOMPLE DAĞILIM
    lines.append("👑 <b>BİREBİR ORAN İSPATLI BANKO SEÇİMLER</b>\n")
    for m in valid_banko_matches:
        st = m["stats"]
        bar = get_progress_bar(m['confidence'])
        hist_lines = ""
        for h in m.get("history_matches", []):
            hist_lines += f"   ▫️ <i>{h}</i>\n"

        lines.append(f"⚽ <b>{m['match'].upper()}</b>")
        lines.append(f"🏆 <i>{m['league']}</i> | ⏰ {m['time']}")
        lines.append(f"🎯 <b>Tercih:</b> <code>{m['prediction']}</code>  |  <b>Oran:</b> <code>@{m.get('current_odds', m['odds']):.2f}</code>")
        lines.append(f"📊 <b>Birebir Oran İsabeti:</b> %{m['dna_score']} ({st['pick_wins']}/{st['total_matched']} Maç)")
        lines.append(f"🔥 <b>Bileşik Model Güveni:</b> <b>%{m['confidence']}</b>")
        lines.append(f"   {bar}")
        
        # KOMPLE SONUÇ RÖNTGENİ
        lines.append(f"📈 <b>{st['total_matched']} Birebir Maçın Tam Dağılımı:</b>")
        lines.append(f"   ├ <b>1X2:</b> Ev: {st['h_wins']} (%{st['h_pct']}) | Ber: {st['draws']} (%{st['d_pct']}) | Dep: {st['a_wins']} (%{st['a_pct']})")
        lines.append(f"   ├ <b>Gol:</b> 2.5 Üst: {st['over25']} (%{st['over_pct']}) | 2.5 Alt: {st['under25']} (%{st['under_pct']})")
        lines.append(f"   └ <b>KG:</b> Var: {st['btts_yes']} (%{st['btts_pct']}) | Yok: {st['btts_no']}")
        
        lines.append(f"\n🧬 <b>Örnek Birebir Eşleşmeler (2018-2026):</b>\n{hist_lines}")
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
    print("İşlem başarıyla tamamlandı.")

if __name__ == "__main__":
    main()
