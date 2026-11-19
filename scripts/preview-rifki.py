#!/usr/bin/env python3
"""Aynı GTK sahne çizicisinden denetlenebilir WebP / isteğe bağlı MP4 üretir.

Yalnızca açıkça verilen çıktı dizinine dosya yazar; pencere / disk kurmaz.
MP4 seçeneği için geliştirme ortamında imageio-ffmpeg gerekir, ISO'da gerekmez.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'system/usr/lib/oguzdows'))
from rifki_scene import Scene
from rifki_motion import LABELS


def font(size):
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'):
        if Path(path).is_file():
            return ImageFont.truetype(path,size)
    return ImageFont.load_default()


def preview(output, video=False):
    output.mkdir(parents=True,exist_ok=True)
    scene=Scene(ROOT/'system/usr/share/oguzdows/rifki/rig')
    sequences=(('perch',5.),('jump',2.4),('tail',6.),('feather',6.),('tea',16.))
    for action,seconds in sequences:
        frames=[]
        for i in range(round(seconds*24)):
            t=i/24
            frame=scene.render(action,t,.20*max(0.,math.sin(t*11)) if action=='perch' else 0.)
            frames.append(frame)
        frames[0].save(output/(action+'.webp'),format='WEBP',save_all=True,append_images=frames[1:],duration=round(1000/24),loop=0,quality=85,method=3)
    (output/'actions.json').write_text(json.dumps(LABELS,ensure_ascii=False)+'\n')
    if not video:
        return
    import imageio_ffmpeg
    width,height=960,640
    with Image.open(ROOT/'system/usr/share/backgrounds/oguzdows/bogaz-sabahi.jpg') as photo:
        background=photo.convert('RGBA').resize((width,height))
    background.alpha_composite(Image.new('RGBA',background.size,(10,24,32,156)))
    draw=ImageDraw.Draw(background)
    draw.rectangle((0,0,width,34),fill='#16232b')
    draw.text((22,7),'OğuzDows',font=font(16),fill='#eff6f5')
    draw.text((714,9),'Rıfkı · Hareket önizlemesi',font=font(12),fill='#9bb8bf')
    draw.rounded_rectangle((151,259,843,569),radius=13,fill='#1b2a34',outline='#5d747b',width=2)
    draw.rounded_rectangle((152,260,842,300),radius=12,fill='#2b414c')
    draw.rectangle((153,284,841,300),fill='#2b414c')
    draw.text((177,270),'OğuzDows · Kurulum rehberi',font=font(15),fill='#e8f1ef')
    draw.rounded_rectangle((798,268,827,292),radius=5,fill='#b83f57')
    draw.text((807,269),'×',font=font(17),fill='white')
    draw.text((191,332),'Rıfkı yanında.',font=font(30),fill='#eaf5f0')
    draw.text((191,391),'Küçük kedi; pencereyi veya kurulum kontrollerini kapatmaz.',font=font(17),fill='#b0c8ce')
    draw.text((191,425),'Gerçek GTK uygulamasında tıklamalar alttaki pencereye geçer.',font=font(16),fill='#b0c8ce')
    draw.text((191,464),'Zıplama · Kuyruk · Tüy topu · Çay molası',font=font(17),fill='#8ed6cd')
    draw.rounded_rectangle((661,509,802,548),radius=7,fill='#3d7373')
    draw.text((687,520),'Kontrol sende',font=font(14),fill='#e8f8f3')
    draw.text((26,608),'Aynı sahne çizicisinden önizleme · Gerçek kurulum veya fiziksel cihaz testi değildir.',font=font(13),fill='#bacbd1')
    writer=imageio_ffmpeg.write_frames(str(output/'Rifki-yeni-hareketler.mp4'),(width,height),fps=24,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',quality=8,macro_block_size=8,ffmpeg_log_level='error',output_params=['-movflags','+faststart'])
    writer.send(None)
    try:
        for action,seconds in sequences:
            for i in range(round(seconds*24)):
                frame=background.copy()
                cat=scene.render(action,i/24,size=(300,224))
                frame.alpha_composite(cat,(174,70))
                label=ImageDraw.Draw(frame)
                label.rounded_rectangle((27,66,332,99),radius=8,fill='#1b3740')
                label.text((40,74),LABELS[action],font=font(14),fill='#c3eee5')
                if action=='perch' and i==0:
                    frame.convert('RGB').save(output/'poster.jpg',quality=94)
                writer.send(frame.convert('RGB').tobytes())
    finally:
        writer.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--video',action='store_true')
    args=parser.parse_args()
    preview(args.output,args.video)


if __name__=='__main__':
    main()
