#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tek bir Mackolik sayfasini indirip HTML olarak kaydeder - SALT OKUNUR,
hicbir yere yazmaz. Amac: sayfanin gercek yapisini gormek.

Calistirma:
    python mackolik_fetch_one.py
"""
import urllib.request

URL = "https://www.mackolik.com/puan-durumu/almanya-bundesliga/2023-2024/6by3h89i2eykc341oz7lv1ddd"
OUT = "mackolik_ornek_sayfa.html"

req = urllib.request.Request(URL, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
    "Referer": "https://www.mackolik.com/",
})
with urllib.request.urlopen(req, timeout=20) as resp:
    html = resp.read().decode("utf-8", errors="replace")

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Kaydedildi: {OUT}  ({len(html)} karakter)")
print("Bu dosyayi Claude'a yukle.")
