# Benzer Oran Bülteni

Aynı ligde oranları benzer olan geçmiş maçlara bakarak gelecek maçlar için her pazarın tahmini ihtimalini ve adil oranını gösteren sayfa.

- Veri: [football-data.co.uk](https://www.football-data.co.uk) (ücretsiz). Son 3 sezon + içinde bulunulan sezon, 22 lig.
- GitHub Actions veriyi **her 4 saatte bir** kendiliğinden indirir ve sayfayı yeniler. Sayfadaki **Güncelle** tuşu en son veriyi getirir.
- Adil oranlar motorun tahminidir, bahis şirketi oranı değildir. Gerçek oran yalnızca MS 1/X/2 ve 2,5 Alt/Üst için vardır (Bet365).

## Kurulum (bir kerelik)

1. GitHub'da **New repository** → ad: `benzer-oran` → **Public** → **Create repository**.
2. **Settings → Pages → Build and deployment → Source: GitHub Actions** seçin.
3. Bu klasördeki dosyaları depoya ekleyin: `index.html`, `guncelle.py`, `README.md` ve `.github/workflows/guncelle.yml`.
   - Web'den eklerken iş akışı dosyası için **Add file → Create new file** deyip adına `.github/workflows/guncelle.yml` yazın ve içeriği yapıştırın.
4. **Actions** sekmesinde **Verileri güncelle** iş akışı çalışır (çalışmazsa **Run workflow**). 1–2 dakika sonra sayfa açılır:
   `https://KULLANICI-ADINIZ.github.io/benzer-oran/`
5. iPhone'da Safari ile açıp **Paylaş → Ana Ekrana Ekle** diyebilirsiniz.

## Bilinmesi gerekenler

- Depo herkese açık olduğu için sayfa da bağlantıyı bilen herkese açıktır.
- GitHub, 60 gün hiç işlem görmeyen depolarda zamanlanmış iş akışlarını durdurur ve e-posta atar; e-postadaki bağlantıyla tek tıkla yeniden açılır.
- football-data.co.uk gelecek maçların oranlarını hafta sonu için Cuma, hafta içi için Salı öğleden sonra yayınlar.
