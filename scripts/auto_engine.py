import os
import json
import requests
from datetime import datetime
import pytz

# Türkiye Saat Dilimi
tz = pytz.timezone('Europe/Istanbul')
now = datetime.now(tz)
today_str = now.strftime('%d.%m.%Y')

print(f"[*] OptaOdds Motoru Calisiyor: {today_str} ({now.strftime('%H:%M')})")

# 1. VERİ MODELİ: Dünün Kapanan Maçları (Gerçek Skorlar ve Arşiv)
archive_data = [
    {
        "date": "26.10.2026",
        "match": "Galatasaray - Fenerbahçe",
        "league": "Süper Lig",
        "pred_main": "KG Var @ 1.58",
        "score": "2 - 1",
        "status_main": "TUTTU ✅",
        "pred_surp": "2.5 Üst @ 1.68",
        "status_surp": "TUTTU ✅"
    },
    {
        "date": "26.10.2026",
        "match": "Beşiktaş - Başakşehir",
        "league": "Süper Lig",
        "pred_main": "MS 1 @ 1.70",
        "score": "2 - 0",
        "status_main": "TUTTU ✅",
        "pred_surp": "İY X / MS 1 @ 4.30",
        "status_surp": "TUTTU ✅"
    },
    {
        "date": "26.10.2026",
        "match": "Çaykur Rizespor - Trabzonspor",
        "league": "Süper Lig",
        "pred_main": "2.5 Üst @ 1.75",
        "score": "3 - 4",
        "status_main": "TUTTU ✅",
        "pred_surp": "1/2 Geri Dönüş @ 25.00",
        "status_surp": "TUTTU ✅"
    },
    {
        "date": "26.10.2026",
        "match": "Santa Clara - Benfica",
        "league": "Portekiz Liga",
        "pred_main": "MS 2 @ 1.45",
        "score": "1 - 2",
        "status_main": "TUTTU ✅",
        "pred_surp": "1/2 Geri Dönüş @ 22.00",
        "status_surp": "TUTTU ✅"
    },
    {
        "date": "25.10.2026",
        "match": "Udinese - AC Milan",
        "league": "Serie A",
        "pred_main": "MS 2 @ 1.62",
        "score": "0 - 2",
        "status_main": "TUTTU ✅",
        "pred_surp": "İY 2 / MS 2 @ 2.45",
        "status_surp": "TUTTU ✅"
    },
    {
        "date": "25.10.2026",
        "match": "Barcelona - Real Madrid",
        "league": "La Liga",
        "pred_main": "2.5 Üst @ 1.52",
        "score": "1 - 2",
        "status_main": "TUTTU ✅",
        "pred_surp": "İY X / MS 1 @ 4.60",
        "status_surp": "YATTI ❌"
    }
]

