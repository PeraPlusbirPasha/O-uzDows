# Rıfkı ve manzara kaynakları

## Paketlenen hafif sürüm

`rifki/portrait.png` ve `rifki/expression.png` bu proje için üretilmiş yapay zekâ görselleridir. Aynı Van kedisinin temel pozu ve kapalı göz / açık ağız ifadesinden hazırlanmış 384×384 PNG kaynakları `system/usr/share/oguzdows/rifki/` altındadır. Karşılamada tek sabit resim; istenince açılan Rıfkı penceresinde en fazla üç küçük, önceden ölçeklenen resim kullanılır. Varsayılan animasyon döngüsü, Cairo çizim geri çağrısı veya pencere katmanı yoktur. İsteğe bağlı ağız geçişi yalnızca konuşma sırasında 2 Hz'dir; azaltılmış hareket profilinde ve kurulumda kapalıdır.

Türkçe WAV'lar yapay zekâ ile hazırlanmış, doğal konuşma tınılı yerel kayıtlardır. Önceki ses seçimi atlandığı için varsayılan ses kullanılmıştır; kullanıcının özellikle seçtiği veya gerçek bir insanın stüdyo kaydı olduğu söylenmez. Aynı ses korunarak hafif sürümün tanıtımı, disk / yardım, ayarlar, sadeleştirme açıklaması, üç kurulum aşaması, iptal ve ek-sürücü uyarısı kaydı eklendi. `speech.json`, **18 açıklamanın tam metin özetini** dosyaya eşler; sonuç türleri yalnızca sabit bir izin listesinden kayıt seçer. Başarılı olmayan veya henüz tamamlanmamış kurulum için başarı kaydı seçilmez.

Çalışma zamanında eSpeak NG, sentez, genlik zarfı taraması, ses önbelleği, mikrofon veya ağ erişimi yoktur. Manzara açıklamaları yeni galeriye göre yenilendi; Tarzlar paneli için aynı sesle kayıt eklendi. Kaydı olmayan değişken hata / hedef / donanım ayrıntıları, Pi'ye özgü açıklamalar ve Güncelleyici/Mağaza/İmece pencereleri yalnızca metindir; robotik sese veya rastgele bir genel başarı kaydına düşülmez. Yeni mesajda kayıt bulunmasa bile önceki ses kesilir.

## Önceki hareketli sürüm — yalnızca geliştirici kaynakları

`perch.png`, `leap.png`, `play.png`, `tea.png`, `teapot.png` ve `tea-glass.png` önceki katmanlı animasyon için üretilmiş poz / obje kaynaklarıdır. `scripts/prepare-rifki.py`, `scripts/preview-rifki.py`, `rifki_scene.py` ve hareket testleri bu kaynakları geliştirme / tarihsel önizleme amacıyla korur. Tam 3B model veya gerçek hayvan videosu değildir.

Bu çizici, pencere takipçisi, hareket planlayıcısı ve `rig/` dokuları **PC veya Pi imajına kopyalanmaz**. Eski `envelopes.json`, artık kullanılmayan tanıtım kayıtları ve dördüncü animasyon karesi de imajdan dışlanır. Önceki video / WebP demosu hafif sürümün çalışma zamanı veya performans gösterimi değildir.

## Türkiye manzaraları

Önceki altı çizim emekli edildi; altı manzaranın da içeriği yenilendi. Boğaz, Kaçkar, Kapadokya, Ölüdeniz, Tuz Gölü ve Ani esintili bu görseller bu proje için yapay zekâyla üretildi. **Gerçek kamera fotoğrafları veya birebir coğrafi belge değildir.** Ticari stok arama önizlemeleri kullanılmadı.

Paketlenen 1920×1080 JPEG dosyaları `system/usr/share/backgrounds/oguzdows/` altındadır; her birinin sağ alt köşesine proje ay-yıldızı ve OğuzDows yazısı eklenmiştir. Ayrı 320×180 önizlemeler yalnızca galeri açılınca yüklenir. Eski `wallpaper.png` uyumluluk yolu yeni Boğaz manzarasından üretilir; eski çizim tekrar paketlenmez.

`landscapes.json`, logosuz özgün kaynağın boyut/SHA-256'sını ve paketlenen logolu JPEG'in SHA-256'sını kaydeder. `scripts/prepare-landscapes.py` logosuz özgün kaynaklarla bir kez çalıştırılan geliştirme aracıdır; derleme sırasında JPEG'e tekrar logo basılmaz. GTK galerisi, yerel belge ve README yapay zekâ kökenini açıkça belirtir.

## Yerel tespih imleci

`scripts/render-assets.py` özgün, küçük boncuk/tane-vurgusu karelerini ve Xcursor v1 dosyalarını çevrimdışı üretir. 24/32/48 px; normal/bağlantı/bekleme için 10 kare, yazı için sabit kare; diğer roller Adwaita'dan miras alınır. Ayrı runtime çizici, masaüstü katmanı veya tıklama izleme servisi yoktur. Format/boyut/hotspot/alpha testleri ve CI içinde gerçek libXcursor okuyucusu kullanılır.
