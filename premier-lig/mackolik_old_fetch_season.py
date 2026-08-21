#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eski sistem (arsiv.mackolik.com) - GERCEK TARAYICI (Playwright) ile bir
sezonun TUM haftalarini dolasip mac sonuclarini ceker. SALT OKUNUR,
hicbir Excel dosyasina yazmaz - sadece data_world_eski/ altina JSON yazar.

Kurulum (ilk sefer, bir kere):
    pip install playwright beautifulsoup4
    playwright install chromium

Kullanim:
    1) Asagidaki JOBS listesine (league_key, season_label, seas_id) ekle.
       - league_key: world_leagues_fetch.py'deki LEAGUES listesindeki "key"
         ile AYNI olmali (orn. "bundesliga", "serie_a", "eredivisie", ...)
       - season_label: "02/03" gibi (range ligler) ya da "2005" gibi
         (Brezilya - "year" tipi ligler) - world_leagues_fetch.py'deki
         season_list() ile AYNI formatta olmali.
       - seas_id: arsiv.mackolik.com/Standings/Default.aspx?sId=XXXX
         adresindeki XXXX sayisi.
    2) python mackolik_old_fetch_season.py

Her sezon icin: data_world_eski/{league_key}__{season_label}.json
(dosya adindaki '/' karakteri '-' ile degistirilir)
"""
import json
import os
import re
import time

from playwright.sync_api import sync_playwright

from mackolik_old_parse import parse_match_table, parse_week_options

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE_DIR, "data_world_eski")

# --- seas_id LISTESI -------------------------------------------------------
# league_key degerleri world_leagues_fetch.py'deki LEAGUES ile birebir ayni.
JOBS = [
    # --- Almanya Bundesliga ---
    ("bundesliga", "02/03", 6),
    ("bundesliga", "03/04", 111),
    ("bundesliga", "04/05", 493),
    ("bundesliga", "05/06", 800),
    ("bundesliga", "06/07", 1244),
    ("bundesliga", "07/08", 1827),
    ("bundesliga", "08/09", 2411),
    ("bundesliga", "09/10", 3060),

    # --- Italya Serie A ---
    ("seriea_it", "02/03", 4),
    ("seriea_it", "03/04", 151),
    ("seriea_it", "04/05", 557),
    ("seriea_it", "05/06", 908),
    ("seriea_it", "06/07", 1383),
    ("seriea_it", "07/08", 1948),
    ("seriea_it", "08/09", 2450),
    ("seriea_it", "09/10", 3064),

    # --- Italya Serie B ---
    ("serieb_it", "02/03", 26),
    ("serieb_it", "03/04", 152),
    ("serieb_it", "04/05", 558),
    ("serieb_it", "05/06", 931),
    ("serieb_it", "06/07", 1384),
    ("serieb_it", "07/08", 1949),
    ("serieb_it", "08/09", 2451),
    ("serieb_it", "09/10", 3122),

    # --- Hollanda Eredivisie ---
    ("eredivisie", "02/03", 8),
    ("eredivisie", "03/04", 148),
    ("eredivisie", "04/05", 515),
    ("eredivisie", "05/06", 844),
    ("eredivisie", "06/07", 1293),
    ("eredivisie", "07/08", 1842),
    ("eredivisie", "08/09", 2448),
    ("eredivisie", "09/10", 3094),

    # --- Fransa Ligue 1 ---
    ("ligue1", "02/03", 5),
    ("ligue1", "03/04", 109),
    ("ligue1", "04/05", 495),
    ("ligue1", "05/06", 837),
    ("ligue1", "06/07", 1262),
    ("ligue1", "07/08", 1761),
    ("ligue1", "08/09", 2381),
    ("ligue1", "09/10", 3057),

    # --- Fransa Ligue 2 ---
    ("ligue2", "02/03", 7),
    ("ligue2", "03/04", 110),
    ("ligue2", "04/05", 496),
    ("ligue2", "05/06", 838),
    ("ligue2", "06/07", 1263),
    ("ligue2", "07/08", 1762),
    ("ligue2", "08/09", 2382),
    ("ligue2", "09/10", 3058),

    # --- Brezilya Serie A (season_kind = "year", 2002 icin id yok) ---
    ("brasileirao_a", "2003", 77),
    ("brasileirao_a", "2004", 307),
    ("brasileirao_a", "2005", 723),
    ("brasileirao_a", "2006", 1130),
    ("brasileirao_a", "2007", 1564),
    ("brasileirao_a", "2008", 2259),
    ("brasileirao_a", "2009", 2937),

    # --- Brezilya Serie B (2002-2005 icin id yok) ---
    ("brasileirao_b", "2006", 1182),
    ("brasileirao_b", "2007", 1633),
    ("brasileirao_b", "2008", 2289),
    ("brasileirao_b", "2009", 2938),
]
# --------------------------------------------------------------------------
# NOT: Bu ID'ler "5 ai calisti bunlar cikti" listesinden geliyor - yani
# baska bir yapay zekanin cikarim/arama sonucu, benim veya senin tek tek
# tarayicidan dogruladigin bir liste DEGIL. Tek dogrulanan deger sId=6
# (Bundesliga 02/03) idi ve listeyle birebir uyustu, bu iyi bir isaret.
# Yine de her sezon asagidaki validate() fonksiyonundan otomatik gecer:
# yanlis ID bir baska ligin/sezonun sayfasina denk gelirse (takim sayisi
# tuhaf, mac sayisi tutmuyor, hafta araligi bozuk) o sezon "SORUNLU"
# olarak isaretlenir ve JSON'a yine de yazilir ama ozet tabloda gorunur -
# hicbir sey sessizce Excel'e karismaz, cunku bu script Excel'e hic
# dokunmuyor.

STANDING_URL = "https://arsiv.mackolik.com/Standings/Default.aspx?sId={seas_id}"


def fetch_season(page, seas_id, season_label):
    url = STANDING_URL.format(seas_id=seas_id)
    page.goto(url, wait_until="networkidle", timeout=30000)
    try:
        page.click("text=Haftalık", timeout=5000)
        page.wait_for_timeout(1500)
    except Exception as e:
        print(f"    [!] 'Haftalık' sekmesine tiklanamadi: {e}")
        return []

    weeks = parse_week_options(page.content())
    if not weeks:
        print("    [!] Hafta secici (weekOpt) bulunamadi, sezon atlaniyor.")
        return []

    print(f"    {len(weeks)} hafta bulundu: {weeks[0]}..{weeks[-1]}")

    all_matches = []
    for wk in weeks:
        ok = False
        matches = []
        for attempt in range(3):
            try:
                page.select_option("#weekOpt", str(wk))
                page.wait_for_load_state("networkidle", timeout=15000)
                page.wait_for_timeout(500)
                html = page.content()
                matches, parsed_week = parse_match_table(html)
                if parsed_week == wk:
                    ok = True
                    break
                time.sleep(1)
            except Exception:
                time.sleep(1)
        if not ok:
            print(f"    [!] Hafta {wk}: dogrulanamadi, atlaniyor (son deneme: {len(matches)} mac bulundu)")
            continue
        for m in matches:
            m["season"] = season_label
        all_matches.extend(matches)
        print(f"    Hafta {wk}: {len(matches)} mac")

    return all_matches


def validate(season_label, matches):
    errors = []
    if not matches:
        return ["mac bulunamadi"]
    teams = set()
    for m in matches:
        teams.add(m["home"]); teams.add(m["away"])
    n_teams = len(teams)
    expected_per_team = 2 * (n_teams - 1)
    expected_total = n_teams * (n_teams - 1)
    if len(matches) != expected_total:
        errors.append(f"beklenen {expected_total} mac, bulunan {len(matches)} ({n_teams} takim)")

    seen_pairs = set()
    for m in matches:
        key = (m["week"], m["home"], m["away"])
        if key in seen_pairs:
            errors.append(f"DUPLIKE: hafta {m['week']} {m['home']}-{m['away']}")
        seen_pairs.add(key)

    counts = {}
    for m in matches:
        counts[m["home"]] = counts.get(m["home"], 0) + 1
        counts[m["away"]] = counts.get(m["away"], 0) + 1
    for t, c in counts.items():
        if c != expected_per_team:
            errors.append(f"{t}: {c} mac (beklenen {expected_per_team})")

    weeks_seen = sorted(set(m["week"] for m in matches))
    n_expected_weeks = n_teams - 1
    if weeks_seen != list(range(1, n_expected_weeks + 1)):
        errors.append(f"hafta araligi anormal: {weeks_seen[:3]}...{weeks_seen[-3:]} (beklenen 1..{n_expected_weeks})")

    return errors


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Toplam {len(JOBS)} sezon islenecek.\n")

    summary = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()

        for league_key, season_label, seas_id in JOBS:
            print(f"[{league_key} {season_label}] sId={seas_id}")
            matches = fetch_season(page, seas_id, season_label)
            errors = validate(season_label, matches)

            safe_label = season_label.replace("/", "-")
            out_path = os.path.join(OUT_DIR, f"{league_key}__{safe_label}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(matches, f, ensure_ascii=False, indent=2)

            status = "OK" if not errors else "SORUNLU"
            print(f"    -> {out_path} ({len(matches)} mac) [{status}]")
            if errors:
                for e in errors:
                    print(f"       ! {e}")
            summary.append((league_key, season_label, len(matches), status))
            print()

        browser.close()

    print("=" * 60)
    print("OZET")
    print("=" * 60)
    for league_key, season_label, n, status in summary:
        print(f"  {league_key:20s} {season_label:8s} {n:4d} mac   [{status}]")


if __name__ == "__main__":
    main()
