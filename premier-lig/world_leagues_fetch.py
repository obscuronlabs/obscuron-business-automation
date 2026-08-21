#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
8 Lig - Mackolik.com Sayfa-Ici JSON'dan Mac Verisi Cekme + Dogrulama
=====================================================================

Bu script SADECE veri katmanidir (Excel'e YAZMAZ - bu 8 lig icin henuz
Excel sablonu yok). Amac: her ligin 2002'den bugune butun sezonlarini
cekip, RESMI hafta/matchday numarasiyla (tarihten tahmin ETMEDEN)
standart formata cevirip dogrulamak.

NASIL CALISIR:
  www.mackolik.com/puan-durumu/{lig-slug}/{sezon}/{lig-id} sayfasinin
  HTML'i icinde <div class="page-competition-index" data-settings="...">
  ozniteliginde COK ZENGIN, yapilandirilmis bir JSON gomulu:

    competition.gamesets = [
      {"name": "1", "matches": {"0": {...mac...}, "1": {...}, ...}},
      {"name": "2", "matches": {...}},
      ...
      {"name": "Play-out Final", "matches": {...}}   <- lig disi, ATLANIR
    ]

  Her mac objesinde:
    scores.ft.home / scores.ft.away   -> mac sonucu
    scores.ht.home / scores.ht.away   -> ilk yari
    contestants["0"/"1"].position     -> "home" / "away"
    contestants["0"/"1"].name         -> takim adi (DOGRUDAN, ID cozmeye gerek yok)
    date                              -> unix timestamp (mac gunu)
    stage.name                        -> "Normal Sezon" (lig) vs baska (kupa/play-off)

  gameset["name"] SAYISAL olan gruplar RESMI matchday numarasidir.
  Sayisal OLMAYAN gruplar ("Play-out Final" gibi play-off/baraj
  maclaridir) - normal lig fikstirune dahil edilmez, ATLANIR.

VERI DOGRULAMA (Excel asamasina gecmeden - simdilik Excel adimi yok):
  - beklenen toplam mac = hafta_sayisi * (takim_sayisi/2)
  - takim basina mac sayisi = hafta_sayisi
  - mukerrer mac yok

Calistirma:
    pip install requests   (yoksa urllib ile de calisir, daha yavas olabilir)
    python world_leagues_fetch.py
