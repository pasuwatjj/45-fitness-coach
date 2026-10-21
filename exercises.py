"""Exercise catalogue. Angles are prototype counting settings, not medical limits.

The chosen exercise is supplied by the user: this is pose tracking, not an
exercise/dumbbell/grip classifier. See each entry's source and limitations.
"""
GROUPS = {'back': 'หลัง', 'arms': 'แขน', 'chest': 'อก', 'shoulders': 'ไหล่', 'legs': 'ขา'}
MAYO = 'https://www.mayoclinic.org/healthy-lifestyle/fitness/multimedia/'
ACE = 'https://www.acefitness.org/resources/everyone/exercise-library/'


def entry(id, name, group, family, equipment, camera, setup, steps, source,
          modes=('right', 'left', 'both'), default='both', limitation=''):
    return dict(id=id, name=name, group=group, group_name=GROUPS[group], family=family,
                equipment=equipment, camera=camera, setup=setup, steps=steps, source=source,
                modes=list(modes), default_arm=default, focus='full' if group == 'legs' else
                'upper',
                limitation=limitation or 'ประเมินการเคลื่อนไหวจากจุดข้อต่อ ไม่ตรวจน้ำหนักดัมเบล ข้อมือ หรือแนวกระดูกสันหลัง',
                tracking='เดิม' if id == 'curl' else 'ทดลองนับจากมุมข้อต่อ')


