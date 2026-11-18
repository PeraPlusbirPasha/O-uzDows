# Rıfkı görsel kaynakları

`rifki/portrait.png` ve `rifki/expression.png` bu proje için üretilmiş yapay zekâ görselleridir. Aynı Van kedisinin temel pozu ve kapalı göz / açık ağız ifadesi kullanılarak, yumuşak bölgesel maskelerle dört 384×384 çalışma karesi hazırlanmıştır. Paketlenen kareler `system/usr/share/oguzdows/rifki/` altındadır.

Animasyon, GTK çizim alanında nefes / hafif baş hareketi, göz kırpma ve önceden hazırlanmış Türkçe sesin 20 Hz genlik zarfıyla ağız karesi seçimi olarak çalışır. Tam 3B model veya gerçek hayvan videosu değildir. Ses seçimi atlandığından varsayılan Türkçe ses kullanılmıştır; kullanıcı tarafından özellikle seçildiği iddia edilmez.

Altı yeni manzara da yapay zekâ üretimidir; gerçek fotoğraf olarak sunulmaz. Paketlenmiş 1920×1080 JPEG dosyaları `system/usr/share/backgrounds/oguzdows/` altındadır. GTK galerisi ve README bu kökeni belirtir.

## Hareketli küçük kedi sürümü

`perch.png`, `leap.png`, `play.png`, `tea.png`, `teapot.png` ve `tea-glass.png` bu istek için üretilen ayrı poz / obje kaynaklarıdır. `scripts/prepare-rifki.py` yeşil zemini ayırıp kenar yansımasını giderir, yumuşak kuyruk katmanı ve 512 piksel rig dokuları üretir. Baş ve pati bölgesinde kesilmiş / boş eklem bırakmayan yumuşak doku deformasyonu kullanılır. Aynı `rifki_scene.py` çizicisi GTK, kare testleri ve video / WebP önizlemesi içindir.

On yeni WAV, mevcut varsayılan Türkçe sesle üretilmiştir. `speech.json` tam metin özetini dosyaya eşler. Genel veya değişen metinler çevrimdışı eSpeak NG Türkçe ile seslendirilir; bu ses hazır kayıtlardan farklıdır. Önceki ses seçimi atlanmıştır; kullanıcının özel seçimi olduğu söylenmez.
