# Kali / Linux Mint incelemesi ve OğuzDows kurulum denetimi

## Kapsam ve sınır

Resmî ISO **derleme tarifleri ve kurucu kaynak kodları** incelendi; Kali/Mint'in çok gigabaytlık yayın ISO'ları bu inceleme için indirilip fiziksel diske kurulmadı. Kaynak kod karşılaştırması, kullanıcının son hatasının nedenini tek başına kanıtlamaz. Son hata ekranı / günlük ve kullanılan ISO'nun kaynak kimliği hâlâ gereklidir.

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
- Calamares, kullandığımız iki tabanla ilişkili `v3.2.61` ve `v3.3.14` kaynakları:
  - [`initramfs.conf`: canlı paketleri önce purge et uyarısı](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/initramfs/initramfs.conf)
  - [`InitramfsJob.cpp`: gerçek update-initramfs çağrısı](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/initramfs/InitramfsJob.cpp)
  - [`packages/main.py`: apt purge ve try_remove hata davranışı](https://github.com/calamares/calamares/blob/v3.3.14/src/modules/packages/main.py)

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

### 2. Sıfır çıkış kodu yeterli değil

Yeni `oguzdowstarget` işi:

1. Temizlikten sonra hedef dpkg durumunda canlı paket / kalıntı veya `update-initramfs` diversion kaydı bulunmadığını denetler.
2. Çekirdek / modül eşleşmesini ve initramfs'in önceki dosya kimliğini kaydeder.
3. Standart Calamares `initramfs` işinden sonra dosyanın gerçekten üretildiğini / yenilendiğini kontrol eder.
4. Arşivde normal disk açılış betikleri ve eşleşen çekirdek modüllerini arar.
5. GRUB üretildikten sonra mevcut çekirdek + initramfs çiftinin, `boot=live` olmayan bir disk köküyle birlikte menüde bulunduğunu denetler.

Bunlar diski yeniden bölümlemez; eksik kanıtta başarı verilmesini engeller. Hedefte `/var/log/oguzdows/target-system.json` bırakılır. Bu dosya **fiziksel açılış kanıtı değildir**. Son başarı işareti yine yalnızca `umount` sonrasındaki iş tarafından üretilir.

### 3. ISO kaynak kimliği

PC `build-info.json` artık `source_revision` ve `source_dirty` içerir. Git / güvenilir kaynak kimliği bulunamazsa commit uydurulmaz; `unknown` yazılır. Başlatıcı bu bilgiyi günlüğün başına da yazar. Böylece aynı dosya adına sahip eski USB ile yeni kaynağı karıştırmak daha kolay fark edilir.

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

## Son cihaz hatası için gereken kanıt

Fotoğraf ve hangi ISO'nun USB'ye yazıldığı ilk adımdır. Canlı oturumda terminal açılabiliyorsa yalnızca aşağıdaki salt-okunur çıktılar istenir:

```sh
cat /usr/share/oguzdows/build-info.json
sudo tail -n 100 /var/log/oguzdows/installer.log
```

Diskten açılmama durumunda mevcut salt-okunur açılış raporu / BIOS-UEFI bilgisi de gerekir. `/dev/sda` gibi tahminî bir aygıta GRUB yazılmaz, veri diski biçimlendirilmez. Yeni ISO eski kurulmuş diski kendiliğinden onarmaz.
