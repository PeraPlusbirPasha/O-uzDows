# Kali / Linux Mint incelemesi ve OğuzDows kurulum denetimi

## Kapsam ve sınır

Resmî ISO **derleme tarifleri ve kurucu kaynak kodları** incelendi; Kali/Mint'in çok gigabaytlık yayın ISO'ları bu inceleme için indirilip fiziksel diske kurulmadı. Son iki cihaz fotoğrafı alındı: birinde GRUB `/boot/grub` aygıtını bulamıyor, diğerinde isteğe bağlı Broadcom komutu kurulumu durduruyor. Hata aşamaları artık biliniyor; kullanılan ISO'nun kaynak kimliği, tam günlük ve disk düzeni henüz bilinmiyor. Kaynak / CI bulgusu ile bu belirli USB'nin kimliği ayrı tutulur.

Önceki OğuzDows çalışması `44416448840` (`bc3bace`) ISO üretimi ve o zamanki kontrolleri geçti. Ancak bu kontrollerin disk testi **firmware → GRUB** noktasındaydı; gerçek kurulu çekirdek / initramfs / kullanıcı alanı açılışını sınamıyordu. Bu bir doğrulama boşluğuydu, tam kurulum başarısı değildi.

## İncelenen birincil kaynaklar

- Kali `kali-live`, incelemede görülen kaynak ucu: `adb2e38941662f105b57134e0155ec468da294ad`:
  - [Proje ve Live / Installer ayrımı](https://gitlab.com/kalilinux/build-scripts/kali-live)
  - [`auto/config`](https://gitlab.com/kalilinux/build-scripts/kali-live/-/blob/adb2e38941662f105b57134e0155ec468da294ad/auto/config)
  - [Binary paket listesi / çevrimdışı EFI paketleri](https://gitlab.com/kalilinux/build-scripts/kali-live/-/blob/adb2e38941662f105b57134e0155ec468da294ad/kali-config/common/package-lists/kali.list.binary)
- Linux Mint `live-installer`, kaynak ucu `95c8204f67291fee3eb761e0cea11933faee703b`:
  - [`installer.py`](https://github.com/linuxmint/live-installer/blob/95c8204f67291fee3eb761e0cea11933faee703b/usr/lib/live-installer/installer.py)
  - [`partitioning.py`](https://github.com/linuxmint/live-installer/blob/95c8204f67291fee3eb761e0cea11933faee703b/usr/lib/live-installer/partitioning.py)
- Linux Mint `ubiquity`, kaynak ucu `ed33101dcf0d615efa00014659b489151280a6e6`:
  - [`scripts/install.py`](https://github.com/linuxmint/ubiquity/blob/ed33101dcf0d615efa00014659b489151280a6e6/scripts/install.py)
- GRUB [2.06 `10_linux`](https://github.com/rhboot/grub2/blob/grub-2.06/util/grub.d/10_linux.in) ve [2.12 `10_linux`](https://github.com/rhboot/grub2/blob/grub-2.12/util/grub.d/10_linux.in): `/dev/disk/by-uuid` / `by-partuuid` adlarının yokluğunda `root=` için geçici aygıt adına düşülebilir.
- Calamares, kullandığımız iki tabanla ilişkili `v3.2.61` ve `v3.3.14` kaynakları:
  - [`initramfs.conf`: canlı paketleri önce purge et uyarısı](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/initramfs/initramfs.conf)
  - [`InitramfsJob.cpp`: gerçek update-initramfs çağrısı](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/initramfs/InitramfsJob.cpp)
  - [`packages/main.py`: apt purge ve try_remove hata davranışı](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/packages/main.py)
  - [`mount/main.py`: eksik extraMounts yalnızca uyarılır](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/mount/main.py), [3.2 mount.conf](https://github.com/calamares/calamares/blob/v3.2.61/src/modules/mount/mount.conf), [3.3 mount.conf](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/mount/mount.conf)
  - [`Runner.cpp`: hedef komutu yalnızca chroot ile başlatır; eksik mount'ları tamamlamaz](https://github.com/calamares/calamares/blob/v3.3.14/src/libcalamares/utils/Runner.cpp)

Mint'in bu iki deposu aynı kurucu olarak sunulmuyor; incelenen kaynaklar, belirli her Mint yayın ISO'sunun birebir dökümü değildir. Özellikle Ubuntu/casper dosya yolları Debian/live-build tabanımıza kopyalanmamalı.

## Yapı farkları

| Başlık | İncelenen kaynakta gözlenen | OğuzDows için sonuç |
| --- | --- | --- |
| ISO üretimi | Kali Live `live-build` kullanıyor. `amd64` için `--debian-installer live` ekliyor. Ayrı Installer projesi Simple-CDD/debian-cd kullanıyor. | Biz de live-build kullanıyoruz, ancak `--debian-installer none` + Calamares seçiyoruz. Bu tek başına bozuk ISO demek değil; D-I akışını bizim Calamares ayarlarımızla karıştırmamak gerekiyor. |
| Kurulum kaynağı | Mint live-installer `/cdrom/casper` veya `/run/live/medium/live` altındaki squashfs'i bağlayıp hedefe aktarır; Ubiquity manifest / kaldırılacak paket listelerini okur. | Bizim `/live/filesystem.squashfs` yolumuz Debian tabanına uygundur. ISO doğrulamasına bu dosyanın varlığı da eklendi; yeni sanal hedef testi gerçekten bu dosyayı açar. |
| Geçici sistem → kurulu sistem | Mint kaynağında canlı paketler / artıklar temizlenir; hedef fstab, initramfs ve GRUB hazırlanır. Mint kodunda canlı `update-initramfs` sarmalayıcısının bazı durumlarda sıfır dönüp işi atlayabildiğine dair açık açıklama da bulunuyor. | Sadece masaüstünün kopyalanması veya GRUB dosyası yetmez. Canlı paket temizliği ve hedefe özgü initramfs üretimi ayrı doğrulanmalı. |
| EFI | Kali binary paket listesi EFI kurucusu için gerekli .deb paketlerini ayrıca tutar; Mint kodu EFI paketlerinin yerel varlığını denetler. | Bizim amd64 ISO'muzda EFI araçları zaten gömülü. Kali/Mint paket depoları eklenmedi, Secure Boot desteği varmış gibi davranılmadı. |
| Testin sonu | Bir menünün açılması ile kurulu işletim sisteminin açılması farklı şeylerdir. | Eski GRUB-only kontrolü korunuyor; ek kontrol gerçek ISO'dan hazırlanan özel diskte çekirdek + initramfs + systemd'ye kadar gider. |

## Somut kaynak düzeltmeleri

### 1. Kritik canlı paket temizliği artık isteğe bağlı değil

Önce `packages.conf` içinde `try_remove` kullanılıyordu. Calamares bu işlemde paket kaldırma hatalarını uyarıya dönüştürüp devam edebilir. Bu davranış **isteğe bağlı Broadcom paketi** için uygundur; `live-tools` / `live-boot` temizliği için uygun değildir.

Artık şu altı paket tek zorunlu `remove` işlemiyle purge edilir:

`live-boot`, `live-boot-initramfs-tools`, `live-config`, `live-config-systemd`, `live-tools`, `calamares`.

Calamares'in APT arka ucu purge + autoremove kullanır. Veritabanı güncellemesi / sistem yükseltmesi açılmadı. Ek sürücü işi ayrı kalır; onun isteğe bağlı hata davranışı değiştirilmedi.

**Gerçek yeni ISO'dan edinilen karşı kanıt:** `44518014229` çalışmasında her iki squashfs'te `live-tools` zaten kurulu değildi ve `update-initramfs` diversion kaydı yoktu. Diğer canlı paketler başarıyla purge edildi; initramfs gerçekten yenilendi. Dolayısıyla sarmalayıcı olasılığı bu CI başarısızlığının nedeni değildir; kullanıcının cihazında da neden olduğu söylenemez. Zorunlu temizlik düzeltmesi bir güvenilirlik önlemidir, kanıtlanmış fiziksel hata teşhisi değil.

### 2. Sıfır çıkış kodu yeterli değil

Yeni `oguzdowstarget` işi:

1. Temizlikten sonra hedef dpkg durumunda canlı paket / kalıntı veya `update-initramfs` diversion kaydı bulunmadığını denetler.
2. Çekirdek / modül eşleşmesini ve initramfs'in önceki dosya kimliğini kaydeder.
3. Standart Calamares `initramfs` işinden sonra dosyanın gerçekten üretildiğini / yenilendiğini kontrol eder.
4. Arşivde normal disk açılış betikleri ve eşleşen çekirdek modüllerini arar.
5. GRUB üretildikten sonra mevcut çekirdek + initramfs çiftinin, `boot=live` olmayan bir disk köküyle birlikte menüde bulunduğunu denetler.

Bunlar diski yeniden bölümlemez; eksik kanıtta başarı verilmesini engeller. Hedefte `/var/log/oguzdows/target-system.json` bırakılır. Bu dosya **fiziksel açılış kanıtı değildir**. Son başarı işareti yine yalnızca `umount` sonrasındaki iş tarafından üretilir.

### 3. ISO kaynak kimliği

PC `build-info.json` artık `source_revision` ve `source_dirty` içerir. Git / güvenilir kaynak kimliği bulunamazsa commit uydurulmaz; `unknown` yazılır. Git çalışma ağacı durumu belirlenemiyorsa `source_dirty: null` kalır; `false` (temiz) diye sunulmaz. ISO testi beklenen commit / mimari eşleşmesini zorunlu tutar ve bilinen kirli kaynağı reddeder; `null` durumunu ise açık bir sınır notuyla kaydeder. Başlatıcı bu bilgiyi günlüğün başına da yazar. Böylece aynı dosya adına sahip eski USB ile yeni kaynağı karıştırmak daha kolay fark edilir.

### 4. Calamares 3.2 / 3.3 servis biçimi aynı değil

İnceleme sırasında `services-systemd.conf` için ayrı bir uyumsuzluk bulundu: [3.2.61 kodu](https://github.com/calamares/calamares/blob/v3.2.61/src/modules/services-systemd/main.py) `services` / `disable` anahtarlarını okurken [3.3.14 kodu](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/services-systemd/main.py) yalnızca `units` okur. Ortak eski dosya trixie'de sessizce hiçbir servis işlemi üretmiyordu. Bu, işlemi durduran bir hata olarak sunulmaz; servisler ISO kancasında zaten etkinleştirilir.

Bookworm biçimi korunur; trixie için `installer/overrides/trixie/services-systemd.conf` uygulanır. Etkinleştirilecek aynı dört servis ve önceki nonfatal politika korunur; masaüstü tercihi değişmez. Yeni test, iki tabanlı CI'de **gerçek kurulu Calamares Python işini** sahte `target_env_call` ile çalıştırıp dört beklenen komutun gerçekten üretildiğini sınar. Bu test fiziksel sisteme veya `systemctl`'e çağrı yapmaz; yapılandırmanın sessizce yok sayılmasını yakalar. `ae2a54c` kaynağındaki [44527596668 PC testleri](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44527596668) iki tabanda da geçti. Yerelde Calamares bulunmadığı için bu tek native test atlanır; resmî 3.2.61 / 3.3.14 kaynaklarıyla yapılan ayrıca izole denemede eski trixie yapılandırmasının sıfır, düzeltilmiş her iki biçimin dört komut ürettiği de yeniden gösterilmiştir.

### 5. Fotoğraftaki GRUB hatası ve doğrulanan eksik mount yapılandırması

ASUS X553M için **amd64 seçimi doğrudur**: ad, AMD markalı işlemci zorunluluğu değil, Intel 64 işlemcilerini de kapsayan x86-64 mimarisidir. Fotoğraftaki `Installing for i386-pc platform` ise GRUB'un **Legacy BIOS** hedefidir; 32-bit ISO indirildiğini göstermez.

Fotoğraftaki gerçek durma noktası:

```text
grub-install --target=i386-pc --recheck --force /dev/sdb
grub-install: error: cannot find a device for /boot/grub (is /dev mounted?).
```

`/dev/sdb` aygıtının dahili disk mi, USB mi olduğu fotoğraftan belirlenemez. Bu hata üzerine tahminî bir diske GRUB yazılmaz veya yeniden biçimlendirme önerilmez.

**Doğrulanmış kaynak hatası:** `b89a617` ve önceki ortak yapılandırmada `mount.conf` yoktu. Calamares bu dosya olmadan `/dev`, `/proc`, `/sys` vb. bağlantıları kendiliğinden kurmuyor; uyarıp devam ediyor. Sadece örnek dosyanın upstream'de bulunması yetmez. [44544369042](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44544369042), `13f68f6` test kaynağında her iki tabanın **gerçek kurulu paketini ve etkin yapılandırma arama yollarını** sınadı. İkisinin kontrol notu da `configuration_file: null, configuration: {}` bildirdi ve `/dev` beklentisiyle regresyon testi başarısız oldu. Önceki elle bağlanmış hedef-OS testleri bu yapılandırma eksikliğini gizliyordu.

Düzeltme ve yeni denetimler:

- Bookworm/Calamares 3.2 için `installer/modules/mount.conf`: `options: bind` metni ve ayrı `extraMountsEfi` listesi.
- Trixie/Calamares 3.3 için sürüm üstüne yazımı: `options: [bind]` listesi ve `efi: true`. 3.2 dosyasını aynen kullanmak da yanlıştır; 3.3 liste bekleyen kod, `bind` metnini `b,i,n,d` hâline getirebilir.
- Her iki biçim `/dev`, `/dev/pts`, `/proc`, `/sys`, `/run` ve `/run/udev` bağlantılarını açıkça tanımlar. Native `unpackfs` aynı listeyi kopyalama dışlaması olarak kullanır; canlı aygıt dizinlerine squashfs içeriği yazılmaz.
- Yeni salt-okunur `oguzdowsmount` işi **mount'tan hemen sonra, dosya aktarımından önce** seçilen kök/ayrı `/boot` bölümünün gerçekten bağlı olduğunu, gerekli bağlama noktalarını ve hedefte aygıt görünürlüğünü doğrular. Native mount başarısızlığının yalnızca uyarıya dönüşmesi artık yeterli değildir.
- **GRUB yazımından önce**, gerçek hedef chroot'unda zaman sınırlı `grub-probe --target=device /boot/grub` (dizin henüz yoksa `/boot`) çalışır. Sonuç seçilen `/boot`/kök aygıtıyla eşleşmezse kurulum açık hata ile durur; rastgele başka disk seçilmez.
- `tests/smoke-calamares-mount.py`, CI'nin kendi özel loop imajında gerçek paket mount işini çalıştırır: boş yapılandırmayla fotoğraftaki aygıt-keşif hatasını arar, yeni yapılandırmayla gerçek chroot probe ve dışlamaları sınar. Bu yeni testin sonucu ayrıca raporlanmalıdır; kaynakta bulunması geçtiğini göstermez.
- ISO-hedef testi, **gerçek squashfs içindeki** mount.conf dosyasının o commit'in mimariye uygun kaynağıyla aynı olduğunu da zorunlu tutar.

**Yeni native test sonucu:** [44546316461](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44546316461), `513daed79e0aaf4253b6b9b9e5289ee20f731719` kaynağında iki tabanda da **başarılı** tamamlandı. Boş yapılandırmada gerçek chroot `grub-probe` çıkış 1 ile tam olarak `cannot find a device for /boot/grub (is /dev mounted?)` iletisini üretti. Düzeltilmiş yapılandırmada aynı özel loop bölümünü (`/dev/loop0p1`) hem yeni bağlantı denetimi hem gerçek chroot probe doğruladı; native unpackfs dışlamaları da doğrulandı. Bu testte diske GRUB yazımı yapılmadı; mevcut ayrı firmware → GRUB testleri de iki tabanda geçti. Gerçek paket birim sözleşmeleri, kurucu pencere ve hafif GTK kontrolleri aynı çalışmada başarılıdır. Yerelde 188 testlik küme başarılıdır (183 geçti, Calamares kurulu olmadığından 5 native test atlandı); native testler CI'de çalıştırıldı.

Bu doğrulanmış hata, fotoğraftaki belirtiyle aynı GRUB aygıt-keşif hatasını üreten bir kod yoludur. Fotoğraftaki USB'nin hangi commit'i içerdiği ve `/dev/sdb` kimliği bilinmeden o fiziksel denemeye kesin kaynak kimliği atanmaz. Yeni ISO eski USB'yi veya yarım kalmış disk kurulumunu kendiliğinden güncellemez. `513daed` testi tam GUI kurulumu veya ASUS'ta fiziksel açılış kanıtı olarak sunulmaz.

İkinci fotoğraftaki `/usr/local/sbin/oguzdows-driver-helper broadcom --offline` çıkış 1 hatası ayrı değerlendirilir. Uyumsuz donanıma Broadcom zorlanmamalı. Mevcut isteğe bağlı sürücü aktarımı bu başarısızlığı uyarıya dönüştürür; fotoğrafın bu düzeltmeyi içeren ISO'dan geldiği henüz kanıtlanmadı.

## Yeni testin yaptığı ve yapmadığı

`tests/smoke-iso-target.py`, yalnızca ayrıcalıklı ve tek kullanımlık CI konteynerinde çalışır:

- Üretilen gerçek ISO'yu salt-okunur bağlar, squashfs'i **kendisinin oluşturduğu dosyaya bağlı loop diske** açar.
- Kaynak commit / mimariyi denetler; aynı üretim temizleme betiğini ve APT purge işlemini çalıştırır.
- Gerçek `update-initramfs -k all -c -t` ve GRUB araçlarını hedefte çalıştırır.
- Diski ayırıp, ağsız QEMU'da ISO takılı olmadan açar.
- Başarı işareti GRUB'dan değil, hedef UUID'li kök dosya sisteminde **systemd tarafından çalıştırılan** test servisinden gelir.
- amd64 için BIOS + temiz NVRAM'li UEFI fallback, i386 için BIOS sınanır.
- Bu adım geçmeden CI, ISO'yu başarılı indirme artefaktı olarak yayımlamaz.

**Sınırlar:** bu bir Calamares GUI bölümleme / kullanıcı oluşturma otomasyonu değildir. Düz ext4 hedefi hazırlar; LUKS, dual boot, seçili ek sürücüler, masaüstünde etkileşim, fiziksel firmware ve fiziksel bilgisayar performansı ayrıca sınanmalıdır. Yeni testin kaynakta bulunması geçtiği anlamına gelmez; sonucu ilgili Actions çalışması ve `OguzDows-ISO-hedef-test-*` çıktısından okunmalıdır.

### İlk denemelerin durumu

`44515268150` (`668622d`) çalışmasında iki ISO üretildi; GTK ve firmware → GRUB kontrolleri geçti. Yeni hedef-OS testi ise `source_dirty: null` değerini yanlışlıkla kirli kaynakla aynı şekilde reddettiği için **çekirdek açılışına ulaşmadı**. Bu test hatası, kullanıcının fiziksel kurulum hatasını açıklamaz. Durum, ISO tekrar derlenmeden `44517607846` kanıt-okuma işiyle ayrıştırıldı. Bilinmeyen / temiz / kirli durumları artık ayrı sınanır. Ayrıca 4096 karakterde kesilen kontrol notlarında gerçek son hatanın kaybolmaması için kısa hata kuyruğu ve doğrudan hedef hata notu eklenmiştir.

İkinci çalışmada (`44518014229`, `9ee2a4b`) her iki gerçek çekirdek ve initramfs açıldı; fakat `root=/dev/loop1p1` / `root=/dev/loop1p3` arandı ve normal kök sisteme geçilemedi. Bu adlar CI konteynerine aittir, sanal makinedeki disk `/dev/vda` olur. GRUB'un UUID bağlantısı bulunmadığında aygıt adına düşen resmî kod yolu incelendi. Test artık yalnızca kendi doğrulanmış loop bölümünün eksik UUID bağlantısını sağlar; var olan başka aygıt bağlantılarını ezmez, kendi oluşturduğu bağlantıyı temizler. **Üretilen grub.cfg elle değiştirilmez.** QEMU'ya geçmeden önce gerçek üretilmiş menünün seçilen hedef UUID'sini içerdiği de zorunlu tutulur. Üretim denetimi de geçici `/dev/loop…` / canlı kök referansını reddeder. Bu test ortamı düzeltmesi, fiziksel cihaz hatasının sebebiymiş gibi sunulmaz.

### İlk başarılı gerçek hedef-OS açılışı

[44521646789](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44521646789), `36ff1ea` kaynağında **başarılı** tamamlandı:

| Gerçek ISO içeriğinden hazırlanan hedef | QEMU sonucu |
| --- | --- |
| amd64 / trixie / `6.12.117+deb13-amd64` | BIOS **ve** temiz NVRAM'li UEFI fallback → çekirdek → initramfs → hedef UUID'li kökte systemd servisi |
| i386 / bookworm / `6.1.0-56-686-pae` | BIOS → çekirdek → initramfs → hedef UUID'li kökte systemd servisi |

İki ISO ve SHA-256 çıktıları ancak bu kontrolden sonra yayımlandı. Raporlar hâlâ `gui_installation_tested: false`, `physical_boot_verified: false`, `encrypted_root_tested: false` içerir. Bu sonuç, sonradan eklenen servis ve mount biçimi düzeltmelerinden önceki `36ff1ea` ISO'larına aittir; yeni kaynak değişiklikleri içeren ISO ayrı kaynak kimliğiyle üretilmelidir. Sonraki `b89a617` / [44527988747](https://github.com/PeraPlusbirPasha/O-uzDows/actions/runs/44527988747) de eski elle bağlanmış hedef-OS testini geçti; bu yeşil sonuç native mount yapılandırmasını sınamadığından yukarıdaki eksikliği dışlamıyordu.

## Son cihaz hatası için gereken kanıt

**Kurulum sırasında** hata alındığı ve hata pencereleri artık biliniyor; yeniden aynı aşama / fotoğraf sorusu sorulmaz. Kalan ihtiyaç: kullanılan ISO dosya adı / kaynak kimliği, tam günlük ve `/dev/sdb` dahil aygıtların düzeni. Canlı oturumda terminal açılabiliyorsa yalnızca aşağıdaki salt-okunur çıktılar istenir:

```sh
cat /usr/share/oguzdows/build-info.json
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,MODEL,TRAN
sudo tail -n 100 /var/log/oguzdows/installer.log
```

Bunlar bölüm oluşturmaz, biçimlendirmez, GRUB yazmaz. İki fotoğrafın aynı denemeye mi yoksa farklı ISO'lara mı ait olduğu da belirtilirse Broadcom ve GRUB izleri doğru kaynağa bağlanabilir. `/dev/sda` veya `/dev/sdb` gibi tahminî bir aygıta onarım yazımı önerilmez. Yeni ISO eski kurulmuş diski kendiliğinden onarmaz.
