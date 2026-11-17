# OğuzDows · Ay Yıldız

**Köklerinden güç alır. Özgürce üretir.**

Türkçe, Xfce tabanlı bir canlı masaüstü ve kurulum ISO’su. Ay-yıldız amblemi, Anadolu kilim geometrisi, al kırmızısı ve turkuaz vurgular; açılış menüsünden masaüstüne kadar aynı OğuzDows kimliğini taşır. Görseller ve pencere teması yerel olarak üretilir; derleme sırasında uzak tema depoları indirilmez.

> Bu depo bir ISO **derleme tarifidir**, hazır veya fiziksel donanımda onaylanmış bir ISO değildir. Üretilen imajı gerçek diske kurmadan önce sanal makinede deneyin ve verilerinizi yedekleyin.

## Neler var?

- **OğuzDows önyükleme menüsü:** normal açılış, güvenli görüntü, düşük bellek ve açılış günlüğü. `amd64` imajı BIOS ve 64 bit UEFI; `i386` imajı klasik BIOS içindir. Normal seçenek 8 saniye sonra başlar.
- **Animasyonlu Plymouth açılışı:** ay-yıldız, OğuzDows yazısı, gerçek önyükleme ilerlemesi ve turkuaz nefes animasyonu. Disk şifresi ve etkileşimli sorular için giriş alanı korunur. Güvenli/düşük bellek açılışında grafik açılış ekranı devre dışıdır.
- **İlk karşılama:** “OğuzDows’u dene”, “OğuzDows’u kur”, “Donanımını tanı”. İlk oturumda açılır; tekrar gösterilmesi seçilebilir. Kurulu sistemde kurulum seçeneği pasiftir. Rehber uygulamalar menüsünden yeniden açılabilir.
- **Türkçe masaüstü:** Q klavye, İstanbul saat dilimi, Türkçe uygulamalar menüsü, kendi pencere/GTK teması, giriş ekranı, duvar kâğıdı ve yerel tarayıcı başlangıç sayfası.
- **OğuzDows kurucusu:** bağımsız Calamares ayarları, Türkçe karşılama, kendi görselleri ve OğuzDows GRUB kimliği. Disk silme seçeneği önceden seçilmez; işlem öncesi onay gerekir.
- **Hafif profil:** 2 GiB ve altında RAM’de veya uyumluluk seçeneğiyle açılınca masaüstü birleştirme efektleri ve GTK animasyonları kapanır. LZ4 zram etkinleştirilir. Masaüstü 3B hızlandırma zorunlu kılmaz.

Kendi ekranlarımızdaki ürün adı OğuzDows’tur. Paket deposu adresleri, derleme araçlarının zorunlu seçenekleri, paket/donanım meta verileri ve üçüncü tarafların lisans, telif ve yasal “hakkında” içerikleri değiştirilmez. Markalama, bunları silmek veya köken bilgilerini yanıltıcı biçimde gizlemek anlamına gelmez.

## Eski cihazlar ve sürücüler

| İmaj | Hedef | Açılış |
| --- | --- | --- |
| `amd64` | 64 bit x86 işlemciler | BIOS + 64 bit UEFI |
| `i386` | i686 / PAE destekli 32 bit işlemciler; tarayıcı için SSE2 gerekir | BIOS |

