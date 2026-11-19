"""Tek küçük RGBA sahne: katmanlı kürk, eklemler, oyuncak ve çay molası.

Aynı Pillow çizicisi masaüstünde, önizlemede ve kare regresyon testinde kullanılır.
Kaynak PNG'ler yalnızca açılışta yüklenir; kare başına dosya / ağ işlemi yoktur.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from rifki_motion import pose_state

ASSETS = Path('/usr/share/oguzdows/rifki/rig')


class Scene:
    def __init__(self, assets=ASSETS):
        self.manifest=json.loads((assets/'rig.json').read_text())
        self.parts={}
        self.cache={}
        for pose, config in self.manifest['poses'].items():
            for name in ['body',*config['layers']]:
                with Image.open(assets/(pose+'-'+name+'.png')) as image:
                    self.parts[(pose,name)]=image.convert('RGBA')
        self.props={}
        for name in ('teapot','tea-glass'):
            with Image.open(assets/(name+'.png')) as image:
                rgba=image.convert('RGBA')
                self.props[name]=rgba.crop(rgba.getbbox())

    def scaled(self, pose, part, size):
        key=(pose,part,size)
        if key not in self.cache:
            if len(self.cache)>=24:
                self.cache.pop(next(iter(self.cache)))
            self.cache[key]=self.parts[(pose,part)].resize((size,size),Image.Resampling.LANCZOS)
        return self.cache[key]

    @staticmethod
    def deform(image, config, state, scale):
        fields=[]
        if config.get('head'):
            x,y,rx,ry=config['head']
            fields.append((x*scale,y*scale,rx*scale,ry*scale,state['head']*1.5*scale,0.))
        if config.get('paw') and abs(state['paw'])>.01:
            x,y,rx,ry=config['paw']
            lift=state['paw']/57.
            fields.append((x*scale,y*scale,rx*scale,ry*scale,-18*lift*scale,70*lift*scale))
        if not fields:
            return image
        width,height=image.size
        def source(x,y):
            dx=dy=0.
            for cx,cy,rx,ry,mx,my in fields:
                weight=math.exp(-2*((x-cx)/rx)**2-2*((y-cy)/ry)**2)
                dx+=mx*weight
                dy+=my*weight
            return x-dx,y-dy
        mesh=[]
        step=max(12,width//14)
        for top in range(0,height,step):
            for left in range(0,width,step):
                right,bottom=min(width,left+step),min(height,top+step)
                quad=(*source(left,top),*source(left,bottom),*source(right,bottom),*source(right,top))
                mesh.append(((left,top,right,bottom),quad))
        return image.transform(image.size,Image.Transform.MESH,mesh,Image.Resampling.BICUBIC)

    def cat(self, state, size, amplitude, supersample=2):
        s=supersample
        image=Image.new('RGBA',(size[0]*s,size[1]*s))
        pose=state['pose']
        config=self.manifest['poses'][pose]
        scale=state['scale']*s
        n=max(1,round(512*scale))
        x,y=round(state['x']*s),round(state['y']*s)
        for name in ('tail','body'):
            if (pose,name) not in self.parts:
                continue
            sprite=self.scaled(pose,name,n)
            if name=='body':
                sprite=sprite.copy()
                draw=ImageDraw.Draw(sprite)
                if state['blink']:
                    for ex,ey in config.get('eyes',[]):
                        ex,ey=ex*scale,ey*scale
                        draw.ellipse((ex-12*scale,ey-8*scale,ex+12*scale,ey+8*scale),fill=(188,164,141,255))
                        draw.arc((ex-10*scale,ey-7*scale,ex+10*scale,ey+5*scale),12,164,fill='#4d4541',width=max(1,round(2*scale)))
                if amplitude>.05 and config.get('mouth'):
                    mx,my=(v*scale for v in config['mouth'])
                    rx=max(1,6*scale)
                    ry=max(1,(1+7*amplitude)*scale)
                    draw.ellipse((mx-rx,my-ry,mx+rx,my+ry),fill='#462b31')
                    if amplitude>.28:
                        draw.ellipse((mx-rx*.55,my,mx+rx*.55,my+ry*.8),fill='#d5949b')
                sprite=self.deform(sprite,config,state,scale)
                height=round(n*state['breathe'])
                sprite=sprite.resize((n,height),Image.Resampling.BICUBIC)
                image.alpha_composite(sprite,(x,y+n-height))
            else:
                bbox=sprite.getbbox()
                if not bbox:
                    continue
                cropped=sprite.crop(bbox)
                angle=state.get(name,0.)
                px,py=config['layers'][name]
                px,py=x+px*scale,y+py*scale
                cx,cy=x+(bbox[0]+bbox[2])/2,y+(bbox[1]+bbox[3])/2
                rad=math.radians(angle)
                dx,dy=cx-px,cy-py
                center=(px+dx*math.cos(rad)+dy*math.sin(rad),py-dx*math.sin(rad)+dy*math.cos(rad))
                rotated=cropped.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
                image.alpha_composite(rotated,(round(center[0]-rotated.width/2),round(center[1]-rotated.height/2)))
        if state['rotation']:
            image=image.rotate(state['rotation'],resample=Image.Resampling.BICUBIC,center=(x+n*.5,y+n*.8))
        return image

    def render(self, action, t, amplitude=0., size=(300,224), reduced=False, shelf=False):
        state=pose_state(action,t,reduced)
        if action=='tail':
            state['tail']=-45+18*math.sin(max(0.,t)*2)
        if action=='tea':
            state['paw']=-57*state['tea']['lift']
        # Oyun sahnesi mantıksal 300×224; tüm pencere boyutlarında aynı geometri.
        image=self.cat(state,(300,224),max(0.,min(1.,amplitude)))
        if shelf:
            ledge=Image.new('RGBA',image.size)
            d=ImageDraw.Draw(ledge)
            d.rounded_rectangle((24,380,574,394),radius=6,fill='#50646a')
            d.line((28,381,570,381),fill='#a6c8c4',width=2)
            ledge.alpha_composite(image)
            image=ledge
        if state['ball']:
            self.feather(image,state['ball'])
        if state['tea']:
            self.tea(image,state['tea'])
        fitted=ImageOps.contain(image,size,Image.Resampling.LANCZOS)
        frame=Image.new('RGBA',size)
        frame.alpha_composite(fitted,((size[0]-fitted.width)//2,(size[1]-fitted.height)//2))
        return frame

    @staticmethod
    def feather(image, ball):
        x,y,rotation=ball
        x,y=x*2,y*2
        draw=ImageDraw.Draw(image)
        draw.ellipse((x-13,y+14,x+18,y+20),fill=(0,0,0,24))
        draw.ellipse((x-11,y-10,x+11,y+11),fill='#d8dce3',outline='#a2bac3',width=2)
        for i in range(34):
            angle=i*math.tau/34+rotation
            reach=15+5*math.sin(i*4.3)
            draw.line((x+8*math.cos(angle),y+8*math.sin(angle),x+reach*math.cos(angle),y+reach*math.sin(angle)),fill=('#faf7e9' if i%3 else '#9fd7d8'),width=2)
        stem=(x-19*math.sin(rotation*.4),y-43)
        draw.line((x,y,*stem),fill='#bbd6cf',width=2)
        for i in range(10):
            yy=y-10-i*3
            spread=7*math.sin((i+1)*math.pi/12)
            cx=x+(stem[0]-x)*(i+3)/14
            draw.line((cx-spread,yy-4,cx,yy+2,cx+spread,yy-4),fill='#f3e5bc',width=2)

    def tea(self, image, tea):
        d=ImageDraw.Draw(image)
        phase,lift,pour,t=tea['phase'],tea['lift'],tea['pour'],tea['steam']
        # Küçük bakır çaydanlık, demlik, ocak ve buhar. Sıcak içecek yalnızca animasyondur.
        kx,ky=76-20*pour,143-25*pour
        kx,ky=kx*2,ky*2
        d.rounded_rectangle((91,333,203,353),radius=8,fill='#344249',outline='#83969b',width=2)
        d.ellipse((118,321,175,335),fill='#ecb86b')
        pot=self.props['teapot']
        pot=pot.resize((142,round(142*pot.height/pot.width)),Image.Resampling.LANCZOS)
        pot=pot.rotate(-16*pour,Image.Resampling.BICUBIC,expand=True)
        image.alpha_composite(pot,(round(kx-pot.width/2),round(ky-pot.height+35)))
        # Bardak / tabak birlikte patiye ve ağıza yaklaşır.
        cx,cy=(129+21*lift)*2,(151-42*lift)*2
        glass=self.props['tea-glass']
        glass=glass.resize((51,round(51*glass.height/glass.width)),Image.Resampling.LANCZOS)
        sip=(max(0.,math.sin((phase-8)*math.pi*2))*5 if 8<phase<12 else 0.)
        glass=glass.rotate(sip,Image.Resampling.BICUBIC,expand=True)
        image.alpha_composite(glass,(round(cx-glass.width/2),round(cy-glass.height+17)))
        if pour>.03:
            d.line([(kx+63,ky-19),(cx-4,cy-27)],fill=(171,94,39,220),width=3)
        for i in range(3):
            sx=(76+i*5)*2
            points=[(sx+math.sin(t*2-j*.7+i)*5,256-j*5-(t*10%9)) for j in range(14)]
            d.line(points,fill=(230,244,243,95),width=2)