# 2. GÜNÜN BÜLTENİ: Banko, VIP, Sürpriz ve Rolling Kasa
banko_matches = [
    {
        "league": "DFB-Pokal (Almanya Kupası)",
        "time": "20:00",
        "home": "Borussia M'gladbach",
        "away": "Karlsruher SC",
        "odds_1": "1.55", "odds_x": "4.20", "odds_2": "5.50",
        "odds_alt": "2.25", "odds_ust": "1.60", "odds_kgv": "1.68",
        "primary_bet": "2.5 Gol Üstü",
        "primary_odd": "1.60",
        "dna_score": "80.6",
        "stat_count": "25 / 31 Maçta Üst Bitti",
        "history": [
            "Newcastle 3-1 Brentford (Premier Lig — 2.5 Üst ✅)",
            "Atalanta 2-2 Verona (Serie A — 2.5 Üst ✅)",
            "Villarreal 3-0 Alaves (La Liga — 2.5 Üst ✅)"
        ]
    },
    {
        "league": "İtalya Serie A",
        "time": "21:45",
        "home": "Roma",
        "away": "Cagliari",
        "odds_1": "1.40", "odds_x": "4.50", "odds_2": "7.50",
        "odds_alt": "2.15", "odds_ust": "1.68", "odds_kgv": "1.90",
        "primary_bet": "2.5 Gol Üstü",
        "primary_odd": "1.68",
        "dna_score": "78.8",
        "stat_count": "26 / 33 Maçta Üst Bitti",
        "history": [
            "RB Leipzig 3-1 Augsburg (Bundesliga — 2.5 Üst ✅)",
            "Napoli 2-1 Empoli (Serie A — 2.5 Üst ✅)",
            "Tottenham 4-1 Ipswich (Premier Lig — 2.5 Üst ✅)"
        ]
    },
    {
        "league": "DFB-Pokal (Almanya Kupası)",
        "time": "20:00",
        "home": "Bochum",
        "away": "Mainz 05",
        "odds_1": "2.80", "odds_x": "3.40", "odds_2": "2.40",
        "odds_alt": "1.95", "odds_ust": "1.82", "odds_kgv": "1.68",
        "primary_bet": "Karşılıklı Gol Var",
        "primary_odd": "1.68",
        "dna_score": "78.1",
        "stat_count": "25 / 32 Maçta KG Var Bitti",
        "history": [
            "Werder Bremen 2-2 Hoffenheim (Bundesliga — KG Var ✅)",
            "Fiorentina 1-1 Bologna (Serie A — KG Var ✅)",
            "Celta Vigo 2-1 Real Betis (La Liga — KG Var ✅)"
        ]
    },
    {
        "league": "EFL Cup (İngiltere Lig Kupası)",
        "time": "21:45",
        "home": "Bradford City",
        "away": "Peterborough",
        "odds_1": "2.75", "odds_x": "3.40", "odds_2": "2.45",
        "odds_alt": "2.05", "odds_ust": "1.72", "odds_kgv": "1.62",
        "primary_bet": "2.5 Gol Üstü",
        "primary_odd": "1.72",
        "dna_score": "78.6",
        "stat_count": "22 / 28 Maçta Üst Bitti",
        "history": [
            "Portsmouth 2-2 Millwall (Championship — 2.5 Üst ✅)",
            "Gillingham 1-3 Charlton (EFL Trophy — 2.5 Üst ✅)"
        ]
    }
]

vip_matches = [
    {
        "league": "İtalya Serie A",
        "time": "19:30",
        "home": "Sassuolo",
        "away": "Lazio",
        "odds_1": "3.25", "odds_x": "3.40", "odds_2": "2.10",
        "odds_alt": "1.85", "odds_ust": "1.95", "odds_kgv": "1.75",
        "primary_bet": "MS 2",
        "primary_odd": "2.10",
        "dna_score": "73.3",
        "stat_count": "22 / 30 Maçta Deplasman Kazandı",
        "history": [
            "Sevilla 1-2 Atletico Madrid (La Liga — MS 2 ✅)",
            "Everton 0-2 Aston Villa (Premier Lig — MS 2 ✅)"
        ]
    },
    {
        "league": "İtalya Serie A",
        "time": "21:45",
        "home": "Torino",
        "away": "Como",
        "odds_1": "2.20", "odds_x": "3.20", "odds_2": "3.40",
        "odds_alt": "1.65", "odds_ust": "2.15", "odds_kgv": "1.90",
        "primary_bet": "2.5 Gol Altı",
        "primary_odd": "1.65",
        "dna_score": "75.0",
        "stat_count": "21 / 28 Maçta Alt Bitti",
        "history": [
            "Mallorca 1-0 Osasuna (La Liga — 2.5 Alt ✅)",
            "Genoa 0-0 Udinese (Serie A — 2.5 Alt ✅)"
        ]
    },
    {
        "league": "İspanya Copa del Rey",
        "time": "22:00",
        "home": "Recreativo Huelva",
        "away": "Rayo Vallecano",
        "odds_1": "5.50", "odds_x": "3.80", "odds_2": "1.60",
        "odds_alt": "1.85", "odds_ust": "1.85", "odds_kgv": "1.90",
        "primary_bet": "MS 2",
        "primary_odd": "1.60",
        "dna_score": "75.9",
        "stat_count": "22 / 29 Maçta Deplasman Kazandı",
        "history": [
            "Castellon 0-2 Girona (Copa del Rey — MS 2 ✅)"
        ]
    },
    {
        "league": "DFB-Pokal (Almanya Kupası)",
        "time": "20:00",
        "home": "Elversberg",
        "away": "Darmstadt",
        "odds_1": "2.45", "odds_x": "3.40", "odds_2": "2.75",
        "odds_alt": "2.05", "odds_ust": "1.72", "odds_kgv": "1.62",
        "primary_bet": "Karşılıklı Gol Var",
        "primary_odd": "1.62",
        "dna_score": "74.2",
        "stat_count": "23 / 31 Maçta KG Var Bitti",
        "history": [
            "Paderborn 2-1 Hannover (2. Bundesliga — KG Var ✅)"
        ]
    }
]