EXERCISES = [
    entry('single_row', 'Single-arm Dumbbell Row', 'back', 'row', 'ดัมเบล + ม้านั่งที่มั่นคง',
          'มุมเฉียงด้านแขนที่เล่น ให้เห็นไหล่ ศอก ข้อมือ และสะโพก',
          'พับสะโพก พยุงมืออีกข้างบนม้านั่ง ปล่อยแขนที่เล่นลง ค้างนิ่ง 2 วินาที',
          ['พยุงตัวบนม้านั่ง หลังอยู่แนวธรรมชาติ', 'ดึงศอกเข้าหาสะโพกโดยไม่บิดลำตัว', 'ค่อย ๆ ลดดัมเบลกลับ'],
          ACE+'126/single-arm-row/', modes=('right','left'), default='right'),
    entry('bent_row', 'Bent-over Dumbbell Row', 'back', 'row', 'ดัมเบล 2 ลูก',
          'เฉียงด้านหน้า 30–45° ให้เห็นแขนทั้งสองและสะโพก',
          'พับสะโพก งอเข่าเล็กน้อย ปล่อยแขนลง ค้างนิ่ง 2 วินาที',
          ['ดันสะโพกไปหลังและคุมแนวหลัง', 'ดึงศอกไปด้านหลังโดยไม่ยกตัวช่วย', 'ลดแขนกลับอย่างควบคุม'],
          MAYO+'bent-over-row/vid-20084680'),
    entry('supported_row', 'Chest-supported Dumbbell Row', 'back', 'row', 'ดัมเบล 2 ลูก + ม้านั่งปรับเอียง',
          'เฉียงด้านหน้า ให้เห็นแขนทั้งสองและแนวลำตัวข้างม้านั่ง',
          'คว่ำอกพิงม้านั่งเอียง ปล่อยแขนลง ค้างนิ่ง 2 วินาที',
          ['วางอกพิงเบาะเอียงและวางเท้าให้มั่นคง', 'ดึงศอกไปหลังโดยอกยังสัมผัสเบาะ', 'ลดดัมเบลลงช้า ๆ'],
          'https://www.acefitness.org/continuing-education/prosource/research-special-issue-2015/5320/dynamite-delts-ace-research-identifies-top-shoulder-exercises/'),
    entry('curl', 'Dumbbell Biceps Curl', 'arms', 'curl', 'ดัมเบล',
          'เฉียงด้านหน้า ให้เห็นหัว ไหล่ ศอก มือ และสะโพก; ทั้งสองข้างใช้มุมเฉียงหน้า',
          'ปล่อยแขนลง ศอกใกล้ลำตัว ค้างนิ่ง 2 วินาที',
          ['ฝ่ามือหันไปด้านหน้า ข้อมืออยู่แนวเดียวกับแขน', 'งอศอกยกขึ้น โดยต้นแขนอยู่ใกล้ตัว', 'ค่อย ๆ ลดแขน ไม่เหวี่ยงลำตัว'],
          MAYO+'biceps-curl/vid-20084675', default='right'),
    entry('hammer_curl', 'Dumbbell Hammer Curl', 'arms', 'curl', 'ดัมเบล',
          'เฉียงด้านหน้า ให้เห็นหัว ไหล่ ศอก มือ และสะโพก',
          'ฝ่ามือหันเข้าหาตัว ปล่อยแขนลง ค้างนิ่ง 2 วินาที',
          ['จับดัมเบลแบบนิ้วโป้งชี้ขึ้น', 'งอศอกโดยไม่ดันศอกไปด้านหน้า', 'ลดกลับช้า ๆ และรักษาข้อมือตรง'],
          ACE+'10/hammer-curl/', limitation='ดูระนาบฝ่ามือแบบทดลองตอนแขนลง มือถูกดัมเบลบังอาจยืนยันไม่ได้ ไม่ยืนยันการคว่ำหรือหงายจากทุกมุม'),
    entry('lying_triceps', 'Lying Dumbbell Triceps Extension', 'arms', 'triceps', 'ดัมเบล + พื้นรองรับหรือม้านั่ง',
          'ด้านข้างระดับลำตัว ให้เห็นไหล่ ศอก ข้อมือ และสะโพก',
          'นอนหงาย ต้นแขนชี้ขึ้น งอศอกอย่างสบาย ค้างนิ่ง 2 วินาที',
          ['นอนหงาย ต้นแขนชี้เพดานและงอศอก', 'เหยียดศอกขึ้นช้า ๆ โดยต้นแขนไม่แกว่ง', 'งอศอกกลับอย่างควบคุม ใช้น้ำหนักที่ควบคุมได้'],
          MAYO+'triceps-extension/vid-20084676'),
    entry('floor_press', 'Dumbbell Floor Press', 'chest', 'chest_press', 'ดัมเบล + เสื่อบนพื้น',
          'เฉียงด้านข้างระดับต่ำ ให้เห็นไหล่ ศอก ข้อมือ และสะโพก ไม่ถ่ายตรงจากปลายเท้า',
          'นอนหงาย งอศอกในท่าล่างอย่างสบาย ค้างนิ่ง 2 วินาที',
          ['นอนหงายและวางเท้าบนพื้น', 'ดันดัมเบลขึ้นโดยไม่ฝืนล็อกศอก', 'ลดช้า ๆ ให้ต้นแขนแตะพื้นเบา ๆ ไม่กระแทก'],
          MAYO+'chest-press/vid-20084677'),
    entry('bench_press', 'Dumbbell Bench Press', 'chest', 'chest_press', 'ดัมเบล + ม้านั่งราบ',
          'เฉียงด้านข้างระดับม้านั่ง ให้เห็นแขนและสะโพก',
          'นอนบนม้านั่ง งอศอกในท่าล่าง ค้างนิ่ง 2 วินาที',
          ['ศีรษะ หลัง และสะโพกมีเบาะรองรับ เท้าวางมั่นคง', 'ดันขึ้นอย่างควบคุม ไม่ใช้เท้าถีบช่วย', 'ลดศอกไม่ต่ำกว่าแนวลำตัว'],
          MAYO+'chest-press/vid-20084677'),
    entry('incline_press', 'Incline Dumbbell Chest Press', 'chest', 'incline_press', 'ดัมเบล + ม้านั่งปรับเอียง',
          'เฉียงข้างให้เห็นมุมพนักพิง ไหล่ ศอก ข้อมือ และสะโพก',
          'เอนบนม้านั่งเอียง งอศอกในท่าล่าง ค้างนิ่ง 2 วินาที',
          ['ปรับพนักพิงและวางเท้าให้มั่นคง', 'ดันดัมเบลขึ้นโดยหลังยังพิงเบาะ', 'ลดกลับช้า ๆ รักษาข้อมืออยู่เหนือศอก'],
          ACE+'25/incline-chest-press/'),
    entry('shoulder_press', 'Dumbbell Shoulder Press', 'shoulders', 'shoulder_press', 'ดัมเบล',
          'เฉียงด้านหน้า ให้เห็นสะโพกถึงมือเมื่อยกเหนือศีรษะ',
          'ยืนมั่นคง ยกต้นแขนและงอศอกในท่าเตรียม ค้างนิ่ง 2 วินาที',
          ['ถือดัมเบลข้างไหล่และเกร็งลำตัวพอสบาย', 'ดันขึ้นเหนือศีรษะโดยไม่แอ่นหลังช่วย', 'ค่อย ๆ ลดกลับระดับไหล่'],
          'https://www.acefitness.org/continuing-education/prosource/research-special-issue-2015/5320/dynamite-delts-ace-research-identifies-top-shoulder-exercises/'),
    entry('lateral_raise', 'Dumbbell Lateral Raise', 'shoulders', 'raise', 'ดัมเบล',
          'หันหน้าหากล้อง ให้เห็นสะโพกและมือทั้งสองเมื่อกางแขน',
          'ยืนตัวตรง ปล่อยแขนข้างตัว ค้างนิ่ง 2 วินาที',
          ['งอศอกเล็กน้อยและใช้ดัมเบลที่ควบคุมได้', 'ยกแขนออกข้างประมาณระดับไหล่', 'ลดกลับช้า ๆ โดยไม่เหวี่ยงตัว'],
          ACE+'26/lateral-raise/', limitation='ดูมุมต้นแขนกับลำตัวและการโยกตัว ยังไม่ยืนยันการหมุนข้อไหล่หรือแรงกดในข้อ'),
    entry('front_raise', 'Dumbbell Front Raise', 'shoulders', 'raise', 'ดัมเบล',
          'ด้านข้างหรือเฉียง ให้เห็นไหล่ถึงสะโพกและมือเมื่อยกไปด้านหน้า',
          'ยืนตัวตรง ปล่อยแขนหน้าขา ค้างนิ่ง 2 วินาที',
          ['รักษาศอกงอเล็กน้อยและข้อมือตรง', 'ยกแขนไปด้านหน้าประมาณระดับไหล่', 'ลดกลับอย่างควบคุมโดยไม่เอนตัวช่วย'],
          ACE+'54/front-raise/', limitation='ดูมุมต้นแขนกับลำตัว ไม่จำแนกทิศหน้ากับข้างอัตโนมัติ ต้องเลือกท่าและตั้งกล้องให้ตรงคู่มือ'),
    entry('goblet_squat', 'Dumbbell Goblet Squat', 'legs', 'squat', 'ดัมเบล 1 ลูก',
          'ด้านข้าง ให้เห็นไหล่ สะโพก เข่า และข้อเท้า เลือกด้านที่หันเข้ากล้อง',
          'ยืนมั่นคง ถือดัมเบลหน้าอก ค้างนิ่ง 2 วินาที',
          ['ถือดัมเบลใกล้อกและวางเท้ามั่นคง', 'ย่อสะโพกลงเท่าที่ควบคุมได้ เข่าไปทิศเดียวกับปลายเท้า', 'ดันพื้นกลับมายืน ไม่เด้งหรือฝืนความลึก'],
          ACE+'362/goblet-squat/', modes=('right','left'), default='right',
          limitation='นับจากเข่าด้านที่กล้องเห็น ท่านี้ใช้สองขา แม้เลือกติดตามด้านเดียว; ไม่วัดแนวเข่ายุบจากมุมด้านข้าง'),
    entry('rdl', 'Dumbbell Romanian Deadlift', 'legs', 'hinge', 'ดัมเบล 2 ลูก',
          'ด้านข้าง ให้เห็นไหล่ สะโพก เข่า และข้อเท้า เลือกด้านที่หันเข้ากล้อง',
          'ยืนตรงและผ่อนเข่าเล็กน้อย ค้างนิ่ง 2 วินาที',
          ['ถือดัมเบลใกล้ขาและผ่อนเข่าเล็กน้อย', 'ดันสะโพกไปหลัง พับที่สะโพก รักษาแนวหลัง', 'กลับมายืนด้วยสะโพก ไม่แอ่นหลังตอนบนสุด'],
          'https://www.acefitness.org/continuing-education/certified/may-2025/8865/the-ace-do-it-better-series-the-romanian-deadlift/',
          modes=('right','left'), default='right', limitation='นับจากมุมสะโพกและดูเข่างอมากเกินไป ไม่ตรวจความโค้งกระดูกสันหลังหรือแรงที่หลังส่วนล่าง'),
    entry('split_squat', 'Dumbbell Split Squat', 'legs', 'squat', 'ดัมเบล',
          'ด้านข้าง ให้เห็นไหล่ถึงข้อเท้า เลือกซ้าย/ขวาตามขาที่อยู่ด้านหน้า',
          'ยืนแยกเท้าหน้าหลัง ขาหน้าเกือบตรง ค้างนิ่ง 2 วินาที',
          ['แยกเท้าหน้าหลังบนพื้นและรักษาสมดุล', 'ย่อตัวลงโดยเข่าหน้าไปทางเดียวกับปลายเท้า', 'กลับขึ้นอย่างควบคุม ทำอีกข้างเป็นรายการแยกในตาราง'],
          'https://www.dvidshub.net/video/548725/dumbbell-split-squat',
          modes=('right','left'), default='right', limitation='ติดตามเข่าขาหน้า ต้องเพิ่มรายการขาซ้ายและขาขวาแยกกันในตาราง; ไม่ประเมินการทรงตัวได้ครบทุกมิติ'),
]
CATALOG = {e['id']: e for e in EXERCISES}