- Intel, AMD/ATI, Nouveau, VESA/fbdev ve standart Xorg sürücüleri; Intel/AMD mikro kodları; yaygın Intel, Realtek, Atheros, Broadcom ve eski Intel kablosuz firmware paketleri ISO’ya alınır. Paketler taban sürümüne göre ayrılır; yeni firmware adları 32 bit eski sürüme zorla eklenmez.
- **Siyah ekran:** açılışta “OğuzDows - güvenli görüntü” seçeneğini deneyin. `nomodeset`, grafik açılışını kapatma ve hafif profil uygular; ACPI/APIC veya bütün Wi-Fi sürücülerini topluca kapatmaz. Bu seçenekle kurulum yapılırsa uyumluluk parametreleri hedefte `/etc/default/grub.d/60-oguzdows-compat.cfg` dosyasında korunur; kurucu canlı ortama ait `boot=live` parametresini taşımaz.
- **Az RAM:** “OğuzDows - düşük bellek” seçeneği efektleri kapatır, sistemi RAM’e kopyalamaz. Canlı sistem/kurucu için en az 1 GiB RAM ve kurulum için 12 GiB boş alan kontrol edilir; günlük kullanım için **en az 2 GiB RAM önerilir**. Tarayıcı ve ofis uygulamaları daha fazla bellek isteyebilir.
- **Donanım merkezi:** PCI/USB aygıtlarını, kullanılan çekirdek sürücülerini ve kablosuz anahtarlarını gösterir. Raporu yalnızca siz kaydedersiniz; otomatik yükleme/telemetri yoktur.
- **Ek Broadcom STA:** yalnızca izin listesindeki uyumlu bir PCI aygıtı algılanırsa sunulur. İnternet ve yönetici onayı gerekir. Çalışan çekirdeğin **tam sürümüne ait** başlıkları ve DKMS’i kullanır; kendiliğinden kurulmaz. İşlem mevcut açık sürücünün yerini alabilir, yeniden başlatma gerektirir. Günlük: `/var/log/oguzdows/drivers.log` (yönetici erişimi).
- STA’yı geri almak için kurulu sistemde `sudo apt-get purge broadcom-sta-dkms` çalıştırıp yeniden başlatabilirsiniz. Çekirdek başlıkları artık depoda yoksa önce sistem/çekirdek güncellemesi gerekebilir.
- Çok eski Intel PRO/Wireless 2100/2200 aygıtları için ayrı lisans onaylı `firmware-ipw2x00` paketi varsayılan ISO’ya eklenmez. Gerekirse kurulu sistemde `sudo apt-get install firmware-ipw2x00` ile lisansını inceleyerek kurabilirsiniz. Ek sürücü indirmek için kablolu bağlantı veya USB internet paylaşımı gerekebilir.

**Sınırlar:** her eski aygıt için garanti yoktur. PAE’siz işlemciler, 32 bit UEFI, Secure Boot ve artık güncel çekirdeklerle çalışmayan eski kapalı NVIDIA/ATI sürücüleri bu profilin kapsamında değildir. UEFI kurulumda Secure Boot kapalı olmalıdır. Wi-Fi, askıya alma, ses ve 3B hızlandırma gerçek cihazda ayrıca sınanmalıdır.

## ISO derleme

Root erişimi, internet bağlantısı ve yeterli disk alanı olan x86_64 bir `live-build` ortamı kullanın. İki mimarinin çalışma alanları ayrıdır; en az 20 GiB boş alan ayırmanız önerilir.

```sh
sudo apt-get update
sudo apt-get install -y live-build debootstrap squashfs-tools xorriso \
  syslinux syslinux-utils isolinux grub-pc-bin grub-efi-amd64-bin \
  mtools dosfstools python3 ca-certificates

sudo ./build.sh amd64
# veya 32 bit imaj:
sudo ./build.sh i386
```

Çıktılar:

```text
OguzDows-amd64.iso
OguzDows-amd64.iso.sha256
OguzDows-i386.iso
OguzDows-i386.iso.sha256
```

Derleme sonunda ISO içindeki BIOS/UEFI seçimleri, çekirdek/initrd yolları, ürün kimliği ve istenmeyen varsayılan menü artıkları denetlenir. Bu kontrol bir açılış testi değildir. `sha256sum -c OguzDows-amd64.iso.sha256` ile imaj bütünlüğünü kontrol edebilirsiniz.

### Yalnızca yapılandırmayı inceleme

`live-build` kuruluysa root veya paket indirmesi olmadan:

```sh
./build.sh amd64 --configure-only
```

`live-build` bile gerektirmeyen, tamamen çevrimdışı hazırlama:

```sh
python3 scripts/configure.py --arch i386 --output /tmp/oguzdows-i386-config
```

Bu komutlar **ISO oluşturmaz**. Gerçek derlemeyi daha sonra temiz bir çalışma alanında başlatın.

### Önceki derlemeyi temizleme

Betik mevcut `build-amd64/` veya `build-i386/` dizinini otomatik silmez. İlgili dizinde önce `sudo lb clean --purge` çalıştırın. Altında bağlı chroot/dosya sistemi kalmadığını doğruladıktan sonra çalışma dizinini kendiniz kaldırın. Bağlı chroot üzerinde `rm -rf` kullanmayın. Başarısız derlemenin ayrıntıları ilgili çalışma dizinindeki `build.log` dosyasındadır.

## Güvenlik ve kurulum davranışı

