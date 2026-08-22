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


def wait_for_week_content(page, wk, max_wait_s=15):
    """networkidle yerine: reklam/takip istekleri sayfayi hic 'sessiz'
    hale getirmeyebilir, o yuzden dogrudan aradigimiz hafta numarasinin
    tabloya gelip gelmedigini kontrol ediyoruz - daha guvenilir.

    ONEMLI: eski hafta hala ekranda goruntuleniyorsa (AJAX henuz
    guncellemediyse) o veriyi ASLA dogru hafta gibi geri dondurmuyoruz -
    aksi halde bir onceki haftanin verisi yanlis hafta numarasiyla
    tekrar tekrar eklenir (duplike + eksik hafta hatasina yol acar)."""
    start = time.time()
    while time.time() - start < max_wait_s:
        html = page.content()
        matches, parsed_week = parse_match_table(html)
        if parsed_week == wk:
            return matches
        page.wait_for_timeout(500)
    return None


def fetch_season(page, seas_id, season_label):
    url = STANDING_URL.format(seas_id=seas_id)

    goto_ok = False
    for attempt in range(6):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(1500)
            page.wait_for_selector("text=Haftalık", timeout=25000)
            goto_ok = True
            break
        except Exception as e:
            print(f"    [!] Sayfa acilamadi (deneme {attempt + 1}/6): {e}")
            time.sleep(4)
    if not goto_ok:
        print("    [!] Sayfa 6 denemede de acilamadi, sezon atlaniyor.")
        return []

    try:
        page.click("text=Haftalık", timeout=15000)
        page.wait_for_selector("#weekOpt", timeout=25000)
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
        matches = None
        for attempt in range(6):
            try:
                page.select_option("#weekOpt", str(wk))
                matches = wait_for_week_content(page, wk, max_wait_s=20)
                if matches is not None:
                    break
            except Exception:
                matches = None
            time.sleep(2)
        if not matches:
            print(f"    [!] Hafta {wk}: dogrulanamadi, atlaniyor")
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
    n_expected_weeks = 2 * (n_teams - 1)
    if weeks_seen != list(range(1, n_expected_weeks + 1)):
        errors.append(f"hafta araligi anormal: {weeks_seen[:3]}...{weeks_seen[-3:]} (beklenen 1..{n_expected_weeks})")

    return errors


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print(f"Toplam {len(JOBS)} sezon islenecek.\n")

    summary = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="tr-TR",
            viewport={"width": 1366, "height": 900},
        )

        for league_key, season_label, seas_id in JOBS:
            safe_label = season_label.replace("/", "-")
            out_path = os.path.join(OUT_DIR, f"{league_key}__{safe_label}.json")

            if os.path.exists(out_path):
                with open(out_path, encoding="utf-8") as f:
                    cached = json.load(f)
                if not validate(season_label, cached):
                    print(f"[{league_key} {season_label}] zaten var ve OK, atlaniyor.\n")
                    summary.append((league_key, season_label, len(cached), "OK (onceki calisma)"))
                    continue
                print(f"[{league_key} {season_label}] daha once SORUNLU kaydedilmis, yeniden deneniyor.")

            print(f"[{league_key} {season_label}] sId={seas_id}")
            # her sezon icin TAZE bir sekme - eski sekmede biriken
            # reklam/takip script yukunu birlikte tasimamak icin.
            page = context.new_page()
            try:
                matches = fetch_season(page, seas_id, season_label)
                errors = validate(season_label, matches)
            except Exception as e:
                print(f"    [!!] SEZON COKTU, atlaniyor: {e}")
                matches = []
                errors = [f"beklenmeyen hata: {e}"]
            finally:
                try:
                    page.close()
                except Exception:
                    pass

            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(matches, f, ensure_ascii=False, indent=2)

            status = "OK" if not errors else "SORUNLU"
            print(f"    -> {out_path} ({len(matches)} mac) [{status}]")
            if errors:
                for e in errors:
                    print(f"       ! {e}")
            summary.append((league_key, season_label, len(matches), status))
            print()
            time.sleep(2)

        browser.close()

    print("=" * 60)
    print("OZET")
    print("=" * 60)
    for league_key, season_label, n, status in summary:
        print(f"  {league_key:20s} {season_label:8s} {n:4d} mac   [{status}]")


if __name__ == "__main__":
    main()