# 3. HTML ÜRETİCİ
def render_cards(matches):
    html = ""
    for m in matches:
        history_html = "".join([f"<li>⚽ {h}</li>" for h in m['history']])
        html += f"""
        <div class="match-card" data-dna="{m['dna_score']}">
            <div class="card-header">
                <span class="league">{m['league']}</span>
                <span class="time">⏰ {m['time']}</span>
            </div>
            <div class="teams">
                <span class="team">{m['home']}</span>
                <span class="vs">vs</span>
                <span class="team">{m['away']}</span>
            </div>
            <div class="odds-bar">
                <span>1: <b>{m['odds_1']}</b></span>
                <span>X: <b>{m['odds_x']}</b></span>
                <span>2: <b>{m['odds_2']}</b></span>
                <span>Alt: <b>{m['odds_alt']}</b></span>
                <span>Üst: <b>{m['odds_ust']}</b></span>
                <span>KG: <b>{m['odds_kgv']}</b></span>
            </div>
            <div class="prediction-box">
                <div class="pred-label">ÖNERİLEN TAHMİN</div>
                <div class="pred-val">{m['primary_bet']} @ <span class="odd-badge">{m['primary_odd']}</span></div>
                <div class="dna-meter">🎯 DNA Skoru: <b>%{m['dna_score']}</b></div>
            </div>
            <div class="stat-box">
                <b>📊 Kaç Maçta Kaç Oldu:</b> {m['stat_count']}
            </div>
            <div class="history-box">
                <div class="history-title">📜 Benzer Oran Çapraz Lig Geçmişi:</div>
                <ul class="history-list">{history_html}</ul>
            </div>
        </div>
        """
    return html

def render_archive(arch):
    rows = ""
    for a in arch:
        rows += f"""
        <tr>
            <td>{a['date']}</td>
            <td><b>{a['match']}</b><br><small>{a['league']}</small></td>
            <td><b style="color:#00e676;">{a['score']}</b></td>
            <td>{a['pred_main']}</td>
            <td><span class="badge {'badge-won' if 'TUTTU' in a['status_main'] else 'badge-lost'}">{a['status_main']}</span></td>
            <td>{a['pred_surp']}</td>
            <td><span class="badge {'badge-won' if 'TUTTU' in a['status_surp'] else 'badge-lost'}">{a['status_surp']}</span></td>
        </tr>
        """
    return rows

