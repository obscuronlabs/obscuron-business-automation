#!/usr/bin/env python3
"""
Premier Lig - Resmi Gameweek/Matchday Bilgisiyle Mac Verisi Pipeline'i
========================================================================

Kaynak: openfootball/england (GitHub, raw.githubusercontent.com)
  https://raw.githubusercontent.com/openfootball/england/master/<SEZON>/1-premierleague.txt

Bu kaynak La Liga calismasindaki Mackolik/football-data.co.uk yaklasimindan
FARKLIDIR: mac sonuclarini KRONOLOJIK tarihe gore degil, ligin kendi resmi
"Matchday" / "Round" basligina gore gruplar. Yani ertelenen/one alinan
maclar bile ait olduklari GERCEK resmi haftanin altinda listelenir. Bu,
projede aranan "gameweek kaynaktan gelmeli, tarihten tahmin edilmemeli"
gereksinimini dogrudan karsilar.

Bu script SADECE veri katmanidir:
  1) 02/03 - 25/26 arasi 24 sezonun tum Premier Lig maclarini ceker (cache'li)
  2) Her satiri parse edip STANDART formata cevirir:
       { season, week, home, away, home_goals, away_goals }
  3) Sikici dogrulamalari yapar (380 mac, 38 hafta, tekrar yok, takim basina
     38 mac, iki bilinen sezonun sampiyonluk puanina karsi capraz kontrol)
  4) Sonucu iki sekilde yazar:
       data/premier_lig_maclar_TUM.json   -> tum maclar, tek standart dosya
       data/hafta_XX.csv                  -> her hafta icin ayri dosya,
                                              tum sezonlar alt alta (25/26 -> 02/03)
                                              Excel'in MAC blogu duzenine hazir.

Excel'e YAZMA burada YAPILMAZ (bu ortamda Excel sablonlari yok). Bu script
sadece dogrulanmis, Excel'e sonradan yazilmaya hazir veriyi uretir.

Calistirma:
    python3 premier_test.py
"""

import csv
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict

# ---------------------------------------------------------------------------
# Ayarlar
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache")
DATA_DIR = os.path.join(BASE_DIR, "data")

RAW_URL_TMPL = (
    "https://raw.githubusercontent.com/openfootball/england/master/"
    "{season}/1-premierleague.txt"
)

SEASON_START_YEARS = list(range(2002, 2026))  # 2002-03 .. 2025-26 (24 sezon)
SEASONS = ["{:02d}/{:02d}".format(y % 100, (y + 1) % 100) for y in SEASON_START_YEARS]
SEASON_FOLDERS = ["{}-{:02d}".format(y, (y + 1) % 100) for y in SEASON_START_YEARS]

HTTP_TIMEOUT = 12
MAX_ATTEMPTS = 2          # kaynak yaniti gec/hata verirse fazla ugrasma
RETRY_DELAY = 2.0

# Bilinen sonuclarla capraz kontrol (parser dogrulugu icin bagimsiz kanit).
# (sezon, sampiyon_takim_ipucu, beklenen_puan)
KNOWN_CHAMPION_POINTS = [
    ("03/04", "Arsenal", 90),        # "Invincibles" - yenilgisiz sampiyon
    ("15/16", "Leicester", 81),      # Leicester City'nin mucizevi sampiyonlugu
    ("22/23", "Manchester City", 89),
]

HEADER_RE = re.compile(
    r"^▪\s*(?:Matchday|Round|Regular\s+Season\s*-)\s*(\d+)", re.IGNORECASE
)
# Tarih basligi satirlari: "Sat Aug 8", "Fri Aug 15 2025" vb. Sadece hafta
# gunu kisaltmasiyle baslamak yeterli DEGIL - "Sunderland" de "Sun" ile
# basliyor ve bir mac satirinin ev sahibi olabiliyor. Ay kisaltmasini da
# zorunlu tutarak bu yanlis eslesmeyi onluyoruz.
DAY_LINE_RE = re.compile(
    r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b"
)
# Format A (coglunlukla eski sezonlar): "Ev Takim   H-A (IY)  Deplasman"
MATCH_LINE_RE_DASH = re.compile(
    r"^\s*(?:\d{1,2}[:.]\d{2}\s*)?"
    r"(?P<home>.+?)\s{2,}"
    r"(?P<hg>\d+)\s*-\s*(?P<ag>\d+)"
    r"(?:\s*\([^)]*\))?"
    r"\s+(?P<away>.+?)\s*$"
)
# Format B (bazi yeni sezonlar, orn. 2024-25): "Ev Takim  v  Deplasman   H-A (IY)"
MATCH_LINE_RE_V = re.compile(
    r"^\s*(?:\d{1,2}[:.]\d{2}\s*)?"
    r"(?P<home>.+?)\s+v\s+"
    r"(?P<away>.+?)\s{2,}"
    r"(?P<hg>\d+)\s*-\s*(?P<ag>\d+)"
    r"(?:\s*\([^)]*\))?\s*$"
)


