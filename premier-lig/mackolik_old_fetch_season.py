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

# --- BURAYA KENDI seas_id LISTENI EKLE -----------------------------------
JOBS = [
    # (league_key,   season_label,  seas_id)
    ("bundesliga",   "02/03",       6),
]
# --------------------------------------------------------------------------

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
