#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
arsiv.mackolik.com'daki bir ligin GUNCEL sayfasini acip, sayfadaki sezon
secici / arsiv linklerini tarayarak eski sezonlarin GERCEK sId
degerlerini bulur. Hicbir ID TAHMIN EDILMEZ - sadece sayfanin kendi
icindeki linkler/dropdown okunur, ve SADECE etiketi acikca "YYYY/YYYY"
sezon formatina uyanlar alinir (ulke listesi, hafta secici, alt
turnuvalar gibi ALAKASIZ sId'ler otomatik elenir).

Bu sadece bir KESIF aracidir - hicbir veri/JSON dosyasi yazmaz, hicbir
mac cekmez. Ciktisi: bulunan (sezon etiketi, sId) eslesmeleri +
mackolik_old_fetch_season.py'nin JOBS listesine eklenebilecek HAZIR
satirlar (etiket "02/03" formatina script tarafindan cevrilir).

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

# Windows konsolu varsayilan olarak cp1252 kullanabilir - Turkce karakterler
# (I, s, vs.) bu kod sayfasinda yok, bu yuzden print() cokebilir. UTF-8'e
# zorla geciriyoruz (PYTHONIOENCODING=utf-8 unutulsa bile calissin diye).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SID_RE = re.compile(r"sId=(\d+)", re.IGNORECASE)
# SADECE "2006/2007", "1996/97" gibi ACIKCA sezon-yili formatindaki
# etiketleri kabul ediyoruz - ulke adi, "Tweede Divisie", "948" gibi
# hafta-secici sizintilari, "U21 ..." gibi seyler bu kaliba UYMAZ.
SEASON_LABEL_RE = re.compile(r"^(\d{4})\s*/\s*(\d{2,4})$")


def normalize_label(raw_label):
    """'2006/2007' -> '06/07', '1996/1997' -> '96/97'. Uymuyorsa None."""
    m = SEASON_LABEL_RE.match(raw_label.strip())
    if not m:
        return None
    y1 = int(m.group(1))
    y2_raw = m.group(2)
    y2 = int(y2_raw) if len(y2_raw) == 4 else (y1 // 100) * 100 + int(y2_raw)
    if y2 != y1 + 1:
        return None  # ardisik olmayan yil araligi - sezon degil, baska bir sey
    return f"{y1 % 100:02d}/{y2 % 100:02d}", y1


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

    all_found = find_season_links(html)
    if not all_found:
        print("\nHICBIR sId linki/degeri bulunamadi.")
        print("Sayfanin yapisi farkli olabilir - mackolik_discover_render.html dosyasini")
        print("acip 'sId=' gecen yerleri elle aramak gerekebilir.")
        return

    print(f"\n(toplam {len(all_found)} ham sId bulundu, sezon etiketine uymayanlar eleniyor)")

    # sadece "YYYY/YYYY" etiketli, ardisik yilli olanlari al; sId'ye gore
    # tekillestir (ayni sId birden fazla yerde gecebilir).
    by_sid = {}
    for raw_label, sid, raw in all_found:
        norm = normalize_label(raw_label)
        if norm is None:
            continue
        short_label, y1 = norm
        by_sid[sid] = (short_label, y1, raw_label)

    if not by_sid:
        print("\nHICBIR 'YYYY/YYYY' formatinda sezon etiketi bulunamadi.")
        print("mackolik_discover_render.html dosyasini acip sezon secicisine elle bakmak gerekebilir.")
        return

    rows = sorted(by_sid.items(), key=lambda kv: kv[1][1])  # yila gore sirala

    print(f"\n{len(rows)} sezon bulundu:\n")
    for sid, (short_label, y1, raw_label) in rows:
        print(f"  {short_label}  sId={sid:6d}  (sayfadaki etiket: {raw_label!r})")

    print("\n--- mackolik_old_fetch_season.py JOBS listesine eklenebilecek satirlar ---")
    print("(yine de goz gezdir - sId'lerin ardisik/mantikli arttigini dogrula)")
    for sid, (short_label, y1, raw_label) in rows:
        print(f'    ("{league_key}", "{short_label}", {sid}),')


if __name__ == "__main__":
    main()