def match_line(line):
    # "v" formatini once dene: "Ev Takim  v  Deplasman   H-A" satirlarinda
    # tire (dash) formati da yanlislikla eslesip skor parantezini
    # "deplasman takimi" sanabiliyor - once daha ozgul (v iceren) formati
    # deneyip sadece o basarisiz olursa tire formatina dusuyoruz.
    mm = MATCH_LINE_RE_V.match(line)
    if mm:
        return mm
    return MATCH_LINE_RE_DASH.match(line)


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------------------
# Fetch (cache + retry + quick-fail)
# ---------------------------------------------------------------------------

def fetch_season_text(season_folder):
    cache_path = os.path.join(CACHE_DIR, season_folder + ".txt")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    url = RAW_URL_TMPL.format(season=season_folder)
    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "premier-lig-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(text)
            return text
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (403, 404):
                break  # bu hatalar tekrar denemekle duzelmez, hizlica vazgec
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_DELAY * attempt)
    raise RuntimeError(f"{season_folder}: veri cekilemedi ({last_err})")


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

def clean_team(name):
    name = re.sub(r"\s+", " ", name).strip()
    return name


def parse_season_text(text, season_label):
    matches = []
    current_week = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not stripped:
            continue

        m = HEADER_RE.match(stripped)
        if m:
            current_week = int(m.group(1))
            continue

        if DAY_LINE_RE.match(stripped):
            continue

        if stripped.startswith("(") or stripped.startswith(")"):
            continue  # gol atan oyuncu devam satiri

        if current_week is None:
            continue

        mm = match_line(line)
        if not mm:
            continue

        home = clean_team(mm.group("home"))
        away = clean_team(mm.group("away"))
        if not home or not away:
            continue

        matches.append(
            {
                "season": season_label,
                "week": current_week,
                "home": home,
                "away": away,
                "home_goals": int(mm.group("hg")),
                "away_goals": int(mm.group("ag")),
            }
        )
    return matches


# ---------------------------------------------------------------------------
# Dogrulama
# ---------------------------------------------------------------------------

def validate_season(season_label, matches):
    errors = []

    if len(matches) != 380:
        errors.append(f"{season_label}: {len(matches)} mac bulundu (beklenen 380)")

    weeks = sorted(set(m["week"] for m in matches))
    if weeks != list(range(1, 39)):
        missing = sorted(set(range(1, 39)) - set(weeks))
        extra = sorted(set(weeks) - set(range(1, 39)))
        errors.append(f"{season_label}: hafta araligi hatali (eksik={missing} fazla={extra})")

    seen_pairs = set()
    for m in matches:
        key = (m["home"], m["away"])
        if key in seen_pairs:
            errors.append(f"{season_label}: duplike mac {m['home']} - {m['away']}")
        seen_pairs.add(key)

    team_match_count = defaultdict(int)
    for m in matches:
        team_match_count[m["home"]] += 1
        team_match_count[m["away"]] += 1
    bad_teams = {t: c for t, c in team_match_count.items() if c != 38}
    if bad_teams:
        errors.append(f"{season_label}: takim basina 38 mac degil -> {bad_teams}")

    return errors


def compute_standings(matches):
    table = defaultdict(lambda: {"O": 0, "G": 0, "B": 0, "M": 0, "A": 0, "Y": 0, "P": 0})
    for m in matches:
        h, a = m["home"], m["away"]
        hg, ag = m["home_goals"], m["away_goals"]
        table[h]["O"] += 1
        table[a]["O"] += 1
        table[h]["A"] += hg
        table[h]["Y"] += ag
        table[a]["A"] += ag
        table[a]["Y"] += hg
        if hg > ag:
            table[h]["G"] += 1
            table[h]["P"] += 3
            table[a]["M"] += 1
        elif hg < ag:
            table[a]["G"] += 1
            table[a]["P"] += 3
            table[h]["M"] += 1
        else:
            table[h]["B"] += 1
            table[a]["B"] += 1
            table[h]["P"] += 1
            table[a]["P"] += 1
    return table


