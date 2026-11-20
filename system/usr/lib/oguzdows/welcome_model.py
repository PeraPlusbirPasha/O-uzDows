"""1.1 karşılayıcısı: GTK'den bağımsız oturum ve gezinme modeli.

Canlı, kurulu PC ve Pi ilk açılış işaretleri ayrıdır. Bir USB oturumunun
'gösterme' tercihi kurulu sistemin ilk karşılamasını susturamaz.
"""
from __future__ import annotations

from dataclasses import dataclass

from rifki_dialogue import HELLO, PANELS

PAGES = (
    ('welcome', 'Hoş geldin', 'go-home-symbolic'),
    ('styles', 'Tasarım', 'preferences-desktop-theme-symbolic'),
    ('appearance', 'Açık / koyu', 'display-brightness-symbolic'),
    ('wallpapers', 'Duvar kâğıdı', 'preferences-desktop-wallpaper-symbolic'),
    ('hardware', 'Donanım', 'computer-symbolic'),
    ('applications', 'Uygulamalar', 'system-software-install-symbolic'),
    ('support', 'Destek', 'help-browser-symbolic'),
)
PAGE_IDS = tuple(page[0] for page in PAGES)


@dataclass(frozen=True)
class Context:
    kind: str
    title: str
    subtitle: str
    intro: str

    @property
    def state_name(self):
        return 'welcome-' + self.kind + '-1.1-seen'

    @property
    def offers_installer(self):
        return self.kind == 'live'


def context(live=False, pi=False):
    # Pi zaten SD/USB'ye kuruludur; /proc/cmdline üstünden PC kurucusu önerme.
    if pi:
        return Context('pi', 'OğuzDows · Pi karşılayıcısı', 'SD / USB üzerinde senin masaüstün',
                       'Sistemin SD veya USB üzerinde hazır. İlk adımlarını, görünümünü ve donanımını birlikte düzenleyelim.')
    if live:
        return Context('live', 'OğuzDows · Canlı karşılayıcı', 'Önce dene, hazır olunca kur',
                       'Diskine dokunmadan keşfet. Hazır olduğunda kurucuyu aç; disk ve kullanıcı seçimlerini son özette sen onaylarsın.')
    return Context('installed', 'OğuzDows · İlk adımlar', 'Kurulum bitti, şimdi kişiselleştirme zamanı',
                   'Masaüstün hazır. Tarzını ve temanı seç; uygulamalarını, güncellemelerini ve donanımını buradan yönet.')


def adjacent(page, direction):
    if direction not in (-1, 1):
        raise ValueError('Geçersiz gezinme yönü.')
    if page not in PAGE_IDS:
        return None  # Kurulum sonucundan kendiliğinden başka sayfaya geçme.
    index = PAGE_IDS.index(page) + direction
    return PAGE_IDS[index] if 0 <= index < len(PAGE_IDS) else None


def page_text(page, session):
    if page not in PAGE_IDS:
        return ''
    if page == 'welcome':
        # Mevcut doğal, genel giriş kaydı; yeni arayüzü yanlış tarif eden eski
        # 'üst sekmeler' kaydı burada kullanılmaz.
        return HELLO
    if page == 'hardware' and session.kind == 'pi':
        return 'Pi donanım paneli. Platform ve SDIO aygıtlarını inceleyebilirsin. PC Broadcom STA paketi Pi kablosuz kartına kurulmaz. Donanım raporun cihazında kalır.'
    if page in ('hardware', 'wallpapers', 'styles'):
        return PANELS[page]
    if page == 'appearance':
        return 'Açık veya koyu temayı seç. Seçimin yalnızca bu hesaba uygulanır; panel ve pencere düğmeleri opak kalır. İlk görünüm değişikliğinden önce ayarların yedeklenir.'
    if page == 'applications':
        return 'Uygulamaları ve güncellemeleri ayrı düğmelerden açabilirsin. Bir düğmeyi açmak paket kurmaz. Ağ, kurulum veya yönetici izni gereken işlem ayrıca bildirilir.'
    return 'Yardım için Rıfkı’yı açabilir veya yerel kullanım rehberini okuyabilirsin. Donanım raporun kendiliğinden gönderilmez. Kaydı olmayan sesli açıklamalar yazılı kalır.'
