import flask, flask_socketio, csv, os, json
from flask_cors import CORS
from datetime import datetime, timedelta

# نجهّز التطبيق و SocketIO ونفتح CORS
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'nbu-secret'
CORS(app, resources={r"/*": {"origins": "*"}})
sio = flask_socketio.SocketIO(app, cors_allowed_origins="*")

# مسارات الملفات
BASE = os.path.dirname(os.path.abspath(__file__))
RELOC_FILE = os.path.join(BASE, 'relocations.json')
NOTIF_FILE = os.path.join(BASE, 'notifications.json')

# ===== قراءة وكتابة JSON =====
# نقرأ ملف JSON ونتجاهل اللي انتهت صلاحيته (eT = وقت الانتهاء)
def load_json(path):
    try:
        with open(path, encoding='utf-8') as f: data = json.load(f)
        return [x for x in data if x.get('eT', 0) > datetime.now().timestamp() * 1000]
    except: return []

# نحفظ البيانات في ملف JSON
def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False)

# اختصارات لتحميل وحفظ النقلات والإشعارات
load_relocs = lambda: load_json(RELOC_FILE)
save_relocs = lambda d: save_json(RELOC_FILE, d)
load_notifs = lambda: load_json(NOTIF_FILE)
save_notifs = lambda d: save_json(NOTIF_FILE, d)

# ===== أدوات =====
# نحوّل الوقت من "0800 - 0940" إلى دقائق
def parse_time(t):
    if " - " not in t: return 0, 0
    a, b = t.split(" - ")
    return int(a[:2])*60 + int(a[2:]), int(b[:2])*60 + int(b[2:])

# نكتشف تعارض القاعات: نفس القاعة ونفس اليوم والوقت متقاطع
def detect_conflicts(data):
    items = list(data.items())
    for c in data.values(): c["has_conflict"], c["conflict_day"] = False, ""
    for i, (k1, c1) in enumerate(items):
        for k2, c2 in items[i+1:]:
            if c1["classroom"] != c2["classroom"] or not c1["classroom"]: continue
            common = set(c1["day"]) & set(c2["day"])
            if common and c1["s_time"] < c2["e_time"] and c1["e_time"] > c2["s_time"]:
                d = next(iter(common))
                for c in (c1, c2): c["has_conflict"], c["conflict_day"] = True, d

# ندوّر على ملف تسجيلات الطلاب (الاسم ممكن يجي بصيغ مختلفة)
def find_id_csv():
    for name in ["ID.fcit.csv", "ID_fcit_csv.csv", "id.fcit.csv"]:
        for folder in [BASE, os.getcwd()]:
            p = os.path.join(folder, name)
            if os.path.exists(p): return p
    return None

# نتأكد إذا القاعة فاضية في يوم ووقت معيّن، مع مراعاة النقلات
def is_hall_free(hall, day, t_start, t_end, relocs):
    # لو فيه مادة منقولة لهالقاعة بنفس الوقت، إذن مشغولة
    for r in relocs:
        if r.get('nD')==day and r.get('nH')==hall and r.get('nST',0) < t_end and r.get('nET',0) > t_start:
            return False
    # بعدها نفحص المواد الأصلية في الملف
    try:
        with open("fcit.csv", encoding="utf-8") as f:
            for row in list(csv.reader(f))[1:]:
                if len(row) < 24 or row[16].strip() != hall: continue
                if day not in [d.strip() for d in row[13].split()]: continue
                rs, re_ = parse_time(row[14].strip())
                if rs >= t_end or re_ <= t_start: continue
                crn = row[1].strip()
                # تبقى مشغولة طالما المادة ما انتقلت من هاليوم
                if not any(r.get('oD')==day and r.get('uK','').startswith(crn) for r in relocs):
                    return False
    except Exception as ex: print(f"خطأ CSV: {ex}")
    return True

# ===== المسارات =====
# الصفحة الرئيسية ترجّع الواجهة
@app.route('/')
def index(): return flask.send_file('index.html')

# نجيب كل المواد من fcit.csv. المفتاح uK = رقم المقرر CRN + رقم الصف
# (لأن المادة الوحدة ممكن تنقسم على كم صف: محاضرة + معمل)
@app.route('/api/courses')
def get_courses():
    data = {}
    try:
        with open("fcit.csv", encoding="utf-8") as f:
            for idx, i in enumerate(list(csv.reader(f))[1:], 1):
                if len(i) < 24: continue
                s, e = parse_time(i[14].strip())
                data[f"{i[1].strip()}_{idx}"] = {
                    "crn": i[1].strip(), "c_name": i[11].strip(), "c_id": i[3].strip().lower(),
                    "t_name": i[23].strip(), "capacity": i[6], "registered": i[7],
                    "classroom": i[16].strip(), "dept": i[18], "semester": i[19],
                    "section": i[21], "day": [d.strip() for d in i[13].split()],
                    "time": i[14].strip(), "s_time": s, "e_time": e,
                    "has_conflict": False, "conflict_day": ""
                }
    except Exception as e: print(f"خطأ fcit.csv: {e}")
    detect_conflicts(data)
    return flask.jsonify(data)

