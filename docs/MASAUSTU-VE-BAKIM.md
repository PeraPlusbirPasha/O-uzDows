# OğuzDows · Masaüstü ve bakım

## Bu sürümün kapsamı

Çalışan Calamares mount / hedef / initramfs / GRUB zinciri değiştirilmez. Yeni özellikler varsayılan Xfce üzerine eklenir. PC: **amd64 → trixie, i386 → bookworm**. ISO kaynak kimliği yine `build-info.json` içindedir. Daha önce kurulmuş sisteme bu kaynak değişiklikleri kendiliğinden taşınmaz; Güncelleyici dağıtımın Git deposunu indirip root olarak çalıştırmaz.

Pi, PC bakım yardımcısını, Pardus kaynağını ve mağaza paketlerini almaz. Yeni görseller, yerel tespih imleci, beş Xfce görünümü ve çevrimdışı İmece araçları ortaktır. ARMv6 / eski Pi / i386 üzerinde Flathub veya gerçek KDE/GNOME kullanılabilirliği varsayılmaz. Bu değişiklik yeni bir fiziksel Pi performans doğrulaması değildir.

## OğuzDows Güncelleyici

Menüden **OğuzDows Güncelleyici** veya Rehber → **Güncelleyici ve Mağaza**:

1. **Paket listelerini yenile**: ağ ve yönetici onayı ister; imzasız / eksik depo güncellemesi başarı sayılmaz.
2. **İşlem planını göster**: kurulacak/yükseltilecek paket adları ve sürümleri; ayrıca özgün dilinde APT teknik çıktısı. Bu adım paket kurmaz.
3. **Planı onayla ve uygula**: açık kullanıcı onayı ve Polkit yönetici doğrulaması. Aday listesi, sürümler ve plan özeti tekrar denetlenir; değişen plan yeniden onay ister.

Sabit görevler dışında paket adı, shell komutu, dosya yolu, dağıtım yükseltmesi veya kaldırma isteği alınmaz. `--no-remove`, imza denetimi, taban sürümü ve mimari denetimi korunur; downgrade / held paket zorlama / `dist-upgrade` yoktur. Yeni bağımlılıklar gerekirse normal `upgrade --with-new-pkgs` içinde görülebilir. Başka bir OğuzDows bakım işi veya APT liste yenilemesiyle çakışma kilitle reddedilir; APT/dpkg'nin kendi kilitleri silinmez. Başka paket yöneticilerini işlem bitene kadar kapalı tutun.

Yardımcı `/usr/local/sbin/oguzdows-maintenance`, izole Python ve dar argüman doğrulamasıyla çalışır. Yetkili kod, üst dizinler, anahtar, pin ve Polkit dosyaları derlemede root sahipli / kullanıcıya yazılamaz yapılır; gerçek ISO kontrolü de bunu denetler. GUI root değildir. Canlı USB'de kalıcı kurulum / kanal açma reddedilir; disk oturumuna geçilir. APT işleminde bilgisayarı kapatmayın. Günlük: **`/var/log/oguzdows/updater.log`**, yalnızca yönetici okuyabilir. Bir güncelleme hatası otomatik disk onarımı veya paket kaldırma başlatmaz.

### Sürücüler

İsteğe bağlı tarama, PCI/USB üreticisi ve aygıt sınıfını yerleşik firmware paketleriyle eşleştirir. Kurulu firmware ayrıca belirtilir; çekirdek sürücü bağı bulunamayan aygıt işaretlenir. **Bu bir firmware önerisidir; arızanın nedeni veya eksik sürücünün kesin tanısı değildir.** Birçok firmware zaten ISO'dadır; o durumda plan boş olabilir. Çalışan modül sökülmez. Yeni ayrıştırılmış firmware paketleri bookworm'da karşılıklarıyla eşleştirilir.

Eski Broadcom STA ve Intel 2100/2200/2915 için mevcut lisans, donanım ve başlık kontrolleri olan çevrimdışı rehber korunur. NVIDIA'nın rastgele/eski kapalı çekirdek modülleri kurulmaz. Ubuntu/Kali/Mint çekirdek veya libc paketleri sistem depolarına karıştırılmaz.

## Mağaza: GNOME Yazılımlar + Flatpak

PC imajında **GNOME Software**, Flatpak eklentisi, PackageKit ve GTK portalı bulunur. Snap eklenmez. Menüde **OğuzDows Mağaza**:

- Sistem (APT) uygulamaları hemen kullanılabilir.
- İlk açılışta Flathub ayrıca sorulur; yalnızca **x86_64** Flatpak mimarisinde bu sürümün otomatik kurulumu sunulur. i386'de APT mağazası kullanılabilir; Flathub'daki her uygulamanın 32-bit sürümü varmış gibi davranılmaz.
- Kaynak yalnızca kullanıcının hesabına, resmî **`https://dl.flathub.org/repo/flathub.flatpakrepo`** tanımından eklenir. GPG denetimi kapatılmaz. Bu ilk anahtar edinimi HTTPS'e dayanır; ayrıca bağımsız bir anahtar doğrulaması olduğu iddia edilmez. Flathub adıyla farklı / imzasız bir kaynak varsa sessizce değiştirilmez.
- **Güncelleyici → Flatpak uygulama güncellemelerini mağazada göster** hem kullanıcı hem sistem kapsamındaki Flatpak'lar için GNOME Yazılımlar'ın Güncellemeler sayfasını açar. Oradaki işlem/onay akışı kullanılır. APT planı ile Flatpak işlemi aynı şey değildir.
- **Depolar ve Mağaza → Flathub kaynağını kur / denetle** ile ilk tercih yeniden açılabilir.
- Mağazanın XDG otomatik başlangıcı bastırılır; otomatik güncelleme indirme varsayılan kapalıdır. Mağaza/PackageKit/portal kullanıcı açtığında veya bir uygulama istediğinde çalışabilir.
- OğuzDows başlatıcısı, varsayılan Xfce/X11'de mağaza pencerelerini **olay tabanlı** izler. Son mağaza penceresi kapanınca sessiz bir servis bırakmak yerine **açık tam çıkış kontrolünü** gösterir. Küçültme / çalışma alanı değişimi kapatma sayılmaz. Sırf pencere gizlendi diye indirme/kurulum iptal edilmez.
- Mağazada bütün işlemlerin bittiğini kontrol ettikten sonra **İşlemler bitti · Mağazayı tamamen kapat** düğmesini kullanın. GNOME Yazılımlar'ın kendi **`--quit`** iptal/temizleme protokolü çağrılır; süreç SIGTERM/SIGKILL ile öldürülmez. **Bu komut iptal edilebilir aktif işleri durdurabilir**; işlerin tamamlandığını kullanıcı doğrulamalıdır. Kontrol penceresinin X düğmesi de ayrıca sorar, varsayılan yanıt Vazgeç'tir. Komut satırında `oguzdows-store --quit` aynı açık tam çıkış isteğidir.
- Wayland veya EWMH pencere bilgisi olmayan oturumda aynı tam çıkış kontrolü baştan görünür. Bu küçük denetleyici yalnızca mağaza kullanılırken vardır; açılış servisi değildir. Yukarıdaki ömür yönetimi OğuzDows başlatıcısıyla açılan mağaza içindir; başka programın doğrudan başlattığı upstream mağaza/PackageKit servisinin bütün davranışlarını değiştirmez.
- Açılmış mağazanın süreç tüketimi boşta temiz Xfce ölçümüyle karıştırılmaz; pencere kapalıyken süreç kaldıysa bellek raporu bunu gösterir. CI, gerçek mağazada küçültmenin ve normal pencere kapanışının otomatik iş iptal etmediğini; **açık tam çıkış isteğinden sonra** hem başlatıcının hem GNOME Yazılımlar D-Bus sahibinin çıktığını ayrıca sınar. Bu ömür testi paket kurmaz ve işlem sırasında kapanışın fiziksel doğrulaması değildir.

Uygulamayı kurmadan önce geliştiricisini, kaynağını, lisansını ve dosya/cihaz izinlerini inceleyin. Flatpak, her uygulamanın zararsız veya her iznin dar olduğu garantisi değildir.

## Kontrollü Pardus 25 kanalı

**Varsayılan kapalı, yalnızca amd64 / trixie.** `/pardus yirmibes main` uygulama kanalı kullanılır; Pardus'un `yirmibes-deb` tabanı veya güvenlik/çekirdek havuzu eklenmez. Şimdiki açık izin listesi:

- `pardus-image-writer`
- `pardus-night-light`
- `pardus-pen`