# Natural joint angle at start / far end / minimum excursion. Tolerance permits
# a near endpoint, while the minimum excursion still rejects tiny movements.
MOTIONS = {
    'row': (150, 80, 45, False, 'มุมศอก'),
    'triceps': (95, 155, 40, True, 'มุมศอก'),
    'chest_press': (100, 155, 40, True, 'มุมศอก'),
    'incline_press': (100, 155, 40, True, 'มุมศอก'),
    'shoulder_press': (100, 155, 40, True, 'มุมศอก'),
    'raise': (20, 80, 40, True, 'มุมต้นแขนกับลำตัว'),
    'squat': (160, 105, 40, False, 'มุมเข่า'),
    'hinge': (165, 105, 40, False, 'มุมสะโพก'),
}


def thresholds(exercise, tolerance):
    family = CATALOG[exercise]['family']
    if family == 'curl':
        return dict(start=max(140-tolerance,min(100,85+tolerance)+25), end=min(100,85+tolerance), excursion=max(30,45-max(0,tolerance-10)*.35),
                    increasing=False, label='มุมศอก')
    start, end, excursion, increasing, label = MOTIONS[family]
    effective=min(tolerance,(abs(end-start)-20)/2)
    excursion=max(25,excursion-max(0,tolerance-10)*.35)
    return dict(start=start+effective if increasing else start-effective,
                end=end-effective if increasing else end+effective,
                excursion=excursion, increasing=increasing, label=label)