def cross_check_known_champions(all_matches_by_season):
    ok = True
    for season_label, name_hint, expected_points in KNOWN_CHAMPION_POINTS:
        matches = all_matches_by_season.get(season_label)
        if not matches:
            log(f"  ! {season_label}: capraz kontrol atlandi (veri yok)")
            ok = False
            continue
        table = compute_standings(matches)
        candidates = {t: v for t, v in table.items() if name_hint.lower() in t.lower()}
        if not candidates:
            log(f"  ! {season_label}: '{name_hint}' takimi bulunamadi -> {list(table.keys())}")
            ok = False
            continue
        team, stats = next(iter(candidates.items()))
        if stats["P"] != expected_points:
            log(f"  X {season_label}: {team} = {stats['P']} puan (beklenen {expected_points})")
            ok = False
        else:
            log(f"  OK {season_label}: {team} = {stats['P']} puan (dogrulandi)")
    return ok


# ---------------------------------------------------------------------------
# Yazma
# ---------------------------------------------------------------------------

def write_outputs(all_matches):
    os.makedirs(DATA_DIR, exist_ok=True)

    json_path = os.path.join(DATA_DIR, "premier_lig_maclar_TUM.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_matches, f, ensure_ascii=False, indent=2)

    by_week = defaultdict(list)
    for m in all_matches:
        by_week[m["week"]].append(m)

    season_order = list(reversed(SEASONS))  # 25/26 -> 02/03 (Excel blok sirasi)

    for week in range(1, 39):
        rows = by_week.get(week, [])
        rows_by_season = defaultdict(list)
        for r in rows:
            rows_by_season[r["season"]].append(r)

        path = os.path.join(DATA_DIR, f"hafta_{week:02d}.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["sezon", "ev_sahibi", "deplasman", "ev_gol", "deplasman_gol"])
            for season_label in season_order:
                for r in rows_by_season.get(season_label, []):
                    writer.writerow(
                        [r["season"], r["home"], r["away"], r["home_goals"], r["away_goals"]]
                    )

    return json_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    all_matches = []
    all_matches_by_season = {}
    per_season_errors = {}
    failed_seasons = []

    log(f"PREMIER LIG MAC VERISI - {len(SEASONS)} sezon cekiliyor (openfootball/england)")
    log("-" * 70)

    for season_label, season_folder in zip(SEASONS, SEASON_FOLDERS):
        try:
            text = fetch_season_text(season_folder)
        except RuntimeError as e:
            log(f"  HATA {season_label}: {e}")
            failed_seasons.append(season_label)
            continue

        matches = parse_season_text(text, season_label)
        errors = validate_season(season_label, matches)
        per_season_errors[season_label] = errors
        all_matches_by_season[season_label] = matches
        all_matches.extend(matches)

        status = "OK" if not errors else "SORUNLU"
        log(f"  {season_label}: {len(matches):3d} mac  [{status}]")
        for e in errors:
            log(f"      - {e}")

    log("-" * 70)
    log("BAGIMSIZ CAPRAZ KONTROL (bilinen sampiyonluk puanlari):")
    champions_ok = cross_check_known_champions(all_matches_by_season)

    total_errors = sum(len(v) for v in per_season_errors.values())
    seasons_ok = len(SEASONS) - len(failed_seasons)

    log("-" * 70)

    if failed_seasons or total_errors or not champions_ok:
        log("SONUC: DOGRULAMA BASARISIZ - veri Excel'e YAZILMAYACAK")
        if failed_seasons:
            log(f"  Cekilemeyen sezonlar: {failed_seasons}")
        if total_errors:
            log(f"  Toplam dogrulama hatasi: {total_errors}")
        if not champions_ok:
            log("  Capraz kontrol basarisiz")
        sys.exit(1)

    json_path = write_outputs(all_matches)

    log("SONUC: TUM DOGRULAMALAR BASARILI")
    log(f"  SEZON SAYISI      : {seasons_ok} / {len(SEASONS)}")
    log(f"  TOPLAM MAC        : {len(all_matches)} (beklenen {len(SEASONS) * 380})")
    log(f"  JSON CIKTI        : {json_path}")
    log(f"  HAFTALIK CSV      : {DATA_DIR}/hafta_01.csv .. hafta_38.csv")
    log("  PUAN DURUMUNA DOKUNULMADI (bu script sadece mac verisi uretir)")
    log("  EXCEL'E YAZMA     : bu ortamda yapilmadi (sablon dosyalari burada yok)")


if __name__ == "__main__":
    main()