APT pin dosyası bu uygulamaları 100, diğer Pardus paketlerini **−1** yapar. Böylece bir uygulamanın Pardus'a özel başka bağımlılığı varsa otomatik zorlanmak yerine çözümsüz plan/hata olarak kalır. Güncelleyici, her değişen paketin gerçek aday sürümünü, mimarisini ve güvenilir APT Origin/Codename alanını ayrıca doğrular. Temel paketler yalnızca kendi Debian tabanının aynı sürüm / updates / security kanallarından kabul edilir. Teknik depo kökeni saklanmaz; ürün adı yine OğuzDows'tur.

**Etkinleştirme sırası:** uygun taban → sabit anahtar SHA-256 → eksiksiz/aynı pin dosyası → güncel `InRelease` dosyasının **gpgv ile gerçek imza denetimi** → Pardus/yirmibes/amd64 kimliği ve tarih → atomik kaynak açma. Adımlardan biri başarısızsa kanal açılmaz. Sırf bir anahtar dosyası var diye güvenilmez; anahtar sunucusundan veya rastgele adresten anahtar indirilmez. HTTPS'ten HTTP'ye düşüş reddedilir. `Valid-Until-Max` ve ön kontrolde 90 günlük azami tarih kullanılır; saat yanlışsa kanal hata verebilir. Kanalı kapatmak kurulu uygulamaları silmez ve kayıp anahtar/pin yüzünden kapatma engellenmez.

Paketlerin karşılıklı çalışması tek başına imza/ortak tabandan garanti edilemez. Plan gösterilir, paket kaldırma reddedilir; gerçek uygulama/donanım testi yine gerekir. İmzalı bir üçüncü taraf paketinin bakım betikleri root olarak çalışabilir. Bu nedenle izin listesi dar, kanal isteğe bağlıdır. Kullanıcının root ile elle eklediği başka kaynaklar/öncelik değişiklikleri bu tarifin dışındadır.

### Pardus anahtarının açık kökeni

