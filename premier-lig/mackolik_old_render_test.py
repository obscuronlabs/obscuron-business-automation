#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Eski sistem sayfasini GERCEK TARAYICI ile (JavaScript calisir halde)
acip, render edilmis HTML'i kaydeder - SALT OKUNUR, hicbir yere yazmaz.

Kurulum (ilk sefer, bir kere):
    pip install playwright
    playwright install chromium

Calistirma:
    python mackolik_old_render_test.py
"""
from playwright.sync_api import sync_playwright

URL = "https://arsiv.mackolik.com/Standings/Default.aspx?sId=6"
OUT = "mackolik_render_edilmis.html"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    # "Haftalik" sekmesine tikla (2. hafta mac sonuclarini gormek icin)
    try:
        page.click("text=Haftalık", timeout=5000)
        page.wait_for_timeout(2000)
    except Exception as e:
        print(f"'Haftalik' sekmesine tiklanamadi (onemli degil, devam): {e}")

    html = page.content()
    browser.close()

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Kaydedildi: {OUT}  ({len(html)} karakter)")
print("Bu dosyayi Claude'a yukle.")
