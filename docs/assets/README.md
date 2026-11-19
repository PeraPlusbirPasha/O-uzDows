# README görselleri

Bu klasör yalnızca GitHub dokümantasyonuna aittir; buradaki görseller PC/Pi imajına eklenmez.

- `oguzdows-banner.svg`: projenin `assets/oguzdows.svg` ay-yıldız geometrisini kullanan statik vektör kapak. Haricî yazı tipi, script, `foreignObject`, takip pikseli veya ağ kaynağı yoktur. İşletim sistemi ekran görüntüsü değildir.
- Altı JPEG: `system/usr/share/backgrounds/oguzdows/` altındaki mevcut, logolu 1920×1080 görsellerin 480×270 küçük kopyaları. README’nin yaklaşık 3 MB tam boy manzara yüklemesi yerine toplam yaklaşık 154 KB önizleme kullanmasını sağlar. Tıklama özgün görsele gider.
- Manzaralar yapay zekâ üretimidir; gerçek kamera fotoğrafı veya doğrulanmış coğrafi belge olarak sunulmaz. Ayrıntılı köken ve üretim bilgileri: [artwork/README.md](../../artwork/README.md) ve [landscapes.json](../../artwork/landscapes.json).

Önizlemeleri repo kökünden, Pillow hazırken çevrimdışı yeniden üretmek için:

```sh
python3 - <<'PY'
from pathlib import Path
from PIL import Image
source = Path('system/usr/share/backgrounds/oguzdows')
for name in ('bogaz-sabahi', 'kackar-sisi', 'kapadokya-isigi',
             'oludeniz-kiyisi', 'tuz-golu-aksami', 'ani-kisi'):
    with Image.open(source / (name + '.jpg')) as image:
        preview = image.convert('RGB').resize((480, 270), Image.Resampling.LANCZOS)
        preview.save(Path('docs/assets') / (name + '.jpg'),
                     format='JPEG', quality=83, optimize=True, progressive=True)
PY
```

Pillow/JPEG kodlayıcı sürümü ikili çıktıyı değiştirebilir; önizlemeler ISO içeriğinin hash kanıtı değildir. ISO ve özgün manzara doğrulamaları bundan ayrıdır.
