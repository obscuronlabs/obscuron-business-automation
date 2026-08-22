#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_world_eski/{league_key}__{season}.json dosyasini inceleyip
build_league_excel.py'nin neden bu sezonu gecersiz saydigini bulur.
SALT OKUNUR.

Calistirma:
    python diagnose_old_season.py seriea_it 02-03
    python diagnose_old_season.py seriea_it 03-04
"""
import json
import os
import sys
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_WORLD_ESKI_DIR = os.path.join(BASE_DIR, "data_world_eski")


def main():
    if len(sys.argv) != 3:
        print("Kullanim: python diagnose_old_season.py <league_key> <season-with-dash>")
        print("orn: python diagnose_old_season.py seriea_it 02-03")
        return

    league_key, season_dash = sys.argv[1], sys.argv[2]
    path = os.path.join(DATA_WORLD_ESKI_DIR, f"{league_key}__{season_dash}.json")
    if not os.path.exists(path):
        print(f"HATA: {path} bulunamadi.")
        return

    with open(path, encoding="utf-8") as f:
        matches = json.load(f)

    print(f"Dosya: {path}")
    print(f"Toplam mac: {len(matches)}")

    teams = set()
    for m in matches:
        teams.add(m["home"]); teams.add(m["away"])
    print(f"Takim sayisi: {len(teams)}")
    print("Takimlar (alfabetik):")
    for t in sorted(teams):
        print(f"  {t!r}  (uzunluk={len(t)})")

    weeks = sorted(set(m["week"] for m in matches))
    print(f"Hafta araligi: {weeks[0]}..{weeks[-1]}  (toplam {len(weeks)} farkli hafta)")
    expected_weeks = list(range(1, 39))
    if weeks != expected_weeks:
        missing = sorted(set(expected_weeks) - set(weeks))
        extra = sorted(set(weeks) - set(expected_weeks))
        if missing:
            print(f"  EKSIK haftalar: {missing}")
        if extra:
            print(f"  FAZLA/BEKLENMEYEN haftalar: {extra}")

    counts = Counter()
    for m in matches:
        counts[m["home"]] += 1
        counts[m["away"]] += 1
    print("Takim basi mac sayisi (38 olmayanlar):")
    any_bad = False
    for t, c in sorted(counts.items()):
        if c != 38:
            any_bad = True
            print(f"  {t!r}: {c} mac")
    if not any_bad:
        print("  (hepsi 38 - sorun yok)")

    print()
    if len(teams) == 20 and len(matches) == 380 and weeks == expected_weeks:
        print("SONUC: Bu dosya aslinda GECERLI gorunuyor (20 takim, 380 mac, 1-38 hafta tam).")
        print("build_league_excel.py'nin neden atladigi ayri incelenmeli.")
    else:
        print("SONUC: Bu dosyada gercekten bir sorun var, yukaridaki detaylara bak.")


if __name__ == "__main__":
    main()
