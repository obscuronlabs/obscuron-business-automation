#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_world_eski/ (arsiv.mackolik.com eski sistem, 2002-2010 civari) icindeki
sezonlari, data_world/ (www.mackolik.com yeni sistem) icindeki ana veri
dosyalarina EKLER - boylece build_league_excel.py daha eski sezonlari da
kullanabilir.

Excel'e islenen tum ligler icin calisir:
  - seriea_it (Italya Serie A)
  - brasileirao_a (Brezilya Serie A)
  - brasileirao_b (Brezilya Serie B)
  - serieb_it (Italya Serie B)
  - eredivisie (Hollanda Eredivisie)
  - ligue1 (Fransa Ligue 1)
  - ligue2 (Fransa Ligue 2)

Bir sezon HEM data_world HEM data_world_eski'de varsa, data_world'daki
(yeni sistem) tercih edilir, data_world_eski'deki o sezon ATLANIR -
hicbir sezon iki kere sayilmaz.

Calistirma:
    python merge_old_data.py

NOT: world_leagues_fetch.py'yi tekrar calistirirsan data_world/*.json
dosyalari sifirdan uretilir ve bu birlestirme kaybolur - o durumda bu
script'i tekrar calistirman gerekir.
"""
import glob
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_WORLD_DIR = os.path.join(BASE_DIR, "data_world")
DATA_WORLD_ESKI_DIR = os.path.join(BASE_DIR, "data_world_eski")

LEAGUE_KEYS = ["seriea_it", "brasileirao_a", "brasileirao_b", "serieb_it", "eredivisie", "ligue1", "ligue2"]


def log(msg):
    print(msg, flush=True)


def main():
    if not os.path.isdir(DATA_WORLD_DIR):
        log(f"HATA: {DATA_WORLD_DIR} yok - once world_leagues_fetch.py calistirilmali.")
        return
    if not os.path.isdir(DATA_WORLD_ESKI_DIR):
        log(f"HATA: {DATA_WORLD_ESKI_DIR} yok - once mackolik_old_fetch_season.py calistirilmali.")
        return

    for key in LEAGUE_KEYS:
        new_path = os.path.join(DATA_WORLD_DIR, f"{key}_maclar_TUM.json")
        if not os.path.exists(new_path):
            log(f"[{key}] {new_path} bulunamadi, atlaniyor.")
            continue

        with open(new_path, encoding="utf-8") as f:
            new_matches = json.load(f)
        existing_seasons = set(m["season"] for m in new_matches)
        log(f"[{key}] yeni sistemde {len(existing_seasons)} sezon var: {sorted(existing_seasons)}")

        old_files = sorted(glob.glob(os.path.join(DATA_WORLD_ESKI_DIR, f"{key}__*.json")))
        added_seasons = []
        skipped_seasons = []
        added_matches = 0

        for path in old_files:
            with open(path, encoding="utf-8") as f:
                old_matches = json.load(f)
            if not old_matches:
                continue
            season = old_matches[0]["season"]
            if season in existing_seasons:
                skipped_seasons.append(season)
                continue
            new_matches.extend(old_matches)
            existing_seasons.add(season)
            added_seasons.append(season)
            added_matches += len(old_matches)

        if skipped_seasons:
            log(f"[{key}] zaten yeni sistemde olan (atlanan) eski sezonlar: {sorted(skipped_seasons)}")
        if added_seasons:
            log(f"[{key}] EKLENEN eski sezonlar: {sorted(added_seasons)} ({added_matches} mac)")
            with open(new_path, "w", encoding="utf-8") as f:
                json.dump(new_matches, f, ensure_ascii=False, indent=2)
            log(f"[{key}] -> {new_path} guncellendi, toplam {len(new_matches)} mac.")
        else:
            log(f"[{key}] eklenecek yeni eski-sezon bulunamadi.")
        log("")


if __name__ == "__main__":
    main()
