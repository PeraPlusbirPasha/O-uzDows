# Masaüstü ve yeni ISO: doğrulama kanıtı

## İmaj kimliği ve indirme

Başarılı PC çalışması: **[44612844625](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44612844625)**.

Her iki ISO içindeki doğrulanmış kaynak commit'i: **`bcd03315873f186ee25f9296afc44356defd0763`**. Bu commit'ten sonraki kanıt aktarma/test ve belge değişiklikleri, yayımlanan ISO'ları değiştirmez. İmajların kaynak kimliğinde `source_dirty: null` vardır: commit eşleşmiştir, fakat derleme sırasında Git çalışma ağacının temizliği belirlenememiştir; `false` olduğu iddia edilmez.

**[v1.0.0 · OğuzDows 1.0 Ay Yıldız](https://github.com/PeraPlusbirPasha/O-uzDows/releases/tag/v1.0.0)** herkese açık, taslak/ön sürüm olmayan yayındır. Etiket yukarıdaki ISO kaynak commit'ini gösterir; varsayılan dala veya daha yeni bir ürün derlemesine işaret etmez.

- **[OguzDows-amd64.iso](https://github.com/PeraPlusbirPasha/O-uzDows/releases/download/v1.0.0/OguzDows-amd64.iso)**: **1.739.718.656 bayt**, 64 bit PC; BIOS ve 64 bit UEFI hedef sistem açılışı geçti.
- **[OguzDows-i386.iso](https://github.com/PeraPlusbirPasha/O-uzDows/releases/download/v1.0.0/OguzDows-i386.iso)**: **1.406.533.632 bayt**, i686/PAE PC; BIOS hedef sistem açılışı geçti.

ISO dosyalarının gerçek SHA-256 özetleri:

```text
78ccb2e231fe1e9e926b1efa2a7d5d597384566ead61882d6e5bc895305cba09  OguzDows-amd64.iso
83b68fc2f077796ae27a43ff5dcc8055b2fb08f816a6fe99b8c9c6f4fa909068  OguzDows-i386.iso
```

**[44635045726 aktarım çalışması](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44635045726)** aynı başarılı derlemenin dosyalarını GitHub içinde indirdi, özgün `.iso.sha256` dosyalarıyla karşılaştırdı ve mevcut taslağa aktardı; **yeni ISO üretmedi, yeniden paketlemedi, iş iptal etmedi**. Aktarıcı kaynak commit'i `4200589409e4738192e5618694a413060e783a01` ISO kaynak commit'inden ayrıdır. Yayın açılmadan ve açıldıktan sonra sekiz dosyanın tamamının boyutu/SHA-256'sı GitHub sunucu `digest` alanıyla da eşleştirildi. Oturumsuz yayın sayfası HTTP 200, iki ISO ve checksum indirme uçları HTTPS dosya bağlantısına HTTP 302 döndürdü.

Release ayrıca **[SHA256SUMS](https://github.com/PeraPlusbirPasha/O-uzDows/releases/download/v1.0.0/SHA256SUMS)**, ayrı `.iso.sha256` dosyaları, iki özgün RAM raporu ve **[release-manifest.json](https://github.com/PeraPlusbirPasha/O-uzDows/releases/download/v1.0.0/release-manifest.json)** içerir; Actions'ın 7 günlük saklama sınırına bağlı değildir. İlgili dizinde `sha256sum -c OguzDows-amd64.iso.sha256` (veya i386 karşılığı) ile bütünlüğü denetleyin. SHA-256 bütünlük kontrolüdür; ayrıca imzalı yayın, Secure Boot veya 32 bit UEFI uyumluluğu iddiası değildir.

Özgün Actions arşivleri ([amd64](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44612844625/artifacts/14575205541), [i386](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44612844625/artifacts/14575475784)) yalnızca ek derleme kökeni bağlantılarıdır; oturum gerekebilir ve 7 gün sonra sona erebilir.

## 600 MB: gerçek tam Xfce oturumu ölçümü

Bu tablo bir bileşenin RSS'i veya yalnızca systemd/GRUB sonucu değildir. Üretilen ISO'nun kendi squashfs'inden hazırlanan özel test diskinde gerçek çekirdek, initramfs, systemd, LightDM ve hedef kullanıcının **tam Xfce oturumu** açılmıştır.

Koşullar: ağsız QEMU/TCG, **2 GiB RAM, 2 sanal CPU, std VGA**; varsayılan OğuzDows/Xfce, compositor kapalı. Rehber/Rıfkı/mağaza/güncelleyici kapalı; geçici test hesabı ve otomatik giriş yalnızca test diskindedir, ISO'ya eklenmemiştir. **120 saniye yerleşme + 5 saniye aralıklı 6 örnek**. Yöntem: **`MemTotal − MemAvailable`**; decimal **MB**, MiB değil.

| İmaj | Medyan kullanım | En yüksek örnek | Geçerli boşta ölçüm | 600 MB hedefi |
| --- | ---: | ---: | --- | --- |
| amd64 / trixie | 459,0 MB | 459,0 MB | Evet | Geçti |
| i386 / bookworm | 518,8 MB | 518,8 MB | Evet | Geçti |

Her iki raporda `valid_idle_measurement: true`, `target_met: true`, `invalid_reasons: []` bulunur. Ham en yüksek değerler amd64'te **458.956.800 bayt**, i386'de **518.795.264 bayt**; örnekleme boyunca CPU meşguliyeti sırasıyla **%2,08** ve **%1,63**. Her altı örnekte hedef UID 1000'in `xfce4-session`, `xfwm4`, `xfce4-panel`, `xfdesktop` süreçleri görülmüş, bilinen açık uygulama/paket işi listesi boş kalmıştır. CPU sayaçlarından hesaplanan oran ve örneklerin en yüksek değeri ayrıca kontrol edilmiştir. RSS değerleri toplanmamış, önbellek düşürülmemiş, swap zorlanmamış, zram iki kez çıkarılmamıştır.

Ham ölçümler release'te **[desktop-idle-amd64.json](https://github.com/PeraPlusbirPasha/O-uzDows/releases/download/v1.0.0/desktop-idle-amd64.json)** ve **[desktop-idle-i386.json](https://github.com/PeraPlusbirPasha/O-uzDows/releases/download/v1.0.0/desktop-idle-i386.json)** olarak baytları değişmeden saklanır. Özgün çalışmadaki **`OguzDows-ISO-hedef-test-amd64`** ve **`OguzDows-ISO-hedef-test-i386`** artefaktlarında dosya adı `desktop-idle.json`'dır; hedef sonuçları `target-os-result.json`, çekirdek/systemd seri günlükleri ve GRUB yapılandırması da bu süreli Actions arşivlerindedir. Hedef sonuçları ayrıca release manifestine alınmıştır. Yeniden ölçüm adımları ve yöntem sınırları [bakım rehberindedir](MASAUSTU-VE-BAKIM.md#600-mb-hedef-ve-tekrarlanabilir-ölçüm).

**[44617059166 kanıt aktarımı](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44617059166)**, tamamlanmış çalışmadaki gerçek altı örneği ve CPU sayaçlarını kontrol notlarına aktarmıştır. Bu çalışma yeni ISO veya yeni ölçüm üretmez; yalnızca saklı raporları okur. Asıl `desktop-idle.json` dosyalarının SHA-256'ları (**ISO checksum'u değildir**):

- amd64: `0b1759706f08a6bd816d3bb6afe96d27268df2ab023dbcd980ab9ce6475449b1`
- i386: `b175f522cf83d23730297e50acea2090938ee16226ae957c72f3a18a74ddf2e6`

**Bu sonuçlar yalnızca bu iki sanal test oturumuna aittir.** ASUS veya başka fiziksel PC, Raspberry Pi, farklı ekran kartları ve gerçek KDE/GNOME oturumları için ölçülmüş sonuç veya 600 MB garantisi değildir. Tam Calamares GUI bölümleme/kullanıcı akışı veya şifreli kurulum testi yerine geçmez.

## Diğer geçen kontroller

- bookworm ve trixie: gerçek GTK güncelleyici/mağaza onayı/İmece pencereleri ve beş gerçek xfconf görünümünün uygulanıp geri alınması; küçük kurucu başlatıcısı, Rıfkı duraklatma ve gerçek Calamares'in disk yazmadan açılması.
- **GNOME Software 43.5 ve 48.3:** gerçek başlatıcı + Xfwm altında küçültme, gerçek geri getirme, normal pencere kapatıldıktan sonra açık tam çıkış kontrolü ve açık çıkış isteğinden sonra başlatıcı/D-Bus sahibinin kalmaması. Test özel, servissiz bir system D-Bus kullanır; **PackageKit/Flatpak paket işlemi yapmaz**. Software 48'in `iso-codes` yokluğunda durması giderilmiştir; veri paketi her iki PC imajında açık bağımlılıktır.
- Gerçek Python-APT/APT ile paket kurmadan yükseltme planları; trixie'de ayrıca KDE/GNOME aday ve bağımlılık planları. Bunlar gerçek KDE/GNOME giriş oturumu veya yetkili güncelleme kurulumu kanıtı değildir.
- Güncel Pardus `InRelease` imzası sabit üretim anahtarıyla `gpgv` üzerinden doğrulandı. Parmak izi: `88561F1612B981756C6C9E94026440E60FE45435`; doğrulanan dosyanın SHA-256'sı: `d70e0854680736b18262fab01cfb3e2ec3df473b5ad4d81b4b0c545493649573`. **Kaynak açılmadı, Pardus paketi kurulmadı.** Gelecekteki açma isteği güncel imza/tarih/mimari/pin kontrollerini yeniden geçmelidir.
- Gerçek ISO'da yetkili bakım kodunun root sahipliği/yazma izinleri, varsayılan kapalı Pardus kaynağı, mağazanın otomatik başlangıcının kapalı olması, altı yeni logolu manzaranın hash'leri ve yerel tespih imleci doğrulandı.
- Zorunlu canlı paket temizliği, gerçekten yenilenen initramfs ve UUID'li GRUB menüsü; ISO takılı olmadan amd64 BIOS+UEFI, i386 BIOS hedef OS açılışı geçti. Bu, fiziksel donanım kanıtı değildir.

Süren işler iptal edilmemiş veya yeniden başlatılmamıştır. Başarısız doğrulamaların ardından ayrı yeni çalışmalar açılmış, bu başarılı çalışmanın ISO'ları ayrıca korunmuştur. README bağlantı/görsel, yayın etiketi ve açık PC/Pi test kapsamı kontrolleri de dahil güncel yerel birim/kontrat paketi **250 test, 6 ortam bağımlı atlama** ile geçmiştir; atlanan Calamares/libXcursor kontrolleri için yerel başarı varsayılmaz, ayrı CI kanıtları kullanılır.