# Photographs from the public-domain free-exercise-db; selected variants use
# original SVG diagrams to avoid teaching a different exercise.
for ex in EXERCISES:
    schematic=ex['id'] in ('front_raise','goblet_squat','rdl','split_squat')
    suffix='svg' if schematic else 'jpg'
    ex['images']=[f"/static/images/exercises/{ex['id']}-{i}.{suffix}" for i in (0,1)]
    ex['image_source']=ex['source'] if schematic else 'https://github.com/yuhonas/free-exercise-db'
    ex['teaching']=ex['name']+'. '+'. '.join(ex['steps'])+'. '+ex['setup']

for ex in EXERCISES:
    if ex['id']=='curl':
        ex['teaching']='กำด้ามให้มั่น นิ้วโป้งโอบรอบด้าม หงายฝ่ามือไปข้างหน้า ข้อมือตรง ศอกอยู่ข้างตัว งอศอกยกขึ้นแล้วลดกลับ ไม่เหวี่ยงตัวนะ ก่อนเริ่มให้กล้องเห็นมือและครึ่งตัว แล้วปล่อยแขนลงค้างสองวินาที'
    elif ex['id']=='hammer_curl':
        ex['teaching']='กำด้ามให้มั่น นิ้วโป้งโอบรอบด้าม ฝ่ามือหันเข้าหากัน ยกแบบถือค้อนโดยไม่หมุนข้อมือ ศอกอยู่ข้างตัว ยกขึ้นแล้วลดกลับ ก่อนเริ่มให้กล้องเห็นมือและครึ่งตัว แล้วปล่อยแขนลงค้างสองวินาที'
    else:
        ex['teaching']=ex['name']+'. '+'. '.join(ex['steps'][:3])+'. '+ex['setup']

