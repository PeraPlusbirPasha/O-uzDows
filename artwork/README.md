# Rıfkı ve manzara kaynakları

## Paketlenen hafif sürüm

`rifki/portrait.png` ve `rifki/expression.png` bu proje için üretilmiş yapay zekâ görselleridir. Aynı Van kedisinin temel pozu ve kapalı göz / açık ağız ifadesinden hazırlanmış 384×384 PNG kaynakları `system/usr/share/oguzdows/rifki/` altındadır. Karşılamada tek sabit resim; istenince açılan Rıfkı penceresinde en fazla üç küçük, önceden ölçeklenen resim kullanılır. Varsayılan animasyon döngüsü, Cairo çizim geri çağrısı veya pencere katmanı yoktur. İsteğe bağlı ağız geçişi yalnızca konuşma sırasında 2 Hz'dir; azaltılmış hareket profilinde ve kurulumda kapalıdır.

Türkçe WAV'lar yapay zekâ ile hazırlanmış, doğal konuşma tınılı yerel kayıtlardır. Önceki ses seçimi atlandığı için varsayılan ses kullanılmıştır; kullanıcının özellikle seçtiği veya gerçek bir insanın stüdyo kaydı olduğu söylenmez. Aynı ses korunarak hafif sürümün tanıtımı, disk / yardım, ayarlar, sadeleştirme açıklaması, üç kurulum aşaması, iptal ve ek-sürücü uyarısı kaydı eklendi. `speech.json`, **17 açıklamanın tam metin özetini** dosyaya eşler; sonuç türleri yalnızca sabit bir izin listesinden kayıt seçer. Başarılı olmayan veya henüz tamamlanmamış kurulum için başarı kaydı seçilmez.

Çalışma zamanında eSpeak NG, sentez, genlik zarfı taraması, ses önbelleği, mikrofon veya ağ erişimi yoktur. Kaydı olmayan değişken hata / hedef / donanım ayrıntıları ve Pi'ye özgü iki panel açıklaması yalnızca metindir; robotik sese veya rastgele bir genel başarı kaydına düşülmez. Yeni mesajda kayıt bulunmasa bile önceki ses kesilir.

## Önceki hareketli sürüm — yalnızca geliştirici kaynakları

`perch.png`, `leap.png`, `play.png`, `tea.png`, `teapot.png` ve `tea-glass.png` önceki katmanlı animasyon için üretilmiş poz / obje kaynaklarıdır. `scripts/prepare-rifki.py`, `scripts/preview-rifki.py`, `rifki_scene.py` ve hareket testleri bu kaynakları geliştirme / tarihsel önizleme amacıyla korur. Tam 3B model veya gerçek hayvan videosu değildir.

Bu çizici, pencere takipçisi, hareket planlayıcısı ve `rig/` dokuları **PC veya Pi imajına kopyalanmaz**. Eski `envelopes.json`, artık kullanılmayan tanıtım kayıtları ve dördüncü animasyon karesi de imajdan dışlanır. Önceki video / WebP demosu hafif sürümün çalışma zamanı veya performans gösterimi değildir.

## Türkiye manzaraları

Altı yeni manzara da yapay zekâ üretimidir; gerçek fotoğraf olarak sunulmaz. Paketlenmiş 1920×1080 JPEG dosyaları `system/usr/share/backgrounds/oguzdows/` altındadır. Önceki altı çizimle birlikte 12 seçenek korunur; ayrı küçük önizlemeler yalnızca galeri açılınca yüklenir. GTK galerisi ve README bu kökeni belirtir.
