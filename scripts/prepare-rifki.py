#!/usr/bin/env python3
"""Üretilmiş kaynak pozlarından şeffaf, katmanlı küçük kedi rig'i hazırla.

Çalışma zamanında ağ / model / matting bağımlılığı yoktur. Pillow yeterlidir.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
RIGS = {
    'perch': {
        'tail': [(599,807),(701,779),(762,692),(748,502),(1012,506),(1011,931),(610,925)],
        'tail_pivot': [617,860],
        'head': [(132,65),(450,92),(470,344),(406,423),(147,412),(109,316)],
        'head_pivot': [306,404], 'eyes': [[240,245],[333,271]], 'mouth': [285,338],
    },
    'leap': {
        'tail': [(677,476),(728,455),(775,339),(1004,311),(1017,466),(753,587),(701,551)],
        'tail_pivot': [718,525],
    },
    'play': {
        'tail': [(2,65),(211,72),(363,232),(433,348),(354,413),(304,366),(256,283),(15,302)],
        'tail_pivot': [355,361],
        'paw': [(553,599),(656,588),(690,681),(675,782),(649,842),(599,842),(580,750),(544,679)],
        'paw_pivot': [644,804],
    },
    'tea': {
        'tail': [(679,766),(777,731),(928,557),(1017,557),(1018,755),(738,866),(685,846)],
        'tail_pivot': [702,812],
        'paw': [(96,547),(282,474),(377,493),(418,545),(350,618),(235,710),(91,731)],
        'paw_pivot': [361,555],
    },
}


def key_green(source):
    source = source.convert('RGB').resize((1024,1024), Image.Resampling.LANCZOS)
    image = Image.new('RGBA', source.size)
    pixels = []
    for r, g, b in source.getdata():
        excess = max(0, g-max(r,b)-5)
        alpha = max(0, min(255, round(255-excess*1.9)))
        if g > 100 and g > max(r,b)*1.42:
            alpha = 0
        # Yeşil key ışığının kürk kenarındaki yansımasını gider; beyaz kürkü koru.
        if g > max(r,b):
            g = min(g, round((r+b)/2)+5)
        pixels.append((r,g,b,alpha))
    image.putdata(pixels)
    return image


def prepare(source, output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'version':1, 'size':512, 'poses':{}}
    for name, config in RIGS.items():
        with Image.open(source / (name+'.png')) as raw:
            image = key_green(raw)
        base = image.copy()
        layers = {}
        # Alt gövde ve ayrılan organ arasında yumuşak 2 px bindirme kalır.
        for part in ('tail',):
            if part not in config:
                continue
            mask = Image.new('L', image.size)
            ImageDraw.Draw(mask).polygon(config[part], fill=255)
            mask = mask.filter(ImageFilter.GaussianBlur(1.2))
            layer = image.copy()
            layer.putalpha(ImageChops.multiply(image.getchannel('A'), mask))
            removal = mask.copy()
            px, py = config[part+'_pivot']
            ImageDraw.Draw(removal).ellipse((px-42,py-42,px+42,py+42),fill=0)
            remaining = ImageChops.invert(removal)
            base.putalpha(ImageChops.multiply(base.getchannel('A'), remaining))
            layer.resize((512,512),Image.Resampling.LANCZOS).save(output/(name+'-'+part+'.png'),optimize=True)
            layers[part] = [v/2 for v in config[part+'_pivot']]
        base.resize((512,512),Image.Resampling.LANCZOS).save(output/(name+'-body.png'),optimize=True)
        entry = {'layers':layers}
        if 'paw_pivot' in config:
            entry['paw'] = [90,310,90,80] if name=='tea' else [300,340,55,85]
        if 'head' in config:
            entry['head'] = [145,130,86,120]
        for key in ('eyes','mouth'):
            if key in config:
                entry[key] = [[v/2 for v in p] for p in config[key]] if key=='eyes' else [v/2 for v in config[key]]
        manifest['poses'][name]=entry
    for prop in ('teapot','tea-glass'):
        with Image.open(source/(prop+'.png')) as raw:
            key_green(raw).resize((384,384),Image.Resampling.LANCZOS).save(output/(prop+'.png'),optimize=True)
    (output/'rig.json').write_text(json.dumps(manifest,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'artwork/rifki')
    parser.add_argument('--output',type=Path,default=ROOT/'system/usr/share/oguzdows/rifki/rig')
    args=parser.parse_args()
    prepare(args.source,args.output)


if __name__=='__main__':
    main()