Canlı oturum: **`oguz` / `oguz`**, otomatik giriş ve parolasız yönetici yetkisi **yalnızca canlı ortamda**. `oguz` adı kurucuda canlı kullanıcı için ayrılmıştır.

Kurulum sırasında hedefteki canlı kullanıcı kaldırılır; canlı oturum servisi, otomatik giriş ayarları ve parolasız sudo kuralı temizlenir. Yeni kullanıcı ve parolası kurucuda belirlenir; kurulu sistem her açılışta bir canlı kullanıcı oluşturmaz. `root` hesabı kilitlidir; yönetim yeni kullanıcının `sudo` yetkisiyle yapılır. Kurucu ve ek sürücü işlemleri açık yönetici onayı isteyen, sabit görevli PolicyKit yardımcıları kullanır.

Canlı oturumdaki değişiklikler, kalıcılık ayrıca ayarlanmadıkça yeniden başlatmada kaybolur. Donanım sürücülerini kalıcı kullanmak için kurulu sistemde işlem yapın.

## Testler

```sh
sudo apt-get install -y python3-pil python3-yaml fonts-dejavu-core shellcheck
python3 -m unittest discover -s tests -p 'test_*.py' -v
shellcheck build.sh hooks/* system/usr/lib/oguzdows/*.sh \
  system/usr/local/bin/* system/usr/local/sbin/oguzdows-installer

# Yalnızca görselleri önizleme dizinine üret; sisteme kurmaz:
python3 scripts/render-assets.py --root preview
```

Testler iki mimarinin paket ayrımını, ilk açılış/kurulum temizliğini, dar yetkili sürücü yardımcısını, gerçek ilerleme geri çağrılarını, BIOS/UEFI menülerini, XML/YAML/JSON dosyalarını ve yerel tema üretimini kontrol eder. `--configure-only` akışı sahte bir `lb` ile sınanır; testler gerçek disklere veya paket yöneticisine yazmaz.

GitHub Actions ayrıca iki taban sürümünde **gerçek GTK penceresini Xvfb ile açar**, küçük ekranı ve donanım sekmesini kontrol eder; ekran görüntülerini artefakt olarak saklar. PR’larda testler, `main` güncellemesinde veya elle çalıştırmada testlerden sonra iki ISO derlemesi çalışır. `.github/workflows/main.yml` etkin iş akışıdır; kökteki `build.yml` eş kopyasıdır.

### Yayın öncesi elle kontrol

- [ ] `amd64`: BIOS ve OVMF/UEFI ile menü → animasyon → Türkçe masaüstü.
- [ ] `i386`: PAE/SSE2 destekli CPU ile BIOS açılışı.
- [ ] Güvenli görüntü ve düşük bellek seçenekleri; ağ, ses ve uyku/uyanma.
- [ ] Karşılama ekranındaki üç işlem; kapatınca tekrar açılmama ve “yeniden göster” tercihi.
- [ ] Boş **sanal diske** çevrimdışı kurulum; yeniden başlatınca OğuzDows GRUB adı.
- [ ] Kurulu sistemde canlı `oguz` kullanıcısı, parolasız sudo ve zorunlu otomatik giriş kalmaması.
- [ ] Şifreli kurulum seçilirse soğuk açılışta parola istemi ve kilit açma.
- [ ] Hedef eski fiziksel cihazlarda görüntü/Wi-Fi/USB/firmware doğrulaması.

Klasik BIOS menüsünde ROM yazı tipi sınırlaması nedeniyle seçim metinleri Türkçenin ASCII karşılıklarıdır; resimdeki OğuzDows başlığı, UEFI, karşılama ve masaüstü Türkçe karakterlidir.

## Kaynak düzeni

- `build.sh`: mimari seçimi ve ISO derleme akışı.
- `packages/`: ortak, taban sürümüne ve mimariye özel paketler.
- `system/`: canlı/kurulu sisteme eklenen dosyalar, karşılama ve sürücü merkezi.
- `installer/`: OğuzDows Calamares ayarları ve markalama.
- `boot/`: Plymouth teması ve animasyonu.
- `assets/`, `scripts/render-assets.py`: vektör kimliği ve çevrimdışı görsel üretimi.
- `scripts/configure-boot.py`, `scripts/verify-iso.py`: ISO menüsü oluşturma ve doğrulama.
- `hooks/`: markalama, görseller, servisler ve son ISO menüsü kancaları.
- `tests/`: izole birim/kontrat testleri ve gerçek GTK smoke testi.
