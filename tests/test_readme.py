"""Proje vitrini: yerel bağlantılar, küçük görseller ve dürüst yayın kimliği."""
import re
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from PIL import Image

from support import ROOT

LANDSCAPES = ('bogaz-sabahi', 'kackar-sisi', 'kapadokya-isigi',
              'oludeniz-kiyisi', 'tuz-golu-aksami', 'ani-kisi')


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ('href', 'src') and value:
                self.links.append(value)
            elif name in ('id', 'name') and value:
                self.anchors.add(value)


class ReadmeTests(unittest.TestCase):
    def test_local_markdown_html_images_and_explicit_navigation_anchors_resolve(self):
        for name in ('README.md', 'docs/TEKNIK-REHBER.md', 'docs/SURUM-POLITIKASI.md', 'docs/assets/README.md'):
            path = ROOT / name
            text = re.sub(r'```.*?```', '', path.read_text(), flags=re.DOTALL)
            html = References()
            html.feed(text)
            links = html.links + re.findall(r'\[[^\]\n]+\]\(([^)\n]+)\)', text)
            self.assertTrue(links)
            for link in links:
                with self.subTest(document=name, link=link):
                    target = urlsplit(link)
                    if target.scheme or target.netloc:
                        self.assertEqual(target.scheme, 'https')
                        continue
                    if not target.path:
                        self.assertIn(unquote(target.fragment), html.anchors)
                        continue
                    destination = (path.parent / unquote(target.path)).resolve()
                    self.assertTrue(destination.is_relative_to(ROOT))
                    self.assertTrue(destination.is_file(), destination)

    def test_downloads_keep_published_v1_while_future_major_names_are_only_policy(self):
        text = (ROOT / 'README.md').read_text()
        links = re.findall(r'https://github\.com/PeraPlusbirPasha/O-uzDows/releases/download/([^/]+)/([^\s)"<>]+)', text)
        self.assertEqual(set(links), {('v1.0.0', name) for name in (
            'OguzDows-amd64.iso', 'OguzDows-amd64.iso.sha256',
            'OguzDows-i386.iso', 'OguzDows-i386.iso.sha256', 'SHA256SUMS')})
        for tag in ('v1.0.0', 'v2.0', 'v3.0'):
            self.assertIn(tag, text)
            self.assertIn(tag, (ROOT / 'docs/SURUM-POLITIKASI.md').read_text())
        self.assertIn('yeniden adlandırılmaz', text)
        self.assertIn('gerçek kamera fotoğrafı', text)
        self.assertIn('masaüstü ekran görüntüsü değil', text)
        self.assertIn('Debian trixie', text)
        self.assertIn('Debian bookworm', text)

    def test_banner_is_static_and_all_six_gallery_previews_are_small_local_derivatives(self):
        banner = ROOT / 'docs/assets/oguzdows-banner.svg'
        root = ET.parse(banner).getroot()
        self.assertEqual(root.attrib['viewBox'], '0 0 1600 560')
        self.assertLess(banner.stat().st_size, 20_000)
        for element in root.iter():
            self.assertNotIn(element.tag.rsplit('}', 1)[-1], ('script', 'foreignObject', 'image'))
            for name, value in element.attrib.items():
                self.assertFalse(name.lower().startswith('on'))
                if name.rsplit('}', 1)[-1] == 'href':
                    self.assertTrue(value.startswith('#'))
        total = 0
        for name in LANDSCAPES:
            path = ROOT / 'docs/assets' / (name + '.jpg')
            total += path.stat().st_size
            with self.subTest(image=name), Image.open(path) as image:
                self.assertEqual(image.size, (480, 270))
                self.assertEqual(image.format, 'JPEG')
            self.assertTrue((ROOT / 'system/usr/share/backgrounds/oguzdows' / (name + '.jpg')).is_file())
        self.assertLess(total, 200_000)

    def test_detailed_installer_and_legacy_device_safeguards_are_kept_in_technical_guide(self):
        guide = (ROOT / 'docs/TEKNIK-REHBER.md').read_text()
        for preserved in ('mbr-before-active-', 'quit-at-end: false',
                          'EFI/BOOT/BOOTX64.EFI', '--no-download --no-remove',
                          'No bootable device', 'broadcom-sta-dkms'):
            self.assertIn(preserved, guide)
        self.assertIn('../README.md', guide)
        self.assertIn('MASAUSTU-TEST-KANITI.md', guide)
        self.assertNotIn('](docs/', guide)


if __name__ == '__main__':
    unittest.main()