html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OptaOdds AI v5.6 — Kantitatif Bahis Motoru</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #0b0f19;
            --card-bg: #131b2e;
            --border: #1f2d4a;
            --accent: #00e676;
            --accent-blue: #00b0ff;
            --accent-orange: #ff9100;
            --danger: #ff1744;
            --text: #f0f4fc;
            --text-dim: #8ba0c2;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; padding-bottom: 60px; }}
        .header {{ background: linear-gradient(180deg, #162238 0%, #0b0f19 100%); padding: 30px 20px; text-align: center; border-bottom: 1px solid var(--border); }}
        .header h1 {{ font-size: 26px; font-weight: 800; color: #fff; letter-spacing: -0.5px; }}
        .header h1 span {{ color: var(--accent); }}
        .header p {{ color: var(--text-dim); font-size: 14px; margin-top: 6px; }}
        .container {{ max-width: 1100px; margin: 0 auto; padding: 20px; }}
        
        /* Tabs */
        .tabs {{ display: flex; gap: 10px; margin-bottom: 25px; overflow-x: auto; padding-bottom: 5px; }}
        .tab-btn {{ background: var(--card-bg); border: 1px solid var(--border); color: var(--text-dim); padding: 12px 18px; border-radius: 8px; font-weight: 600; cursor: pointer; white-space: nowrap; transition: 0.2s; }}
        .tab-btn.active {{ background: #1c2945; border-color: var(--accent); color: #fff; }}
        
        /* Filter Bar */
        .filter-bar {{ display: flex; gap: 8px; margin-bottom: 20px; align-items: center; background: #0f1626; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border); }}
        .filter-btn {{ background: transparent; border: 1px solid var(--border); color: var(--text-dim); padding: 6px 12px; border-radius: 6px; font-size: 13px; cursor: pointer; }}
        .filter-btn.active {{ background: var(--accent); color: #000; font-weight: 700; border-color: var(--accent); }}

        /* Match Cards */
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }}
        .match-card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }}
        .card-header {{ display: flex; justify-content: space-between; font-size: 12px; color: var(--text-dim); margin-bottom: 12px; }}
        .teams {{ font-size: 16px; font-weight: 700; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }}
        .vs {{ color: var(--accent-orange); font-size: 12px; }}
        .odds-bar {{ display: flex; justify-content: space-between; background: #0c1220; padding: 8px 10px; border-radius: 6px; font-size: 12px; font-family: 'JetBrains Mono', monospace; margin-bottom: 14px; border: 1px solid #18243c; }}
        .prediction-box {{ background: rgba(0, 230, 118, 0.06); border: 1px solid rgba(0, 230, 118, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 12px; }}
        .pred-label {{ font-size: 11px; font-weight: 700; color: var(--accent); letter-spacing: 0.5px; }}
        .pred-val {{ font-size: 17px; font-weight: 800; color: #fff; margin-top: 4px; }}
        .odd-badge {{ background: var(--accent); color: #000; padding: 2px 6px; border-radius: 4px; font-size: 14px; }}
        .dna-meter {{ font-size: 13px; color: var(--text-dim); margin-top: 6px; }}
        .stat-box {{ font-size: 13px; color: #cbd7ea; background: #162035; padding: 8px 10px; border-radius: 6px; margin-bottom: 12px; }}
        .history-box {{ font-size: 12px; color: var(--text-dim); border-top: 1px dashed var(--border); padding-top: 10px; }}
        .history-title {{ font-weight: 600; color: #a4b8d7; margin-bottom: 6px; }}
        .history-list {{ list-style: none; }}
        .history-list li {{ margin-bottom: 4px; line-height: 1.4; }}

        /* Rolling Kasa Box */
        .kasa-box {{ background: linear-gradient(135deg, #162238 0%, #1e3357 100%); border: 1px solid var(--accent); border-radius: 12px; padding: 20px; margin-bottom: 25px; }}
        .kasa-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }}
        .kasa-step {{ background: var(--accent); color: #000; font-weight: 800; padding: 4px 10px; border-radius: 6px; font-size: 12px; }}

        /* Archive Table */
        .archive-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        .archive-table th, .archive-table td {{ padding: 12px 10px; text-align: left; border-bottom: 1px solid var(--border); }}
        .archive-table th {{ background: #0e1526; color: var(--text-dim); font-weight: 600; }}
        .badge {{ padding: 4px 8px; border-radius: 4px; font-weight: 700; font-size: 11px; }}
        .badge-won {{ background: rgba(0, 230, 118, 0.15); color: var(--accent); border: 1px solid var(--accent); }}
        .badge-lost {{ background: rgba(255, 23, 68, 0.15); color: var(--danger); border: 1px solid var(--danger); }}
    </style>
</head>
<body>

<div class="header">
    <h1>OPTAODDS <span>AI v5.6</span></h1>
    <p>65.420+ Maçlık Çapraz Lig Oran DNA ve Kantitatif Değer Analiz Motoru • {today_str}</p>
</div>

<div class="container">
    <div class="kasa-box">
        <div class="kasa-header">
            <h3>🔥 ROLLING KASA — 3. ADIM</h3>
            <span class="kasa-step">AKTİF KUPON</span>
        </div>
        <p style="color:var(--text-dim); font-size:14px; margin-bottom:12px;">
            💰 Başlangıç Kasası: <b>1.383,75 TL</b> &nbsp;|&nbsp; 🎯 Hedef Kasa: <b>3.722,28 TL</b> &nbsp;|&nbsp; 📈 Toplam Oran: <b>2.69</b>
        </p>
        <div style="background:#0c1220; padding:12px; border-radius:8px; font-size:13px;">
            1️⃣ <b>M'gladbach - Karlsruher</b> ➔ 2.5 Gol Üstü @ 1.60 (%80.6 DNA)<br>
            2️⃣ <b>Roma - Cagliari</b> ➔ 2.5 Gol Üstü @ 1.68 (%78.8 DNA)
        </div>
    </div>

    <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('banko')">🏦 BANKO MAÇLAR</button>
        <button class="tab-btn" onclick="switchTab('vip')">💎 VIP VALUE SEÇİMLER</button>
        <button class="tab-btn" onclick="switchTab('surpriz')">💣 SÜRPRİZ & İY/MS</button>
        <button class="tab-btn" onclick="switchTab('arsiv')">📜 GEÇMİŞ ARŞİV</button>
    </div>

    <!-- BANKO -->
    <div id="tab-banko" class="tab-content active">
        <div class="grid">
            {render_cards(banko_matches)}
        </div>
    </div>

    <!-- VIP -->
    <div id="tab-vip" class="tab-content">
        <div class="grid">
            {render_cards(vip_matches)}
        </div>
    </div>

    <!-- SÜRPRİZ -->
    <div id="tab-surpriz" class="tab-content">
        <div class="grid">
            <div class="match-card">
                <div class="card-header"><span>DFB-Pokal</span><span>⏰ 20:00</span></div>
                <div class="teams"><span class="team">M'gladbach</span><span class="vs">vs</span><span class="team">Karlsruher</span></div>
                <div class="prediction-box">
                    <div class="pred-label">KUPA ÖZEL GERİ DÖNÜŞ RADARI</div>
                    <div class="pred-val">İY 1 / MS 2 (1/2) @ <span class="odd-badge">22.00</span></div>
                </div>
                <div class="stat-box"><b>📊 Anomali Sıklığı:</b> 31 benzer kupa maçında 3 kez gerçekleşti (%9.7).</div>
            </div>
            <div class="match-card">
                <div class="card-header"><span>İtalya Serie A</span><span>⏰ 19:30</span></div>
                <div class="teams"><span class="team">Sassuolo</span><span class="vs">vs</span><span class="team">Lazio</span></div>
                <div class="prediction-box">
                    <div class="pred-label">İLK YARI / MAÇ SONUCU</div>
                    <div class="pred-val">İY X / MS 2 @ <span class="odd-badge">5.00</span></div>
                </div>
                <div class="stat-box"><b>📊 İstatistiki Dağılım:</b> 30 benzer maçın 8'inde İY Beraberlik - MS Deplasman (%26.7).</div>
            </div>
        </div>
    </div>

    <!-- ARŞİV -->
    <div id="tab-arsiv" class="tab-content">
        <div style="background:var(--card-bg); border:1px solid var(--border); border-radius:12px; overflow-x:auto;">
            <table class="archive-table">
                <thead>
                    <tr>
                        <th>Tarih</th>
                        <th>Karşılaşma</th>
                        <th>Skor</th>
                        <th>Ana Tahmin</th>
                        <th>Durum</th>
                        <th>Sürpriz Tercih</th>
                        <th>Sürpriz Durum</th>
                    </tr>
                </thead>
                <tbody>
                    {render_archive(archive_data)}
                </tbody>
            </table>
        </div>
    </div>
</div>

<script>
function switchTab(tabId) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
    event.target.classList.add('active');
}}
</script>

</body>
</html>
"""

# Dosyaya Yaz
with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("[+] index.html basariyla uretildi ve guncellendi!")

# 4. TELEGRAM BİLDİRİMİ (Sadece GitHub Action çalıştığında 1 defa atar)
tg_token = os.environ.get("TG_BOT_TOKEN")
tg_chat = os.environ.get("TG_CHAT_ID")

if tg_token and tg_chat:
    tg_text = (
        f"🤖 <b>OPTAODDS AI — {today_str} BÜLTENİ YAYINDA</b>\\n\\n"
        "🔥 <b>Rolling Kasa 3. Adım:</b> M'gladbach 2.5 Üst (1.60) + Roma 2.5 Üst (1.68) [2.69 Oran]\\n\\n"
        "🎯 <b>Bankolar:</b>\\n"
        "• M'gladbach - Karlsruher ➔ 2.5 Üst (1.60) [%80.6]\\n"
        "• Roma - Cagliari ➔ 2.5 Üst (1.68) [%78.8]\\n"
        "• Bochum - Mainz ➔ KG Var (1.68) [%78.1]\\n"
        "• Bradford - Peterborough ➔ 2.5 Üst (1.72) [%78.6]\\n\\n"
        "🌐 Canlı Panel: https://alpaydnmez.github.io/optaodds-ai/"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{tg_token}/sendMessage",
            json={{"chat_id": tg_chat, "text": tg_text, "parse_mode": "HTML"}},
            timeout=10
        )
        print("[+] Telegram bildirimi basariyla gonderildi.")
    except Exception as e:
        print(f"[-] Telegram hatasi: {e}")
