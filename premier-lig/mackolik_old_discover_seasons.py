#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arsiv.mackolik.com'daki bir ligin GUNCEL sayfasini acip, sayfadaki sezon
secici / arsiv linklerini tarayarak eski sezonlarin GERCEK sId
degerlerini bulur. Hicbir ID TAHMIN EDILMEZ - sadece sayfanin kendi
icindeki linkler/dropdown okunur.

Bu sadece bir KESIF aracidir - hicbir veri/JSON dosyasi yazmaz, hicbir
mac cekmez. Ciktisi: bulunan (sezon etiketi, sId) eslesmeleri +
mackolik_old_fetch_season.py'nin JOBS listesine eklenebilecek hazir
satirlar.

Kurulum (mackolik_old_fetch_season.py ile ayni):
    pip install playwright beautifulsoup4
    playwright install chromium

Kullanim:
    python mackolik_old_discover_seasons.py <baslangic_url> <league_key>

Ornek:
    python mackolik_old_discover_seasons.py https://arsiv.mackolik.com/Puan-Durumu/s=67205/HOLLANDA-Eerste-Divisie eerste_divisie
"""
import re
import sys
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SID_RE = re.compile(r"sId=(\d+)", re.IGNORECASE)
SEASON_LABEL_RE = re.compile(r"(20)?(\d{2})\s*[-/]\s*(20)?(\d{2,4})")


def find_season_links(html):
    """Sayfadaki TUM <a> ve <option> etiketlerinden sId iceren
    linkleri/degerleri toplar, metniyle birlikte."""
    soup = BeautifulSoup(html, "html.parser")
    found = []

    for a in soup.find_all("a", href=True):
        m = SID_RE.search(a["href"])
        if m:
            found.append((a.get_text(strip=True), int(m.group(1)), a["href"]))

    for opt in soup.find_all("option"):
        val = opt.get("value", "")
        m = SID_RE.search(val)
        if m:
            found.append((opt.get_text(strip=True), int(m.group(1)), val))
        elif val.isdigit():
            # bazi dropdown'larda value dogrudan sId olabilir
            found.append((opt.get_text(strip=True), int(val), val))

    return found


def main():
    if len(sys.argv) < 3:
        print("Kullanim: python mackolik_old_discover_seasons.py <url> <league_key>")
        sys.exit(1)
    start_url = sys.argv[1]
    league_key = sys.argv[2]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="tr-TR",
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()
        print(f"Aciliyor: {start_url}")
        page.goto(start_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(2000)

        # Sayfada "Sezon"/"Season"/arsiv gecmisi acan bir eleman varsa
        # tiklamayi dene (sessizce basarisiz olabilir, sorun degil).
        for label in ["Sezon", "Season", "Arşiv", "Geçmiş Sezonlar", "Diğer Sezonlar"]:
            try:
                page.click(f"text={label}", timeout=3000)
                page.wait_for_timeout(1000)
                print(f"  '{label}' elementine tiklandi.")
            except Exception:
                pass

        html = page.content()
        out_html_path = "mackolik_discover_render.html"
        with open(out_html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Render edilmis HTML kaydedildi: {out_html_path} (otomatik bulma basarisiz olursa buradan elle bakilabilir)")

        browser.close()

    found = find_season_links(html)
    if not found:
        print("\nHICBIR sId linki/degeri bulunamadi.")
        print("Sayfanin yapisi farkli olabilir - mackolik_discover_render.html dosyasini")
        print("acip 'sId=' gecen yerleri elle aramak gerekebilir.")
        return

    # tekrarlananlari temizle, sId'ye gore sirala
    seen = set()
    unique = []
    for label, sid, raw in found:
        if sid in seen:
            continue
        seen.add(sid)
        unique.append((label, sid, raw))
    unique.sort(key=lambda x: x[1])

    print(f"\n{len(unique)} benzersiz sId bulundu:\n")
    for label, sid, raw in unique:
        print(f"  sId={sid:6d}  etiket='{label}'  ({raw})")

    print("\n--- mackolik_old_fetch_season.py JOBS listesine eklenebilecek satirlar ---")
    print("(ETIKETLERI KONTROL ET - hangi sId hangi sezona ait dogru mu bak,")
    print(" sonra season_label'i '02/03' formatina kendin duzenle)")
    for label, sid, raw in unique:
        print(f'    ("{league_key}", "??/??",  {sid}),  # sayfadaki etiket: {label!r}')


if __name__ == "__main__":
    main()
