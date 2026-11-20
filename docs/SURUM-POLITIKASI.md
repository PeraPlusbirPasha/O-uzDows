# Yayın ve sürümleme politikası

[← Proje vitrini](../README.md) · [Yayınlar](https://github.com/PeraPlusbirPasha/OguzDows/releases)

## Ana yayın adları

- İlk yayımlanmış PC sürümü **v1.0.0 · OğuzDows 1.0 Ay Yıldız** olarak kalır. Kaynak etiketi, ISO adları veya dosya içeriği yalnızca yeni bir adlandırma düzenine geçmek için değiştirilmez.
- Bundan sonraki yeni ana yayınlar **v2.0**, **v3.0**, … olarak adlandırılır. Sırf README, sürümleme belgesi veya GitHub görünümü değişti diye yeni ana sürüm yayımlanmaz.
- Yayın aracı hem yeni `v2.0` biçimini hem mevcut `v1.0.0` biçimini kabul eder. Bir etiket biçiminin kabul edilmesi o sürümün yayımlandığı anlamına gelmez.
- Bu düzen bir yayın takvimi, otomatik yükseltme sistemi veya henüz tamamlanmamış özellik taahhüdü değildir. Yeni bir ISO mevcut kurulumları kendiliğinden değiştirmez.

## 1.1 ara güncellemesi

Kullanıcının istediği **v1.1**, v1.0.0 üzerine geliştirilen ara güncellemedir; sonraki ana sürümlerin v2.0 / v3.0 adlandırmasını değiştirmez. Yeni karşılayıcı, tema, mağaza, galeri, Rıfkı ve cihaz / dosya uyumluluğu kaynak dalında geliştirilir. **Henüz yayımlanmış v1.1 ISO yoktur.** v1.0.0 etiketi / ISO'ları / sekiz yayın dosyası korunur. Yeni ISO ve 1.1'e ait tam masaüstü ölçümü kendi kaynak kimliğiyle tamamlanmadan eski sayılar 1.1 sonucu diye sunulmaz. Ayrıntılar: [1.1 geliştirme kaydı](V1.1-GELISTIRME.md).

## Her yayında aynı kimlik

Her yeni ana yayında ürün içindeki sürüm bilgisi, açık kaynak commit kimliği, yayın etiketi, sürüm notları ve ISO’lar birbiriyle uyumlu olmalıdır. Daha eski ISO’lar yeni ürün değişikliklerini içeriyormuş gibi yeniden etiketlenmez.

Sonraki değişiklikler yalnızca belge, test veya yayın aracıyla sınırlıysa mevcut ISO’nun yeniden derlenmediği açıkça belirtilir. Kaynak çalışma ağacının temizliği belirlenemediğinde `source_dirty: null`, temiz (`false`) olarak sunulmaz.

## Yayın kontrol listesi

1. Kaynak değişikliklerini çalışma dalında tamamla, birim/kontrat ve ilgili gerçek ortam testlerini çalıştır.
2. PC için başarılı amd64/i386 derlemelerini ve mimariye uygun hedef OS açılış testlerini kullan. Yayımlanan ISO’nun içeriği/kaynak commit’i eşleşmeli.
3. Boşta RAM iddiası varsa tam grafik oturumunu ölç; yöntem, örnekler, koşullar ve hedefi tutturamayan sonuçlar dahil sınırlamaları açıkça paylaş. Bileşen RSS’i veya GRUB menüsü tam masaüstü kanıtı değildir.
4. Yayın **taslağı** oluştur. Hedef commit’i açıkça seç; varsayılan dalın en son commit’ine sessizce etiket koyma.
5. ISO’ları özgün `.iso.sha256` dosyalarıyla doğrula. İki ISO, ayrı checksum dosyaları, birleşik `SHA256SUMS`, kaynak/dosya manifesti ve ilgili test kanıtlarını ekle.
6. Türkçe sürüm notlarında yeni özellikleri, ISO’nun gerçek kaynak kimliğini, test sonuçlarını ve bilinen sınırları belirt. Yapay zekâ görsel/ses kökenini gizleme.
7. Eksiksiz dosya listesi, boyutlar ve SHA-256 özetleri doğrulanınca taslağı yayımla. Sonrasında herkese açık indirme uçlarını ve etiket hedefini tekrar kontrol et.
8. README’deki güncel sürüm, ISO, checksum ve test bağlantılarını yeni yayına taşı. Önceki sürümlerin yayınlarını ve kanıtlarını koru.

**Süren bir derleme, yeni yayın işi geldi diye iptal edilmez veya yeniden başlatılmaz.** Artefakt aktarımı ISO’yu yeniden paketlemez; yalnızca gerekli başarılı çıktıları taşır. `pc-release` işi kendiliğinden yeni release/etiket oluşturmaz, dosya ezmez ve taslağı herkese açmaz; son yayın ayrı bir karardır.

## v1.0.0 kaydı

- [Yayımlanmış sürüm](https://github.com/PeraPlusbirPasha/OguzDows/releases/tag/v1.0.0)
- [Türkçe sürüm notları](releases/v1.0.0.md)
- [Kaynak, SHA-256 ve ölçüm kanıtı](MASAUSTU-TEST-KANITI.md)

Bu belgede fiziksel PC/Raspberry Pi, Secure Boot, gerçek KDE/GNOME oturumu, şifreli tam kurulum veya gerçek yetkili paket kurulumları için tamamlanmamış testler tamamlanmış sayılmaz.