- Kaynak: [Pardus-Kurumsal/pardus-archive-keyring](https://github.com/Pardus-Kurumsal/pardus-archive-keyring/tree/d28a52a8a5c502adb02bf72a825815ccff6c4d2c), `active-keys/index` tarafından seçilen **`add-pardus-new-public-key`**. Eski development/testing anahtarı alınmaz.
- Birincil parmak izi: **`88561F1612B981756C6C9E94026440E60FE45435`**.
- Paketlenen ASCII anahtarın SHA-256'sı: **`7e0f0db2d7ef3aea57bb41469286061a050a184fbfd6f6fee8fb946d78af686e`**.
- Tarihsel kaynağın varlığı, güncel deponun doğrulandığı diye sunulmaz. Kanal açılırken ve isteğe bağlı CI ağ kontrolünde güncel imza gerçekten sınanır. Anahtar değişirse elle yeni anahtar kabul edilmez; kaynak/fingerprint incelemesi ve yeni imaj gerekir. Sabitlenen resmî GitHub kaynak kimliği başlangıç güven dayanağıdır; ayrı fiziksel/bağımsız bir anahtar teslim töreni yapılmış değildir.
- Üst kaynak `debian/copyright`, anahtarların telif kapsamına girmediğini belirtir. O dosyadaki destek betikleri buraya kopyalanmaz; üçüncü tarafların teknik/yasal kökeni silinmez.

Kaynak/pin/anahtar yolları: `/etc/apt/sources.list.d/oguzdows-pardus.sources`, `/etc/apt/preferences.d/oguzdows-pardus`, `/usr/share/keyrings/oguzdows-pardus.asc`.

## Beş hafif tarz; ayrıca gerçek masaüstleri

Rehber → **Tarzlar**: **OğuzDows, KDE tarzı, GNOME tarzı, Klasik Xfce, Mac esintisi**. Bunlar Xfce panel yerleşimi/boyutu, GTK/pencere teması ve düğme konumlarını değiştirir. Şeffaf dock, ek kabuk veya resident görünüm süreci çalışmaz. İlk değişiklikten önce ayarlar `~/.local/state/oguzdows/profiles/before-first-change.json` içinde saklanır; **İlk görünüm ayarlarıma dön** düğmesi vardır. Hata olursa eldeki önceki değerler geri alınmaya çalışılır. Duvar kâğıdı, dosyalar, ağ, disk, güç eylemleri değiştirilmez.

**Gerçek KDE Plasma / GNOME** ayrıca, amd64'te Güncelleyici paket planından kurulabilir. Xfce varsayılan kalır; LightDM değiştirilmez. X11 oturum dosyaları için `kwin-x11` ve `gnome-session-xsession` açıkça istenir. Oturumu kapatıp giriş ekranının oturum seçicisinden yeni masaüstünü seçin. İnternet, daha fazla disk/RAM ve uygun grafik sürücüsü gerekir. Eski cihazlarda görünüm tarzlarını tercih edin. **600 MB hedefi gerçek KDE/GNOME için geçerli değildir.**

## Yerel hareketli tespih imleci

**OğuzDows Tespih** Xcursor teması 24/32/48 piksel boyutlarında derleme sırasında üretilir. Normal/bağlantı/bekleme imlecinde 10 kare, sabit tıklama noktası; yazı imlecinde sabit kare ve diğer roller için Adwaita mirası vardır. Taneler ilmek üzerinde ilerler, ilmek hafifçe sallanır ve tane vurgusu dolaşır; ok ucu ve tıklama noktası sabittir. Hareket yerel imleç altyapısındadır; Python animasyon süreci, masaüstü katmanı veya global tıklama dinleyicisi yoktur. Xcursor'un sağlayamadığı “her tıklamaya küresel tepki” iddia edilmez. Fare/Görünüm ayarlarından Adwaita'ya dönülebilir. “Resident süreç yok” sıfır X sunucusu maliyeti demek değildir; küçük kare verileri ve yerel imleç animasyonu vardır.

## İmece: dört küçük araç

Menü → **İmece · OğuzDows Araçları**. İstenmeden çalışmaz; pencere kapanınca süreç/zamanlayıcı kalmaz.

1. **Çay Molası:** kullanıcı başlatırsa 25 dakika odak / 5 dakika mola; bildirim ve sayaç. Kapatınca durur. Sağlık/tedavi iddiası yoktur.
2. **Türkçe Hızlı Yazım:** I/ı ve İ/i ayrımını koruyan büyük/küçük harf, Türkçe harf düğmeleri, kibar ileti şablonu ve kullanıcının bastığı kopyalama. Genel klavye veya pano dinlemez.
3. **Heybe:** seçilmiş görünür ev klasörünün, tercihen başka diske `.tar.gz` yedeği + SHA-256. Kaynak silinmez; otomatik geri yükleme/üzerine yazma yoktur. Gizli dosyalar, bilinen anahtar dizinleri, sembolik bağlantılar ve alt bağlama noktaları dışlanır. Aynı kaynak içine yedek konulmaz; 2 GiB / 100.000 dosya sınırı vardır. Aynı diskte kopya disk arızasına karşı yedek değildir.
4. **İmece Paketi:** seçilmiş en fazla 100 görünür dosya için ZIP + dosya başına SHA-256 manifesti ve dış doğrulama dosyası. 2 GiB sınırı, aynı adları reddetme ve taşınabilir güvenli arşiv adları. Sunucu/port açılmaz; hiçbir yere otomatik gönderilmez. USB veya seçtiğin yöntemle paketi sen taşırsın.

Arşivler 0600 izinle, yeni benzersiz adla oluşturulur. Dosyalar okunurken bağlantı değişiklikleri ve normal dosya türü kontrol edilir. **Şifreleme yoktur; dosya içeriği için sır/kişisel veri tarayıcısı değildir.** Paylaşmadan önce içeriği kontrol edin, hassas yedeği şifreli bir ortamda tutun. SHA-256 bozulmayı saptamaya yarar; tek başına gönderenin kimliğini doğrulamaz. Başarısız işlemde kaynak dosya değiştirilmez; eksik yeni arşiv kaldırılır.

## 600 MB: hedef ve tekrarlanabilir ölçüm

Varsayılan Xfce'de compositor ve GTK animasyonları kapalı; zram LZ4 kalır. Rıfkı isteğe bağlı, galeri tembel yüklenir; yeni güncelleyici/mağaza/İmece açılış servisi eklemez. Ağ, yetkilendirme, disk veya güvenlik servisleri RAM puanı için kapatılmaz.

**600 MB = 600.000.000 bayt hedefidir; bütün cihazlarda ölçülmüş/garanti edilmiş bir sonuç değildir.** Bir GTK bileşeninin RSS'i veya systemd'nin tek başına açılması tam masaüstü RAM'i değildir. Sanal makine ölçümü de ASUS / diğer fiziksel PC / Pi sonucu değildir.

Tekrarlama:

1. Kurulu sistemde varsayılan OğuzDows Xfce oturumunu aç; Rehber, Rıfkı, tarayıcı, mağaza, Güncelleyici ve İmece'yi kapat. Güncellemelerin bitmesini bekle. Harici programları kapattığını kendin doğrula.
2. Tercihen ayrı bir sanal konsoldan aynı kullanıcıyla (grafik oturumu açık kalırken), aksi halde terminalin ek maliyetini de not ederek:

   ```sh
   oguzdows-memory-report --idle-confirmed --output "$HOME/oguzdows-bosta-ram.json"
   ```

3. Araç **120 saniye yerleşme + 5 saniye aralıklı 6 örnek** alır. `MemTotal − MemAvailable` kullanır, decimal MB ve MiB'yi ayırır; CPU sakinliği, tam Xfce süreçleri, bilinen açık uygulamalar ve örnek kararlılığını kontrol eder. Sadece anlık ölçüm için Güncelleyici'de ayrı düğme vardır; o düğme hedefe ulaşıldığını kanıtlamaz.
4. JSON'da `valid_idle_measurement` ve nedenleri, medyan/en yüksek kullanım, `target_met`, zram'ın gerçek ayrılan RAM'i ve tanı için süreç RSS'leri bulunur. `target_met`, ancak uygun koşullardaki **bütün örnekler** hedefin altındaysa true olur. CPU/süreç kontrolleri bilinmeyen her uygulamanın kapalı olduğunun matematiksel kanıtı değildir; operatör doğrulaması da gerekir.

Önbellek düşürme, swap zorlayarak sayı küçültme, zram'ı RAM'den iki kez çıkarma veya RSS toplamını fiziksel RAM diye sunma yoktur. Ölçüm aracının kendi yükü de sistem toplamına dahildir.

CI, `smoke-iso-target.py --graphical-idle` ile ISO içeriğinden hazırlanan **yalnızca geçici test diskinde** parola ile girişi kilitli, ağsız bir test hesabı ve LightDM otomatik girişi kurar. Ağsız, 2 GiB RAM / 2 sanal CPU / std VGA QEMU'da gerçek Xfce oturumu açılır; aynı ölçüm `desktop-idle.json` ve serial kanıtına yazılır. Bu test hesabı/otomatik giriş **ISO'ya veya kullanıcının kurulumuna eklenmez**. Grafik oturumunun açılması zorunludur; 600 MB aşılırsa veya ölçüm sakin değilse uyarı ve gerçek sayı raporlanır, “hedef geçti” diye etiketlenmez. Tam Calamares GUI kullanıcı/bölümleme testi veya fiziksel cihaz kanıtı değildir.

## Görseller ve ses kapsamı

Önceki altı çizim emekli edilmiştir; altı manzaranın da içeriği yenilenmiştir. **Boğaz Sabahı, Kaçkar Sisi, Kapadokya Işığı, Ölüdeniz Kıyısı, Tuz Gölü Akşamı, Ani Kışı**: her birinin sağ altında ay-yıldız + OğuzDows işareti. 1920×1080 JPEG, ayrı 320×180 önizleme; varsayılan Boğaz. Eski `wallpaper.png` yolu uyumluluk için aynı yeni manzarayı içerir. Eski çizim seçimleri bir defa yeni karşılıklarına geçirilir, yeni geçerli seçim her girişte sıfırlanmaz.

Görseller bu proje için **yapay zekâyla üretilmiştir, gerçek kamera fotoğrafları veya birebir coğrafi belge değildir**. `artwork/landscapes.json` özgün kaynak ve paketlenen çıktı özetlerini tutar. Paketlenen JPEG'e her derlemede tekrar logo basılmaz. `scripts/prepare-landscapes.py` ayrı geliştirme aracıdır.

Rıfkı'nın doğal Türkçe ses karakteri korunur; değişen manzara açıklamaları yenilenir ve Tarzlar kaydı eklenir. **18 tam metin eşlemesi + sabit sonuç kayıtları** vardır. Yapay zekâ konuşma kaydıdır, gerçek bir insanın stüdyo kaydı değildir. Pi'ye özgü açıklamalar, yeni Güncelleyici/Mağaza/İmece pencereleri ve değişken hata/donanım ayrıntıları henüz bütünüyle seslendirilmez. “Bütün paneller tamamlandı” iddiası yoktur; robotik çalışma-zamanı sese düşülmez.