# نجيب النقلات المحفوظة
@app.route('/api/relocations')
def get_relocations(): return flask.jsonify(load_relocs())

# نجيب الإشعارات، ونشيل إشعار تحرّر القاعة لو رجعت مشغولة
@app.route('/api/notifications')
def get_notifications():
    notifs, relocs = load_notifs(), load_relocs()
    valid = [n for n in notifs if n.get('type') != 'hall_freed' or is_hall_free(
        n.get('hall'), n.get('day'), n.get('freed_start',0), n.get('freed_end',0), relocs)]
    if len(valid) != len(notifs): save_notifs(valid)
    return flask.jsonify(valid)

# نجيب مواد طالب معيّن بالرقم الجامعي
@app.route('/api/student_courses/<student_id>')
def get_student_courses(student_id):
    student_id, path = student_id.strip(), find_id_csv()
    if not path: return flask.jsonify({"student_name": "", "courses": []})
    clean = lambda v: v.strip().strip('"').strip("'")  # ننظّف القيمة من المسافات والاقتباسات
    courses, seen, student_name = [], set(), ""
    for enc in ["utf-8-sig", "utf-8", "cp1256"]:  # نجرّب أكثر من ترميز عشان العربي
        try:
            with open(path, encoding=enc) as f:
                for row in list(csv.reader(f))[1:]:
                    if len(row) < 13 or clean(row[11]) != student_id: continue
                    if not student_name: student_name = clean(row[12])
                    c_id, section = clean(row[5]).lower(), clean(row[8])
                    key = f"{c_id}|{section}"
                    if key in seen: continue  # ما نكرّر نفس الشعبة
                    seen.add(key)
                    courses.append({"c_id": c_id, "t_name": clean(row[7]),
                                    "c_name": clean(row[6]), "section": section})
            break
        except UnicodeDecodeError: continue
        except Exception as e: print(f"خطأ: {e}"); break
    return flask.jsonify({"student_name": student_name, "courses": courses})

# دخول الدكتور بالاسم (نطابق جزء من الاسم)
@app.route('/api/doctor_login/<name>')
def doctor_login(name):
    needle, found = name.strip().lower(), set()
    try:
        with open("fcit.csv", encoding="utf-8") as f:
            for row in list(csv.reader(f))[1:]:
                if len(row) >= 24 and needle in row[23].strip().lower():
                    found.add(row[23].strip())
    except Exception as e: print(f"خطأ: {e}")
    if not found: return flask.jsonify({"found": False, "full_name": ""})
    return flask.jsonify({"found": True, "full_name": sorted(found)[0]})

# ===== جداول طلاب المادة =====
# نجيب جداول كل الطلاب المسجّلين في مادة، عشان نتأكد قبل نقل المحاضرة ما نتعارض مع أحد
# ملاحظة: في ID.fcit.csv العمود row[8] = رقم المقرر CRN
@app.route('/api/course_students_schedules/<crn>')
def get_course_students_schedules(crn):
    crn = crn.strip()

    # نبني خريطة: لكل CRN قائمة محاضراته من fcit.csv مع الـ uK
    course_crn_map = {}
    try:
        with open("fcit.csv", encoding="utf-8") as f:
            for idx, row in enumerate(list(csv.reader(f))[1:], 1):
                if len(row) < 24: continue
                row_crn = row[1].strip()
                days = [d.strip() for d in row[13].split() if d.strip()]
                s_time, e_time = parse_time(row[14].strip())
                uK = f"{row_crn}_{idx}"
                if days and e_time > s_time:
                    course_crn_map.setdefault(row_crn, []).append({
                        "uK": uK, "crn": row_crn,
                        "days": days, "s_time": s_time, "e_time": e_time,
                    })
    except Exception as e:
        print(f"خطأ fcit.csv: {e}")

    path = find_id_csv()
    if not path:
        return flask.jsonify({"students_count": 0, "schedules": {}})

    clean = lambda v: v.strip().strip('"').strip("'")
    students = set()
    student_schedules = {}

    for enc in ["utf-8-sig", "utf-8", "cp1256"]:
        try:
            with open(path, encoding=enc) as f:
                rows = list(csv.reader(f))[1:]

            # أول خطوة: نحدّد مين الطلاب المسجّلين في هالمادة
            for row in rows:
                if len(row) < 13: continue
                if clean(row[8]) == crn:
                    students.add(clean(row[11]))

            # ثاني خطوة: نجمع باقي مواد نفس الطلاب عشان نعرف أوقاتهم المشغولة
            seen_uks = {}  # لكل طالب مجموعة uK حتى ما نكرّر
            for row in rows:
                if len(row) < 13: continue
                sid = clean(row[11])
                if sid not in students: continue
                row_crn = clean(row[8])
                if row_crn == crn: continue  # نتجاهل نفس المادة اللي بننقلها
                for sch in course_crn_map.get(row_crn, []):
                    uk = sch['uK']
                    if uk not in seen_uks.setdefault(sid, set()):
                        seen_uks[sid].add(uk)
                        student_schedules.setdefault(sid, []).append(sch)
            break
        except UnicodeDecodeError: continue
        except Exception as e: print(f"خطأ: {e}"); break

    return flask.jsonify({
        "students_count": len(students),
        "schedules": student_schedules,
    })

