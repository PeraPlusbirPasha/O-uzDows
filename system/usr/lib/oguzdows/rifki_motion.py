"""GTK'den bağımsız davranış / hareket planı; disk veya pencereyi değiştirmez."""
from __future__ import annotations

import math
from dataclasses import dataclass

ACTIONS = {'perch':8., 'jump':2.4, 'tail':8., 'feather':12., 'tea':16.}
LABELS = {'perch':'Pencerede dinleniyor', 'jump':'Pencereye zıplıyor', 'tail':'Kuyruğunu sallıyor', 'feather':'Tüy topuyla oynuyor', 'tea':'Çay demliyor ve içiyor'}


def ease(value):
    value = max(0., min(1., value))
    return value*value*(3-2*value)


def jump_path(start, end, progress, height=64):
    p = max(0., min(1., progress))
    q = ease(p)
    return (start[0]+(end[0]-start[0])*q, start[1]+(end[1]-start[1])*q-4*height*p*(1-p))


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


def perch_position(window: Rect, work: Rect):
    """Kapat / ileri düğmesini kapatmadan üst kenara yerleşecek küçük alan.

    Üstte 54 px bile yoksa en iyi tahminle kontrol üstüne çizmek yerine oyun
    alanına dönülür. Negatif ekran koordinatları çoklu monitörde geçerlidir.
    """
    gap = window.y-work.y-8
    if gap < 54 or window.width < 250:
        return None
    scale = min(1., gap/170, window.width/600)
    width, height = round(300*scale), round(224*scale)
    baseline = round(190*scale)
    x = min(work.x+work.width-width, max(work.x, window.x+24))
    y = window.y-baseline
    if y < work.y or y+height > work.y+work.height:
        return None
    return Rect(x,y,width,height)


class Behaviour:
    def __init__(self, now=0., reduced=False):
        self.action='perch'
        self.since=now
        self.paused=False
        self.reduced=reduced
        self.automatic=not reduced
        self.index=0
        self.frozen=0.
        self.paused_at=now

    def choose(self, action, now):
        if action not in ACTIONS:
            raise ValueError('Bilinmeyen kedi hareketi.')
        self.action, self.since=action,now
        self.frozen=0.

    def set_paused(self,value,now):
        if value and not self.paused:
            self.frozen=max(0.,now-self.since)
            self.paused_at=now
        elif self.paused and not value:
            self.since=now-self.frozen
        self.paused=bool(value)

    def tick(self, now):
        if self.paused:
            return self.action, self.frozen
        elapsed=max(0.,now-self.since)
        if self.automatic and elapsed>ACTIONS[self.action]:
            cycle=('tail','feather','perch','tea','jump','perch')
            self.choose(cycle[self.index%len(cycle)],now)
            self.index+=1
            elapsed=0.
        return self.action,elapsed


def pose_state(action, t, reduced=False):
    """Tek bir karedeki eklem / obje parametreleri, aralıklar sınırlıdır."""
    if action not in ACTIONS:
        action='perch'
    speed = .45 if reduced else 1.
    t=max(0.,t)*speed
    pose='play' if action=='feather' else ('tea' if action=='tea' else 'perch')
    state={'pose':pose,'x':84.,'y':15.,'scale':.37,'rotation':0.,
           'tail':7*math.sin(t*1.6),'head':1.1*math.sin(t*.9),
           'paw':0.,'breathe':1+.006*math.sin(t*2.1),'blink':t%4.8>4.60,
           'ball':None,'tea':None,'mouth':0.}
    if action=='tail':
        state['tail']=19*math.sin(t*2.)+4*math.sin(t*3.6)
    elif action=='jump':
        p=min(1.,t/2.4)
        if p<.16:
            state['breathe']=1-.13*math.sin(math.pi*p/.16)
        elif p<.88:
            flight=(p-.16)/.72
            x,y=jump_path((135.,73.),(70.,18.),flight,72.)
            state.update(pose='leap',x=x,y=y,scale=.30,rotation=8-17*ease(flight),tail=5*math.sin(t*4.))
        else:
            state.update(x=70.,y=18.,breathe=1-.08*math.sin(math.pi*(p-.88)/.12))
    elif action=='feather':
        state.update(x=45.,y=22.,scale=.36,paw=22*math.sin(t*4.),tail=10*math.sin(t*2.6),rotation=.7*math.sin(t*2.))
        phase=t%6.
        roll=ease(phase/3.) if phase<3 else 1-ease((phase-3)/3.)
        state['ball']=(315-145*roll,160-abs(31*math.sin(t*2.2)),t*1.4)
    elif action=='tea':
        phase=t%16.
        # Isıtma → demliğe / bardağa dökme → bardağı kaldırıp içme → mola.
        lift=ease((phase-7)/2)-ease((phase-11)/2)
        pour=math.sin(math.pi*max(0.,min(1.,(phase-3)/3))) if 3<phase<6 else 0.
        state.update(x=108.,y=22.,scale=.34,paw=-16*lift,head=2+4*lift,tail=4*math.sin(t*1.4))
        state['tea']={'phase':phase,'lift':lift,'pour':pour,'steam':t}
    return state