"""

import html as html_module
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, "cache_world")
DATA_DIR = os.path.join(BASE_DIR, "data_world")

HTTP_TIMEOUT = 20
MAX_ATTEMPTS = 2
RETRY_DELAY = 2.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Referer": "https://www.mackolik.com/",
}

# =============================================================================
# LIG TANIMLARI - sizin verdiginiz URL tablosundan
# =============================================================================
# season_kind: "range" -> URL'de "2010-2011" gibi, etiket "10/11"
#              "year"  -> URL'de tek yil "2010" gibi (Brezilya, takvim yili sezonu)

LEAGUES = [
    {"key": "bundesliga", "name": "Almanya Bundesliga", "slug": "almanya-bundesliga",
     "id": "6by3h89i2eykc341oz7lv1ddd", "season_kind": "range",
     "start_year": 2002, "end_year": 2025},
    {"key": "seriea_it", "name": "Italya Serie A", "slug": "italya-serie-a",
     "id": "1r097lpxe0xn03ihb7wi98kao", "season_kind": "range",
     "start_year": 2002, "end_year": 2025},
    {"key": "serieb_it", "name": "Italya Serie B", "slug": "italya-serie-b",
     "id": "8ey0ww2zsosdmwr8ehsorh6t7", "season_kind": "range",
     "start_year": 2002, "end_year": 2025},
    {"key": "eredivisie", "name": "Hollanda Eredivisie", "slug": "hollanda-eredivisie",
     "id": "akmkihra9ruad09ljapsm84b3", "season_kind": "range",
     "start_year": 2002, "end_year": 2025},
    {"key": "ligue1", "name": "Fransa Ligue 1", "slug": "fransa-ligue-1",
     "id": "dm5ka0os1e3dxcp3vh05kmp33", "season_kind": "range",
     "start_year": 2002, "end_year": 2025},
    {"key": "ligue2", "name": "Fransa Ligue 2", "slug": "fransa-ligue-2",
     "id": "4w7x0s5gfs5abasphlha5de8k", "season_kind": "range",
     "start_year": 2002, "end_year": 2025},
    {"key": "brasileirao_a", "name": "Brezilya Serie A", "slug": "brezilya-serie-a",
     "id": "scf9p4y91yjvqvg5jndxzhxj", "season_kind": "year",
     "start_year": 2002, "end_year": 2025},
    {"key": "brasileirao_b", "name": "Brezilya Serie B", "slug": "brezilya-serie-b",
     "id": "5zr0b05eyx25km7z1k03ca9jx", "season_kind": "year",
     "start_year": 2002, "end_year": 2025},
]

DATA_SETTINGS_RE = re.compile(r'data-settings="(.*?)"(?=\s|>)', re.DOTALL)


def log(msg):
    print(msg, flush=True)


def season_list(league):
    out = []  # [(url_season_str, label), ...]
    if league["season_kind"] == "range":
        for y in range(league["start_year"], league["end_year"] + 1):
            url_s = f"{y}-{y + 1}"
            label = f"{y % 100:02d}/{(y + 1) % 100:02d}"
            out.append((url_s, label))
    else:  # "year"
        for y in range(league["start_year"], league["end_year"] + 2):  # brezilya 2026'ya kadar verildi
            out.append((str(y), str(y)))
    return out


def build_url(league, url_season):
    return f"https://www.mackolik.com/puan-durumu/{league['slug']}/{url_season}/{league['id']}"


def fetch_page(league_key, url_season, url):
    cache_path = os.path.join(CACHE_DIR, f"{league_key}__{url_season}.html")
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return f.read()

    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(text)
            return text
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (403, 404):
                break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_DELAY * attempt)
    raise RuntimeError(f"{url}: cekilemedi ({last_err})")


def extract_competition_json(html_doc):
    """Sayfadaki butun data-settings ozniteliklerini dener, icinde
    'competition.gamesets' olani bulup doner. Bulamazsa None doner."""
    for m in DATA_SETTINGS_RE.finditer(html_doc):
        raw = m.group(1)
        if "gamesets" not in raw:
            continue
        try:
            unescaped = html_module.unescape(raw)
            data = json.loads(unescaped)
        except (json.JSONDecodeError, ValueError):
            continue
        comp = data.get("competition")
        if comp and "gamesets" in comp:
            return comp
    return None


def parse_matches(comp, season_label):
    matches = []
    skipped_non_numeric = []
    for gs in comp.get("gamesets", []):
        name = gs.get("name", "")
        if not re.fullmatch(r"\d+", str(name).strip()):
            skipped_non_numeric.append(name)
            continue
        week = int(name)
        for m in gs.get("matches", {}).values():
            contestants = m.get("contestants") or {}
            home = away = None
            for c in contestants.values():
                if c.get("position") == "home":
                    home = c.get("name")
                elif c.get("position") == "away":
                    away = c.get("name")
            if not home or not away:
                continue
            scores = m.get("scores") or {}
            ft = scores.get("ft") or {}
            ht = scores.get("ht") or {}
            if ft.get("home") is None or ft.get("away") is None:
                continue  # oynanmamis/veri eksik mac

            date_dm = None
            ts = m.get("date")
            if ts:
                import datetime
                dt = datetime.datetime.utcfromtimestamp(int(ts))
                date_dm = f"{dt.day:02d}/{dt.month:02d}"

            matches.append({
                "season": season_label,
                "week": week,
                "home": home.strip(),
                "away": away.strip(),
                "home_goals": ft["home"],
                "away_goals": ft["away"],
                "ht_home_goals": ht.get("home"),
                "ht_away_goals": ht.get("away"),
                "date_dm": date_dm,
            })
    return matches, skipped_non_numeric


def validate_season(season_label, matches):
    errors = []
    if not matches:
        return ["mac bulunamadi"]

    teams = set()
    for m in matches:
        teams.add(m["home"]); teams.add(m["away"])
    n_teams = len(teams)
    if n_teams % 2 != 0:
        errors.append(f"tek sayida takim ({n_teams}) - anormal")
        return errors

    weeks = sorted(set(m["week"] for m in matches))
    expected_weeks = (n_teams - 1) * 2
    matches_per_week = n_teams // 2

    per_week = defaultdict(int)
    for m in matches:
        per_week[m["week"]] += 1
    bad_weeks = {w: c for w, c in per_week.items() if c != matches_per_week}
    if bad_weeks:
        errors.append(f"hafta basina {matches_per_week} mac degil -> {bad_weeks}")

    seen = set()
    for m in matches:
        key = (m["home"], m["away"], m["week"])
        if key in seen:
            errors.append(f"duplike mac: {m['home']}-{m['away']} hafta {m['week']}")
        seen.add(key)

    team_count = defaultdict(int)
    for m in matches:
        team_count[m["home"]] += 1
        team_count[m["away"]] += 1
    expected_per_team = len(weeks)
    bad_teams = {t: c for t, c in team_count.items() if c != expected_per_team}
    if bad_teams:
        errors.append(f"takim basina {expected_per_team} mac degil -> {bad_teams}")

    return errors


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    overall_summary = []

    for league in LEAGUES:
        log("=" * 70)
        log(league["name"])
        log("=" * 70)

        seasons = season_list(league)
        all_matches = []
        n_ok = 0
        n_fail = 0

        for url_season, label in seasons:
            url = build_url(league, url_season)
            try:
                html_doc = fetch_page(league["key"], url_season, url)
            except RuntimeError as e:
                log(f"  {label}: CEKILEMEDI ({e})")
                n_fail += 1
                continue

            comp = extract_competition_json(html_doc)
            if comp is None:
                log(f"  {label}: SAYFADA VERI BULUNAMADI (yapisi degismis olabilir)")
                n_fail += 1
                continue

            matches, skipped = parse_matches(comp, label)
            errors = validate_season(label, matches)

            if errors:
                log(f"  {label}: {len(matches):3d} mac  [SORUNLU]")
                for e in errors[:3]:
                    log(f"      - {e}")
                n_fail += 1
                continue

            n_teams = len(set(m["home"] for m in matches) | set(m["away"] for m in matches))
            n_weeks = len(set(m["week"] for m in matches))
            log(f"  {label}: {len(matches):3d} mac, {n_teams} takim, {n_weeks} hafta  [OK]"
                + (f"  (atlanan play-off grubu: {skipped})" if skipped else ""))
            all_matches.extend(matches)
            n_ok += 1

        out_path = os.path.join(DATA_DIR, f"{league['key']}_maclar_TUM.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_matches, f, ensure_ascii=False, indent=2)

        log(f"  -> {n_ok}/{len(seasons)} sezon basarili, {n_fail} sorunlu/basarisiz")
        log(f"  -> {out_path} ({len(all_matches)} mac)")
        log("")
        overall_summary.append((league["name"], n_ok, len(seasons), len(all_matches)))

    log("=" * 70)
    log("GENEL OZET")
    log("=" * 70)
    for name, ok, total, n_matches in overall_summary:
        log(f"  {name:25s}: {ok:2d}/{total:2d} sezon basarili, {n_matches:5d} mac")


if __name__ == "__main__":
    main()