# ===== أحداث SocketIO =====
# نضيف نقلة جديدة ونبثّ الإشعارات لكل المستخدمين
@sio.on('add_reloc')
def handle_add_reloc(data):
    now_ms = int(datetime.now().timestamp() * 1000)
    expiry = (datetime.now() + timedelta(days=7)).timestamp() * 1000  # النقلة تنتهي بعد أسبوع
    # نشيل أي نقلة سابقة لنفس المادة ونفس اليوم (نستبدلها بالجديدة)
    relocs = [r for r in load_relocs() if not (r['uK']==data['uK'] and r['oD']==data['oD'])]
    data['eT'] = expiry
    relocs.append(data); save_relocs(relocs); sio.emit('relocs_updated', relocs)

    saved = load_notifs()

    # إشعار إن القاعة القديمة تحرّرت (لو صارت فاضية فعلاً) — يروح للدكاترة
    if data.get('oldHall'):
        oh, od = data['oldHall'], data.get('oD')
        fs, fe = data.get('oST',0), data.get('oET',0)
        if is_hall_free(oh, od, fs, fe, relocs):
            n = {'type':'hall_freed', 'id':f"{oh}_{od}_{fs}_{now_ms//1000}",
                 'hall':oh, 'day':od, 'freed_start':fs, 'freed_end':fe,
                 'ts':now_ms, 'eT':expiry}
            saved.append(n); sio.emit('hall_freed', n)

    # إشعار إن المادة انتقلت — يروح لطلاب المادة
    move = {'type':'course_moved', 'id':f"move_{data.get('uK')}_{data.get('oD')}_{now_ms//1000}",
            'c_name':data.get('c_name','—'), 'c_id':data.get('c_id',''),
            'crn': data.get('crn') or data.get('uK','').split('_')[0],
            't_name':data.get('t_name','—'),
            'oD':data.get('oD'),  'nD':data.get('nD'),
            'oST':data.get('oST'),'oET':data.get('oET'),
            'oH':data.get('oldHall',''),
            'nST':data.get('nST'),'nET':data.get('nET'),
            'nH':data.get('nH'),  'ts':now_ms, 'eT':expiry}
    saved.append(move); save_notifs(saved); sio.emit('course_moved', move)
    print(f"نقل: {data.get('uK')} من {data.get('oD')} إلى {data.get('nD')} | {data.get('nH')}")

# نحذف نقلة (تراجع) ونشيل إشعار النقل تبعها
@sio.on('delete_reloc')
def handle_delete_reloc(data):
    uK, oD = data.get('uK'), data.get('oD')
    relocs = [r for r in load_relocs() if not (r['uK']==uK and r['oD']==oD)]
    save_relocs(relocs); sio.emit('relocs_updated', relocs)
    notifs = [n for n in load_notifs() if not (
        (n.get('type')=='course_moved' and n.get('id','').startswith(f"move_{uK}_{oD}_"))
    )]
    save_notifs(notifs)
    sio.emit('reloc_deleted', {'uK': uK, 'oD': oD})
    print(f"إلغاء نقل: {uK} - {oD}")

# نحذف كل النقلات دفعة واحدة (تراجع شامل) — نتجنّب سباق التوقيت
@sio.on('delete_all_relocs')
def handle_delete_all_relocs(data=None):
    save_relocs([])  # نمسح كل النقلات مرة وحدة
    sio.emit('relocs_updated', [])
    # نشيل كل إشعارات نقل المواد (نخلّي بس إشعارات تحرّر القاعة لو لها داعي — بنشيلها كلها أبسط)
    notifs = [n for n in load_notifs() if n.get('type') != 'course_moved']
    save_notifs(notifs)
    sio.emit('reloc_deleted', {'all': True})
    print("تراجع شامل: حُذفت كل النقلات")

# أول ما يتصل مستخدم جديد نرسل له النقلات الحالية
@sio.on('connect')
def on_connect(): flask_socketio.emit('relocs_updated', load_relocs())

# نشغّل السيرفر على بورت 5000
if __name__ == '__main__': sio.run(app, port=5000, debug=True)