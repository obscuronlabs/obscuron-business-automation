# Premier Lig - Resmi Gameweek Mac Verisi

La Liga calismasindaki mantigin devami: Excel sablonlarina yazilacak Premier
Lig mac sonuclarini, **resmi gameweek/matchday numarasiyla** (tarihe gore
tahmin etmeden) toplayip dogrulayan pipeline.

## Neden bu kaynak

Daha once denenen kaynaklarda karsilasilan sorunlar:

- **Mackolik** fixture endpoint'i mac asamasinda 502 vermeye basladi.
- **WorldFootball** 403 verdi.
- **football-data.co.uk** CSV'leri sadece tarih iceriyor, resmi gameweek
  bilgisi yok -> ertelenen/one alinan maclar yuzunden kronolojik 38'e bolme
  yanlis sonuc veriyordu (dokumandaki "MAC HAFTAYA YERLESTIRILEMEDI" hatalari).

**openfootball/england** (GitHub) her sezonu ligin kendi resmi
"Matchday N" / "Round N" / "Regular Season - N" basligina gore gruplu
tutuyor. Bir mac ertelenip baska tarihte oynansa bile dosyada hala ait
oldugu orijinal haftanin altinda listeleniyor. Bu, aradigimiz "gameweek
kaynaktan gelsin, tarihten tahmin edilmesin" gereksinimini karsiliyor.

Kaynak: `https://raw.githubusercontent.com/openfootball/england/master/<SEZON>/1-premierleague.txt`

## Calistirma

```bash
python3 premier_test.py
```

- Ham `.txt` dosyalari `cache/` altina indirilir (tekrar calistirmalarda
  ag istegi atilmaz).
- Sonuc `data/premier_lig_maclar_TUM.json` (standart format) ve
  `data/hafta_01.csv .. hafta_38.csv` (her hafta icin, sezonlar 25/26 -> 02/03
  sirasiyla alt alta - Excel blok duzenine hazir) olarak yazilir.

## Dogrulama (Excel'e yazmadan ONCE calisir, hepsi gecmeden veri uretilmez)

1. Her sezon icin tam 380 mac.
2. Hafta numaralari 1..38 aralik disina cikmiyor.
3. Ayni (ev, deplasman) ciftinden duplikasyon yok.
4. Her takim sezon basina tam 38 mac oynuyor.
5. Baska hicbir kaynaga bakmadan sadece maclardan hesaplanan puanla,
   bilinen 3 sampiyonluk sonucu capraz kontrol edilir:
   - 03/04 Arsenal (Invincibles) = 90 puan
   - 15/16 Leicester City = 81 puan
   - 22/23 Manchester City = 89 puan

Su an: **24/24 sezon, 9120/9120 mac, tum kontroller basarili.**

## Su an YAPILMAYAN kisim

- **Excel'e yazma burada yapilmadi.** Bu ortamda (bu repo) La Liga/Premier
  Lig Excel sablonlari yok - onlar kullanicinin kendi bilgisayarinda.
  `data/` altindaki JSON/CSV ciktilari dogrulanmis ve Excel'e yazilmaya
  hazir standart formatta.
- **Takim adi normalizasyonu eksik.** Kaynaktaki takim adlari sezonlar arasi
  tutarli degil (orn. "Manchester United" vs "Manchester United FC",
  "AFC Bournemouth" vs "Bournemouth"). Excel'deki puan durumu asamasinda
  kullanilan (Mackolik kaynakli) TAKIM etiketleriyle birebir eslesmeleri
  icin, Excel sablonlarina erisilen ortamda bir isim eslestirme tablosu
  (`TEAM_NAME_MAP`) eklenmesi gerekiyor - o adimin bu pipeline'in ciktisini
  tuketen tarafta yapilmasi gerekiyor.

## Standart format

```json
{"season": "23/24", "week": 1, "home": "Burnley", "away": "Manchester City", "home_goals": 0, "away_goals": 3}
```
