"""Game difficulty presets and hysteretic arm selection; not clinical standards."""
from exercises import CATALOG

LEVELS=('beginner','pro','expert')
# Endpoints remain exercise-specific (exercises.MOTIONS); these are game margins.
MARGINS={'curl':(3,0),'row':(4,1),'triceps':(4,1),'chest_press':(4,1),
         'incline_press':(4,1),'shoulder_press':(4,1),'raise':(3,0),
         'squat':(4,1),'hinge':(4,1)}

def options(exercise,level,tolerance,settings,target=80):
    if level not in LEVELS:raise ValueError('Invalid difficulty / ระดับไม่ถูกต้อง')
    cfg=dict(settings)
    if level=='beginner':
        cfg['curl_target_deg']=target
        return cfg,tolerance
    expert=level=='expert';margin=MARGINS[CATALOG[exercise]['family']][int(expert)]
    cfg.update(curl_target_deg=50 if expert else 60,extension_count_grace_deg=0 if expert else 5,
               minimum_rep_excursion_deg=65 if expert else 55,
               torso_base_limit_deg=7 if expert else 10,upper_arm_base_limit_deg=10 if expert else 15)
    return cfg,margin

def supports_auto(exercise):
    return CATALOG[exercise]['group']!='legs' and {'left','right'}<=set(CATALOG[exercise]['modes'])

class ArmSelector:
    """Prefer the clearly visible arm; never oscillate when both are equally visible."""
    def __init__(self,side='right'):
        self.side=side;self.candidate=None;self.since=None;self.samples=0
    def choose(self,landmarks,now):
        scores={}
        for side,ids in [('left',(11,13,15)),('right',(12,14,16))]:
            points=[landmarks[i] for i in ids] if landmarks and len(landmarks)>16 else []
            good=points and all((p.visibility or 0)>=.65 and (getattr(p,'presence',1) or 0)>=.65 and 0<=p.x<=1 and 0<=p.y<=1 for p in points)
            scores[side]=sum(min(p.visibility or 0,getattr(p,'presence',1) or 0) for p in points)/3 if good else 0
        other='left' if self.side=='right' else 'right'
        candidate=other if scores[other]>.65 and (scores[self.side]==0 or scores[other]>scores[self.side]+.18) else None
        if candidate!=self.candidate:self.candidate=candidate;self.since=now;self.samples=0
        if candidate:
            self.samples+=1
            if now-self.since>=450 and self.samples>=3:
                self.side=candidate;self.candidate=None;self.samples=0
                return self.side,True
        return self.side,False
