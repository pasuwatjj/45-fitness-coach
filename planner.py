"""Per-profile calendar. Set credits are awarded from saved server counters only."""
import calendar
from datetime import date, datetime, timedelta, timezone
import re

from exercises import CATALOG

SCHEMA = '''
CREATE TABLE IF NOT EXISTS workout_days (
    id INTEGER PRIMARY KEY, profile_id INTEGER NOT NULL REFERENCES profiles(id),
    day TEXT NOT NULL, completed_at TEXT, UNIQUE(profile_id,day));
CREATE TABLE IF NOT EXISTS plan_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT, day_id INTEGER NOT NULL REFERENCES workout_days(id),
    position INTEGER NOT NULL, exercise TEXT NOT NULL, arm_mode TEXT NOT NULL,
    target_sets INTEGER NOT NULL, target_reps INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS items_day ON plan_items(day_id,position);
CREATE TABLE IF NOT EXISTS plan_credits (
    set_id TEXT PRIMARY KEY REFERENCES workout_sets(id),
    item_id INTEGER NOT NULL REFERENCES plan_items(id), set_number INTEGER NOT NULL,
    UNIQUE(item_id,set_number));
'''


def today_thailand():
    return datetime.now(timezone(timedelta(hours=7))).date()


def day_value(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        raise ValueError('วันที่ต้องอยู่ในรูปแบบ YYYY-MM-DD')
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError('วันที่ไม่ถูกต้อง') from None


def month_days(month):
    if not isinstance(month,str) or not re.fullmatch(r'\d{4}-\d{2}',month):
        raise ValueError('เลือกเดือนให้ถูกต้อง')
    first = day_value(month+'-01')
    if not 2020 <= first.year <= 2100:
        raise ValueError('เลือกปีระหว่าง 2020–2100')
    return [first+timedelta(days=i) for i in range(calendar.monthrange(first.year,first.month)[1])]


def validate_items(items):
    if not isinstance(items,list) or len(items)>15:
        raise ValueError('กำหนดได้ไม่เกิน 15 รายการต่อวัน หรือเว้นว่างเป็นวันพัก')
    clean = []
    for item in items:
        if not isinstance(item,dict):
            raise ValueError('รายการท่าไม่ถูกต้อง')
        ex = item.get('exercise')
        if not isinstance(ex,str) or ex not in CATALOG:
            raise ValueError('เลือกท่าจากรายการที่เปิดใช้งาน')
        mode = item.get('arm_mode',CATALOG[ex]['default_arm'])
        if mode not in CATALOG[ex]['modes']:
            raise ValueError('ด้านที่เลือกใช้กับท่านี้ไม่ได้')
        sets,reps = item.get('target_sets'),item.get('target_reps')
        if type(sets) is not int or not 1<=sets<=10 or type(reps) is not int or not 1<=reps<=100:
            raise ValueError('ตั้ง 1–10 เซต และ 1–100 ครั้งต่อเซต')
        clean.append(dict(exercise=ex,arm_mode=mode,target_sets=sets,target_reps=reps))
    return clean


def streaks(days, today):
    """Only scheduled training days increment/break a streak; rest is neutral.

    Today remains possible until midnight in Thailand. Future days are ignored.
    Missing past scheduled training breaks the chain without deleting history.
    """
    current=best=completed=0
    for day in sorted(days,key=lambda x:x['date']):
        if day['date']>today.isoformat() or not day['items']:
            continue
        if day['complete']:
            current+=1
            completed+=1
            best=max(best,current)
        elif day['date']<today.isoformat():
            current=0
    return dict(current=current,best=best,completed=completed,
                label='วันฝึกตามแผน',note='วันพักไม่เพิ่มและไม่ตัดไฟ ขาดวันฝึกที่วางแผนไว้จะเริ่มนับใหม่ในวันถัดไป')


class PlannerMixin:
    @staticmethod
    def _day(db, profile_id, day, today):
        row = db.execute('SELECT * FROM workout_days WHERE profile_id=? AND day=?',
                         (profile_id,day)).fetchone()
        result = dict(date=day,planned=bool(row),items=[],complete=False,completed_sets=0,
                      total_sets=0,status='empty',locked=day<today.isoformat())
        if not row:
            return result
        items = db.execute('''SELECT i.*,COUNT(c.set_id) AS completed_sets
            FROM plan_items i LEFT JOIN plan_credits c ON c.item_id=i.id
            WHERE i.day_id=? GROUP BY i.id ORDER BY i.position''',(row['id'],)).fetchall()
        for item in items:
            ex = CATALOG[item['exercise']]
            result['items'].append(dict(id=item['id'],exercise=item['exercise'],name=ex['name'],
                group=ex['group'],group_name=ex['group_name'],arm_mode=item['arm_mode'],
                target_sets=item['target_sets'],target_reps=item['target_reps'],
                completed_sets=item['completed_sets'],complete=item['completed_sets']>=item['target_sets']))
        result['total_sets'] = sum(i['target_sets'] for i in result['items'])
        result['completed_sets'] = sum(i['completed_sets'] for i in result['items'])
        result['complete'] = bool(items) and result['completed_sets']>=result['total_sets']
        result['locked'] |= result['completed_sets']>0
        result['can_adjust'] = day==today.isoformat() and not result['complete']
        result['status'] = ('rest' if not items else 'complete' if result['complete'] else
                            'missed' if day<today.isoformat() else
                            'progress' if result['completed_sets'] else 'planned')
        return result

    def plan_day(self, profile_id, day=None):
        today = today_thailand()
        day = today.isoformat() if day is None else day_value(day).isoformat()
        with self.lock,self.connect() as db:
            return self._day(db,profile_id,day,today)

    def plan_month(self, profile_id, month):
        dates = month_days(month)
        today = today_thailand()
        with self.lock,self.connect() as db:
            profile = db.execute('SELECT id,name FROM profiles WHERE id=?',(profile_id,)).fetchone()
            if not profile:
                raise ValueError('ไม่พบชื่อผู้เล่น')
            days = [self._day(db,profile_id,d.isoformat(),today) for d in dates]
            rows = db.execute('SELECT day FROM workout_days WHERE profile_id=? AND day<=? ORDER BY day',
                              (profile_id,today.isoformat())).fetchall()
            history = [self._day(db,profile_id,r['day'],today) for r in rows]
            return dict(profile=dict(profile),month=month,today=today.isoformat(),days=days,
                        streak=streaks(history,today),today_plan=self._day(db,profile_id,today.isoformat(),today))

    @staticmethod
    def _replace_day(db, profile_id, day, items):
        db.execute('INSERT OR IGNORE INTO workout_days(profile_id,day) VALUES(?,?)',(profile_id,day))
        day_id = db.execute('SELECT id FROM workout_days WHERE profile_id=? AND day=?',
                            (profile_id,day)).fetchone()['id']
        db.execute('DELETE FROM plan_items WHERE day_id=?',(day_id,))
        db.execute('UPDATE workout_days SET completed_at=NULL WHERE id=?',(day_id,))
        db.executemany('''INSERT INTO plan_items(day_id,position,exercise,arm_mode,target_sets,target_reps)
                       VALUES(?,?,?,?,?,?)''',[(day_id,pos,i['exercise'],i['arm_mode'],i['target_sets'],i['target_reps'])
                                             for pos,i in enumerate(items)])

    def upload_week(self, profile_id, data, active_date=None):
        if not isinstance(data,dict):
            raise ValueError('รูปแบบตารางไม่ถูกต้อง')
        dates = month_days(data.get('month'))
        start = day_value(data.get('start_date'))
        today = today_thailand()
        if start.strftime('%Y-%m')!=data['month'] or start<today:
            raise ValueError('วันเริ่มต้องอยู่ในเดือนที่เลือก และไม่เป็นวันย้อนหลัง')
        week = data.get('week')
        if not isinstance(week,dict) or set(week)!={str(i) for i in range(7)}:
            raise ValueError('กำหนดให้ครบจันทร์ถึงอาทิตย์ โดยวันพักเป็นรายการว่าง')
        week = {k:validate_items(v) for k,v in week.items()}
        changed,skipped = [],[]
        with self.lock,self.connect() as db:
            if not db.execute('SELECT id FROM profiles WHERE id=?',(profile_id,)).fetchone():
                raise ValueError('ไม่พบชื่อผู้เล่น')
            for d in dates:
                if d<start:
                    continue
                key=d.isoformat()
                existing=self._day(db,profile_id,key,today)
                if key==active_date or existing['locked']:
                    skipped.append(key)
                    continue
                self._replace_day(db,profile_id,key,week[str(d.weekday())])
                changed.append(key)
        return dict(changed=changed,skipped=skipped)

    def save_plan_day(self, profile_id, day, items, active_date=None, adjust_remaining=False):
        day=day_value(day).isoformat()
        items=validate_items(items)
        today=today_thailand()
        with self.lock,self.connect() as db:
            if not db.execute('SELECT id FROM profiles WHERE id=?',(profile_id,)).fetchone():
                raise ValueError('ไม่พบชื่อผู้เล่น')
            current=self._day(db,profile_id,day,today)
            if adjust_remaining and day==today.isoformat() and not current['complete'] and day!=active_date:
                # Preserve all credited sets and their references; replace unfinished work only.
                if not items:raise ValueError('ใส่ท่าที่จะเล่นแทนอย่างน้อย 1 ท่า / Add a replacement exercise')
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT OR IGNORE INTO workout_days(profile_id,day) VALUES(?,?)',(profile_id,day))
                day_id=db.execute('SELECT id FROM workout_days WHERE profile_id=? AND day=?',(profile_id,day)).fetchone()[0]
                for old in current['items']:
                    if old['completed_sets']:
                        db.execute('UPDATE plan_items SET target_sets=? WHERE id=?',(old['completed_sets'],old['id']))
                    else:db.execute('DELETE FROM plan_items WHERE id=?',(old['id'],))
                offset=len(current['items'])
                db.executemany('INSERT INTO plan_items(day_id,position,exercise,arm_mode,target_sets,target_reps) VALUES(?,?,?,?,?,?)',
                    [(day_id,offset+i,x['exercise'],x['arm_mode'],x['target_sets'],x['target_reps']) for i,x in enumerate(items)])
                return self._day(db,profile_id,day,today)
            if current['locked'] or day==active_date:
                raise ValueError('วันย้อนหลัง วันที่นับครบเซตแล้ว หรือวันที่กำลังเล่น แก้ตารางไม่ได้เพื่อเก็บประวัติ')
            self._replace_day(db,profile_id,day,items)
            return self._day(db,profile_id,day,today)

    def next_plan(self, profile_id):
        day = self.plan_day(profile_id)
        for item in day['items']:
            if not item['complete']:
                return dict(item_id=item['id'],date=day['date'],profile_id=profile_id,
                            exercise=item['exercise'],name=item['name'],arm_mode=item['arm_mode'],
                            target_reps=item['target_reps'],target_sets=item['target_sets'],
                            set_number=item['completed_sets']+1,
                            day_completed_sets=day['completed_sets'],day_total_sets=day['total_sets'])
        return None

    @staticmethod
    def credit_plan(db, set_id, profile_id, exercise, mode, reps, plan):
        """Called inside the same transaction as the workout set insert.

        A shortened attempt stays in workout history, but is not a completed
        target set. A repeated request never grants a second slot or day.
        """
        if not plan:
            return False
        row=db.execute('''SELECT i.*,d.profile_id,d.day FROM plan_items i
            JOIN workout_days d ON d.id=i.day_id WHERE i.id=?''',(plan['item_id'],)).fetchone()
        if not row or (row['profile_id'],row['exercise'],row['arm_mode'])!=(profile_id,exercise,mode):
            raise ValueError('เซตไม่ตรงกับตารางของผู้เล่น')
        if row['day']!=plan['date'] or row['day']!=today_thailand().isoformat() or reps<row['target_reps']:
            return False
        existing=db.execute('SELECT item_id,set_number FROM plan_credits WHERE set_id=?',(set_id,)).fetchone()
        if existing:
            return existing['item_id']==row['id'] and existing['set_number']==plan['set_number']
        count=db.execute('SELECT COUNT(*) FROM plan_credits WHERE item_id=?',(row['id'],)).fetchone()[0]
        if plan['set_number']!=count+1 or count>=row['target_sets']:
            return False
        db.execute('INSERT OR IGNORE INTO plan_credits(set_id,item_id,set_number) VALUES(?,?,?)',
                   (set_id,row['id'],plan['set_number']))
        totals=db.execute('''SELECT SUM(target_sets) FROM plan_items WHERE day_id=?''',(row['day_id'],)).fetchone()[0]
        done=db.execute('''SELECT COUNT(*) FROM plan_credits c JOIN plan_items i ON i.id=c.item_id
                          WHERE i.day_id=?''',(row['day_id'],)).fetchone()[0]
        if totals and done>=totals:
            db.execute('UPDATE workout_days SET completed_at=COALESCE(completed_at,CURRENT_TIMESTAMP) WHERE id=?',
                       (row['day_id'],))
        return True