# User-supplied Jeff demonstration pages, preserving every supplied step.
JEFF_PAGES={'split_squat':[2,1],'rdl':[3,4],'goblet_squat':[5,6],
    'front_raise':[7,8,9],'lateral_raise':[10,11],'shoulder_press':[12,13,14],
    'incline_press':[16,15],'bench_press':[17,18],'floor_press':[19,20],
    'curl':[21,22],'hammer_curl':[23,24],'single_row':[25,26],'bent_row':[27,28]}
for ex in EXERCISES:
    if ex['id'] in JEFF_PAGES:
        ex['images']=[f'/static/images/jeff/page-{p:02}.jpg' for p in JEFF_PAGES[ex['id']]]
        ex['image_source']=''
        ex['image_credit']='Jeff'
        ex['image_note']='ภาพที่ให้มาสาธิตบนพื้น หากฝึก Bench Press ต้องใช้ม้านั่งที่มั่นคง' if ex['id']=='bench_press' else ''
        if ex['id']=='split_squat':ex['image_note']='ภาพนี้เป็น Split Squat รูปแบบยกเท้าหลังบนม้านั่ง'
        ex['image_note_en']=('The supplied demonstration is on the floor. A bench press requires a stable bench.' if ex['id']=='bench_press' else 'This demonstration shows the rear-foot-elevated split squat variation.' if ex['id']=='split_squat' else '')

# v24: camera yaw uses estimated 3-D geometry when readable.
for ex in EXERCISES:
    ex['camera']='ใช้มุมหน้าหรือด้านข้าง ให้เห็นข้อต่อของข้างที่เลือกครบ หากแขนหรือขาบังกันให้ขยับกล้องเฉียงเล็กน้อย'
    if ex['group']=='legs':ex['camera']+=' ต้องเห็นไหล่ สะโพก เข่า และข้อเท้า'
    else:ex['camera']+=' ต้องเห็นไหล่ ศอก ข้อมือ และสะโพก'
    if ex['id']=='shoulder_press':
        ex['setup']='ยืนตรง ถือดัมเบลข้างขา ค้างนิ่ง 2 วินาที แล้วยกมาระดับไหล่ก่อนดันขึ้น การยกเข้าท่าเตรียมยังไม่นับ'
    elif ex['id']=='lateral_raise':ex['setup']='ยืนตรง ถือดัมเบลข้างขา ค้างนิ่ง 2 วินาที แล้วยกออกด้านข้าง'
    elif ex['id']=='front_raise':ex['setup']='ยืนตรง ถือดัมเบลหน้าขา ค้างนิ่ง 2 วินาที แล้วยกไปด้านหน้า'
    if ex['group']=='shoulders':ex['teaching']=ex['setup']+'. '+'. '.join(ex['steps'])
