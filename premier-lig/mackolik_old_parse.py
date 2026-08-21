#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eski sistem (arsiv.mackolik.com) - Playwright ile render edilmis bir HTML
sayfasindan "N. HAFTA MAC SONUCLARI" tablosunu ayristirir.

Bu dosya SADECE parse fonksiyonlarini icerir - fetch islemini
mackolik_old_fetch_season.py yapacak. Test icin:

    python mackolik_old_parse.py mackolik_render_edilmis.html
"""
import re
import sys
from bs4 import BeautifulSoup


def parse_week_number(soup):
    """Tablo basligindan hafta numarasini cikarir: '34. HAFTA MAC SONUCLARI' -> 34"""
    header = soup.find("table", id="tblResult")
    if header is None:
        return None
    th = header.find("td", class_=None, colspan="9")
    if th is None:
        # fallback: ilk tr'nin ilk td'si
        first_tr = header.find("tr")
        th = first_tr.find("td") if first_tr else None
    if th is None:
        return None
    m = re.search(r"(\d+)\.\s*HAFTA", th.get_text(strip=True))
    return int(m.group(1)) if m else None


def parse_match_table(html):
    """Render edilmis HTML string'inden mac listesini cikarir.

    Donen her mac dict'i standart semaya uyar:
        {season, week, home, away, home_goals, away_goals,
         ht_home_goals, ht_away_goals, date_dm,
         home_rank, away_rank}
    (season alani burada doldurulmaz, cagiran fonksiyon ekler.)
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="tblResult")
    if table is None:
        return [], None

    week = parse_week_number(soup)

    matches = []
    rows = table.find_all("tr")
    for tr in rows:
        if "table-header" in (tr.get("class") or []):
            continue
        tds = tr.find_all("td")
        if len(tds) < 10:
            continue

        date_dm = tds[0].get_text(strip=True) or None

        home_rank_txt = tds[2].get_text(strip=True)
        home_rank = int(home_rank_txt) if home_rank_txt.isdigit() else None

        home_a = tds[3].find("a")
        home = home_a.get_text(strip=True) if home_a else tds[3].get_text(strip=True)

        ft_a = tds[5].find("a")
        ft_text = ft_a.get_text(strip=True) if ft_a else tds[5].get_text(strip=True)
        ft_m = re.match(r"(\d+)\s*-\s*(\d+)", ft_text)
        if not ft_m:
            # oynanmamis/ertelenmis mac gibi gorunuyor, atla
            continue
        home_goals, away_goals = int(ft_m.group(1)), int(ft_m.group(2))

        away_a = tds[7].find("a")
        away = away_a.get_text(strip=True) if away_a else tds[7].get_text(strip=True)

        away_rank_txt = tds[8].get_text(strip=True)
        away_rank = int(away_rank_txt) if away_rank_txt.isdigit() else None

        ht_text = tds[9].get_text(strip=True)
        ht_m = re.match(r"(\d+)\s*-\s*(\d+)", ht_text)
        ht_home_goals, ht_away_goals = (int(ht_m.group(1)), int(ht_m.group(2))) if ht_m else (None, None)

        if not home or not away:
            continue

        matches.append({
            "week": week,
            "home": home,
            "away": away,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "ht_home_goals": ht_home_goals,
            "ht_away_goals": ht_away_goals,
            "date_dm": date_dm,
            "home_rank": home_rank,
            "away_rank": away_rank,
        })

    return matches, week


def parse_week_options(html):
    """Sayfadaki #weekOpt dropdown'undan mevcut hafta numaralarini dondurur."""
    soup = BeautifulSoup(html, "html.parser")
    sel = soup.find("select", id="weekOpt")
    if sel is None:
        return []
    weeks = []
    for opt in sel.find_all("option"):
        val = opt.get("value")
        if val and val.isdigit():
            weeks.append(int(val))
    return sorted(weeks)


if __name__ == "__main__":
    fname = sys.argv[1] if len(sys.argv) > 1 else "mackolik_render_edilmis.html"
    with open(fname, encoding="utf-8") as f:
        html = f.read()

    weeks_available = parse_week_options(html)
    print(f"Dropdown'daki haftalar: {weeks_available[:5]}...{weeks_available[-5:]} (toplam {len(weeks_available)})")

    matches, week = parse_match_table(html)
    print(f"Bu sayfadaki hafta: {week}, mac sayisi: {len(matches)}")
    for m in matches:
        print(f"  {m['date_dm']}  ({m['home_rank']}) {m['home']}  {m['home_goals']}-{m['away_goals']} (IY {m['ht_home_goals']}-{m['ht_away_goals']})  {m['away']} ({m['away_rank']})")
