import os, re, io, csv, json, calendar, time, unicodedata, threading, urllib.request, urllib.parse, sqlite3, secrets, functools
from datetime import datetime, timedelta, date
from flask import Flask, request, session, redirect, url_for, render_template, flash, abort, g, send_file, Response
from jinja2 import DictLoader
from werkzeug.security import generate_password_hash as gph, check_password_hash as cph
from werkzeug.utils import secure_filename

B = os.path.dirname(os.path.abspath(__file__)); DB = os.path.join(B, 'db.sqlite3')
UP = os.path.join(B, 'static', 'uploads'); os.makedirs(UP, exist_ok=True)
app = Flask(__name__); app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024
kf = os.path.join(B, 'secret.key')
if not os.path.exists(kf): open(kf, 'w').write(secrets.token_hex(32))
app.secret_key = open(kf).read()
ROLES = {'boss': 'Boshliq', 'admin': 'Admin', 'teacher': "O'qituvchi", 'student': "O'quvchi", 'parent': 'Ota-ona'}
EXT = {'jpg','jpeg','png','gif','webp','mp4','webm','mov','mp3','ogg','wav','m4a','aac','weba','opus','pdf','doc','docx','ppt','pptx','xls','xlsx','txt','zip'}
PAT = {'once': 'Bir marta', 'daily': 'Har kuni', 'every2': 'Kunora', 'odd': 'Toq kunlar (Du-Chor-Ju)', 'even': 'Juft kunlar (Se-Pay-Shan)'}
DAYS = ['Du', 'Se', 'Chor', 'Pay', 'Ju', 'Sha', 'Yak']
STAT = {'sent': ('📨 Yuborildi — tekshirilmoqda', 'info'), 'graded': ('✅ Qabul qilindi', 'ok'),
        'rejected': ('❌ Rad etildi — qayta topshiring', 'bad'), 'reopened': ('↩️ Bekor qilindi — qayta topshiring', 'warn')}
DEF = {'shop': '1', 'rating': '1', 'trate': '1', 'chat': '1', 'bonus': '1', 'force_pw': '1', 'paused': '0'}
GATE = {'shop': 'shop', 'buy': 'shop', 'rating': 'rating', 'teachers': 'trate', 'rate_teacher': 'trate', 'messages': 'chat', 'thread': 'chat', 'course_chat': 'chat'}

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, pw TEXT, role TEXT, first TEXT DEFAULT '', last TEXT DEFAULT '', avatar TEXT DEFAULT '', bg TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY, name TEXT, info TEXT, teacher_id INTEGER, color TEXT DEFAULT '#6c5ce7');
CREATE TABLE IF NOT EXISTS cs(course_id INTEGER, student_id INTEGER, UNIQUE(course_id, student_id));
CREATE TABLE IF NOT EXISTS sched(id INTEGER PRIMARY KEY, course_id INTEGER, start TEXT, end TEXT, time TEXT, pattern TEXT);
CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY, course_id INTEGER, kind TEXT, title TEXT, text TEXT, link TEXT, video TEXT, audio TEXT, file TEXT, deadline TEXT, created TEXT, maxscore INTEGER DEFAULT 100);
CREATE TABLE IF NOT EXISTS subs(id INTEGER PRIMARY KEY, post_id INTEGER, student_id INTEGER, text TEXT, link TEXT, file TEXT, audio TEXT, at TEXT, late INTEGER, score INTEGER, fb TEXT, status TEXT DEFAULT 'sent', reason TEXT DEFAULT '', UNIQUE(post_id, student_id));
CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY, name TEXT, info TEXT, price INTEGER, stock INTEGER);
CREATE TABLE IF NOT EXISTS buys(id INTEGER PRIMARY KEY, user_id INTEGER, item_id INTEGER, item TEXT, price INTEGER, at TEXT, given INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS notifs(id INTEGER PRIMARY KEY, user_id INTEGER, text TEXT, link TEXT, seen INTEGER DEFAULT 0, at TEXT);
CREATE TABLE IF NOT EXISTS news(id INTEGER PRIMARY KEY, title TEXT, body TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS trate(id INTEGER PRIMARY KEY, teacher_id INTEGER, student_id INTEGER, stars INTEGER, comment TEXT, at TEXT, UNIQUE(teacher_id, student_id));
CREATE TABLE IF NOT EXISTS att(course_id INTEGER, student_id INTEGER, day TEXT, present INTEGER, UNIQUE(course_id, student_id, day));
CREATE TABLE IF NOT EXISTS quizzes(id INTEGER PRIMARY KEY, course_id INTEGER, title TEXT, minutes INTEGER, maxscore INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS qq(id INTEGER PRIMARY KEY, quiz_id INTEGER, q TEXT, a TEXT, b TEXT, c TEXT, d TEXT, ans TEXT);
CREATE TABLE IF NOT EXISTS qatt(id INTEGER PRIMARY KEY, quiz_id INTEGER, student_id INTEGER, score INTEGER, total INTEGER, good INTEGER, at TEXT, started TEXT, answers TEXT DEFAULT '', UNIQUE(quiz_id, student_id));
CREATE TABLE IF NOT EXISTS comments(id INTEGER PRIMARY KEY, post_id INTEGER, user_id INTEGER, text TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS bonus(id INTEGER PRIMARY KEY, user_id INTEGER, reason TEXT, points INTEGER, at TEXT, day TEXT, UNIQUE(user_id, reason, day));
CREATE TABLE IF NOT EXISTS msgs(id INTEGER PRIMARY KEY, from_id INTEGER, to_id INTEGER, text TEXT, at TEXT, seen INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS cmsg(id INTEGER PRIMARY KEY, course_id INTEGER, user_id INTEGER, text TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS perms(scope TEXT, ref TEXT, k TEXT, val INTEGER, PRIMARY KEY(scope, ref, k));
CREATE TABLE IF NOT EXISTS fees(id INTEGER PRIMARY KEY, student_id INTEGER, month TEXT, amount INTEGER, paid INTEGER DEFAULT 0, paid_at TEXT, note TEXT DEFAULT '', UNIQUE(student_id, month));
CREATE TABLE IF NOT EXISTS grps(id INTEGER PRIMARY KEY, name TEXT, color TEXT DEFAULT '#6c5ce7');
CREATE TABLE IF NOT EXISTS gs(group_id INTEGER, student_id INTEGER, UNIQUE(group_id, student_id));
CREATE TABLE IF NOT EXISTS library(id INTEGER PRIMARY KEY, course_id INTEGER, title TEXT, info TEXT, file TEXT, link TEXT, user_id INTEGER, at TEXT);
CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY, course_id INTEGER, title TEXT, done INTEGER DEFAULT 0, ord INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS joinreq(id INTEGER PRIMARY KEY, course_id INTEGER, student_id INTEGER, at TEXT, status TEXT DEFAULT 'pending', UNIQUE(course_id, student_id));
CREATE TABLE IF NOT EXISTS polls(id INTEGER PRIMARY KEY, question TEXT, course_id INTEGER, created TEXT, closed INTEGER DEFAULT 0, user_id INTEGER);
CREATE TABLE IF NOT EXISTS poll_opts(id INTEGER PRIMARY KEY, poll_id INTEGER, text TEXT);
CREATE TABLE IF NOT EXISTS votes(poll_id INTEGER, user_id INTEGER, opt_id INTEGER, UNIQUE(poll_id, user_id));
CREATE TABLE IF NOT EXISTS challenges(id INTEGER PRIMARY KEY, title TEXT, info TEXT, points INTEGER, ends TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS ch_done(challenge_id INTEGER, student_id INTEGER, at TEXT, status TEXT DEFAULT 'pending', UNIQUE(challenge_id, student_id));
CREATE TABLE IF NOT EXISTS qrtok(token TEXT PRIMARY KEY, course_id INTEGER, day TEXT, exp REAL);
CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, user_id INTEGER, ua TEXT, ip TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS login_fail(k TEXT PRIMARY KEY, n INTEGER, until REAL);
"""

def migrate():  # eski bazalarni ham yangilaydi
    c = sqlite3.connect(DB); c.executescript(SCHEMA)
    for t, col, d in [('courses', 'color', "TEXT DEFAULT '#6c5ce7'"), ('posts', 'maxscore', 'INTEGER DEFAULT 100'),
                      ('subs', 'status', "TEXT DEFAULT 'sent'"), ('subs', 'reason', "TEXT DEFAULT ''"),
                      ('subs', 'gat', 'TEXT'), ('users', 'child_id', 'INTEGER'), ('users', 'tg', "TEXT DEFAULT ''"),
                      ('users', 'fee', 'INTEGER DEFAULT 0'), ('users', 'must_change', 'INTEGER DEFAULT 0'), ('courses', 'group_id', 'INTEGER'), ('news', 'group_id', 'INTEGER'),
                      ('sched', 'link', "TEXT DEFAULT ''"), ('quizzes', 'final', 'INTEGER DEFAULT 0'), ('quizzes', 'pass_pct', 'INTEGER DEFAULT 60')]:
        if col not in [r[1] for r in c.execute(f"PRAGMA table_info({t})")]: c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {d}")
    c.execute("UPDATE subs SET status='graded' WHERE score IS NOT NULL AND status='sent'")
    c.commit(); c.close()
migrate()

def now(): return datetime.utcnow() + timedelta(hours=5)  # Toshkent vaqti
def ns(): return now().strftime('%Y-%m-%d %H:%M')
def cl(v): return v if v and re.match(r'^#[0-9a-fA-F]{6}$', v) else '#6c5ce7'

def q(sql, a=(), one=False, w=False):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    r = c.execute(sql, a)
    if w:
        c.commit(); i = r.lastrowid; c.close(); return i
    rows = r.fetchall(); c.close()
    return (rows[0] if rows else None) if one else rows

def st():
    if 'st' not in g: g.st = {**DEF, **{r['k']: r['v'] for r in q("SELECT * FROM settings")}}
    return g.st

def save(f):
    if not f or not f.filename: return ''
    e = f.filename.rsplit('.', 1)[-1].lower()
    if e not in EXT: flash("Bu fayl turi ruxsat etilmagan"); return ''
    n = secrets.token_hex(6) + '_' + secure_filename(f.filename)
    f.save(os.path.join(UP, n)); return n

def notify(uid, text, link=''):
    q("INSERT INTO notifs(user_id,text,link,at) VALUES(?,?,?,?)", (uid, text, link, ns()), w=True)
    try:
        r = q("SELECT tg FROM users WHERE id=?", (uid,), one=True); k = q("SELECT v FROM settings WHERE k='tg_token'", one=True)
        if r and r['tg'] and k and k['v']: threading.Thread(target=_tg, args=(k['v'], r['tg'], text), daemon=True).start()
    except Exception: pass

def me():
    if 'me' not in g:
        g.me = q("SELECT * FROM users WHERE id=?", (session.get('uid'),), one=True) if session.get('uid') else None
    return g.me

def need(*roles):
    def d(f):
        @functools.wraps(f)
        def w(*a, **k):
            u = me()
            if not u: return redirect(url_for('login'))
            if roles and u['role'] not in roles: abort(403)
            return f(*a, **k)
        return w
    return d

ADM = ('boss', 'admin')
def is_adm(): return me()['role'] in ADM
def can_course(c): return is_adm() or (me()['role'] == 'teacher' and c['teacher_id'] == me()['id'])
EV = ("SELECT s.student_id AS uid, s.score AS pts, p.course_id AS cid, COALESCE(s.gat, s.at) AS at FROM subs s JOIN posts p ON p.id=s.post_id WHERE s.status='graded' AND s.score IS NOT NULL "
      "UNION ALL SELECT student_id, score, (SELECT course_id FROM quizzes WHERE id=quiz_id), at FROM qatt WHERE score IS NOT NULL "
      "UNION ALL SELECT user_id, points, NULL, at FROM bonus")
def earned(uid): return q("SELECT COALESCE(SUM(pts),0) s FROM (" + EV + ") WHERE uid=?", (uid,), one=True)['s']
def balance(uid): return earned(uid) - q("SELECT COALESCE(SUM(price),0) s FROM buys WHERE user_id=?", (uid,), one=True)['s']
def my_courses():
    u = me()
    if u['role'] in ADM: return q("SELECT * FROM courses")
    if u['role'] == 'teacher': return q("SELECT * FROM courses WHERE teacher_id=?", (u['id'],))
    return q("SELECT c.* FROM courses c JOIN cs ON cs.course_id=c.id WHERE cs.student_id=?", ((u['child_id'] or 0) if u['role'] == 'parent' else u['id'],))

def board(cid=None, period=None):
    start = {'week': (now() - timedelta(days=now().weekday())).strftime('%Y-%m-%d'), 'month': now().strftime('%Y-%m-01')}.get(period, '')
    j = "JOIN cs ON cs.student_id=u.id AND cs.course_id=?" if cid else ""
    sql = ("SELECT u.*, COALESCE((SELECT SUM(pts) FROM (" + EV + ") e WHERE e.uid=u.id AND (? IS NULL OR e.cid=?) AND e.at>=?),0) pts FROM users u " + j + " WHERE u.role='student' ORDER BY pts DESC, u.username")
    return q(sql, [cid, cid, start] + ([cid] if cid else []))

DONE = "(SELECT post_id FROM subs WHERE student_id=? AND status IN ('sent','graded'))"
def todo(uid):
    return q("SELECT p.*, c.name cname, c.color FROM posts p JOIN courses c ON c.id=p.course_id JOIN cs ON cs.course_id=p.course_id AND cs.student_id=? WHERE p.kind='hw' AND p.id NOT IN " + DONE + " ORDER BY p.deadline=''," + " p.deadline", (uid, uid))

def lessons(days=14, t0=None, cmap=None):
    out = []; ids = cmap or {c['id']: c['name'] for c in my_courses()}
    t0 = t0 or now().date()
    for s in q("SELECT * FROM sched ORDER BY time"):
        if s['course_id'] not in ids: continue
        s0 = date.fromisoformat(s['start']); en = date.fromisoformat(s['end']) if s['end'] else None
        for i in range(days):
            d = t0 + timedelta(days=i)
            if d < s0 or (en and d > en): continue
            p = s['pattern']; wd = d.weekday()
            if (p == 'once' and d == s0) or p == 'daily' or (p == 'every2' and (d - s0).days % 2 == 0) \
               or (p == 'odd' and wd in (0, 2, 4)) or (p == 'even' and wd in (1, 3, 5)):
                out.append((d, s['time'], ids[s['course_id']], s['id']))
    return sorted(out, key=lambda x: (x[0], x[1]))

@app.before_request
def guard():
    if request.method == 'POST' and request.form.get('_t') != session.get('_t'): abort(400)
    ep = request.endpoint or ''
    if ep == 'static': return
    if session.get('uid'):
        if not session.get('sid'): start_session(session['uid'])
        elif not q("SELECT 1 FROM sessions WHERE id=?", (session['sid'],), one=True): session.clear()
    u = me()
    if st()['paused'] == '1' and ep not in ('login', 'logout', 'register', 'forgot', 'lang', 'manifest', 'sw', 'icon') and not (u and u['role'] in ADM):
        return render_template('pause.html'), 503
    if ep in GATE and st()[GATE[ep]] != '1' and not (u and u['role'] in ADM):
        flash("Bu bo'lim vaqtincha o'chirilgan"); return redirect(url_for('dash'))
    if u and u['must_change'] and st()['force_pw'] == '1' and ep not in ('change_password', 'logout', 'lang', 'manifest', 'sw', 'icon'): return redirect(url_for('change_password'))
    k = EPERM.get((ep, request.method)) or EPERM.get((ep, '*'))
    if k and u and not allow(k): abort(403)
    if u and ep == 'dash': daily_jobs()

@app.context_processor
def ctx():
    session.setdefault('_t', secrets.token_hex(16)); u = me(); warn = []; unread = 0; munread = 0
    if u:
        unread = q("SELECT COUNT(*) n FROM notifs WHERE user_id=? AND seen=0", (u['id'],), one=True)['n']
        munread = q("SELECT COUNT(*) n FROM msgs WHERE to_id=? AND seen=0", (u['id'],), one=True)['n']
        if u['role'] == 'student':
            soon = (now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M')
            for p in q("SELECT p.* FROM posts p JOIN cs ON cs.course_id=p.course_id AND cs.student_id=? WHERE p.kind='hw' AND p.deadline!='' AND p.deadline<=? AND p.id NOT IN " + DONE, (u['id'], soon, u['id'])):
                warn.append((p, p['deadline'] < ns()))
    return dict(me=u, ROLES=ROLES, PAT=PAT, DAYS=DAYS, STAT=STAT, csrf=lambda: '<input type=hidden name=_t value=%s>' % session['_t'],
                unread=unread, warn=warn, adm=bool(u and u['role'] in ADM), earned=earned, balance=balance,
                S=lambda k: st()[k], paused=st()['paused'] == '1',
                badges=badges, munread=munread, lang=session.get('lang', 'uz'), MONS=MONS, WDS=WDS, allow=allow, is_live=is_live)

# ---------- kirish ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if q("SELECT 1 FROM users", one=True): return redirect(url_for('login'))
    if request.method == 'POST':
        un, pw = request.form['username'].strip(), request.form['password']
        if len(un) < 3 or len(pw) < 4: flash("Login kamida 3, parol kamida 4 belgi")
        else:
            i = q("INSERT INTO users(username,pw,role) VALUES(?,?,'boss')", (un, gph(pw)), w=True)
            start_session(i); return redirect(url_for('dash'))
    return render_template('auth.html', title="Birinchi kirish", sub="Siz Boshliq bo'lasiz. Login va parol tanlang.", btn="Ro'yxatdan o'tish")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if not q("SELECT 1 FROM users", one=True): return redirect(url_for('register'))
    if request.method == 'POST':
        un = request.form['username'].strip(); key = (un.lower() + '|' + _ip())[:120]
        fl = q("SELECT * FROM login_fail WHERE k=?", (key,), one=True)
        if fl and fl['until'] > time.time():
            flash("Juda ko'p xato urinish. %d daqiqadan so'ng qayta urinib ko'ring." % (int((fl['until'] - time.time()) / 60) + 1))
        else:
            u = q("SELECT * FROM users WHERE username=?", (un,), one=True)
            if u and cph(u['pw'], request.form['password']):
                q("DELETE FROM login_fail WHERE k=?", (key,), w=True); start_session(u['id']); return redirect(url_for('dash'))
            n = 0 if (not fl or (fl['until'] and fl['until'] < time.time())) else fl['n']; n += 1
            q("INSERT OR REPLACE INTO login_fail(k,n,until) VALUES(?,?,?)", (key, n, time.time() + 600 if n >= 5 else 0), w=True)
            flash("Login yoki parol xato" + (" (%d ta urinish qoldi)" % (5 - n) if n < 5 else ". 10 daqiqaga bloklandingiz."))
    return render_template('auth.html', title="Xush kelibsiz!", sub="Hisobingizga kiring", btn="Kirish")

@app.route('/logout')
def logout():
    q("DELETE FROM sessions WHERE id=?", (session.get('sid', ''),), w=True); session.clear(); return redirect(url_for('login'))

# ---------- bosh sahifa ----------
@app.route('/')
@need()
def dash():
    u = me()
    if u['role'] == 'parent': return redirect(url_for('child'))
    today = now().date(); info = {}
    if u['role'] == 'student':
        daily(u['id']); b = board()
        info = dict(debt=debt(u['id']), att=att_pct(u['id'])[0], streak=streak(u['id']), bal=balance(u['id']), earn=earned(u['id']), total=len(b), todo=len(todo(u['id'])),
                    rank=next((i + 1 for i, x in enumerate(b) if x['id'] == u['id']), '-'))
    gn = q("SELECT COUNT(*) n FROM subs s JOIN posts p ON p.id=s.post_id JOIN courses c ON c.id=p.course_id WHERE s.status='sent' AND (c.teacher_id=? OR ?)", (u['id'], is_adm()), one=True)['n'] if u['role'] != 'student' else 0
    return render_template('dash.html', today=[l for l in lessons(1) if l[0] == today], news=news_rows(3),
                           grade_n=gn, info=info, links={r['id']: r['link'] for r in q("SELECT id,link FROM sched")}, stats=[(r, q("SELECT COUNT(*) n FROM users WHERE role=?", (r,), one=True)['n']) for r in ROLES] if is_adm() else [])

@app.route('/my')
@need('student')
def my():
    rows = q("SELECT s.*, p.title, p.maxscore, p.deadline, c.name cname, c.color FROM subs s JOIN posts p ON p.id=s.post_id JOIN courses c ON c.id=p.course_id WHERE s.student_id=? ORDER BY s.id DESC", (me()['id'],))
    return render_template('my.html', rows=rows, todo=todo(me()['id']), now=ns())

# ---------- foydalanuvchilar ----------
@app.route('/users', methods=['GET', 'POST'])
@need()
def users():
    if request.method == 'POST':
        f = request.form; role = f['role']
        if role not in (ROLES if me()['role'] == 'boss' else ('teacher', 'student', 'parent')) or role == 'boss': abort(403)
        if q("SELECT 1 FROM users WHERE username=?", (f['username'].strip(),), one=True) or len(f['password']) < 4: flash("Login band yoki parol qisqa")
        else:
            q("INSERT INTO users(username,pw,role,first,last,child_id,must_change) VALUES(?,?,?,?,?,?,1)", (f['username'].strip(), gph(f['password']), role, f['first'], f['last'], (f.get('child') or None) if role == 'parent' else None), w=True); flash("Qo'shildi ✅")
    return render_template('users.html', rows=q("SELECT * FROM users ORDER BY role, username"), students=q("SELECT * FROM users WHERE role='student'"))

@app.route('/users/<int:i>', methods=['POST'])
@need()
def user_act(i):
    u = q("SELECT * FROM users WHERE id=?", (i,), one=True) or abort(404); f = request.form; boss = me()['role'] == 'boss'
    if u['role'] == 'boss' or (u['role'] == 'admin' and not boss): abort(403)
    a = f['a']; log("Foydalanuvchi #%s (%s): %s" % (i, u['username'], a))
    if not allow({'name': 'users_edit', 'pw': 'users_edit', 'child': 'users_edit', 'role': 'users_role', 'del': 'users_delete'}.get(a, 'users_edit')): abort(403)
    if a == 'name': q("UPDATE users SET first=?, last=? WHERE id=?", (f['first'], f['last'], i), w=True)
    elif a == 'role' and f['role'] in (ROLES if boss else ('teacher', 'student', 'parent')) and f['role'] != 'boss':
        q("UPDATE users SET role=? WHERE id=?", (f['role'], i), w=True)
    elif a == 'pw' and len(f['pw']) >= 4: q("UPDATE users SET pw=?, must_change=1 WHERE id=?", (gph(f['pw']), i), w=True)
    elif a == 'child': q("UPDATE users SET child_id=? WHERE id=?", (f.get('child') or None, i), w=True)
    elif a == 'del':
        q("DELETE FROM subs WHERE student_id=?", (i,), w=True); q("DELETE FROM buys WHERE user_id=?", (i,), w=True)
        q("DELETE FROM notifs WHERE user_id=?", (i,), w=True); q("DELETE FROM cs WHERE student_id=?", (i,), w=True)
        q("DELETE FROM trate WHERE student_id=? OR teacher_id=?", (i, i), w=True); q("DELETE FROM users WHERE id=?", (i,), w=True)
    flash("Bajarildi ✅"); return redirect(url_for('users'))

# ---------- kurslar ----------
@app.route('/courses', methods=['GET', 'POST'])
@need()
def courses():
    if request.method == 'POST' and allow('courses_manage'):
        q("INSERT INTO courses(name,info,teacher_id,color) VALUES(?,?,?,?)", (request.form['name'], request.form['info'], request.form.get('teacher') or None, cl(request.form.get('color'))), w=True)
        flash("Kurs qo'shildi ✅")
    ids = [c['id'] for c in my_courses()]
    rows = q("SELECT c.*, t.username tu, t.first tf, t.last tl, (SELECT COUNT(*) FROM cs WHERE course_id=c.id) n, (SELECT COUNT(*) FROM posts WHERE course_id=c.id) pc FROM courses c LEFT JOIN users t ON t.id=c.teacher_id WHERE c.id IN (%s)" % ','.join('?' * len(ids)), ids) if ids else []
    others = []; pending = set()
    if me()['role'] == 'student':
        others = q("SELECT * FROM courses WHERE group_id IS NULL AND id NOT IN (SELECT course_id FROM cs WHERE student_id=?)", (me()['id'],))
        pending = {r['course_id'] for r in q("SELECT course_id FROM joinreq WHERE student_id=? AND status='pending'", (me()['id'],))}
    return render_template('courses.html', rows=rows, teachers=q("SELECT * FROM users WHERE role='teacher'"), others=others, pending=pending)

@app.route('/course/<int:i>', methods=['GET', 'POST'])
@need()
def course(i):
    c = q("SELECT * FROM courses WHERE id=?", (i,), one=True) or abort(404)
    if c['id'] not in [x['id'] for x in my_courses()]: abort(403)
    if request.method == 'POST' and allow('courses_manage'):
        q("UPDATE courses SET teacher_id=? WHERE id=?", (request.form.get('teacher') or None, i), w=True)
        q("DELETE FROM cs WHERE course_id=?", (i,), w=True)
        for s in request.form.getlist('st'): q("INSERT OR IGNORE INTO cs VALUES(?,?)", (i, s), w=True)
        flash("Saqlandi ✅"); return redirect(url_for('course', i=i))
    mine = [r['student_id'] for r in q("SELECT student_id FROM cs WHERE course_id=?", (i,))]
    return render_template('course.html', c=c, posts=q("SELECT * FROM posts WHERE course_id=? ORDER BY id DESC", (i,)),
                           students=q("SELECT * FROM users WHERE role='student'"), mine=mine, can=can_course(c),
                           teachers=q("SELECT * FROM users WHERE role='teacher'"), sch=q("SELECT * FROM sched WHERE course_id=?", (i,)),
                           tname=q("SELECT * FROM users WHERE id=?", (c['teacher_id'],), one=True),
                           cert=(me()['role'] == 'student' and cert_ok(i, me()['id'])[0]),
                           grps=q("SELECT * FROM grps"), topics=q("SELECT * FROM topics WHERE course_id=? ORDER BY ord, id", (i,)))

@app.route('/course/<int:i>/edit', methods=['POST'])
@need()
def course_edit(i):
    log("Kurs #%s: %s" % (i, "o'chirish" if request.form.get('del') else 'tahrirlash'))
    if request.form.get('del'):
        q("DELETE FROM subs WHERE post_id IN (SELECT id FROM posts WHERE course_id=?)", (i,), w=True)
        for t in ('posts', 'sched', 'cs'): q(f"DELETE FROM {t} WHERE course_id=?", (i,), w=True)
        q("DELETE FROM courses WHERE id=?", (i,), w=True); flash("Kurs o'chirildi"); return redirect(url_for('courses'))
    q("UPDATE courses SET name=?, info=?, color=?, group_id=? WHERE id=?", (request.form['name'], request.form['info'], cl(request.form.get('color')), request.form.get('group') or None, i), w=True); sync_course(i); flash("Saqlandi ✅")
    return redirect(url_for('course', i=i))

@app.route('/course/<int:i>/post', methods=['POST'])
@need()
def new_post(i):
    c = q("SELECT * FROM courses WHERE id=?", (i,), one=True) or abort(404)
    if not can_course(c): abort(403)
    f = request.form
    try: mx = max(1, min(1000, int(f.get('maxscore') or 100)))
    except ValueError: mx = 100
    pid = q("INSERT INTO posts(course_id,kind,title,text,link,video,audio,file,deadline,created,maxscore) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (i, f['kind'], f['title'], f['text'], f['link'], save(request.files.get('video')), save(request.files.get('audio')),
             save(request.files.get('file')), f['deadline'].replace('T', ' '), ns(), mx), w=True)
    for s in q("SELECT student_id FROM cs WHERE course_id=?", (i,)):
        notify(s['student_id'], ("Yangi uy ishi: " if f['kind'] == 'hw' else "Yangi dars: ") + f['title'], url_for('post', i=pid))
    flash("Joylandi ✅"); return redirect(url_for('post', i=pid))

# ---------- dars / uy ishi ----------
@app.route('/post/<int:i>')
@need()
def post(i):
    p = q("SELECT * FROM posts WHERE id=?", (i,), one=True) or abort(404)
    c = q("SELECT * FROM courses WHERE id=?", (p['course_id'],), one=True)
    if c['id'] not in [x['id'] for x in my_courses()]: abort(403)
    mine = q("SELECT * FROM subs WHERE post_id=? AND student_id=?", (i, me()['id']), one=True)
    subs = q("SELECT s.*, u.username, u.first, u.last FROM subs s JOIN users u ON u.id=s.student_id WHERE post_id=? ORDER BY s.id DESC", (i,))
    missing = q("SELECT u.* FROM users u JOIN cs ON cs.student_id=u.id AND cs.course_id=? WHERE u.id NOT IN (SELECT student_id FROM subs WHERE post_id=?)", (p['course_id'], i))
    return render_template('post.html', p=p, c=c, mine=mine, subs=subs, missing=missing, can=can_course(c), late=bool(p['deadline'] and p['deadline'] < ns()),
                           cmts=q("SELECT m.*, u.username, u.first, u.last, u.avatar, u.role FROM comments m JOIN users u ON u.id=m.user_id WHERE post_id=? ORDER BY m.id", (i,)))

@app.route('/post/<int:i>/edit', methods=['POST'])
@need()
def post_edit(i):
    p = q("SELECT * FROM posts WHERE id=?", (i,), one=True) or abort(404)
    if not can_course(q("SELECT * FROM courses WHERE id=?", (p['course_id'],), one=True)): abort(403)
    if request.form.get('del'):
        q("DELETE FROM subs WHERE post_id=?", (i,), w=True); q("DELETE FROM posts WHERE id=?", (i,), w=True); log("Dars/uy ishi o'chirildi #%s" % i)
        flash("O'chirildi"); return redirect(url_for('course', i=p['course_id']))
    try: mx = max(1, min(1000, int(request.form.get('maxscore') or 100)))
    except ValueError: mx = p['maxscore'] or 100
    q("UPDATE posts SET deadline=?, maxscore=? WHERE id=?", (request.form['deadline'].replace('T', ' '), mx, i), w=True)
    q("UPDATE subs SET score=MIN(score,?) WHERE post_id=? AND score IS NOT NULL", (mx, i), w=True)
    for s in q("SELECT student_id FROM cs WHERE course_id=?", (p['course_id'],)): notify(s['student_id'], "Uy ishi sozlamasi o'zgardi: " + p['title'], url_for('post', i=i))
    flash("Saqlandi ✅"); return redirect(url_for('post', i=i))

@app.route('/post/<int:i>/submit', methods=['POST'])
@need('student')
def submit(i):
    p = q("SELECT * FROM posts WHERE id=?", (i,), one=True) or abort(404)
    if p['course_id'] not in [x['id'] for x in my_courses()] or p['kind'] != 'hw': abort(403)
    old = q("SELECT * FROM subs WHERE post_id=? AND student_id=?", (i, me()['id']), one=True)
    if old and old['status'] == 'graded': flash("Qabul qilingan ishni o'zgartirib bo'lmaydi"); return redirect(url_for('post', i=i))
    f = request.form; late = int(bool(p['deadline'] and p['deadline'] < ns()))
    fl, au = save(request.files.get('file')), save(request.files.get('audio'))
    if old: fl = fl or old['file']; au = au or old['audio']
    if not (f['text'].strip() or f['link'].strip() or fl or au): flash("Hech narsa kiritilmadi"); return redirect(url_for('post', i=i))
    q("INSERT INTO subs(post_id,student_id,text,link,file,audio,at,late,score,fb,status,reason) VALUES(?,?,?,?,?,?,?,?,NULL,'','sent','') "
      "ON CONFLICT(post_id,student_id) DO UPDATE SET text=excluded.text, link=excluded.link, file=excluded.file, audio=excluded.audio, at=excluded.at, late=excluded.late, score=NULL, fb='', status='sent', reason=''",
      (i, me()['id'], f['text'], f['link'], fl, au, ns(), late), w=True)
    t = q("SELECT teacher_id FROM courses WHERE id=?", (p['course_id'],), one=True)['teacher_id']
    if t: notify(t, "%s uy ishini topshirdi%s: %s" % (me()['username'], " (KECHIKKAN)" if late else "", p['title']), url_for('post', i=i))
    if late: notify(me()['id'], "Ogohlantirish: '%s' uy ishi kechikib topshirildi!" % p['title'], url_for('post', i=i))
    flash("✅ Uy ishingiz yuborildi! Holatini “Ishlarim” bo'limida ko'rishingiz mumkin."); return redirect(url_for('post', i=i))

@app.route('/sub/<int:i>/grade', methods=['POST'])
@need()
def grade(i):
    s = q("SELECT * FROM subs WHERE id=?", (i,), one=True) or abort(404)
    p = q("SELECT * FROM posts WHERE id=?", (s['post_id'],), one=True)
    if not can_course(q("SELECT * FROM courses WHERE id=?", (p['course_id'],), one=True)): abort(403)
    a = request.form.get('a', 'grade'); fb = request.form.get('fb', '').strip(); to = url_for('post', i=p['id']); mx = p['maxscore'] or 100
    log("Baholash: %s | ish #%s | o'quvchi #%s | ball=%s" % (a, p['id'], s['student_id'], request.form.get('score', '')))
    if a == 'grade':
        try: sc = max(0, min(mx, int(request.form['score'])))
        except (ValueError, KeyError): flash("Ball kiriting"); return redirect(to)
        q("UPDATE subs SET score=?, fb=?, status='graded', reason='', gat=? WHERE id=?", (sc, fb, ns(), i), w=True)
        notify(s['student_id'], "'%s' uy ishingiz qabul qilindi: %d/%d ball" % (p['title'], sc, mx), to); flash("Qabul qilindi va baholandi ✅")
    elif a == 'reject':
        q("UPDATE subs SET score=NULL, fb='', status='rejected', reason=? WHERE id=?", (fb or "Sabab ko'rsatilmagan", i), w=True)
        notify(s['student_id'], "'%s' uy ishingiz RAD ETILDI. Qayta topshiring." % p['title'], to); flash("Rad etildi")
    elif a == 'reopen':
        q("UPDATE subs SET score=NULL, fb='', status='reopened', reason=? WHERE id=?", (fb or "Baho bekor qilindi", i), w=True)
        notify(s['student_id'], "'%s' bahosi bekor qilindi. Qayta topshirishingiz mumkin." % p['title'], to); flash("Bekor qilindi, o'quvchi qayta topshira oladi")
    return redirect(to)

# ---------- jadval, reyting ----------
@app.route('/schedule', methods=['GET', 'POST'])
@need()
def schedule():
    if request.method == 'POST' and allow('schedule_manage'):
        f = request.form
        q("INSERT INTO sched(course_id,start,end,time,pattern,link) VALUES(?,?,?,?,?,?)", (f['course'], f['start'], f['end'], f['time'], f['pattern'], _lk(f.get('link'))), w=True)
        for s in q("SELECT student_id FROM cs WHERE course_id=?", (f['course'],)): notify(s['student_id'], "Yangi dars jadvali qo'shildi", url_for('schedule'))
        flash("Qo'shildi ✅")
    if request.args.get('del') and allow('schedule_manage'): q("DELETE FROM sched WHERE id=?", (request.args['del'],), w=True); return redirect(url_for('schedule'))
    return render_template('schedule.html', rows=lessons(14), links={r['id']: r['link'] for r in q("SELECT id,link FROM sched")}, courses=q("SELECT * FROM courses"), all=q("SELECT s.*, c.name FROM sched s JOIN courses c ON c.id=s.course_id"))

@app.route('/rating')
@need()
def rating():
    cid = request.args.get('course', type=int); per = request.args.get('period') or None
    b = board(None, 'month'); star = b[0] if b and b[0]['pts'] > 0 else None
    return render_template('rating.html', rows=board(cid, per), courses=q("SELECT * FROM courses"), cid=cid, period=per, star=star)

# ---------- ustozlarni baholash ----------
@app.route('/teachers')
@need()
def teachers():
    u = me(); rows = q("SELECT u.*, (SELECT ROUND(AVG(stars),1) FROM trate WHERE teacher_id=u.id) avg, (SELECT COUNT(*) FROM trate WHERE teacher_id=u.id) n FROM users u WHERE u.role='teacher' ORDER BY avg DESC")
    mine, ok, cm = {}, set(), []
    if u['role'] == 'student':
        mine = {r['teacher_id']: r for r in q("SELECT * FROM trate WHERE student_id=?", (u['id'],))}
        ok = {r['teacher_id'] for r in my_courses() if r['teacher_id']}
    if allow('trate_manage'): cm = q("SELECT t.*, s.username su, s.first sf, s.last sl, te.username tu FROM trate t JOIN users s ON s.id=t.student_id JOIN users te ON te.id=t.teacher_id ORDER BY t.id DESC LIMIT 100")
    elif u['role'] == 'teacher': cm = q("SELECT * FROM trate WHERE teacher_id=? ORDER BY id DESC", (u['id'],))
    return render_template('teachers.html', rows=rows, mine=mine, ok=ok, cm=cm)

@app.route('/teachers/rate/<int:t>', methods=['POST'])
@need('student')
def rate_teacher(t):
    if t not in {r['teacher_id'] for r in my_courses()}: abort(403)
    try: stars = max(1, min(5, int(request.form['stars'])))
    except (ValueError, KeyError): abort(400)
    q("INSERT OR REPLACE INTO trate(teacher_id,student_id,stars,comment,at) VALUES(?,?,?,?,?)", (t, me()['id'], stars, request.form.get('comment', '')[:300], ns()), w=True)
    flash("Bahoyingiz uchun rahmat ⭐"); return redirect(url_for('teachers'))

@app.route('/teachers/del/<int:i>', methods=['POST'])
@need()
def trate_del(i): log("Ustoz bahosi o'chirildi #%s" % i); q("DELETE FROM trate WHERE id=?", (i,), w=True); return redirect(url_for('teachers'))

# ---------- sozlamalar ----------
@app.route('/settings', methods=['GET', 'POST'])
@need()
def settings():
    if request.method == 'POST':
        for k in DEF:
            if k == 'paused' and not allow('pause_app'): continue
            q("INSERT OR REPLACE INTO settings(k,v) VALUES(?,?)", (k, '1' if request.form.get(k) else '0'), w=True)
        if me()['role'] == 'boss' and 'tg_token' in request.form: q("INSERT OR REPLACE INTO settings(k,v) VALUES('tg_token',?)", (request.form['tg_token'].strip(),), w=True)
        log("Sozlamalar o'zgartirildi"); g.pop('st', None); flash("Sozlamalar saqlandi ✅")
    k = q("SELECT v FROM settings WHERE k='tg_token'", one=True)
    return render_template('settings.html', tgtok=k['v'] if k and me()['role'] == 'boss' else '')

# ---------- magazin ----------
@app.route('/shop', methods=['GET', 'POST'])
@need()
def shop():
    if request.method == 'POST' and allow('shop_manage'):
        f = request.form; q("INSERT INTO items(name,info,price,stock) VALUES(?,?,?,?)", (f['name'], f['info'], int(f['price']), int(f['stock'])), w=True)
    return render_template('shop.html', items=q("SELECT * FROM items"), my=q("SELECT * FROM buys WHERE user_id=? ORDER BY id DESC", (me()['id'],)),
                           all=q("SELECT b.*, u.username FROM buys b JOIN users u ON u.id=b.user_id ORDER BY b.id DESC LIMIT 50") if allow('shop_manage') else [])

@app.route('/shop/buy/<int:i>', methods=['POST'])
@need('student')
def buy(i):
    it = q("SELECT * FROM items WHERE id=?", (i,), one=True) or abort(404)
    if it['stock'] == 0: flash("Tugagan")
    elif balance(me()['id']) < it['price']: flash("Ball yetarli emas")
    else:
        q("INSERT INTO buys(user_id,item_id,item,price,at) VALUES(?,?,?,?,?)", (me()['id'], i, it['name'], it['price'], ns()), w=True)
        if it['stock'] > 0: q("UPDATE items SET stock=stock-1 WHERE id=?", (i,), w=True)
        for a in q("SELECT id FROM users WHERE role IN ('boss','admin')"): notify(a['id'], "%s sotib oldi: %s" % (me()['username'], it['name']), url_for('shop'))
        flash("Sotib olindi! 🎉")
    return redirect(url_for('shop'))

@app.route('/shop/give/<int:i>', methods=['POST'])
@need()
def give(i):
    b = q("SELECT * FROM buys WHERE id=?", (i,), one=True) or abort(404)
    q("UPDATE buys SET given=1 WHERE id=?", (i,), w=True); notify(b['user_id'], "'%s' sovg'angiz topshirildi" % b['item'], url_for('shop'))
    return redirect(url_for('shop'))

@app.route('/shop/edit/<int:i>', methods=['POST'])
@need()
def item_edit(i):
    f = request.form; q("UPDATE items SET name=?, info=?, price=?, stock=? WHERE id=?", (f['name'], f['info'], int(f['price']), int(f['stock']), i), w=True)
    flash("Saqlandi ✅"); return redirect(url_for('shop'))

@app.route('/shop/del/<int:i>', methods=['POST'])
@need()
def item_del(i): log("Mahsulot o'chirildi #%s" % i); q("DELETE FROM items WHERE id=?", (i,), w=True); return redirect(url_for('shop'))

# ---------- yangilik, bildirishnoma, profil ----------
@app.route('/news', methods=['GET', 'POST'])
@need()
def news():
    if request.method == 'POST' and allow('news_post'):
        gid = request.form.get('group') or None
        q("INSERT INTO news(title,body,at,group_id) VALUES(?,?,?,?)", (request.form['title'], request.form['body'], ns(), gid), w=True)
        if gid: rec = {r['id'] for r in q("SELECT u.id FROM users u WHERE u.role IN ('boss','admin','teacher') OR u.id IN (SELECT student_id FROM gs WHERE group_id=?) OR u.child_id IN (SELECT student_id FROM gs WHERE group_id=?)", (gid, gid))}
        else: rec = {r['id'] for r in q("SELECT id FROM users")}
        for uid in rec: notify(uid, "Yangilik: " + request.form['title'], url_for('news'))
        flash("E'lon qilindi ✅")
    return render_template('news.html', rows=news_rows(), grps=q("SELECT * FROM grps"))

@app.route('/news/del/<int:i>', methods=['POST'])
@need()
def news_del(i): log("Yangilik o'chirildi #%s" % i); q("DELETE FROM news WHERE id=?", (i,), w=True); return redirect(url_for('news'))

@app.route('/notifs')
@need()
def notifs():
    rows = q("SELECT * FROM notifs WHERE user_id=? ORDER BY id DESC LIMIT 100", (me()['id'],))
    q("UPDATE notifs SET seen=1 WHERE user_id=?", (me()['id'],), w=True)
    return render_template('notifs.html', rows=rows)

@app.route('/profile', methods=['GET', 'POST'])
@need()
def profile():
    if request.method == 'POST':
        f = request.form; u = me(); av = save(request.files.get('avatar')) or u['avatar']; bg = save(request.files.get('bg')) or u['bg']
        if f.get('rmbg'): bg = ''
        q("UPDATE users SET first=?, last=?, avatar=?, bg=?, tg=? WHERE id=?", (f['first'], f['last'], av, bg, f.get('tg', '').strip(), u['id']), w=True)
        if f.get('pw') and len(f['pw']) >= 4: q("UPDATE users SET pw=?, must_change=0 WHERE id=?", (gph(f['pw']), u['id']), w=True)
        flash("Saqlandi ✅"); return redirect(url_for('profile'))
    return render_template('profile.html')


# ===================== YANGI IMKONIYATLAR =====================
MONS = {'uz': ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun', 'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'],
        'ru': ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
        'en': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']}
WDS = {'uz': ['Du', 'Se', 'Chor', 'Pay', 'Ju', 'Sha', 'Yak'], 'ru': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'], 'en': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']}

_TR = """Bosh sahifa|Главная|Home
Kurslar|Курсы|Courses
Ishlarim|Мои работы|My work
Farzandim|Мой ребёнок|My child
Jadval|Расписание|Schedule
Kalendar|Календарь|Calendar
Reyting|Рейтинг|Ranking
Ustozlar|Учителя|Teachers
Magazin|Магазин|Shop
Yangiliklar|Новости|News
Xabarlar|Сообщения|Messages
Foydalanuvchilar|Пользователи|Users
Hisobotlar|Отчёты|Reports
Tarix|История|History
Sozlamalar|Настройки|Settings
Zaxira|Резервная копия|Backup
Bildirishnomalar|Уведомления|Notifications
Bildirishnoma|Уведомления|Notifications
Chiqish|Выйти|Log out
Qidirish|Поиск|Search
Qidiruv|Поиск|Search
O'quv markaz|Учебный центр|Learning Center
Boshliq|Руководитель|Boss
O'qituvchi va o'quvchilar|Учитель и ученики|Teacher and students
O'qituvchi izohi|Комментарий учителя|Teacher comment
O'qituvchi|Учитель|Teacher
O'quvchilar reytingi|Рейтинг учеников|Student ranking
O'quvchi|Ученик|Student
Ota-ona|Родитель|Parent
Xush kelibsiz!|Добро пожаловать!|Welcome!
Hisobingizga kiring|Войдите в аккаунт|Sign in to your account
Parolni unutdingizmi?|Забыли пароль?|Forgot your password?
Login yoki parol xato|Неверный логин или пароль|Wrong username or password
Kirish|Войти|Sign in
Parol|Пароль|Password
Login|Логин|Username
Salom|Привет|Hello
Bugungi darslar|Уроки сегодня|Today lessons
So'nggi yangiliklar|Последние новости|Latest news
Bugun dars yo'q|Сегодня уроков нет|No lessons today
Balans|Баланс|Balance
Jami yig'ilgan|Всего набрано|Total earned
Bajariladigan|К выполнению|To do
Davomat saqlandi|Посещаемость сохранена|Attendance saved
Davomat|Посещаемость|Attendance
Seriya|Серия|Streak
Yutuqlarim|Мои достижения|My achievements
Yutuqlar|Достижения|Achievements
Tekshirilmagan|Не проверено|Unchecked
Kurs qo'shish|Добавить курс|Add course
Kursni tahrirlash|Редактировать курс|Edit course
Kursni o'chirish|Удалить курс|Delete course
Kurs nomi|Название курса|Course name
Kursga qaytish|Назад к курсу|Back to course
Kurs chati|Чат курса|Course chat
Saqlash|Сохранить|Save
Joylash|Опубликовать|Publish
Dars / Uy ishi qo'shish|Добавить урок / задание|Add lesson / homework
Dars materiali|Материал урока|Lesson material
Sarlavha|Заголовок|Title
Matn / topshiriq|Текст / задание|Text / task
Havola (link)|Ссылка|Link
Ovozli xabar|Голосовое сообщение|Voice message
Maksimal ball|Максимум баллов|Max score
Maks. ball|Макс. баллов|Max score
Qayta topshirish|Сдать заново|Resubmit
Topshirish|Сдать|Submit
Yuborish|Отправить|Send
Mening javobim|Мой ответ|My answer
Topshirilgan ishlar|Сданные работы|Submitted work
Topshirmaganlar|Не сдали|Not submitted
Hali hech kim topshirmagan|Пока никто не сдал|Nobody has submitted yet
Yuborildi — tekshirilmoqda|Отправлено — проверяется|Sent — under review
Qabul qilindi|Принято|Accepted
Rad etildi — qayta topshiring|Отклонено — сдайте заново|Rejected — resubmit
Bekor qilindi — qayta topshiring|Отменено — сдайте заново|Cancelled — resubmit
Qabul + baho|Принять + оценка|Accept + grade
Rad etish|Отклонить|Reject
Bekor qilish|Отменить|Cancel
Kechikkan|С опозданием|Late
Uy ishingiz yuborildi!|Ваше задание отправлено!|Your homework was sent!
Bajarilishi kerak|Нужно выполнить|To be done
Yuborilgan ishlar|Отправленные работы|Sent work
Hammasi bajarilgan!|Всё выполнено!|All done!
Dars jadvali|Расписание уроков|Lesson schedule
Darslar yo'q|Уроков нет|No lessons
Barcha jadvallar|Все расписания|All schedules
Qo'shish|Добавить|Add
Ko'rish|Показать|Show
Ustozlar reytingi|Рейтинг учителей|Teacher ranking
Bahoni yangilash|Обновить оценку|Update rating
Baholash|Оценить|Rate
Fikringiz (ixtiyoriy)|Ваш отзыв (необязательно)|Your feedback (optional)
Fikrlar|Отзывы|Feedback
Umumiy reyting|Общий рейтинг|Overall ranking
Barcha vaqt|Всё время|All time
Shu hafta|Эта неделя|This week
Shu oy|Этот месяц|This month
Oy o'quvchisi|Ученик месяца|Student of the month
Sotib olish|Купить|Buy
Xaridlarim|Мои покупки|My purchases
Ballaringiz|Ваши баллы|Your points
Profil|Профиль|Profile
Familiya|Фамилия|Surname
Ismni saqlash|Сохранить имя|Save name
Orqa fon rasmi|Фоновое изображение|Background image
Fonni o'chirish|Убрать фон|Remove background
Yangi parol (ixtiyoriy)|Новый пароль (необязательно)|New password (optional)
Ilovani to'xtatib turish|Приостановить приложение|Pause the app
Ustozlarni baholash tizimi|Система оценки учителей|Teacher rating system
Kunlik bonus va seriya|Ежедневный бонус и серия|Daily bonus and streak
Xabarlar va kurs chati|Сообщения и чат курса|Messages and course chat
Testlar|Тесты|Quizzes
Testni boshlaysizmi?|Начать тест?|Start the test?
Boshlash|Начать|Start
Yakunlash|Завершить|Finish
Keldi|Присутствовал|Present
Yangi xabar|Новое сообщение|New message
Xabar yozing|Напишите сообщение|Write a message
Izohlar|Комментарии|Comments
Sertifikat|Сертификат|Certificate
Jurnal|Журнал|Gradebook
Harakatlar tarixi|История действий|Activity log
Kurslar bo'yicha|По курсам|By course
Parolni tiklash|Сбросить пароль|Reset password
Rolni o'zgartirish|Сменить роль|Change role
Kechikkan|С опозданием|Late
Texnik tanaffus|Технический перерыв|Maintenance
Ilova vaqtincha to'xtatilgan|Приложение временно приостановлено|The app is temporarily paused
Kutubxona|Библиотека|Library
So'rovnomalar|Опросы|Polls
Vazifalar|Задания|Challenges
To'lovlarim|Мои платежи|My payments
To'lovlar|Платежи|Payments
Guruhlar musobaqasi|Соревнование групп|Group competition
Guruhlar|Группы|Groups
So'rovlar|Заявки|Requests
Huquqlar boshqaruvi|Управление правами|Permissions
Huquqlar|Права|Permissions
Mening huquqlarim|Мои права|My permissions
Xotira|Хранилище|Storage
Qarzdorlik|Задолженность|Debt
Faol qurilmalar|Активные устройства|Active devices
Baholar varaqasi|Табель оценок|Report card
Dars rejasi|План занятий|Lesson plan
Boshqa kurslar|Другие курсы|Other courses
Yozilish so'rovi|Заявка на запись|Enrollment request
Yakuniy imtihon|Итоговый экзамен|Final exam
QR bilan davomat|Посещаемость по QR|QR attendance
Mavzu|Тема|Theme
To'lov nazorati|Контроль платежей|Payment control
Parolni o'zgartiring|Смените пароль|Change your password"""
TRS = sorted([tuple(l.split('|')) for l in _TR.strip().split('\n')], key=lambda x: -len(x[0]))

@app.after_request
def translate(resp):
    L = session.get('lang', 'uz')
    if L != 'uz' and resp.mimetype == 'text/html' and not resp.direct_passthrough:
        h = resp.get_data(as_text=True).replace('&#39;', "'")
        for k, ru, en in TRS: h = h.replace(k, ru if L == 'ru' else en)
        resp.set_data(h)
    return resp

@app.route('/lang/<code>')
def lang(code):
    if code in ('uz', 'ru', 'en'): session['lang'] = code
    ref = request.referrer or ''
    return redirect(ref if ref and request.host in ref else url_for('dash'))

# ---------- yordamchi funksiyalar ----------
def log(a):
    try: q("INSERT INTO logs(user_id,action,at) VALUES(?,?,?)", (me()['id'] if me() else None, a, ns()), w=True)
    except Exception: pass

def _tg(tok, chat, text):
    try: urllib.request.urlopen(urllib.request.Request('https://api.telegram.org/bot%s/sendMessage' % tok, urllib.parse.urlencode({'chat_id': chat, 'text': text}).encode()), timeout=6)
    except Exception: pass

def att_pct(uid, cid=None):
    r = q("SELECT COUNT(*) n, COALESCE(SUM(present),0) p FROM att WHERE student_id=?" + (" AND course_id=?" if cid else ""), (uid, cid) if cid else (uid,), one=True)
    return (round(r['p'] * 100 / r['n']) if r['n'] else 100, r['n'])

def streak(uid):
    days = {r['day'] for r in q("SELECT day FROM bonus WHERE user_id=? AND reason='daily'", (uid,))}
    d = now().date()
    if d.isoformat() not in days: d -= timedelta(days=1)
    n = 0
    while d.isoformat() in days: n += 1; d -= timedelta(days=1)
    return n

def daily(uid):
    if st()['bonus'] != '1': return
    d = now().date().isoformat()
    if q("SELECT 1 FROM bonus WHERE user_id=? AND reason='daily' AND day=?", (uid, d), one=True): return
    q("INSERT INTO bonus(user_id,reason,points,at,day) VALUES(?,?,?,?,?)", (uid, 'daily', 1, ns(), d), w=True)
    n = streak(uid); msg = "🔥 Kunlik bonus: +1 ball (seriya: %d kun)" % n
    if n % 7 == 0:
        q("INSERT INTO bonus(user_id,reason,points,at,day) VALUES(?,?,?,?,?)", (uid, 'streak7', 5, ns(), d), w=True); msg += " · 7 kunlik seriya: +5 ball!"
    flash(msg)

def badges(uid):
    out = []; gr = q("SELECT s.score, p.maxscore FROM subs s JOIN posts p ON p.id=s.post_id WHERE s.student_id=? AND s.status='graded'", (uid,))
    n = len(gr); e = earned(uid)
    if n >= 1: out.append(('🚀', 'Birinchi qadam', "Birinchi uy ishi qabul qilindi"))
    if n >= 5: out.append(('🔥', 'Faol', "5 ta uy ishi bajarildi"))
    if n >= 20: out.append(('🏆', 'Mehnatkash', "20 ta uy ishi bajarildi"))
    if any((r['score'] or 0) >= (r['maxscore'] or 100) for r in gr): out.append(('⭐', 'Mukammal', "To'liq ball oldingiz"))
    r = q("SELECT COUNT(*) n, COALESCE(SUM(late),0) l FROM subs WHERE student_id=?", (uid,), one=True)
    if r['n'] >= 3 and r['l'] == 0: out.append(('⏱', 'Intizomli', "Hech qachon kechikmagan"))
    if e >= 100: out.append(('🏅', '100 ball', "100 ball yig'dingiz"))
    if e >= 500: out.append(('💎', '500 ball', "500 ball yig'dingiz"))
    pct, cnt = att_pct(uid)
    if cnt >= 5 and pct >= 90: out.append(('📅', 'Davomli', "Davomat 90% dan yuqori"))
    if any(a['score'] * 100 >= 90 * a['maxscore'] for a in q("SELECT a.score, z.maxscore FROM qatt a JOIN quizzes z ON z.id=a.quiz_id WHERE a.student_id=? AND a.score IS NOT NULL", (uid,))): out.append(('🧠', 'Test ustasi', "Testdan 90% dan yuqori natija"))
    if streak(uid) >= 7: out.append(('🔥', '7 kunlik seriya', "7 kun ketma-ket kirdingiz"))
    return out

def cert_ok(cid, sid):
    hws = q("SELECT id FROM posts WHERE course_id=? AND kind='hw'", (cid,))
    fin = q("SELECT * FROM quizzes WHERE course_id=? AND final=1", (cid,))
    if not hws and not fin: return (False, 0)
    avg = 100
    if hws:
        sc = q("SELECT s.score, p.maxscore FROM subs s JOIN posts p ON p.id=s.post_id WHERE p.course_id=? AND s.student_id=? AND s.status='graded'", (cid, sid))
        if len(sc) < len(hws): return (False, 0)
        avg = round(sum((r['score'] or 0) * 100 / (r['maxscore'] or 100) for r in sc) / len(sc))
        if avg < 50: return (False, avg)
    for z in fin:
        a = q("SELECT score FROM qatt WHERE quiz_id=? AND student_id=? AND score IS NOT NULL", (z['id'], sid), one=True)
        if not a or a['score'] * 100 < (z['pass_pct'] or 60) * z['maxscore']: return (False, avg)
        if not hws: avg = round(a['score'] * 100 / z['maxscore'])
    return (True, avg)

def parse_quiz(txt):
    out = []
    for blk in re.split(r'\n\s*\n', txt.replace('\r', '').strip()):
        ls = [l.strip() for l in blk.split('\n') if l.strip()]
        opts = {}; ans = ''; qs = []
        for l in ls:
            a = re.match(r'^(javob|answer|ответ)\s*[:\-]\s*([ABCDabcd])', l, re.I); m = re.match(r'^([ABCDabcd])[\)\.\:]\s*(.+)$', l)
            if a: ans = a.group(2).upper()
            elif m: opts[m.group(1).upper()] = m.group(2)
            else: qs.append(l)
        if not qs or len(opts) < 2 or ans not in opts: return None
        out.append((' '.join(qs), opts.get('A', ''), opts.get('B', ''), opts.get('C', ''), opts.get('D', ''), ans))
    return out or None

def csv_resp(name, header, rows):
    s_ = io.StringIO(); w_ = csv.writer(s_); w_.writerow(header); w_.writerows(rows)
    return Response('\ufeff' + s_.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=%s.csv' % name})

def _member(cid): return cid in [x['id'] for x in my_courses()]
def _who(u): return (u['first'] + ' ' + u['last']).strip() or u['username']

# ---------- PWA ----------
@app.route('/manifest.json')
def manifest():
    return Response(json.dumps({'name': "O'quv markaz", 'short_name': "O'quv markaz", 'start_url': '/', 'display': 'standalone', 'background_color': '#f2f3fb',
                                'theme_color': '#6c5ce7', 'icons': [{'src': '/icon.svg', 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any maskable'}]}), mimetype='application/manifest+json')

@app.route('/sw.js')
def sw(): return Response("self.addEventListener('install',function(){self.skipWaiting()});self.addEventListener('fetch',function(){});", mimetype='application/javascript')

@app.route('/icon.svg')
def icon():
    return Response('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#5b49d6"/><stop offset="1" stop-color="#a363ff"/></linearGradient></defs><rect width="512" height="512" rx="110" fill="url(#g)"/><text x="256" y="345" font-size="260" text-anchor="middle">📚</text></svg>', mimetype='image/svg+xml')

# ---------- parolni unutdim ----------
@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        u = q("SELECT * FROM users WHERE username=?", (request.form['username'].strip(),), one=True)
        if u:
            for a in q("SELECT id FROM users WHERE role IN ('boss','admin')"): notify(a['id'], "🔑 %s parolni tiklashni so'radi" % u['username'], url_for('users'))
        flash("Agar bunday login mavjud bo'lsa, adminlarga so'rov yuborildi. Admin sizga yangi parol beradi.")
        return redirect(url_for('login'))
    return render_template('forgot.html')

# ---------- davomat ----------
@app.route('/course/<int:i>/attendance', methods=['GET', 'POST'])
@need()
def attendance(i):
    c = q("SELECT * FROM courses WHERE id=?", (i,), one=True) or abort(404)
    if not can_course(c): abort(403)
    day = request.values.get('day') or now().strftime('%Y-%m-%d')
    stu = q("SELECT u.* FROM users u JOIN cs ON cs.student_id=u.id AND cs.course_id=? ORDER BY u.first, u.username", (i,))
    if request.method == 'POST' and request.form.get('save'):
        for x in stu:
            pr = 1 if request.form.get('p%d' % x['id']) else 0
            q("INSERT OR REPLACE INTO att(course_id,student_id,day,present) VALUES(?,?,?,?)", (i, x['id'], day, pr), w=True)
            if not pr:
                notify(x['id'], "📋 Siz %s kuni '%s' darsida qatnashmadingiz" % (day, c['name']), url_for('my_att'))
                last = q("SELECT present FROM att WHERE course_id=? AND student_id=? ORDER BY day DESC LIMIT 3", (i, x['id']))
                if len(last) == 3 and not any(r['present'] for r in last):
                    for a in q("SELECT id FROM users WHERE role IN ('boss','admin')"): notify(a['id'], "⚠️ %s '%s' darsiga 3 marta ketma-ket kelmadi" % (_who(x), c['name']), url_for('attendance', i=i))
        flash("Davomat saqlandi ✅")
    ex = {r['student_id']: r['present'] for r in q("SELECT * FROM att WHERE course_id=? AND day=?", (i, day))}
    return render_template('attendance.html', c=c, day=day, stu=stu, ex=ex, dflt=0 if ex else 1, pcts={x['id']: att_pct(x['id'], i) for x in stu})

@app.route('/attendance')
@need('student', 'parent')
def my_att():
    u = me(); sid = u['id'] if u['role'] == 'student' else (u['child_id'] or 0); rows = []
    for c in my_courses():
        pct, n = att_pct(sid, c['id'])
        rows.append(dict(c=c, pct=pct, n=n, absent=[r['day'] for r in q("SELECT day FROM att WHERE course_id=? AND student_id=? AND present=0 ORDER BY day DESC LIMIT 10", (c['id'], sid))]))
    return render_template('att_me.html', rows=rows)

# ---------- testlar ----------
@app.route('/course/<int:i>/quizzes', methods=['GET', 'POST'])
@need()
def quizzes(i):
    c = q("SELECT * FROM courses WHERE id=?", (i,), one=True) or abort(404)
    if not _member(i): abort(403)
    if request.method == 'POST' and can_course(c) and allow('quiz_create'):
        f = request.form; qs = parse_quiz(f['qs'])
        if not qs: flash("Savollar formati noto'g'ri. Namunaga qarang.")
        else:
            try: mn = max(0, min(300, int(f.get('minutes') or 0))); mx = max(1, min(1000, int(f.get('maxscore') or 100)))
            except ValueError: mn, mx = 10, 100
            zid = q("INSERT INTO quizzes(course_id,title,minutes,maxscore,created,final,pass_pct) VALUES(?,?,?,?,?,?,?)", (i, f['title'], mn, mx, ns(), 1 if f.get('final') else 0, max(1, min(100, int(f.get('pass_pct') or 60)))), w=True)
            for x in qs: q("INSERT INTO qq(quiz_id,q,a,b,c,d,ans) VALUES(?,?,?,?,?,?,?)", (zid,) + x, w=True)
            for s_ in q("SELECT student_id FROM cs WHERE course_id=?", (i,)): notify(s_['student_id'], "Yangi test: " + f['title'], url_for('quiz', i=zid))
            flash("Test joylandi ✅")
    rows = q("SELECT z.*, (SELECT COUNT(*) FROM qq WHERE quiz_id=z.id) n, (SELECT COUNT(*) FROM qatt WHERE quiz_id=z.id AND score IS NOT NULL) done FROM quizzes z WHERE course_id=? ORDER BY id DESC", (i,))
    mine = {r['quiz_id']: r for r in q("SELECT * FROM qatt WHERE student_id=?", (me()['id'],))}
    return render_template('quizzes.html', c=c, rows=rows, mine=mine, can=can_course(c) and allow('quiz_create'))

@app.route('/quiz/<int:i>')
@need()
def quiz(i):
    z = q("SELECT * FROM quizzes WHERE id=?", (i,), one=True) or abort(404)
    c = q("SELECT * FROM courses WHERE id=?", (z['course_id'],), one=True)
    if not _member(c['id']): abort(403)
    qs = q("SELECT * FROM qq WHERE quiz_id=? ORDER BY id", (i,))
    att = q("SELECT * FROM qatt WHERE quiz_id=? AND student_id=?", (i, me()['id']), one=True); left = 0
    can = can_course(c)
    res = q("SELECT a.*, u.username, u.first, u.last FROM qatt a JOIN users u ON u.id=a.student_id WHERE quiz_id=? ORDER BY a.id DESC", (i,)) if can else []
    if att and att['score'] is None and z['minutes']:
        el = (now() - datetime.strptime(att['started'], '%Y-%m-%d %H:%M:%S')).total_seconds(); left = max(1, int(z['minutes'] * 60 - el))
    answers = json.loads(att['answers']) if att and att['answers'] else {}
    return render_template('quiz.html', z=z, c=c, qs=qs, att=att, left=left, res=res, can=can, answers=answers)

@app.route('/quiz/<int:i>/start', methods=['POST'])
@need('student')
def quiz_start(i):
    z = q("SELECT * FROM quizzes WHERE id=?", (i,), one=True) or abort(404)
    if not _member(z['course_id']): abort(403)
    n = q("SELECT COUNT(*) n FROM qq WHERE quiz_id=?", (i,), one=True)['n']
    q("INSERT OR IGNORE INTO qatt(quiz_id,student_id,score,total,good,at,started,answers) VALUES(?,?,NULL,?,NULL,?,?,'')", (i, me()['id'], n, ns(), now().strftime('%Y-%m-%d %H:%M:%S')), w=True)
    return redirect(url_for('quiz', i=i))

@app.route('/quiz/<int:i>/submit', methods=['POST'])
@need('student')
def quiz_submit(i):
    z = q("SELECT * FROM quizzes WHERE id=?", (i,), one=True) or abort(404)
    att = q("SELECT * FROM qatt WHERE quiz_id=? AND student_id=?", (i, me()['id']), one=True)
    if not att or att['score'] is not None: return redirect(url_for('quiz', i=i))
    qs = q("SELECT * FROM qq WHERE quiz_id=?", (i,)); ans = {str(x['id']): request.form.get('q%d' % x['id'], '') for x in qs}
    good = sum(1 for x in qs if ans[str(x['id'])] == x['ans'])
    el = (now() - datetime.strptime(att['started'], '%Y-%m-%d %H:%M:%S')).total_seconds()
    over = bool(z['minutes']) and el > z['minutes'] * 60 + 60
    score = 0 if over else round(good * z['maxscore'] / max(1, len(qs)))
    q("UPDATE qatt SET score=?, good=?, total=?, at=?, answers=? WHERE id=?", (score, good, len(qs), ns(), json.dumps(ans), att['id']), w=True)
    t = q("SELECT teacher_id FROM courses WHERE id=?", (z['course_id'],), one=True)['teacher_id']
    if t: notify(t, "%s testni yakunladi: %s (%d/%d)" % (me()['username'], z['title'], score, z['maxscore']), url_for('quiz', i=i))
    flash("⏰ Vaqt tugagan edi — ball berilmadi" if over else "✅ Test yakunlandi: %d/%d ball" % (score, z['maxscore']))
    return redirect(url_for('quiz', i=i))

@app.route('/quiz/<int:i>/reset/<int:sid>', methods=['POST'])
@need()
def quiz_reset(i, sid):
    z = q("SELECT * FROM quizzes WHERE id=?", (i,), one=True) or abort(404)
    if not can_course(q("SELECT * FROM courses WHERE id=?", (z['course_id'],), one=True)): abort(403)
    q("DELETE FROM qatt WHERE quiz_id=? AND student_id=?", (i, sid), w=True); notify(sid, "Test qayta topshirishga ochildi: " + z['title'], url_for('quiz', i=i))
    log("Test natijasi bekor qilindi: test #%s, o'quvchi #%s" % (i, sid)); return redirect(url_for('quiz', i=i))

@app.route('/quiz/<int:i>/del', methods=['POST'])
@need()
def quiz_del(i):
    z = q("SELECT * FROM quizzes WHERE id=?", (i,), one=True) or abort(404)
    if not can_course(q("SELECT * FROM courses WHERE id=?", (z['course_id'],), one=True)): abort(403)
    for t in ('qq', 'qatt'): q("DELETE FROM %s WHERE quiz_id=?" % t, (i,), w=True)
    q("DELETE FROM quizzes WHERE id=?", (i,), w=True); log("Test o'chirildi #%s" % i); return redirect(url_for('quizzes', i=z['course_id']))

# ---------- sertifikat ----------
@app.route('/certificate/<int:cid>')
@need()
def certificate(cid):
    u = me(); c = q("SELECT * FROM courses WHERE id=?", (cid,), one=True) or abort(404)
    if u['role'] in ('student', 'parent'):
        if not allow('cert_view'): abort(403)
        sid = u['id'] if u['role'] == 'student' else (u['child_id'] or 0); ok, avg = cert_ok(cid, sid)
        if not ok: flash("Sertifikat uchun barcha uy ishlari baholangan va o'rtacha kamida 50% bo'lishi kerak"); return redirect(url_for('course', i=cid))
    else:
        if not (can_course(c) and allow('cert_issue')): abort(403)
        sid = request.args.get('s', type=int) or abort(400); ok, avg = cert_ok(cid, sid)
    s_ = q("SELECT * FROM users WHERE id=?", (sid,), one=True) or abort(404)
    if not q("SELECT 1 FROM cs WHERE course_id=? AND student_id=?", (cid, sid), one=True): abort(403)
    return render_template('cert.html', c=c, s=s_, avg=avg, day=now().strftime('%d.%m.%Y'), tn=q("SELECT * FROM users WHERE id=?", (c['teacher_id'],), one=True))

# ---------- izohlar ----------
@app.route('/post/<int:i>/comment', methods=['POST'])
@need()
def post_comment(i):
    p = q("SELECT * FROM posts WHERE id=?", (i,), one=True) or abort(404)
    if not _member(p['course_id']): abort(403)
    t = request.form.get('text', '').strip()[:1000]
    if t:
        q("INSERT INTO comments(post_id,user_id,text,at) VALUES(?,?,?,?)", (i, me()['id'], t, ns()), w=True)
        people = {r['user_id'] for r in q("SELECT DISTINCT user_id FROM comments WHERE post_id=?", (i,))}
        tc = q("SELECT teacher_id FROM courses WHERE id=?", (p['course_id'],), one=True)['teacher_id']
        if tc: people.add(tc)
        people.discard(me()['id'])
        for uid in people: notify(uid, "💬 %s izoh yozdi: %s" % (_who(me()), p['title']), url_for('post', i=i))
    return redirect(url_for('post', i=i) + '#c')

@app.route('/comment/<int:i>/del', methods=['POST'])
@need()
def del_comment(i):
    m = q("SELECT * FROM comments WHERE id=?", (i,), one=True) or abort(404)
    if not (is_adm() or m['user_id'] == me()['id']): abort(403)
    q("DELETE FROM comments WHERE id=?", (i,), w=True); return redirect(url_for('post', i=m['post_id']))

# ---------- ota-ona ----------
@app.route('/child')
@need('parent')
def child():
    u = me(); s_ = q("SELECT * FROM users WHERE id=?", (u['child_id'] or 0,), one=True)
    if not s_: return render_template('child.html', s=None)
    b = board()
    info = dict(debt=debt(s_['id']), bal=balance(s_['id']), earn=earned(s_['id']), total=len(b), att=att_pct(s_['id'])[0], todo=len(todo(s_['id'])),
                rank=next((k + 1 for k, x in enumerate(b) if x['id'] == s_['id']), '-'))
    subs = q("SELECT s.*, p.title, p.maxscore, c.name cname, c.color FROM subs s JOIN posts p ON p.id=s.post_id JOIN courses c ON c.id=p.course_id WHERE s.student_id=? ORDER BY s.id DESC LIMIT 15", (s_['id'],))
    certs = [c for c in my_courses() if cert_ok(c['id'], s_['id'])[0]]
    return render_template('child.html', s=s_, info=info, subs=subs, certs=certs)

# ---------- xabarlar ----------
@app.route('/messages')
@need()
def messages():
    m = me()['id']
    partners = q("""SELECT u.*, (SELECT COUNT(*) FROM msgs WHERE from_id=u.id AND to_id=? AND seen=0) unr,
        (SELECT text FROM msgs WHERE (from_id=u.id AND to_id=?) OR (from_id=? AND to_id=u.id) ORDER BY id DESC LIMIT 1) lm
        FROM users u WHERE u.id IN (SELECT from_id FROM msgs WHERE to_id=? UNION SELECT to_id FROM msgs WHERE from_id=?)
        ORDER BY (SELECT MAX(id) FROM msgs WHERE (from_id=u.id AND to_id=?) OR (from_id=? AND to_id=u.id)) DESC""", (m,) * 7)
    return render_template('messages.html', partners=partners, users_=q("SELECT * FROM users WHERE id!=? ORDER BY role, first, username", (m,)))

@app.route('/messages/<int:uid>', methods=['GET', 'POST'])
@need()
def thread(uid):
    o = q("SELECT * FROM users WHERE id=?", (uid,), one=True) or abort(404); m = me()['id']
    if uid == m: abort(400)
    if request.method == 'POST':
        t = request.form.get('text', '').strip()[:2000]
        if t:
            q("INSERT INTO msgs(from_id,to_id,text,at) VALUES(?,?,?,?)", (m, uid, t, ns()), w=True)
            lk = url_for('thread', uid=m)
            if not q("SELECT 1 FROM notifs WHERE user_id=? AND link=? AND seen=0", (uid, lk), one=True): notify(uid, "✉️ Yangi xabar: " + _who(me()), lk)
        return redirect(url_for('thread', uid=uid))
    q("UPDATE msgs SET seen=1 WHERE from_id=? AND to_id=?", (uid, m), w=True)
    rows = q("SELECT * FROM msgs WHERE (from_id=? AND to_id=?) OR (from_id=? AND to_id=?) ORDER BY id DESC LIMIT 100", (m, uid, uid, m))[::-1]
    return render_template('thread.html', o=o, rows=rows)

@app.route('/course/<int:i>/chat', methods=['GET', 'POST'])
@need()
def course_chat(i):
    c = q("SELECT * FROM courses WHERE id=?", (i,), one=True) or abort(404)
    if not _member(i): abort(403)
    if request.method == 'POST':
        if me()['role'] == 'parent': abort(403)
        t = request.form.get('text', '').strip()[:1000]
        if t: q("INSERT INTO cmsg(course_id,user_id,text,at) VALUES(?,?,?,?)", (i, me()['id'], t, ns()), w=True)
        return redirect(url_for('course_chat', i=i))
    rows = q("SELECT m.*, u.username, u.first, u.last, u.avatar, u.role FROM cmsg m JOIN users u ON u.id=m.user_id WHERE course_id=? ORDER BY m.id DESC LIMIT 100", (i,))[::-1]
    return render_template('chat.html', c=c, rows=rows)

@app.route('/cmsg/<int:i>/del', methods=['POST'])
@need()
def cmsg_del(i):
    m = q("SELECT * FROM cmsg WHERE id=?", (i,), one=True) or abort(404)
    q("DELETE FROM cmsg WHERE id=?", (i,), w=True); return redirect(url_for('course_chat', i=m['course_id']))

# ---------- hisobotlar, jurnal ----------
def _rep():
    cr = q("""SELECT c.id, c.name, c.color, (SELECT COUNT(*) FROM cs WHERE course_id=c.id) students,
        (SELECT COUNT(*) FROM posts WHERE course_id=c.id AND kind='hw') hw,
        (SELECT COUNT(*) FROM subs s JOIN posts p ON p.id=s.post_id WHERE p.course_id=c.id) subs,
        (SELECT COUNT(*) FROM subs s JOIN posts p ON p.id=s.post_id WHERE p.course_id=c.id AND s.late=1) late,
        (SELECT ROUND(AVG(s.score*100.0/p.maxscore),1) FROM subs s JOIN posts p ON p.id=s.post_id WHERE p.course_id=c.id AND s.status='graded') avgp FROM courses c""")
    ts = q("""SELECT u.id, u.username, u.first, u.last, (SELECT COUNT(*) FROM courses WHERE teacher_id=u.id) courses,
        (SELECT COUNT(*) FROM subs s JOIN posts p ON p.id=s.post_id JOIN courses c ON c.id=p.course_id WHERE c.teacher_id=u.id AND s.status='graded') graded,
        (SELECT COUNT(*) FROM subs s JOIN posts p ON p.id=s.post_id JOIN courses c ON c.id=p.course_id WHERE c.teacher_id=u.id AND s.status='sent') pending,
        (SELECT ROUND(AVG(stars),1) FROM trate WHERE teacher_id=u.id) rate FROM users u WHERE u.role='teacher'""")
    ss = []
    for u in q("SELECT * FROM users WHERE role='student'"):
        r = q("SELECT COUNT(*) n, COALESCE(SUM(late),0) l FROM subs WHERE student_id=?", (u['id'],), one=True)
        ss.append(dict(u=u, earned=earned(u['id']), att=att_pct(u['id'])[0], subs=r['n'], late=r['l']))
    ss.sort(key=lambda x: -x['earned'])
    return cr, ts, ss

@app.route('/reports')
@need()
def reports():
    cr, ts, ss = _rep(); return render_template('reports.html', cr=cr, ts=ts, ss=ss)

@app.route('/reports/csv')
@need()
def reports_csv():
    cr, ts, ss = _rep(); t = request.args.get('t', 'courses')
    if t == 'teachers': return csv_resp('ustozlar', ['Ustoz', 'Kurslar', 'Baholangan', 'Kutilmoqda', 'Reyting'], [[_who(x), x['courses'], x['graded'], x['pending'], x['rate'] or ''] for x in ts])
    if t == 'students': return csv_resp('oquvchilar', ["O'quvchi", 'Ball', 'Davomat %', 'Topshirgan', 'Kechikkan'], [[_who(x['u']), x['earned'], x['att'], x['subs'], x['late']] for x in ss])
    return csv_resp('kurslar', ['Kurs', "O'quvchilar", 'Uy ishlari', 'Topshirilgan', 'Kechikkan', "O'rtacha %"], [[x['name'], x['students'], x['hw'], x['subs'], x['late'], x['avgp'] or ''] for x in cr])

@app.route('/course/<int:i>/journal')
@need()
def journal(i):
    c = q("SELECT * FROM courses WHERE id=?", (i,), one=True) or abort(404)
    if not can_course(c): abort(403)
    hws = q("SELECT * FROM posts WHERE course_id=? AND kind='hw' ORDER BY id", (i,))
    stu = q("SELECT u.* FROM users u JOIN cs ON cs.student_id=u.id AND cs.course_id=? ORDER BY u.first, u.username", (i,))
    sm = {(r['post_id'], r['student_id']): r for r in q("SELECT s.* FROM subs s JOIN posts p ON p.id=s.post_id WHERE p.course_id=?", (i,))}
    SYM = {'sent': '📨', 'rejected': '❌', 'reopened': '↩️'}; rows = []
    for x in stu:
        cells = []; tot = 0
        for h in hws:
            r = sm.get((h['id'], x['id']))
            if not r: cells.append('—')
            elif r['status'] == 'graded': cells.append(r['score']); tot += r['score'] or 0
            else: cells.append(SYM.get(r['status'], '?'))
        rows.append(dict(s=x, cells=cells, total=tot, att=att_pct(x['id'], i)[0]))
    if request.args.get('csv'):
        return csv_resp('jurnal-%d' % i, ["O'quvchi"] + [h['title'] for h in hws] + ['Jami', 'Davomat %'], [[_who(r['s'])] + r['cells'] + [r['total'], r['att']] for r in rows])
    return render_template('journal.html', c=c, hws=hws, rows=rows)

# ---------- tarix, zaxira ----------
@app.route('/logs')
@need()
def logs():
    return render_template('logs.html', rows=q("SELECT l.*, u.username uname FROM logs l LEFT JOIN users u ON u.id=l.user_id ORDER BY l.id DESC LIMIT 200"))

@app.route('/backup')
@need()
def backup():
    import tempfile
    fd, p = tempfile.mkstemp(suffix='.sqlite3'); os.close(fd)
    a = sqlite3.connect(DB); b = sqlite3.connect(p); a.backup(b); b.close(); a.close()
    log("Zaxira nusxa yuklab olindi")
    r = send_file(p, as_attachment=True, download_name='backup-%s.sqlite3' % now().strftime('%Y%m%d-%H%M'))
    r.call_on_close(lambda: os.path.exists(p) and os.remove(p))
    return r

# ---------- kalendar, qidiruv ----------
@app.route('/calendar')
@need()
def cal():
    try: y, mo = map(int, (request.args.get('m') or now().strftime('%Y-%m')).split('-')); first = date(y, mo, 1)
    except Exception: first = now().date().replace(day=1)
    y, mo = first.year, first.month; nd = calendar.monthrange(y, mo)[1]; ev = {}
    for d, t, cn, _ in lessons(nd, first): ev.setdefault(d.day, []).append(('ls', t + ' ' + cn, '/schedule'))
    ids = [c['id'] for c in my_courses()]
    if ids:
        for p in q("SELECT id, title, deadline FROM posts WHERE kind='hw' AND deadline LIKE ? AND course_id IN (%s)" % ','.join('?' * len(ids)), [first.strftime('%Y-%m') + '%'] + ids):
            ev.setdefault(int(p['deadline'][8:10]), []).append(('dl', '📝 ' + p['title'] + ' ' + p['deadline'][11:], '/post/%d' % p['id']))
    return render_template('cal.html', weeks=calendar.monthcalendar(y, mo), ev=ev, y=y, mo=mo, today=now().date(),
                           prev=(first - timedelta(days=1)).strftime('%Y-%m'), nxt=(first + timedelta(days=nd)).strftime('%Y-%m'))

@app.route('/search')
@need()
def search():
    k = request.args.get('q', '').strip(); like = '%' + k + '%'; cs_ = []; ps = []; us = []
    if len(k) >= 2:
        ids = [c['id'] for c in my_courses()]
        if ids:
            ph = ','.join('?' * len(ids))
            cs_ = q("SELECT * FROM courses WHERE id IN (%s) AND (name LIKE ? OR info LIKE ?)" % ph, ids + [like, like])
            ps = q("SELECT p.*, c.name cname FROM posts p JOIN courses c ON c.id=p.course_id WHERE p.course_id IN (%s) AND (p.title LIKE ? OR p.text LIKE ?) ORDER BY p.id DESC LIMIT 30" % ph, ids + [like, like])
        us = q("SELECT * FROM users WHERE " + ("" if is_adm() else "role='teacher' AND ") + "(username LIKE ? OR first LIKE ? OR last LIKE ?) LIMIT 30", (like, like, like))
    return render_template('search.html', k=k, cs_=cs_, ps=ps, us=us)

# ===================== 3-BOSQICH: HUQUQLAR, TO'LOV, GURUH VA BOSHQALAR =====================
def _s(x): return set(x.split())
PERMS = [
 ('👥 Foydalanuvchilar', [('users_view', "Foydalanuvchilar ro'yxatini ko'rish"), ('users_create', "Yangi foydalanuvchi qo'shish"), ('users_edit', "Ism, parol va farzandni o'zgartirish"),
                           ('users_role', "Rolni o'zgartirish"), ('users_delete', "Foydalanuvchini o'chirish"), ('users_import', "CSV orqali ommaviy qo'shish")]),
 ('📘 Kurslar va dars jarayoni', [('courses_manage', "Kurs yaratish/tahrirlash/o'chirish, o'quvchi biriktirish"), ('groups_manage', "Guruhlarni boshqarish"), ('schedule_manage', "Dars jadvalini boshqarish"),
                                  ('post_create', "Dars va uy ishi joylash/tahrirlash"), ('plan_manage', "Dars rejasini yuritish"), ('quiz_create', "Test yaratish va natijani bekor qilish"),
                                  ('attendance', "Davomat olish (QR ham)"), ('journal', "Jurnalni ko'rish"), ('enroll_approve', "Kursga yozilish so'rovlarini ko'rib chiqish"),
                                  ('library_upload', "Kutubxonaga material qo'shish"), ('library_manage', "Kutubxonadagi hamma materialni boshqarish"), ('poll_create', "So'rovnoma yaratish"), ('challenge_manage', "Haftalik vazifa yaratish va tasdiqlash")]),
 ('📝 Baholash', [('grade', "Uy ishini baholash / rad etish / bekor qilish"), ('cert_issue', "O'quvchi uchun sertifikat chiqarish"), ('reportcard_staff', "O'quvchining baholar varaqasini ko'rish"), ('trate_manage', "Ustoz baholari va fikrlarini ko'rish/o'chirish")]),
 ('💰 Moliya va magazin', [('payments_manage', "To'lovlarni boshqarish"), ('shop_manage', "Magazin mahsulotlari va xaridlarni boshqarish"), ('news_post', "Yangilik e'lon qilish va o'chirish")]),
 ('⚙️ Tizim', [('reports_view', "Hisobotlarni ko'rish"), ('logs_view', "Harakatlar tarixini ko'rish"), ('settings_manage', "Sozlamalarni o'zgartirish"), ('pause_app', "Ilovani to'xtatib turish"),
               ('storage_manage', "Xotira va fayllarni boshqarish"), ('backup', "Bazaning zaxira nusxasini yuklab olish")]),
 ('🎓 O\'quvchi imkoniyatlari', [('submit_hw', "Uy ishi topshirish"), ('quiz_take', "Test yechish"), ('shop_buy', "Magazindan sotib olish"), ('rate_teacher', "Ustozlarni baholash"),
                                ('join_request', "Kursga yozilish so'rovi yuborish"), ('challenge_claim', "Vazifani bajardim deb belgilash"), ('poll_vote', "So'rovnomada ovoz berish"), ('cert_view', "Sertifikat olish")]),
 ('👁 Ko\'rish', [('view_rating', "Reytingni ko'rish"), ('view_shop', "Magazinni ko'rish"), ('view_teachers', "Ustozlar reytingini ko'rish"), ('view_news', "Yangiliklarni ko'rish"), ('library_view', "Kutubxonani ko'rish")]),
 ('💬 Muloqot', [('msg_use', "Shaxsiy xabarlar"), ('chat_use', "Kurs chatini o'qish"), ('chat_post', "Kurs chatiga yozish"), ('chat_moderate', "Chat xabarlarini o'chirish"), ('comment_post', "Dars ostida izoh yozish"), ('profile_edit', "Profilni tahrirlash")]),
]
PERM_KEYS = [k for _, items in PERMS for k, _ in items]
VIEWS = "view_rating view_shop view_teachers view_news library_view poll_vote msg_use chat_use profile_edit"
DEFP = {
 'admin': _s("users_view users_create users_edit users_role users_import courses_manage groups_manage schedule_manage post_create plan_manage quiz_create attendance journal enroll_approve library_upload library_manage poll_create challenge_manage grade cert_issue reportcard_staff trate_manage payments_manage shop_manage news_post reports_view logs_view settings_manage pause_app chat_post chat_moderate comment_post " + VIEWS),
 'teacher': _s("enroll_approve post_create plan_manage quiz_create attendance journal library_upload poll_create challenge_manage grade cert_issue reportcard_staff chat_post comment_post " + VIEWS),
 'student': _s("submit_hw quiz_take shop_buy rate_teacher join_request challenge_claim cert_view chat_post comment_post " + VIEWS),
 'parent': _s("cert_view " + VIEWS),
}
EPERM = {('users', 'GET'): 'users_view', ('users', 'POST'): 'users_create', ('users_import', '*'): 'users_import', ('courses', 'POST'): 'courses_manage', ('course', 'POST'): 'courses_manage',
 ('course_edit', '*'): 'courses_manage', ('new_post', '*'): 'post_create', ('post_edit', '*'): 'post_create', ('grade', '*'): 'grade', ('submit', '*'): 'submit_hw', ('schedule', 'POST'): 'schedule_manage',
 ('rating', '*'): 'view_rating', ('groups_rating', '*'): 'view_rating', ('teachers', '*'): 'view_teachers', ('rate_teacher', '*'): 'rate_teacher', ('trate_del', '*'): 'trate_manage', ('settings', '*'): 'settings_manage',
 ('run_jobs', '*'): 'settings_manage', ('shop', 'GET'): 'view_shop', ('shop', 'POST'): 'shop_manage', ('buy', '*'): 'shop_buy', ('give', '*'): 'shop_manage', ('item_edit', '*'): 'shop_manage', ('item_del', '*'): 'shop_manage',
 ('news', 'GET'): 'view_news', ('news', 'POST'): 'news_post', ('news_del', '*'): 'news_post', ('profile', 'POST'): 'profile_edit', ('attendance', '*'): 'attendance', ('qr_page', '*'): 'attendance',
 ('quiz_start', '*'): 'quiz_take', ('quiz_submit', '*'): 'quiz_take', ('quiz_reset', '*'): 'quiz_create', ('quiz_del', '*'): 'quiz_create', ('post_comment', '*'): 'comment_post',
 ('messages', '*'): 'msg_use', ('thread', '*'): 'msg_use', ('course_chat', 'GET'): 'chat_use', ('course_chat', 'POST'): 'chat_post', ('cmsg_del', '*'): 'chat_moderate',
 ('reports', '*'): 'reports_view', ('reports_csv', '*'): 'reports_view', ('journal', '*'): 'journal', ('logs', '*'): 'logs_view', ('backup', '*'): 'backup',
 ('payments', '*'): 'payments_manage', ('payments_csv', '*'): 'payments_manage', ('groups', '*'): 'groups_manage', ('group', '*'): 'groups_manage',
 ('library', 'GET'): 'library_view', ('library', 'POST'): 'library_upload', ('topics_add', '*'): 'plan_manage', ('topic_toggle', '*'): 'plan_manage', ('topic_del', '*'): 'plan_manage',
 ('join_course', '*'): 'join_request', ('requests', '*'): 'enroll_approve', ('request_act', '*'): 'enroll_approve', ('polls', 'POST'): 'poll_create', ('poll_vote', '*'): 'poll_vote',
 ('challenges', 'POST'): 'challenge_manage', ('challenge_claim', '*'): 'challenge_claim', ('challenge_review', '*'): 'challenge_manage', ('storage', '*'): 'storage_manage', ('backup_dl', '*'): 'backup'}

def _pc():
    if 'pc' not in g: g.pc = {(r['scope'], r['ref'], r['k']): r['val'] for r in q("SELECT * FROM perms")}
    return g.pc

def role_allows(role, key):
    if role == 'boss': return True
    v = _pc().get(('role', role, key))
    return bool(v) if v is not None else key in DEFP.get(role, set())

def allow(key, u=None):
    u = u or me()
    if not u: return False
    if u['role'] == 'boss': return True
    v = _pc().get(('user', str(u['id']), key))
    return bool(v) if v is not None else role_allows(u['role'], key)

def set_perm(scope, ref, k, val, default=None):
    if default is not None and bool(val) == bool(default): q("DELETE FROM perms WHERE scope=? AND ref=? AND k=?", (scope, ref, k), w=True)
    else: q("INSERT OR REPLACE INTO perms(scope,ref,k,val) VALUES(?,?,?,?)", (scope, ref, k, 1 if val else 0), w=True)

@app.errorhandler(403)
def e403(e): return render_template('403.html'), 403

@app.route('/permissions', methods=['GET', 'POST'])
@need('boss')
def permissions():
    roles = ['admin', 'teacher', 'student', 'parent']
    if request.method == 'POST':
        if request.form.get('reset'):
            q("DELETE FROM perms WHERE scope='role'", w=True); log("Rol huquqlari standartga qaytarildi"); flash("Standart holatga qaytarildi ✅"); return redirect(url_for('permissions'))
        for r in roles:
            for k in PERM_KEYS: set_perm('role', r, k, bool(request.form.get('r_%s_%s' % (r, k))), k in DEFP[r])
        log("Rol huquqlari o'zgartirildi")
        for a in q("SELECT id FROM users WHERE role!='boss'"): pass
        flash("Huquqlar saqlandi ✅"); g.pop('pc', None); return redirect(url_for('permissions'))
    return render_template('perms.html', roles=roles, groups=PERMS, cur={r + '|' + k: role_allows(r, k) for r in roles for k in PERM_KEYS})

@app.route('/permissions/user/<int:i>', methods=['GET', 'POST'])
@need('boss')
def user_perms(i):
    u = q("SELECT * FROM users WHERE id=?", (i,), one=True) or abort(404)
    if u['role'] == 'boss': abort(400)
    if request.method == 'POST':
        for k in PERM_KEYS:
            v = request.form.get('u_' + k, '')
            if v in ('0', '1'): set_perm('user', str(i), k, v == '1')
            else: q("DELETE FROM perms WHERE scope='user' AND ref=? AND k=?", (str(i), k), w=True)
        log("Foydalanuvchi huquqlari o'zgartirildi: #%s" % i); notify(i, "🔐 Sizning huquqlaringiz o'zgartirildi", url_for('my_perms')); flash("Saqlandi ✅"); g.pop('pc', None)
        return redirect(url_for('user_perms', i=i))
    cur = {k: ('' if ('user', str(i), k) not in _pc() else str(_pc()[('user', str(i), k)])) for k in PERM_KEYS}
    return render_template('user_perms.html', u=u, groups=PERMS, base={k: role_allows(u['role'], k) for k in PERM_KEYS}, cur=cur)

@app.route('/my-permissions')
@need()
def my_perms():
    return render_template('my_perms.html', groups=PERMS, eff={k: allow(k) for k in PERM_KEYS})

# ---------- sessiyalar, parol almashtirish, havfsizlik ----------
def _ip(): return (request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr or '')[:60]

def start_session(uid):
    sid = secrets.token_hex(16)
    q("INSERT INTO sessions(id,user_id,ua,ip,at) VALUES(?,?,?,?,?)", (sid, uid, (request.headers.get('User-Agent') or '')[:200], _ip(), ns()), w=True)
    session['uid'] = uid; session['sid'] = sid; return sid

@app.route('/sessions', methods=['GET', 'POST'])
@need()
def sessions():
    m = me()['id']
    if request.method == 'POST':
        a = request.form.get('a')
        if a == 'all': q("DELETE FROM sessions WHERE user_id=? AND id!=?", (m, session.get('sid', '')), w=True); flash("Boshqa barcha qurilmalardan chiqildi ✅")
        elif a == 'kill': q("DELETE FROM sessions WHERE id=? AND user_id=?", (request.form.get('sid', ''), m), w=True); flash("Qurilmadan chiqildi")
        return redirect(url_for('sessions'))
    return render_template('sessions.html', rows=q("SELECT * FROM sessions WHERE user_id=? ORDER BY at DESC", (m,)), cur=session.get('sid'))

@app.route('/change-password', methods=['GET', 'POST'])
@need()
def change_password():
    if request.method == 'POST':
        a, b = request.form.get('p1', ''), request.form.get('p2', '')
        if len(a) < 6: flash("Parol kamida 6 belgi bo'lsin")
        elif a != b: flash("Parollar mos kelmadi")
        elif cph(me()['pw'], a): flash("Yangi parol eskisidan farq qilsin")
        else:
            q("UPDATE users SET pw=?, must_change=0 WHERE id=?", (gph(a), me()['id']), w=True); flash("Parol yangilandi ✅"); return redirect(url_for('dash'))
    return render_template('chpw.html')

# ---------- kunlik ishlar: eslatma, zaxira ----------
def _once(uid, text, link=''):
    if not q("SELECT 1 FROM notifs WHERE user_id=? AND text=? AND at>=?", (uid, text, now().strftime('%Y-%m-%d')), one=True): notify(uid, text, link)

def ensure_fees(m):
    for u in q("SELECT id, fee FROM users WHERE role='student' AND fee>0"):
        q("INSERT OR IGNORE INTO fees(student_id,month,amount,paid) VALUES(?,?,?,0)", (u['id'], m, u['fee']), w=True)

def debt(uid): return q("SELECT COALESCE(SUM(amount),0) s FROM fees WHERE student_id=? AND paid=0 AND month<=?", (uid, now().strftime('%Y-%m')), one=True)['s']
def parents_of(uid): return [r['id'] for r in q("SELECT id FROM users WHERE role='parent' AND child_id=?", (uid,))]

def reminders():
    t = now(); cur = t.strftime('%Y-%m-%d %H:%M'); soon = (t + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M'); month = t.strftime('%Y-%m')
    for p in q("SELECT * FROM posts WHERE kind='hw' AND deadline!='' AND deadline>? AND deadline<=?", (cur, soon)):
        for s_ in q("SELECT student_id FROM cs WHERE course_id=? AND student_id NOT IN (SELECT student_id FROM subs WHERE post_id=? AND status IN ('sent','graded'))", (p['course_id'], p['id'])):
            _once(s_['student_id'], "⏰ 24 soat ichida muddat tugaydi: '%s' (%s)" % (p['title'], p['deadline']), '/post/%d' % p['id'])
    cm = {c['id']: c['name'] for c in q("SELECT * FROM courses")}
    for d, tm, cn, sid in lessons(1, None, cm):
        sc = q("SELECT * FROM sched WHERE id=?", (sid,), one=True)
        for s_ in q("SELECT student_id FROM cs WHERE course_id=?", (sc['course_id'],)):
            _once(s_['student_id'], "📅 Bugun %s da '%s' darsi%s" % (tm, cn, (" — havola: " + sc['link']) if sc['link'] else ''), '/schedule')
    ensure_fees(month)
    for u in q("SELECT id FROM users WHERE role='student' AND fee>0"):
        late = q("SELECT COUNT(*) n FROM fees WHERE student_id=? AND paid=0 AND (month<? OR (month=? AND ?>=5))", (u['id'], month, month, t.day), one=True)['n']
        if late:
            d_ = debt(u['id'])
            for rid in [u['id']] + parents_of(u['id']): _once(rid, "💳 To'lov eslatmasi: qarzdorlik %d so'm" % d_, '/my-fees')

def auto_backup():
    d = os.path.join(B, 'backups'); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, 'db-%s.sqlite3' % now().strftime('%Y%m%d'))
    if not os.path.exists(p):
        a = sqlite3.connect(DB); b = sqlite3.connect(p); a.backup(b); b.close(); a.close()
    fs = sorted(f for f in os.listdir(d) if f.startswith('db-'))
    for f in fs[:-7]: os.remove(os.path.join(d, f))

def daily_jobs(force=False):
    d = now().date().isoformat(); r = q("SELECT v FROM settings WHERE k='last_job'", one=True)
    if not force and r and r['v'] == d: return
    q("INSERT OR REPLACE INTO settings(k,v) VALUES('last_job',?)", (d,), w=True)
    for fn in (reminders, auto_backup):
        try: fn()
        except Exception: pass

@app.route('/run-jobs', methods=['POST'])
@need()
def run_jobs():
    daily_jobs(True); log("Avtomatik ishlar qo'lda ishga tushirildi"); flash("Eslatmalar yuborildi va zaxira nusxa olindi ✅"); return redirect(url_for('settings'))

def _lk(v):
    v = (v or '').strip(); return v if v.startswith(('http://', 'https://')) else ''

def is_live(d, t):
    try: st_ = datetime.combine(d, datetime.strptime(t, '%H:%M').time())
    except Exception: return False
    return st_ - timedelta(minutes=15) <= now() <= st_ + timedelta(hours=3)

# ---------- to'lovlar ----------
@app.route('/payments', methods=['GET', 'POST'])
@need()
def payments():
    m = request.values.get('m') or now().strftime('%Y-%m'); cur = now().strftime('%Y-%m')
    if request.method == 'POST':
        f = request.form; a = f.get('a'); sid = f.get('sid', type=int)
        if a == 'fee' and sid:
            try: amt = max(0, int(f.get('fee') or 0))
            except ValueError: amt = 0
            q("UPDATE users SET fee=? WHERE id=? AND role='student'", (amt, sid), w=True)
            if amt: q("UPDATE fees SET amount=? WHERE student_id=? AND paid=0 AND month>=?", (amt, sid, cur), w=True); ensure_fees(cur)
            else: q("DELETE FROM fees WHERE student_id=? AND paid=0 AND month>=?", (sid, cur), w=True)
            log("To'lov summasi o'zgardi: o'quvchi #%s = %s" % (sid, amt))
        elif a == 'paid' and sid:
            q("UPDATE fees SET paid=1, paid_at=?, note=? WHERE student_id=? AND month=?", (ns(), f.get('note', '')[:100], sid, m), w=True); notify(sid, "✅ %s oyi uchun to'lov qabul qilindi" % m, '/my-fees'); log("To'lov qabul qilindi: #%s %s" % (sid, m))
        elif a == 'unpaid' and sid: q("UPDATE fees SET paid=0, paid_at=NULL WHERE student_id=? AND month=?", (sid, m), w=True); log("To'lov bekor qilindi: #%s %s" % (sid, m))
        elif a == 'remind' and sid:
            for rid in [sid] + parents_of(sid): notify(rid, "💳 To'lov eslatmasi: %s oyi uchun to'lov kutilmoqda" % m, '/my-fees')
            flash("Eslatma yuborildi ✅")
        elif a == 'remind_all':
            n = 0
            for r in q("SELECT student_id FROM fees WHERE month=? AND paid=0", (m,)):
                for rid in [r['student_id']] + parents_of(r['student_id']): notify(rid, "💳 To'lov eslatmasi: %s oyi uchun to'lov kutilmoqda" % m, '/my-fees')
                n += 1
            flash("%d ta qarzdorga eslatma yuborildi ✅" % n)
        return redirect(url_for('payments', m=m))
    ensure_fees(m)
    rows = q("SELECT f.*, u.username, u.first, u.last, u.avatar FROM fees f JOIN users u ON u.id=f.student_id WHERE f.month=? ORDER BY f.paid, u.first, u.username", (m,))
    tot = sum(r['amount'] for r in rows); paid = sum(r['amount'] for r in rows if r['paid'])
    y, mo = map(int, m.split('-')); first = date(y, mo, 1)
    return render_template('payments.html', m=m, y=y, mo=mo, rows=rows, tot=tot, paid=paid, students=q("SELECT * FROM users WHERE role='student' ORDER BY first, username"),
                           prev=(first - timedelta(days=1)).strftime('%Y-%m'), nxt=(first + timedelta(days=32)).strftime('%Y-%m'))

@app.route('/payments/csv')
@need()
def payments_csv():
    m = request.args.get('m') or now().strftime('%Y-%m'); ensure_fees(m)
    return csv_resp('tolovlar-' + m, ["O'quvchi", 'Oy', "Summa", "Holat", "To'langan vaqt"], [[_who(r), r['month'], r['amount'], "To'langan" if r['paid'] else 'Qarz', r['paid_at'] or ''] for r in
                    q("SELECT f.*, u.username, u.first, u.last FROM fees f JOIN users u ON u.id=f.student_id WHERE f.month=?", (m,))])

@app.route('/my-fees')
@need('student', 'parent')
def my_fees():
    u = me(); sid = u['id'] if u['role'] == 'student' else (u['child_id'] or 0)
    return render_template('my_fees.html', rows=q("SELECT * FROM fees WHERE student_id=? ORDER BY month DESC", (sid,)), debt=debt(sid), s=q("SELECT * FROM users WHERE id=?", (sid,), one=True))

# ---------- guruhlar ----------
def sync_course(cid):
    c = q("SELECT group_id FROM courses WHERE id=?", (cid,), one=True)
    if c and c['group_id']:
        for r in q("SELECT student_id FROM gs WHERE group_id=?", (c['group_id'],)): q("INSERT OR IGNORE INTO cs VALUES(?,?)", (cid, r['student_id']), w=True)

def sync_group(gid):
    for c in q("SELECT id FROM courses WHERE group_id=?", (gid,)): sync_course(c['id'])

def news_rows(limit=None):
    u = me(); gids = None
    if u['role'] not in ('boss', 'admin', 'teacher'):
        sid = u['child_id'] if u['role'] == 'parent' else u['id']; gids = [r['group_id'] for r in q("SELECT group_id FROM gs WHERE student_id=?", (sid or 0,))]
    sql = "SELECT n.*, g.name gname FROM news n LEFT JOIN grps g ON g.id=n.group_id"
    if gids is not None: sql += " WHERE n.group_id IS NULL" + (" OR n.group_id IN (%s)" % ','.join('?' * len(gids)) if gids else "")
    sql += " ORDER BY n.id DESC" + (" LIMIT %d" % limit if limit else "")
    return q(sql, gids or [])

@app.route('/groups', methods=['GET', 'POST'])
@need()
def groups():
    if request.method == 'POST' and request.form.get('name', '').strip():
        q("INSERT INTO grps(name,color) VALUES(?,?)", (request.form['name'].strip(), cl(request.form.get('color'))), w=True); flash("Guruh qo'shildi ✅"); log("Guruh yaratildi")
    return render_template('groups.html', rows=q("SELECT g.*, (SELECT COUNT(*) FROM gs WHERE group_id=g.id) n, (SELECT COUNT(*) FROM courses WHERE group_id=g.id) c FROM grps g ORDER BY name"))

@app.route('/groups/<int:i>', methods=['GET', 'POST'])
@need()
def group(i):
    g_ = q("SELECT * FROM grps WHERE id=?", (i,), one=True) or abort(404)
    if request.method == 'POST':
        if request.form.get('del'):
            for t in ('gs',): q("DELETE FROM %s WHERE group_id=?" % t, (i,), w=True)
            q("UPDATE courses SET group_id=NULL WHERE group_id=?", (i,), w=True); q("UPDATE news SET group_id=NULL WHERE group_id=?", (i,), w=True); q("DELETE FROM grps WHERE id=?", (i,), w=True)
            log("Guruh o'chirildi #%s" % i); flash("Guruh o'chirildi"); return redirect(url_for('groups'))
        q("UPDATE grps SET name=?, color=? WHERE id=?", (request.form['name'].strip() or g_['name'], cl(request.form.get('color')), i), w=True)
        q("DELETE FROM gs WHERE group_id=?", (i,), w=True)
        for sid in request.form.getlist('st'): q("INSERT OR IGNORE INTO gs VALUES(?,?)", (i, sid), w=True)
        sync_group(i); flash("Saqlandi ✅ (guruh kurslariga o'quvchilar avtomatik yozildi)"); return redirect(url_for('group', i=i))
    return render_template('group.html', g=g_, students=q("SELECT * FROM users WHERE role='student' ORDER BY first, username"), mine=[r['student_id'] for r in q("SELECT student_id FROM gs WHERE group_id=?", (i,))],
                           courses=q("SELECT * FROM courses WHERE group_id=?", (i,)))

@app.route('/groups/rating')
@need()
def groups_rating():
    per = request.args.get('period') or None; pts = {x['id']: x['pts'] for x in board(None, per)}; rows = []
    for g_ in q("SELECT * FROM grps"):
        mem = [r['student_id'] for r in q("SELECT student_id FROM gs WHERE group_id=?", (g_['id'],))]; tot = sum(pts.get(m, 0) for m in mem)
        rows.append(dict(g=g_, n=len(mem), tot=tot, avg=round(tot / len(mem), 1) if mem else 0))
    rows.sort(key=lambda r: -r['avg'])
    return render_template('groups_rating.html', rows=rows, period=per, mx=max([r['avg'] for r in rows] + [1]))

# ---------- CSV orqali ommaviy qo'shish ----------
def _slug(a, b):
    t = unicodedata.normalize('NFKD', (a + '.' + b).strip('.').lower()).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9.]+', '', t).strip('.') or 'user'

@app.route('/users/import', methods=['GET', 'POST'])
@need()
def users_import():
    created = []
    if request.method == 'POST':
        txt = request.form.get('data', ''); f = request.files.get('file')
        if f and f.filename: txt = f.read().decode('utf-8-sig', errors='ignore')
        role = request.form.get('role', 'student')
        if role not in ('student', 'teacher', 'parent'): role = 'student'
        dg = request.form.get('group') or None
        for line in txt.splitlines():
            p = [x.strip() for x in re.split(r'[;,\t]', line)]
            if not p or not p[0] or p[0].lower() in ('ism', 'first', 'name', 'имя'): continue
            first, last = p[0], (p[1] if len(p) > 1 else ''); login = p[2] if len(p) > 2 and p[2] else _slug(first, last)
            base = login
            while q("SELECT 1 FROM users WHERE username=?", (login,), one=True): login = base + str(secrets.randbelow(900) + 100)
            pw = ''.join(secrets.choice('abcdefghjkmnpqrstuvwxyz23456789') for _ in range(8))
            uid = q("INSERT INTO users(username,pw,role,first,last,must_change) VALUES(?,?,?,?,?,1)", (login, gph(pw), role, first, last), w=True)
            gname = p[3] if len(p) > 3 and p[3] else None; gid = dg
            if gname:
                r = q("SELECT id FROM grps WHERE lower(name)=?", (gname.lower(),), one=True); gid = r['id'] if r else q("INSERT INTO grps(name) VALUES(?)", (gname,), w=True)
            if gid and role == 'student': q("INSERT OR IGNORE INTO gs VALUES(?,?)", (gid, uid), w=True); sync_group(int(gid))
            created.append((first, last, login, pw))
        log("CSV orqali %d ta foydalanuvchi qo'shildi" % len(created)); flash("%d ta foydalanuvchi qo'shildi ✅" % len(created))
    return render_template('import.html', created=created, grps=q("SELECT * FROM grps"))

# ---------- baholar varaqasi ----------
@app.route('/report-card/<int:sid>')
@need()
def report_card(sid):
    u = me(); s_ = q("SELECT * FROM users WHERE id=? AND role='student'", (sid,), one=True) or abort(404)
    if u['role'] == 'student' and u['id'] != sid: abort(403)
    elif u['role'] == 'parent' and (u['child_id'] or 0) != sid: abort(403)
    elif u['role'] in ('teacher', 'admin'):
        if not allow('reportcard_staff'): abort(403)
        if u['role'] == 'teacher' and not q("SELECT 1 FROM cs JOIN courses c ON c.id=cs.course_id WHERE cs.student_id=? AND c.teacher_id=?", (sid, u['id']), one=True): abort(403)
    rows = []
    for c in q("SELECT c.* FROM courses c JOIN cs ON cs.course_id=c.id WHERE cs.student_id=?", (sid,)):
        hw = q("SELECT COUNT(*) n FROM posts WHERE course_id=? AND kind='hw'", (c['id'],), one=True)['n']
        gr = q("SELECT s.score, p.maxscore FROM subs s JOIN posts p ON p.id=s.post_id WHERE p.course_id=? AND s.student_id=? AND s.status='graded'", (c['id'], sid))
        avg = round(sum((x['score'] or 0) * 100 / (x['maxscore'] or 100) for x in gr) / len(gr)) if gr else None
        qz = q("SELECT a.score, z.maxscore FROM qatt a JOIN quizzes z ON z.id=a.quiz_id WHERE z.course_id=? AND a.student_id=? AND a.score IS NOT NULL", (c['id'], sid))
        qa = round(sum(x['score'] * 100 / x['maxscore'] for x in qz) / len(qz)) if qz else None
        rows.append(dict(c=c, hw=hw, done=len(gr), pts=sum(x['score'] or 0 for x in gr), avg=avg, qavg=qa, att=att_pct(sid, c['id'])[0], cert=cert_ok(c['id'], sid)[0]))
    b = board()
    return render_template('rcard.html', s=s_, rows=rows, total=earned(sid), rank=next((k + 1 for k, x in enumerate(b) if x['id'] == sid), '-'), n=len(b), att=att_pct(sid)[0], day=now().strftime('%d.%m.%Y'), bl=badges(sid))

# ---------- kutubxona ----------
@app.route('/library', methods=['GET', 'POST'])
@need()
def library():
    ids = [c['id'] for c in my_courses()]
    if request.method == 'POST':
        f = request.form; cid = int(f['course']) if f.get('course') else None
        if cid and cid not in ids: abort(403)
        if not cid and not allow('library_manage'): flash("Umumiy kutubxonaga faqat vakolatli xodim qo'sha oladi"); return redirect(url_for('library'))
        fl = save(request.files.get('file')); lk = _lk(f.get('link'))
        if not (fl or lk): flash("Fayl yoki havola kiriting")
        else:
            q("INSERT INTO library(course_id,title,info,file,link,user_id,at) VALUES(?,?,?,?,?,?,?)", (cid, f['title'], f.get('info', ''), fl, lk, me()['id'], ns()), w=True)
            if cid:
                for s_ in q("SELECT student_id FROM cs WHERE course_id=?", (cid,)): notify(s_['student_id'], "📚 Kutubxonaga yangi material: " + f['title'], '/library')
            flash("Qo'shildi ✅")
        return redirect(url_for('library'))
    kq = request.args.get('q', '').strip(); cid = request.args.get('course', type=int)
    cond = "(l.course_id IS NULL" + (" OR l.course_id IN (%s)" % ','.join('?' * len(ids)) if ids else "") + ")"; a = list(ids)
    if kq: cond += " AND (l.title LIKE ? OR l.info LIKE ?)"; a += ['%' + kq + '%'] * 2
    if cid: cond += " AND l.course_id=?"; a.append(cid)
    rows = q("SELECT l.*, c.name cname, c.color, u.username, u.first, u.last FROM library l LEFT JOIN courses c ON c.id=l.course_id LEFT JOIN users u ON u.id=l.user_id WHERE " + cond + " ORDER BY l.id DESC", a)
    return render_template('library.html', rows=rows, courses=my_courses(), kq=kq, cid=cid)

@app.route('/library/del/<int:i>', methods=['POST'])
@need()
def library_del(i):
    r = q("SELECT * FROM library WHERE id=?", (i,), one=True) or abort(404)
    if not (r['user_id'] == me()['id'] or allow('library_manage')): abort(403)
    q("DELETE FROM library WHERE id=?", (i,), w=True); return redirect(url_for('library'))

# ---------- dars rejasi ----------
@app.route('/course/<int:i>/topics', methods=['POST'])
@need()
def topics_add(i):
    c = q("SELECT * FROM courses WHERE id=?", (i,), one=True) or abort(404)
    if not can_course(c): abort(403)
    n = q("SELECT COALESCE(MAX(ord),0) m FROM topics WHERE course_id=?", (i,), one=True)['m']
    for l in request.form.get('lines', '').splitlines():
        if l.strip(): n += 1; q("INSERT INTO topics(course_id,title,ord) VALUES(?,?,?)", (i, l.strip()[:200], n), w=True)
    return redirect(url_for('course', i=i))

def _topic(i):
    t = q("SELECT * FROM topics WHERE id=?", (i,), one=True) or abort(404)
    if not can_course(q("SELECT * FROM courses WHERE id=?", (t['course_id'],), one=True)): abort(403)
    return t

@app.route('/topic/<int:i>/toggle', methods=['POST'])
@need()
def topic_toggle(i):
    t = _topic(i); q("UPDATE topics SET done=? WHERE id=?", (0 if t['done'] else 1, i), w=True); return redirect(url_for('course', i=t['course_id']))

@app.route('/topic/<int:i>/del', methods=['POST'])
@need()
def topic_del(i):
    t = _topic(i); q("DELETE FROM topics WHERE id=?", (i,), w=True); return redirect(url_for('course', i=t['course_id']))

# ---------- kursga yozilish so'rovi ----------
@app.route('/course/<int:i>/join', methods=['POST'])
@need('student')
def join_course(i):
    c = q("SELECT * FROM courses WHERE id=?", (i,), one=True) or abort(404)
    if c['group_id'] or _member(i): abort(403)
    q("INSERT OR IGNORE INTO joinreq(course_id,student_id,at,status) VALUES(?,?,?,'pending')", (i, me()['id'], ns()), w=True)
    rec = {r['id'] for r in q("SELECT id FROM users WHERE role IN ('boss','admin')")}
    if c['teacher_id']: rec.add(c['teacher_id'])
    for uid in rec: notify(uid, "📥 %s '%s' kursiga yozilmoqchi" % (_who(me()), c['name']), '/requests')
    flash("So'rov yuborildi ✅"); return redirect(url_for('courses'))

@app.route('/requests', endpoint='requests')
@need()
def requests_():
    u = me()
    rows = q("SELECT r.*, c.name cname, c.teacher_id, s.username, s.first, s.last FROM joinreq r JOIN courses c ON c.id=r.course_id JOIN users s ON s.id=r.student_id WHERE r.status='pending' ORDER BY r.id")
    if u['role'] == 'teacher': rows = [r for r in rows if r['teacher_id'] == u['id']]
    return render_template('requests.html', rows=rows)

@app.route('/requests/<int:i>/<act>', methods=['POST'])
@need()
def request_act(i, act):
    r = q("SELECT * FROM joinreq WHERE id=?", (i,), one=True) or abort(404); c = q("SELECT * FROM courses WHERE id=?", (r['course_id'],), one=True)
    if me()['role'] == 'teacher' and c['teacher_id'] != me()['id']: abort(403)
    if act == 'ok':
        q("INSERT OR IGNORE INTO cs VALUES(?,?)", (c['id'], r['student_id']), w=True); q("UPDATE joinreq SET status='ok' WHERE id=?", (i,), w=True); notify(r['student_id'], "✅ '%s' kursiga yozilishingiz tasdiqlandi" % c['name'], '/course/%d' % c['id'])
    else: q("UPDATE joinreq SET status='no' WHERE id=?", (i,), w=True); notify(r['student_id'], "❌ '%s' kursiga yozilish so'rovi rad etildi" % c['name'])
    return redirect(url_for('requests'))

# ---------- so'rovnomalar ----------
@app.route('/polls', methods=['GET', 'POST'])
@need()
def polls():
    ids = [c['id'] for c in my_courses()]
    if request.method == 'POST':
        f = request.form; opts = [o.strip() for o in f.get('opts', '').splitlines() if o.strip()][:8]; cid = int(f['course']) if f.get('course') else None
        if len(opts) < 2: flash("Kamida 2 ta variant kiriting")
        elif cid and cid not in ids: abort(403)
        else:
            pid = q("INSERT INTO polls(question,course_id,created,user_id) VALUES(?,?,?,?)", (f['question'], cid, ns(), me()['id']), w=True)
            for o in opts: q("INSERT INTO poll_opts(poll_id,text) VALUES(?,?)", (pid, o), w=True)
            rc = q("SELECT student_id id FROM cs WHERE course_id=?", (cid,)) if cid else q("SELECT id FROM users WHERE role='student'")
            for r in rc: notify(r['id'], "🗳 Yangi so'rovnoma: " + f['question'], '/polls')
            flash("So'rovnoma joylandi ✅")
    cond = "course_id IS NULL" + (" OR course_id IN (%s)" % ','.join('?' * len(ids)) if ids else "")
    rows = []
    for p in q("SELECT * FROM polls WHERE " + cond + " ORDER BY id DESC", ids):
        opts = q("SELECT o.*, (SELECT COUNT(*) FROM votes WHERE opt_id=o.id) n FROM poll_opts o WHERE poll_id=?", (p['id'],))
        mine = q("SELECT opt_id FROM votes WHERE poll_id=? AND user_id=?", (p['id'], me()['id']), one=True)
        rows.append(dict(p=p, opts=opts, total=sum(o['n'] for o in opts), mine=mine['opt_id'] if mine else None))
    return render_template('polls.html', rows=rows, courses=my_courses())

@app.route('/polls/<int:i>/vote', methods=['POST'])
@need()
def poll_vote(i):
    p = q("SELECT * FROM polls WHERE id=?", (i,), one=True) or abort(404)
    if p['closed'] or (p['course_id'] and not _member(p['course_id'])): abort(403)
    o = request.form.get('opt', type=int)
    if o and q("SELECT 1 FROM poll_opts WHERE id=? AND poll_id=?", (o, i), one=True): q("INSERT OR IGNORE INTO votes VALUES(?,?,?)", (i, me()['id'], o), w=True); flash("Ovozingiz qabul qilindi ✅")
    return redirect(url_for('polls'))

@app.route('/polls/<int:i>/<act>', methods=['POST'])
@need()
def poll_act(i, act):
    p = q("SELECT * FROM polls WHERE id=?", (i,), one=True) or abort(404)
    if not (p['user_id'] == me()['id'] or is_adm()): abort(403)
    if act == 'close': q("UPDATE polls SET closed=1-closed WHERE id=?", (i,), w=True)
    elif act == 'del':
        q("DELETE FROM votes WHERE poll_id=?", (i,), w=True); q("DELETE FROM poll_opts WHERE poll_id=?", (i,), w=True); q("DELETE FROM polls WHERE id=?", (i,), w=True)
    return redirect(url_for('polls'))

# ---------- haftalik vazifalar ----------
@app.route('/challenges', methods=['GET', 'POST'])
@need()
def challenges():
    m = me()
    if request.method == 'POST':
        f = request.form
        try: pts = max(1, min(1000, int(f.get('points') or 10)))
        except ValueError: pts = 10
        q("INSERT INTO challenges(title,info,points,ends,created) VALUES(?,?,?,?,?)", (f['title'], f.get('info', ''), pts, f.get('ends', ''), ns()), w=True)
        for r in q("SELECT id FROM users WHERE role='student'"): notify(r['id'], "🎯 Yangi vazifa: %s (+%d ball)" % (f['title'], pts), '/challenges')
        flash("Vazifa joylandi ✅")
    pend = q("SELECT d.*, c.title, c.points, u.username, u.first, u.last FROM ch_done d JOIN challenges c ON c.id=d.challenge_id JOIN users u ON u.id=d.student_id WHERE d.status='pending' ORDER BY d.at") if allow('challenge_manage') else []
    return render_template('challenges.html', rows=q("SELECT * FROM challenges ORDER BY id DESC"), mine={r['challenge_id']: r for r in q("SELECT * FROM ch_done WHERE student_id=?", (m['id'],))}, pend=pend, today=now().strftime('%Y-%m-%d'))

@app.route('/challenges/<int:i>/claim', methods=['POST'])
@need('student')
def challenge_claim(i):
    c = q("SELECT * FROM challenges WHERE id=?", (i,), one=True) or abort(404)
    q("INSERT OR IGNORE INTO ch_done(challenge_id,student_id,at,status) VALUES(?,?,?,'pending')", (i, me()['id'], ns()), w=True)
    rec = {r['id'] for r in q("SELECT id FROM users WHERE role IN ('boss','admin')")} | {r['teacher_id'] for r in q("SELECT c.teacher_id FROM courses c JOIN cs ON cs.course_id=c.id WHERE cs.student_id=? AND c.teacher_id IS NOT NULL", (me()['id'],))}
    for uid in rec: notify(uid, "🎯 %s vazifani bajardim dedi: %s" % (_who(me()), c['title']), '/challenges')
    flash("Yuborildi — tekshirilishini kuting ✅"); return redirect(url_for('challenges'))

@app.route('/challenges/<int:i>/review/<int:sid>/<act>', methods=['POST'])
@need()
def challenge_review(i, sid, act):
    c = q("SELECT * FROM challenges WHERE id=?", (i,), one=True) or abort(404)
    if act == 'ok':
        q("UPDATE ch_done SET status='done' WHERE challenge_id=? AND student_id=?", (i, sid), w=True)
        q("INSERT OR IGNORE INTO bonus(user_id,reason,points,at,day) VALUES(?,?,?,?,?)", (sid, 'ch%d' % i, c['points'], ns(), now().strftime('%Y-%m-%d')), w=True)
        notify(sid, "🎉 Vazifa tasdiqlandi: %s (+%d ball)" % (c['title'], c['points']), '/challenges')
    else: q("UPDATE ch_done SET status='rejected' WHERE challenge_id=? AND student_id=?", (i, sid), w=True); notify(sid, "❌ Vazifa qabul qilinmadi: " + c['title'], '/challenges')
    return redirect(url_for('challenges'))

# ---------- QR davomat ----------
@app.route('/course/<int:i>/qr')
@need()
def qr_page(i):
    c = q("SELECT * FROM courses WHERE id=?", (i,), one=True) or abort(404)
    if not can_course(c): abort(403)
    tok = secrets.token_urlsafe(8); q("INSERT INTO qrtok(token,course_id,day,exp) VALUES(?,?,?,?)", (tok, i, now().strftime('%Y-%m-%d'), time.time() + 1200), w=True)
    q("DELETE FROM qrtok WHERE exp<?", (time.time(),), w=True)
    return render_template('qr.html', c=c, url=url_for('qr_scan', token=tok, _external=True))

@app.route('/qr/<token>')
@need('student')
def qr_scan(token):
    r = q("SELECT * FROM qrtok WHERE token=?", (token,), one=True)
    if not r or r['exp'] < time.time(): flash("QR kod eskirgan. O'qituvchidan yangisini so'rang."); return redirect(url_for('dash'))
    if not q("SELECT 1 FROM cs WHERE course_id=? AND student_id=?", (r['course_id'], me()['id']), one=True): flash("Siz bu kursga biriktirilmagansiz"); return redirect(url_for('dash'))
    q("INSERT OR REPLACE INTO att(course_id,student_id,day,present) VALUES(?,?,?,1)", (r['course_id'], me()['id'], r['day']), w=True)
    flash("✅ Davomat belgilandi!"); return redirect(url_for('course', i=r['course_id']))

# ---------- xotira ----------
def _refs():
    r = set()
    for t, c in [('users', 'avatar'), ('users', 'bg'), ('posts', 'video'), ('posts', 'audio'), ('posts', 'file'), ('subs', 'file'), ('subs', 'audio'), ('library', 'file')]:
        for x in q("SELECT %s v FROM %s WHERE %s IS NOT NULL AND %s!=''" % (c, t, c, c)): r.add(x['v'])
    return r

def _size(p): return os.path.getsize(p) if os.path.exists(p) else 0

@app.route('/storage', methods=['GET', 'POST'])
@need()
def storage():
    files = [(f, _size(os.path.join(UP, f))) for f in os.listdir(UP) if os.path.isfile(os.path.join(UP, f))]; refs = _refs()
    orphans = [x for x in files if x[0] not in refs]
    if request.method == 'POST' and request.form.get('a') == 'clean':
        for f, sz in orphans: os.remove(os.path.join(UP, f))
        log("Yetim fayllar tozalandi: %d ta" % len(orphans)); flash("%d ta ortiqcha fayl o'chirildi (%.1f MB)" % (len(orphans), sum(x[1] for x in orphans) / 1048576)); return redirect(url_for('storage'))
    bd = os.path.join(B, 'backups'); bks = sorted([(f, _size(os.path.join(bd, f))) for f in os.listdir(bd)], reverse=True) if os.path.isdir(bd) else []
    up = sum(x[1] for x in files); db = _size(DB); bk = sum(x[1] for x in bks)
    big = sorted(files, key=lambda x: -x[1])[:15]
    return render_template('storage.html', n=len(files), up=up, db=db, bk=bk, total=up + db + bk, orphans=orphans, osz=sum(x[1] for x in orphans), big=[(f, sz, f in refs) for f, sz in big], bks=bks, limit=512 * 1048576)

@app.route('/backups/<name>')
@need()
def backup_dl(name):
    if not re.match(r'^db-\d{8}\.sqlite3$', name): abort(404)
    p = os.path.join(B, 'backups', name)
    if not os.path.exists(p): abort(404)
    log("Zaxira yuklab olindi: " + name); return send_file(p, as_attachment=True, download_name=name)

# ---------- shablonlar ----------
BASE = """{% from 'm' import ava %}<!doctype html><html lang=uz><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>{% block t %}O'quv markaz{% endblock %}</title><link rel=stylesheet href="{{ url_for('static', filename='style.css') }}?v=4"><link rel=manifest href="/manifest.json"><meta name=theme-color content="#6c5ce7"><link rel=icon href="/icon.svg"><script>try{var d=document.documentElement,t=localStorage.getItem('th'),a=localStorage.getItem('ac');if(t)d.dataset.theme=t;if(a)d.dataset.accent=a}catch(e){}
function setTh(t){try{if(t)localStorage.setItem('th',t);else localStorage.removeItem('th')}catch(e){}if(t)document.documentElement.dataset.theme=t;else delete document.documentElement.dataset.theme}
function setAc(a){try{if(a)localStorage.setItem('ac',a);else localStorage.removeItem('ac')}catch(e){}if(a)document.documentElement.dataset.accent=a;else delete document.documentElement.dataset.accent}</script></head>
<body class="{{ 'app' if me else 'guest' }}"{% if me and me.bg %} style="background-image:url('/static/uploads/{{ me.bg }}')"{% endif %}>
<div class=toasts>{% for m in get_flashed_messages() %}<div class=toast>{{ m }}</div>{% endfor %}</div>
{% if me %}<input type=checkbox id=mn><aside class=side><a class=logo href="/">📚 O'quv markaz</a><form action="/search" class=sq><input name=q placeholder="🔍 Qidirish" required></form><nav>
<a href="/">🏠 Bosh sahifa</a><a href="/courses">📘 Kurslar</a>{% if me.role=='student' %}<a href="/my">📝 Ishlarim</a>{% endif %}{% if me.role=='parent' %}<a href="/child">👪 Farzandim</a>{% endif %}<a href="/schedule">📅 Jadval</a><a href="/calendar">📆 Kalendar</a>
{% if allow('view_rating') and (S('rating')=='1' or adm) %}<a href="/rating">🏆 Reyting{{ ' 🔒' if S('rating')!='1' }}</a>{% endif %}
{% if allow('view_teachers') and (S('trate')=='1' or adm) %}<a href="/teachers">⭐ Ustozlar{{ ' 🔒' if S('trate')!='1' }}</a>{% endif %}
{% if allow('view_shop') and (S('shop')=='1' or adm) %}<a href="/shop">🛒 Magazin{{ ' 🔒' if S('shop')!='1' }}</a>{% endif %}
{% if allow('view_news') %}<a href="/news">📰 Yangiliklar</a>{% endif %}{% if S('chat')=='1' and allow('msg_use') %}<a href="/messages">✉️ Xabarlar{% if munread %}<b class=badge>{{ munread }}</b>{% endif %}</a>{% endif %}
{% if allow('library_view') %}<a href="/library">📚 Kutubxona</a>{% endif %}<a href="/polls">🗳 So'rovnomalar</a>{% if me.role!='parent' %}<a href="/challenges">🎯 Vazifalar</a>{% endif %}
{% if me.role in ['student','parent'] %}<a href="/my-fees">💳 To'lovlarim</a>{% endif %}{% if allow('payments_manage') %}<a href="/payments">💳 To'lovlar</a>{% endif %}{% if allow('groups_manage') %}<a href="/groups">🧩 Guruhlar</a>{% endif %}{% if allow('enroll_approve') %}<a href="/requests">📥 So'rovlar</a>{% endif %}
{% if allow('users_view') %}<a href="/users">👥 Foydalanuvchilar</a>{% endif %}{% if allow('reports_view') %}<a href="/reports">📈 Hisobotlar</a>{% endif %}{% if allow('logs_view') %}<a href="/logs">🧾 Tarix</a>{% endif %}
{% if me.role=='boss' %}<a href="/permissions">🔐 Huquqlar</a>{% endif %}{% if allow('settings_manage') %}<a href="/settings">⚙️ Sozlamalar</a>{% endif %}{% if allow('storage_manage') %}<a href="/storage">🗄 Xotira</a>{% endif %}{% if allow('backup') %}<a href="/backup">💾 Zaxira</a>{% endif %}
<a href="/notifs">🔔 Bildirishnoma{% if unread %}<b class=badge>{{ unread }}</b>{% endif %}</a></nav>
<a class=usercard href="/profile">{{ ava(me) }}<span><b>{{ (me.first ~ ' ' ~ me.last).strip() or me.username }}</b><small>{{ ROLES[me.role] }}</small></span></a><div class=lang><a href="/lang/uz">UZ</a><a href="/lang/ru">RU</a><a href="/lang/en">EN</a><a href="#" onclick="setTh(document.documentElement.dataset.theme=='dark'?'light':'dark');return false" title="Mavzu">🌓</a></div><a class=out href="/logout">🚪 Chiqish</a></aside>
<div class=wrap><div class=top><label for=mn class=burger>☰</label><b>📚 O'quv markaz</b><a href="/notifs" style="margin-left:auto">🔔{% if unread %}<b class=badge>{{ unread }}</b>{% endif %}</a></div>
<main>{% if paused and adm %}<div class="flash bad">⏸ Ilova to'xtatilgan — faqat adminlar kira oladi. <a href="/settings">Sozlamalar</a></div>{% endif %}
{% for p,over in warn %}<div class="flash {{ 'bad' if over else 'warn' }}">{{ "⚠️ MUDDAT O'TGAN" if over else "⏰ Muddat yaqin" }}: <a href="/post/{{ p.id }}">{{ p.title }}</a> ({{ p.deadline }})</div>{% endfor %}
{% block c %}{% endblock %}</main></div>{% else %}<main class=g>{% block g %}{% endblock %}<div class="lang guestlang"><a href="/lang/uz">UZ</a><a href="/lang/ru">RU</a><a href="/lang/en">EN</a><a href="#" onclick="setTh(document.documentElement.dataset.theme=='dark'?'light':'dark');return false">🌓</a></div></main>{% endif %}
<script>
if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js');
document.querySelectorAll('.side nav a').forEach(function(a){var h=a.getAttribute('href'),p=location.pathname;if(h===p||(h!=='/'&&p.indexOf(h)===0))a.classList.add('on')});
document.querySelectorAll('.toast').forEach(function(t){t.onclick=function(){t.remove()}});
document.querySelectorAll('input[type=file][name=audio]').forEach(function(inp){
 var b=document.createElement('button');b.type='button';b.textContent='🎙 Ovoz yozish';var s=document.createElement('span');s.style.marginLeft='8px';
 var au=document.createElement('audio');au.controls=true;au.style.display='none';inp.parentNode.append(b,s,au);var rec,ch,on=false;
 b.onclick=async function(){
  if(!on){var m;try{m=await navigator.mediaDevices.getUserMedia({audio:true});}catch(e){alert("Mikrofonga ruxsat berilmadi (HTTPS kerak)");return;}
   ch=[];rec=new MediaRecorder(m);rec.ondataavailable=function(e){ch.push(e.data)};
   rec.onstop=function(){m.getTracks().forEach(function(t){t.stop()});var t=rec.mimeType||'audio/webm';var x=t.indexOf('mp4')>-1?'m4a':(t.indexOf('ogg')>-1?'ogg':'weba');
    var f=new File(ch,'voice.'+x,{type:t});var dt=new DataTransfer();dt.items.add(f);inp.files=dt.files;au.src=URL.createObjectURL(f);au.style.display='block';s.textContent='✅ Tayyor';};
   rec.start();on=true;b.textContent="⏹ To'xtatish";b.className='red';s.textContent='🔴 Yozilmoqda...';
  }else{rec.stop();on=false;b.textContent='🎙 Qayta yozish';b.className='';}
 };});
</script></body></html>"""

MEDIA = """{% macro media(f) %}{% if f %}{% set e=f.rsplit('.',1)[-1]|lower %}
{% if e in ['mp4','webm','mov'] %}<video controls src="/static/uploads/{{ f }}"></video>
{% elif e in ['mp3','ogg','wav','m4a','aac','weba','opus'] %}<audio controls src="/static/uploads/{{ f }}"></audio>
{% elif e in ['jpg','jpeg','png','gif','webp'] %}<img class=pic src="/static/uploads/{{ f }}">
{% else %}<a class=btn href="/static/uploads/{{ f }}" target=_blank>📎 {{ f.split('_',1)[-1] }}</a>{% endif %}{% endif %}{% endmacro %}
{% macro name(u) %}{{ (u.first ~ ' ' ~ u.last).strip() or u.username }}{% endmacro %}
{% macro ava(u, big=false) %}{% if u.avatar %}<img class="av{{ ' lg' if big }}" src="/static/uploads/{{ u.avatar }}">{% else %}<span class="av{{ ' lg' if big }}">{{ ((u.first or u.username or '?')[:1])|upper }}</span>{% endif %}{% endmacro %}
{% macro stars(n) %}{% set r=(n or 0)|round|int %}<span class=stars>{{ '★'*r }}{{ '☆'*(5-r) }}</span>{% endmacro %}"""

def P(body): return "{% extends 'base' %}{% from 'm' import media, name, ava, stars %}{% block c %}" + body + "{% endblock %}"
def G(body): return "{% extends 'base' %}{% block g %}" + body + "{% endblock %}"

T = {'base': BASE, 'm': MEDIA,
'pause.html': """<!doctype html><html lang=uz><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Texnik tanaffus</title><link rel=stylesheet href="/static/style.css?v=3"></head>
<body class=guest><main class=g><div class="card center"><div style="font-size:64px">⏸</div><h2>Ilova vaqtincha to'xtatilgan</h2><p class=mut>Texnik ishlar olib borilmoqda. Iltimos, birozdan so'ng qayta urinib ko'ring.</p>
<a class=btn href="/logout">Chiqish</a></div></main></body></html>""",
'auth.html': G("""<div class="card center"><div style="font-size:54px">📚</div><h2>{{ title }}</h2><p class=mut>{{ sub }}</p><form method=post>{{ csrf()|safe }}
<input name=username placeholder="Login" required autofocus><input name=password type=password placeholder="Parol" required><button class=wide>{{ btn }}</button></form>{% if title=="Xush kelibsiz!" %}<p><a href="/forgot">Parolni unutdingizmi?</a></p>{% endif %}</div>"""),
'dash.html': P("""<div class=hero><h2>Salom, {{ me.first or me.username }}! 👋</h2><p>{{ ROLES[me.role] }} · {{ today|length }} ta dars bugun</p></div>
<div class=grid>
{% if me.role=='student' %}<div class="card stat"><span>💰 Balans</span><div class=big>{{ info.bal }}</div><small>Jami yig'ilgan: {{ info.earn }}</small></div>
<div class="card stat"><span>🏆 O'rin</span><div class=big>{{ info.rank }}<small>/{{ info.total }}</small></div></div>
<a class="card stat" href="/my"><span>📝 Bajariladigan</span><div class=big>{{ info.todo }}</div><small>uy ishi</small></a><a class="card stat" href="/attendance"><span>📋 Davomat</span><div class=big>{{ info.att }}%</div></a><div class="card stat"><span>🔥 Seriya</span><div class=big>{{ info.streak }}<small> kun</small></div></div>{% if info.debt %}<a class="card stat" href="/my-fees"><span>💳 Qarzdorlik</span><div class=big style="color:var(--bad)">{{ info.debt }}</div><small>so'm</small></a>{% endif %}{% endif %}
{% if me.role!='student' %}<div class="card stat"><span>📨 Tekshirilmagan</span><div class=big>{{ grade_n }}</div><small>topshirilgan ish</small></div>{% endif %}
{% for r,n in stats %}<div class="card stat"><span>{{ ROLES[r] }}</span><div class=big>{{ n }}</div></div>{% endfor %}</div>
{% if me.role=='student' %}<div class=card><h3>🏅 Yutuqlarim</h3>{% for e,t,d in badges(me.id) %}<span class=tag title="{{ d }}">{{ e }} {{ t }}</span>{% else %}<span class=mut>Hali yutuq yo'q — uy ishlarini bajaring!</span>{% endfor %}</div>{% endif %}
<div class=card><h3>📅 Bugungi darslar</h3>{% for d,t,c,i in today %}<p><span class=tag>{{ t }}</span> {{ c }} {% if links.get(i) %}<a class=btn style="padding:3px 12px;font-size:13px" href="{{ links[i] }}" target=_blank rel=noopener>{{ '🔴 Hozir — kirish' if is_live(d,t) else '🎥 Dars havolasi' }}</a>{% endif %}</p>{% else %}<p class=mut>Bugun dars yo'q</p>{% endfor %}</div>
<div class=card><h3>📰 So'nggi yangiliklar</h3>{% for n in news %}<p><b>{{ n.title }}</b><br>{{ n.body }}<br><small class=mut>{{ n.at }}</small></p>{% else %}<p class=mut>Yo'q</p>{% endfor %}</div>"""),
'my.html': P("""<h2>📝 Ishlarim <a class=btn href="/report-card/{{ me.id }}" target=_blank style="font-size:13px;float:right">🧾 Baholar varaqasi</a></h2>
<h3>Bajarilishi kerak ({{ todo|length }})</h3><div class=grid>{% for p in todo %}<a class="card cc" style="--c:{{ p.color }}" href="/post/{{ p.id }}"><small class=mut>{{ p.cname }}</small><h3>{{ p.title }}</h3>
<span class=tag>🎯 {{ p.maxscore }} ball</span>{% if p.deadline %}<span class="tag {{ 'bad' if p.deadline<now else 'warn' }}">⏰ {{ p.deadline }}</span>{% endif %}</a>{% else %}<div class=card>🎉 Hammasi bajarilgan!</div>{% endfor %}</div>
<h3 style="margin-top:22px">Yuborilgan ishlar ({{ rows|length }})</h3>
{% for s in rows %}<a class="card cc" style="--c:{{ s.color }}" href="/post/{{ s.post_id }}"><div class=row><div style="flex:1"><small class=mut>{{ s.cname }} · {{ s.at }}</small><h3 style="margin:2px 0">{{ s.title }}</h3>
<span class="status {{ STAT[s.status][1] }}">{{ STAT[s.status][0] }}</span>{% if s.late %} <span class="tag bad">Kechikkan</span>{% endif %}</div>
{% if s.status=='graded' %}<div class=score>{{ s.score }}<small>/{{ s.maxscore }}</small></div>{% endif %}</div>{% if s.reason %}<div class="note bad">💬 {{ s.reason }}</div>{% endif %}</a>{% else %}<div class=card>Hali hech narsa yubormagansiz</div>{% endfor %}"""),
'users.html': P("""<h2>👥 Foydalanuvchilar {% if allow('users_import') %}<a class=btn href="/users/import" style="font-size:13px;float:right">📥 CSV orqali qo'shish</a>{% endif %}</h2><div class=card><h3>Yangi qo'shish</h3><form method=post class=row>{{ csrf()|safe }}
<input name=username placeholder=Login required><input name=password placeholder=Parol required><input name=first placeholder=Ism><input name=last placeholder=Familiya>
<select name=role><option value=student>O'quvchi<option value=teacher>O'qituvchi<option value=parent>Ota-ona{% if me.role=='boss' %}<option value=admin>Admin{% endif %}</select><select name=child><option value="">Farzand (ota-ona uchun)</option>{% for s in students %}<option value={{ s.id }}>{{ name(s) }}</option>{% endfor %}</select><button>Qo'shish</button></form></div>
{% for u in rows %}<div class=card><div class=row>{{ ava(u) }}<b>{{ name(u) }}</b> <small class=mut>@{{ u.username }}</small> <span class=tag>{{ ROLES[u.role] }}</span>{% if u.role=='student' and allow('reportcard_staff') %}<a href="/report-card/{{ u.id }}" target=_blank title="Baholar varaqasi">🧾</a>{% endif %}{% if me.role=='boss' and u.role!='boss' %}<a class=btn style="padding:3px 12px;font-size:13px;margin-left:auto" href="/permissions/user/{{ u.id }}">🔐 Huquqlar</a>{% endif %}</div>
{% if u.role!='boss' and (me.role=='boss' or u.role in ['teacher','student','parent']) %}
<form method=post action="/users/{{ u.id }}" class=row>{{ csrf()|safe }}<input type=hidden name=a value=name><input name=first value="{{ u.first }}" placeholder=Ism><input name=last value="{{ u.last }}" placeholder=Familiya><button>Ismni saqlash</button></form>
<form method=post action="/users/{{ u.id }}" class=row>{{ csrf()|safe }}<input type=hidden name=a value=role><select name=role>{% for k,v in ROLES.items() if k!='boss' and (me.role=='boss' or k in ['teacher','student','parent']) %}<option value={{ k }} {{ 'selected' if k==u.role }}>{{ v }}{% endfor %}</select><button>Rolni o'zgartirish</button></form>
<form method=post action="/users/{{ u.id }}" class=row>{{ csrf()|safe }}<input type=hidden name=a value=pw><input name=pw placeholder="Yangi parol"><button>Parolni tiklash</button></form>
{% if u.role=='parent' %}<form method=post action="/users/{{ u.id }}" class=row>{{ csrf()|safe }}<input type=hidden name=a value=child><select name=child><option value="">Farzand yo'q</option>{% for s in students %}<option value={{ s.id }} {{ 'selected' if s.id==u.child_id }}>{{ name(s) }}</option>{% endfor %}</select><button>Farzandni biriktirish</button></form>{% endif %}
{% if allow('users_delete') %}<form method=post action="/users/{{ u.id }}" onsubmit='return confirm("O’chirilsinmi?")'>{{ csrf()|safe }}<input type=hidden name=a value=del><button class=red>O'chirish</button></form>{% endif %}{% endif %}</div>{% endfor %}"""),
'courses.html': P("""<h2>📘 Kurslar</h2>{% if allow('courses_manage') %}<div class=card><form method=post class=row>{{ csrf()|safe }}<input type=color name=color value="#6c5ce7" title="Kurs rangi"><input name=name placeholder="Kurs nomi (Ona tili, Matematika...)" required><input name=info placeholder=Izoh>
<select name=teacher><option value="">O'qituvchi</option>{% for t in teachers %}<option value={{ t.id }}>{{ name(t) }}{% endfor %}</select><button>Kurs qo'shish</button></form></div>{% endif %}
<div class=grid>{% for c in rows %}<a class="card course" style="--c:{{ c.color }}" href="/course/{{ c.id }}"><div class=cbar></div><h3>{{ c.name }}</h3><p class=mut>{{ c.info }}</p>
<span class=tag>👨‍🎓 {{ c.n }}</span><span class=tag>📄 {{ c.pc }}</span>{% if c.tu %}<br><small class=mut>👨‍🏫 {{ (c.tf ~ ' ' ~ c.tl).strip() or c.tu }}</small>{% endif %}</a>{% else %}<div class=card>Kurs yo'q</div>{% endfor %}</div>
{% if others %}<h3 style="margin-top:22px">➕ Boshqa kurslar</h3><div class=grid>{% for c in others %}<div class="card course" style="--c:{{ c.color }}"><div class=cbar></div><h3>{{ c.name }}</h3><p class=mut>{{ c.info }}</p>{% if c.id in pending %}<span class="status warn">⏳ So'rov yuborilgan</span>{% elif allow('join_request') %}<form method=post action="/course/{{ c.id }}/join">{{ csrf()|safe }}<button class=wide>📩 Yozilish so'rovi</button></form>{% endif %}</div>{% endfor %}</div>{% endif %}"""),
'course.html': P("""<div class=hero style="--c:{{ c.color }}"><h2>{{ c.name }}</h2><p>{{ c.info }}</p>{% if tname %}<p>👨‍🏫 {{ name(tname) }}</p>{% endif %}{% for s in sch %}<span class="tag light">{{ PAT[s.pattern] }} · {{ s.time }}</span>{% endfor %}</div>
<div class=row style="margin:10px 0">{% if S('chat')=='1' %}<a class=btn href="/course/{{ c.id }}/chat">💬 Kurs chati</a>{% endif %}<a class=btn href="/course/{{ c.id }}/quizzes">🧪 Testlar</a>{% if can and allow('attendance') %}<a class=btn href="/course/{{ c.id }}/attendance">📋 Davomat</a>{% endif %}{% if can and allow('journal') %}<a class=btn href="/course/{{ c.id }}/journal">📒 Jurnal</a>{% endif %}{% if cert %}<a class=btn href="/certificate/{{ c.id }}" target=_blank>🎓 Sertifikat</a>{% endif %}</div>
<div class=card><h3>🗂 Dars rejasi {% if topics %}<small class=mut>({{ topics|selectattr('done')|list|length }}/{{ topics|length }})</small>{% endif %}</h3>{% if topics %}<div class=bar><i style="width:{{ (topics|selectattr('done')|list|length*100/(topics|length))|round|int }}%"></i></div>{% endif %}
{% for t in topics %}<div class=row style="padding:4px 0"><span>{{ '✅' if t.done else '⬜' }}</span><span style="flex:1;{{ 'text-decoration:line-through;opacity:.6' if t.done }}">{{ t.title }}</span>{% if can and allow('plan_manage') %}<form method=post action="/topic/{{ t.id }}/toggle">{{ csrf()|safe }}<button class=gray style="padding:2px 10px">{{ '↩' if t.done else '✔' }}</button></form><form method=post action="/topic/{{ t.id }}/del">{{ csrf()|safe }}<button class=red style="padding:2px 10px">✖</button></form>{% endif %}</div>{% else %}<p class=mut>Reja hali tuzilmagan</p>{% endfor %}
{% if can and allow('plan_manage') %}<form method=post action="/course/{{ c.id }}/topics"><textarea name=lines placeholder="Mavzular (har qatorda bittadan)"></textarea><button>Mavzu qo'shish</button></form>{% endif %}</div>
{% if allow('courses_manage') %}<div class=card><h3>✏️ Kursni tahrirlash</h3><form method=post action="/course/{{ c.id }}/edit" class=row>{{ csrf()|safe }}<input type=color name=color value="{{ c.color }}"><input name=name value="{{ c.name }}" required><input name=info value="{{ c.info or '' }}"><select name=group><option value="">Guruh yo'q</option>{% for g in grps %}<option value={{ g.id }} {{ 'selected' if g.id==c.group_id }}>{{ g.name }}</option>{% endfor %}</select><button>Saqlash</button>
<button name=del value=1 class=red onclick='return confirm("Kurs va barcha darslari o’chirilsinmi?")'>Kursni o'chirish</button></form></div>
<div class=card><h3>👥 O'qituvchi va o'quvchilar</h3><form method=post>{{ csrf()|safe }}<select name=teacher><option value="">—</option>{% for t in teachers %}<option value={{ t.id }} {{ 'selected' if t.id==c.teacher_id }}>{{ name(t) }}{% endfor %}</select>
<div class=chk>{% for s in students %}<label><input type=checkbox name=st value={{ s.id }} {{ 'checked' if s.id in mine }}> {{ name(s) }}</label>{% endfor %}</div><button>Saqlash</button></form></div>{% endif %}
{% if can and allow('post_create') %}<div class=card><h3>➕ Dars / Uy ishi qo'shish</h3><form method=post action="/course/{{ c.id }}/post" enctype=multipart/form-data>{{ csrf()|safe }}
<select name=kind><option value=lesson>📖 Dars materiali<option value=hw>📝 Uy ishi</select><input name=title placeholder=Sarlavha required><textarea name=text placeholder="Matn / topshiriq"></textarea><input name=link placeholder="Havola (link)">
<label>🎥 Video <input type=file name=video accept="video/*"></label><label>🎤 Ovozli xabar <input type=file name=audio accept="audio/*"></label><label>🖼 Rasm/fayl <input type=file name=file></label>
<div class=row><label>⏰ Muddat <input type=datetime-local name=deadline></label><label>🎯 Maksimal ball <input type=number name=maxscore value=100 min=1 max=1000></label></div><button>Joylash</button></form></div>{% endif %}
{% for p in posts %}<a class="card cc" style="--c:{{ c.color }}" href="/post/{{ p.id }}"><b>{{ '📝' if p.kind=='hw' else '📖' }} {{ p.title }}</b>{% if p.kind=='hw' %} <span class=tag>🎯 {{ p.maxscore }}</span>{% endif %}{% if p.deadline %} <span class=tag>⏰ {{ p.deadline }}</span>{% endif %}<br><small class=mut>{{ p.created }}</small></a>{% endfor %}"""),
'post.html': P("""<div class=hero style="--c:{{ c.color }}"><small>{{ c.name }}</small><h2>{{ p.title }}</h2>{% if p.kind=='hw' %}<span class="tag light">🎯 Maksimal ball: {{ p.maxscore }}</span> <span class="tag light">⏰ {{ p.deadline or "Muddat yo'q" }}</span>{% if late %} <span class="tag bad">muddat o'tgan</span>{% endif %}{% endif %}</div>
<div class=card><p style="white-space:pre-wrap">{{ p.text }}</p>{% if p.link %}<p><a class=btn href="{{ p.link }}" target=_blank rel=noopener>🔗 Havola</a></p>{% endif %}{{ media(p.video) }}{{ media(p.audio) }}{{ media(p.file) }}
{% if can and allow('post_create') and p.kind=='hw' %}<form method=post action="/post/{{ p.id }}/edit" class=row>{{ csrf()|safe }}<label>Muddat <input type=datetime-local name=deadline value="{{ p.deadline.replace(' ','T') }}"></label><label>Maks. ball <input type=number name=maxscore value="{{ p.maxscore }}" min=1 max=1000></label><button>Saqlash</button><button name=del value=1 class=red onclick='return confirm("O’chirilsinmi?")'>O'chirish</button></form>
{% elif can and allow('post_create') %}<form method=post action="/post/{{ p.id }}/edit" class=row>{{ csrf()|safe }}<input type=hidden name=deadline value=""><button name=del value=1 class=red onclick='return confirm("O’chirilsinmi?")'>O'chirish</button></form>{% endif %}</div>
{% if p.kind=='hw' and me.role=='student' %}<div class=card><h3>📬 Mening javobim</h3>
{% if mine %}<div class="status {{ STAT[mine.status][1] }}">{{ STAT[mine.status][0] }}</div> <small class=mut>{{ mine.at }}</small>{% if mine.late %} <span class="tag bad">Kechikkan</span>{% endif %}
{% if mine.reason %}<div class="note bad"><b>O'qituvchi izohi:</b> {{ mine.reason }}</div>{% endif %}
<div class=ans><p style="white-space:pre-wrap">{{ mine.text }}</p>{% if mine.link %}<a href="{{ mine.link }}" target=_blank rel=noopener>{{ mine.link }}</a>{% endif %}{{ media(mine.file) }}{{ media(mine.audio) }}</div>
{% if mine.status=='graded' %}<div class=score>{{ mine.score }}<small>/{{ p.maxscore }}</small></div>{% if mine.fb %}<p>💬 {{ mine.fb }}</p>{% endif %}{% endif %}{% endif %}
{% if not mine or mine.status!='graded' %}<form method=post action="/post/{{ p.id }}/submit" enctype=multipart/form-data>{{ csrf()|safe }}<h4>{{ '🔁 Qayta topshirish' if mine else '📤 Topshirish' }}</h4>
<textarea name=text placeholder="Javobingizni yozing">{{ mine.text if mine }}</textarea><input name=link placeholder=Havola value="{{ mine.link if mine }}">
<label>🖼 Rasm/fayl <input type=file name=file></label><label>🎤 Ovoz <input type=file name=audio accept="audio/*"></label><button class=wide>Yuborish</button></form>{% endif %}</div>{% endif %}
{% if can and allow('grade') and p.kind=='hw' %}<h3>📥 Topshirilgan ishlar ({{ subs|length }})</h3>{% for s in subs %}<div class="card sub"><div class=row><b>{{ name(s) }}</b><span class="status {{ STAT[s.status][1] }}">{{ STAT[s.status][0] }}</span><small class=mut>{{ s.at }}</small>{% if s.late %}<span class="tag bad">Kechikkan</span>{% endif %}</div>
<p style="white-space:pre-wrap">{{ s.text }}</p>{% if s.link %}<a href="{{ s.link }}" target=_blank rel=noopener>{{ s.link }}</a>{% endif %}{{ media(s.file) }}{{ media(s.audio) }}
{% if s.status=='graded' %}<p>Ball: <b>{{ s.score }}/{{ p.maxscore }}</b></p>{% endif %}{% if s.reason %}<div class="note warn">Sabab: {{ s.reason }}</div>{% endif %}
<form method=post action="/sub/{{ s.id }}/grade" class=row>{{ csrf()|safe }}<input type=number name=score min=0 max="{{ p.maxscore }}" value="{{ s.score if s.score is not none else '' }}" placeholder="Ball 0–{{ p.maxscore }}"><input name=fb value="{{ s.fb or '' }}" placeholder="Izoh / rad etish sababi">
<button name=a value=grade>✅ Qabul + baho</button><button name=a value=reject class=red>❌ Rad etish</button><button name=a value=reopen class=gray>↩️ Bekor qilish</button></form></div>{% else %}<div class=card>Hali hech kim topshirmagan</div>{% endfor %}
{% if missing %}<div class=card><h3>⏳ Topshirmaganlar ({{ missing|length }})</h3>{% for u in missing %}<span class=tag>{{ name(u) }}</span>{% endfor %}</div>{% endif %}{% endif %}
<h3 style="margin-top:22px">💬 Izohlar ({{ cmts|length }})</h3>
{% for m in cmts %}<div class=card><div class=row>{{ ava(m) }}<b>{{ name(m) }}</b><span class=tag>{{ ROLES[m.role] }}</span><small class=mut>{{ m.at }}</small>{% if adm or m.user_id==me.id %}<form method=post action="/comment/{{ m.id }}/del" style="margin-left:auto">{{ csrf()|safe }}<button class=red>✖</button></form>{% endif %}</div><p style="white-space:pre-wrap">{{ m.text }}</p></div>{% endfor %}
{% if allow('comment_post') %}<form method=post action="/post/{{ p.id }}/comment" class=card>{{ csrf()|safe }}<textarea name=text placeholder="Savol yoki izoh yozing..." required></textarea><button>Yuborish</button></form>{% endif %}"""),
'schedule.html': P("""<h2>📅 Dars jadvali (14 kun)</h2>{% if allow('schedule_manage') %}<div class=card><form method=post class=row>{{ csrf()|safe }}<select name=course>{% for c in courses %}<option value={{ c.id }}>{{ c.name }}{% endfor %}</select>
<select name=pattern>{% for k,v in PAT.items() %}<option value={{ k }}>{{ v }}{% endfor %}</select><label>Boshlanish <input type=date name=start required></label><label>Tugash <input type=date name=end></label><input type=time name=time required><input name=link placeholder="Onlayn dars havolasi (Zoom/Meet/Jitsi)"><button>Qo'shish</button></form></div>{% endif %}
<div class=card>{% for d,t,c,i in rows %}<p><span class=tag>{{ d }} · {{ DAYS[d.weekday()] }}</span> <b>{{ t }}</b> — {{ c }} {% if links.get(i) %}<a class=btn style="padding:3px 12px;font-size:13px" href="{{ links[i] }}" target=_blank rel=noopener>{{ '🔴 Hozir — kirish' if is_live(d,t) else '🎥 Dars havolasi' }}</a>{% endif %}</p>{% else %}<p class=mut>Darslar yo'q</p>{% endfor %}</div>
{% if allow('schedule_manage') %}<div class=card><h3>Barcha jadvallar</h3>{% for s in all %}<p>{{ s.name }} · {{ PAT[s.pattern] }} · {{ s.start }} → {{ s.end or '…' }} · {{ s.time }} <a href="?del={{ s.id }}" onclick='return confirm("O’chirilsinmi?")'>❌</a></p>{% endfor %}</div>{% endif %}"""),
'rating.html': P("""<h2>🏆 Reyting <a class=btn href="/groups/rating" style="font-size:13px;float:right">🧩 Guruhlar musobaqasi</a></h2><form method=get class=row><select name=period onchange="this.form.submit()"><option value="">Barcha vaqt</option><option value=week {{ 'selected' if period=='week' }}>Shu hafta</option><option value=month {{ 'selected' if period=='month' }}>Shu oy</option></select><select name=course onchange="this.form.submit()"><option value="">Umumiy reyting</option>{% for c in courses %}<option value={{ c.id }} {{ 'selected' if c.id==cid }}>{{ c.name }}{% endfor %}</select></form>
{% if star %}<div class=hero><h2>🌟 Oy o'quvchisi: {{ name(star) }}</h2><p>{{ star.pts }} ball</p></div>{% endif %}<div class=podium>{% for u in rows[:3] %}<div class="pod p{{ loop.index }}"><div style="font-size:34px">{{ ['🥇','🥈','🥉'][loop.index0] }}</div>{{ ava(u, true) }}<h3>{{ name(u) }}</h3><div class=big>{{ u.pts }}</div><small class=mut>ball</small></div>{% endfor %}</div>
<div class=card><table>{% for u in rows[3:] %}<tr class="{{ 'meRow' if u.id==me.id }}"><td width=40>{{ loop.index+3 }}</td><td>{{ ava(u) }} {{ name(u) }}</td><td align=right><b>{{ u.pts }}</b> ball</td></tr>{% endfor %}</table></div>"""),
'teachers.html': P("""<h2>⭐ Ustozlar reytingi</h2><div class=grid>{% for t in rows %}<div class=card>{{ ava(t, true) }}<h3>{{ name(t) }}</h3><div>{{ stars(t.avg) }} <b>{{ t.avg or '—' }}</b> <small class=mut>({{ t.n }} baho)</small></div>
{% if t.id in ok %}<form method=post action="/teachers/rate/{{ t.id }}">{{ csrf()|safe }}<select name=stars>{% for n in [5,4,3,2,1] %}<option value={{ n }} {{ 'selected' if mine.get(t.id) and mine[t.id].stars==n }}>{{ '★'*n }} ({{ n }})</option>{% endfor %}</select>
<input name=comment maxlength=300 placeholder="Fikringiz (ixtiyoriy)" value="{{ mine[t.id].comment if mine.get(t.id) else '' }}"><button class=wide>{{ 'Bahoni yangilash' if mine.get(t.id) else 'Baholash' }}</button></form>{% endif %}</div>{% else %}<div class=card>Hali o'qituvchi yo'q</div>{% endfor %}</div>
{% if cm %}<h3 style="margin-top:20px">💬 Fikrlar</h3>{% for c in cm %}<div class=card><div class=row>{{ stars(c.stars) }}{% if adm %}<small class=mut>{{ (c.sf ~ ' ' ~ c.sl).strip() or c.su }} → {{ c.tu }}</small>
<form method=post action="/teachers/del/{{ c.id }}" style="margin-left:auto">{{ csrf()|safe }}<button class=red>O'chirish</button></form>{% else %}<small class=mut>Anonim</small>{% endif %}</div>{% if c.comment %}<p>{{ c.comment }}</p>{% endif %}<small class=mut>{{ c.at }}</small></div>{% endfor %}{% endif %}"""),
'settings.html': P("""<h2>⚙️ Sozlamalar</h2><form method=post class=card>{{ csrf()|safe }}<h3>Bo'limlarni yoqish / o'chirish</h3>
<label class=opt><input type=checkbox name=shop {{ 'checked' if S('shop')=='1' }}> 🛒 Magazin</label>
<label class=opt><input type=checkbox name=rating {{ 'checked' if S('rating')=='1' }}> 🏆 O'quvchilar reytingi</label>
<label class=opt><input type=checkbox name=trate {{ 'checked' if S('trate')=='1' }}> ⭐ Ustozlarni baholash tizimi</label>
<label class=opt><input type=checkbox name=chat {{ 'checked' if S('chat')=='1' }}> ✉️ Xabarlar va kurs chati</label>
<label class=opt><input type=checkbox name=bonus {{ 'checked' if S('bonus')=='1' }}> 🔥 Kunlik bonus va seriya</label>
<label class=opt><input type=checkbox name=force_pw {{ 'checked' if S('force_pw')=='1' }}> 🔑 Admin bergan parolni birinchi kirishda almashtirish</label><hr>
<h3>Ilovani to'xtatib turish</h3><label class=opt><input type=checkbox name=paused {{ 'checked' if S('paused')=='1' }}> ⏸ Ilovani to'xtatish (faqat adminlar kira oladi)</label>{% if me.role=='boss' %}<hr><h3>🤖 Telegram bot</h3><input name=tg_token placeholder="Bot token (@BotFather)" value="{{ tgtok }}"><small class=mut>Foydalanuvchi profilida chat ID kiritsa, bildirishnomalar Telegramga ham keladi.</small>{% endif %}<button class=wide>Saqlash</button></form>
<form method=post action="/run-jobs" class=card>{{ csrf()|safe }}<h3>⏰ Avtomatik ishlar</h3><p class=mut>Eslatmalar (uy ishi muddati, dars, to'lov) va kunlik zaxira har kuni birinchi kirishda o'zi ishlaydi. Hozir qo'lda ishga tushirish:</p><button>▶ Hozir ishga tushirish</button></form>"""),
'shop.html': P("""<h2>🛒 Magazin</h2>{% if me.role=='student' %}<div class="card stat"><span>💰 Ballaringiz</span><div class=big>{{ balance(me.id) }}</div></div>{% endif %}
{% if allow('shop_manage') %}<div class=card><form method=post class=row>{{ csrf()|safe }}<input name=name placeholder=Nomi required><input name=info placeholder=Izoh><input type=number name=price placeholder=Narx(ball) required><input type=number name=stock value=-1 title="-1 = cheksiz"><button>Qo'shish</button></form></div>{% endif %}
<div class=grid>{% for i in items %}<div class=card><h3>🎁 {{ i.name }}</h3><p class=mut>{{ i.info }}</p><div class=big>{{ i.price }} <small>ball</small></div><small class=mut>{{ 'Cheksiz' if i.stock<0 else 'Qoldi: ' ~ i.stock }}</small>
{% if me.role=='student' and allow('shop_buy') %}<form method=post action="/shop/buy/{{ i.id }}">{{ csrf()|safe }}<button class=wide>Sotib olish</button></form>{% endif %}
{% if allow('shop_manage') %}<form method=post action="/shop/edit/{{ i.id }}">{{ csrf()|safe }}<input name=name value="{{ i.name }}"><input name=info value="{{ i.info }}"><input type=number name=price value="{{ i.price }}"><input type=number name=stock value="{{ i.stock }}"><button>Saqlash</button></form>
<form method=post action="/shop/del/{{ i.id }}">{{ csrf()|safe }}<button class=red>O'chirish</button></form>{% endif %}</div>{% endfor %}</div>
{% if me.role=='student' %}<div class=card><h3>Xaridlarim</h3>{% for b in my %}<p>{{ b.item }} — {{ b.price }} ball · {{ 'Topshirildi ✅' if b.given else 'Kutilmoqda ⏳' }}</p>{% endfor %}</div>{% endif %}
{% if allow('shop_manage') %}<div class=card><h3>Xaridlar</h3>{% for b in all %}<p>{{ b.username }}: {{ b.item }} ({{ b.price }}) {% if b.given %}✅{% else %}<form method=post action="/shop/give/{{ b.id }}" style="display:inline">{{ csrf()|safe }}<button>Topshirildi</button></form>{% endif %}</p>{% endfor %}</div>{% endif %}"""),
'news.html': P("""<h2>📰 Yangiliklar</h2>{% if allow('news_post') %}<div class=card><form method=post>{{ csrf()|safe }}<input name=title placeholder=Sarlavha required><textarea name=body placeholder=Matn></textarea><select name=group><option value="">Hamma uchun</option>{% for g in grps %}<option value={{ g.id }}>Faqat: {{ g.name }}</option>{% endfor %}</select><button>E'lon qilish</button></form></div>{% endif %}
{% for n in rows %}<div class=card><h3>{{ n.title }}{% if n.gname %} <span class=tag>{{ n.gname }}</span>{% endif %}</h3><p>{{ n.body }}</p><small class=mut>{{ n.at }}</small>{% if allow('news_post') %}<form method=post action="/news/del/{{ n.id }}">{{ csrf()|safe }}<button class=red>O'chirish</button></form>{% endif %}</div>{% endfor %}"""),
'notifs.html': P("""<h2>🔔 Bildirishnomalar</h2><div class=card>{% for n in rows %}<p>{% if n.link %}<a href="{{ n.link }}">{{ n.text }}</a>{% else %}{{ n.text }}{% endif %} <small class=mut>{{ n.at }}</small></p>{% else %}<p class=mut>Yo'q</p>{% endfor %}</div>"""),
'profile.html': P("""<h2>👤 Profil</h2><div class=row style="margin-bottom:6px"><a class=btn href="/sessions">🔒 Faol qurilmalar</a><a class=btn href="/my-permissions">🔐 Mening huquqlarim</a>{% if me.role=='student' %}<a class=btn href="/report-card/{{ me.id }}" target=_blank>🧾 Baholar varaqasi</a>{% endif %}</div>
<div class=card><h3>🎨 Mavzu</h3><div class=row><button type=button class=gray onclick="setTh('light')">☀️ Yorug'</button><button type=button class=gray onclick="setTh('dark')">🌙 Qorong'i</button><button type=button class=gray onclick="setTh('')">🖥 Avto</button>
<button type=button onclick="setAc('')" style="background:#6c5ce7">&nbsp;</button><button type=button onclick="setAc('blue')" style="background:#2f80ed">&nbsp;</button><button type=button onclick="setAc('green')" style="background:#16a34a">&nbsp;</button><button type=button onclick="setAc('pink')" style="background:#e11d74">&nbsp;</button><button type=button onclick="setAc('orange')" style="background:#f97316">&nbsp;</button></div></div>
<div class=card><form method=post enctype=multipart/form-data>{{ csrf()|safe }}<div class=row>{{ ava(me, true) }}<div><b>@{{ me.username }}</b><br><span class=tag>{{ ROLES[me.role] }}</span></div></div>
<input name=first value="{{ me.first }}" placeholder=Ism><input name=last value="{{ me.last }}" placeholder=Familiya>
<input name=tg value="{{ me.tg or '' }}" placeholder="Telegram chat ID (xabarnoma uchun, ixtiyoriy)">
<label>Avatar <input type=file name=avatar accept="image/*"></label><label>Orqa fon rasmi <input type=file name=bg accept="image/*"></label><label class=opt><input type=checkbox name=rmbg value=1> Fonni o'chirish</label>
<input type=password name=pw placeholder="Yangi parol (ixtiyoriy)"><button class=wide>Saqlash</button></form></div>
{% if me.role=='student' %}<div class=card><h3>🏅 Yutuqlarim</h3>{% for e,t,d in badges(me.id) %}<span class=tag title="{{ d }}">{{ e }} {{ t }}</span>{% else %}<span class=mut>Hali yutuq yo'q</span>{% endfor %}</div>{% endif %}"""),
}

T.update({
'forgot.html': G("""<div class="card center"><div style="font-size:54px">🔑</div><h2>Parolni tiklash</h2><p class=mut>Loginingizni yozing — adminlarga so'rov yuboriladi.</p><form method=post>{{ csrf()|safe }}<input name=username placeholder="Login" required autofocus><button class=wide>So'rov yuborish</button></form><p><a href="/login">← Kirish</a></p></div>"""),
'attendance.html': P("""<h2>📋 Davomat — {{ c.name }}</h2><form method=get class=row><input type=date name=day value="{{ day }}"><button>Ko'rish</button><a class=btn href="/course/{{ c.id }}/qr">📲 QR bilan davomat</a></form>
<form method=post class=card>{{ csrf()|safe }}<input type=hidden name=day value="{{ day }}"><input type=hidden name=save value=1><table>{% for s in stu %}<tr><td>{{ ava(s) }} {{ name(s) }}</td><td><label class=opt><input type=checkbox name="p{{ s.id }}" {{ 'checked' if ex.get(s.id,dflt) }}> Keldi</label></td><td class=mut>{{ pcts[s.id][0] }}%</td></tr>{% else %}<tr><td>Kursda o'quvchi yo'q</td></tr>{% endfor %}</table><button class=wide>Saqlash</button></form>
<a href="/course/{{ c.id }}">← Kursga qaytish</a>"""),
'att_me.html': P("""<h2>📋 Davomat</h2>{% for r in rows %}<div class="card cc" style="--c:{{ r.c.color }}"><h3>{{ r.c.name }}</h3><div class=bar><i style="width:{{ r.pct }}%"></i></div><p><b>{{ r.pct }}%</b> <small class=mut>({{ r.n }} ta belgilangan dars)</small></p>{% if r.absent %}<small class=mut>Kelmagan kunlar: {{ r.absent|join(', ') }}</small>{% endif %}</div>{% else %}<div class=card>Ma'lumot yo'q</div>{% endfor %}"""),
'quizzes.html': P("""<div class=hero style="--c:{{ c.color }}"><h2>🧪 Testlar</h2><p>{{ c.name }}</p></div>
{% if can %}<div class=card><h3>➕ Yangi test</h3><form method=post>{{ csrf()|safe }}<input name=title placeholder="Test nomi" required><div class=row><label class=opt><input type=checkbox name=final> 🏁 Yakuniy imtihon (sertifikat uchun)</label><label>O'tish bali, % <input type=number name=pass_pct value=60 min=1 max=100></label></div><div class=row><label>⏱ Daqiqa (0 = cheksiz) <input type=number name=minutes value=10 min=0 max=300></label><label>🎯 Maksimal ball <input type=number name=maxscore value=100 min=1 max=1000></label></div>
<textarea name=qs rows=10 required placeholder="Savol matni?&#10;A) variant&#10;B) variant&#10;C) variant&#10;D) variant&#10;Javob: B&#10;&#10;(keyingi savol bo'sh qator bilan ajratiladi)"></textarea><button>Testni joylash</button></form></div>{% endif %}
<div class=grid>{% for z in rows %}<a class="card cc" style="--c:{{ c.color }}" href="/quiz/{{ z.id }}"><h3>{{ z.title }}{% if z.final %} <span class="tag warn">🏁 Yakuniy</span>{% endif %}</h3><span class=tag>❓ {{ z.n }}</span><span class=tag>🎯 {{ z.maxscore }}</span>{% if z.minutes %}<span class=tag>⏱ {{ z.minutes }} daq</span>{% endif %}
{% if mine.get(z.id) and mine[z.id].score is not none %}<br><span class="status ok">✅ {{ mine[z.id].score }}/{{ z.maxscore }}</span>{% elif mine.get(z.id) %}<br><span class="status warn">Davom etmoqda</span>{% endif %}{% if can %}<br><small class=mut>Topshirgan: {{ z.done }}</small>{% endif %}</a>{% else %}<div class=card>Hali test yo'q</div>{% endfor %}</div>
<a href="/course/{{ c.id }}">← Kursga qaytish</a>"""),
'quiz.html': P("""<div class=hero style="--c:{{ c.color }}"><small>{{ c.name }}</small><h2>🧪 {{ z.title }}</h2><span class="tag light">❓ {{ qs|length }} savol</span> <span class="tag light">🎯 {{ z.maxscore }} ball</span>{% if z.minutes %} <span class="tag light">⏱ {{ z.minutes }} daqiqa</span>{% endif %}</div>
{% if me.role=='student' %}{% if not att %}<div class=card><h3>Testni boshlaysizmi?</h3><p>Faqat bir marta topshirish mumkin.{% if z.minutes %} Vaqt: {{ z.minutes }} daqiqa.{% endif %}</p><form method=post action="/quiz/{{ z.id }}/start">{{ csrf()|safe }}<button class=wide>▶ Boshlash</button></form></div>
{% elif att.score is none %}<div class=card><div class=row><h3 style="margin:0;flex:1">Test davom etmoqda</h3>{% if z.minutes %}<span class="status warn" id=tm></span>{% endif %}</div></div>
<form method=post action="/quiz/{{ z.id }}/submit" id=qf>{{ csrf()|safe }}{% for x in qs %}<div class=card><b>{{ loop.index }}. {{ x.q }}</b>{% for l in ['A','B','C','D'] %}{% set o=x[l|lower] %}{% if o %}<label class=opt><input type=radio name="q{{ x.id }}" value={{ l }}> {{ l }}) {{ o }}</label>{% endif %}{% endfor %}</div>{% endfor %}<button class=wide>Yakunlash</button></form>
{% if z.minutes %}<script>var L={{ left }},tm=document.getElementById('tm'),fm=document.getElementById('qf');function tick(){var m=Math.floor(L/60),s=L%60;tm.textContent='⏱ '+m+':'+(s<10?'0':'')+s;if(L<=0){fm.submit();return}L--;setTimeout(tick,1000)}tick();</script>{% endif %}
{% else %}<div class=card><div class=score>{{ att.score }}<small>/{{ z.maxscore }}</small></div><p>To'g'ri javoblar: <b>{{ att.good }}/{{ att.total }}</b></p></div>
{% for x in qs %}<div class=card><b>{{ loop.index }}. {{ x.q }}</b>{% for l in ['A','B','C','D'] %}{% set o=x[l|lower] %}{% if o %}<div class="note {{ 'ok' if l==x.ans else ('bad' if answers.get(x.id|string)==l else '') }}">{{ l }}) {{ o }}{{ ' ✔' if l==x.ans }}{{ ' (sizning javobingiz)' if answers.get(x.id|string)==l }}</div>{% endif %}{% endfor %}</div>{% endfor %}{% endif %}{% endif %}
{% if can %}<div class=card><h3>📊 Natijalar ({{ res|length }})</h3><table>{% for a in res %}<tr><td>{{ name(a) }}</td><td>{% if a.score is none %}<span class="tag warn">davom etmoqda</span>{% else %}<b>{{ a.score }}/{{ z.maxscore }}</b> <small class=mut>({{ a.good }}/{{ a.total }})</small>{% endif %}</td><td align=right><form method=post action="/quiz/{{ z.id }}/reset/{{ a.student_id }}" style="display:inline">{{ csrf()|safe }}<button class=gray>↩️ Qayta topshirtirish</button></form></td></tr>{% else %}<tr><td>Hali hech kim topshirmagan</td></tr>{% endfor %}</table></div>
<div class=card><h3>❓ Savollar va javoblar</h3>{% for x in qs %}<p>{{ loop.index }}. {{ x.q }} <small class=mut>(javob: {{ x.ans }})</small></p>{% endfor %}<form method=post action="/quiz/{{ z.id }}/del" onsubmit='return confirm("Test o’chirilsinmi?")'>{{ csrf()|safe }}<button class=red>Testni o'chirish</button></form></div>{% endif %}
<a href="/course/{{ c.id }}/quizzes">← Testlar</a>"""),
'cert.html': """<!doctype html><html lang=uz><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Sertifikat</title><style>
body{margin:0;background:#eceefc;font-family:Georgia,serif;display:flex;flex-direction:column;align-items:center;padding:20px}
.c{width:min(1000px,96vw);aspect-ratio:1.414;background:#fff;border:14px double {{ c.color }};padding:30px;text-align:center;display:flex;flex-direction:column;justify-content:center;box-sizing:border-box}
h1{font-size:clamp(26px,6vw,58px);color:{{ c.color }};margin:0;letter-spacing:4px}.n{font-size:clamp(24px,5vw,46px);margin:18px 0;border-bottom:2px solid #999;display:inline-block;padding:0 30px}
p{font-size:clamp(13px,2.2vw,22px);margin:8px}button{margin:16px;padding:12px 24px;font-size:16px;border:0;border-radius:10px;background:#6c5ce7;color:#fff;cursor:pointer}
@media print{body{background:#fff;padding:0}button{display:none}.c{width:100%;height:100vh}}@page{size:landscape;margin:0}</style></head><body>
<div class=c><div style="font-size:50px">🎓</div><h1>SERTIFIKAT</h1><p>Ushbu sertifikat quyidagi o'quvchiga topshiriladi</p><div><span class=n>{{ ((s.first ~ ' ' ~ s.last)|trim) or s.username }}</span></div>
<p>«{{ c.name }}» kursini muvaffaqiyatli tamomlagani uchun</p><p>O'rtacha natija: <b>{{ avg }}%</b></p><p>{{ day }}{% if tn %} · O'qituvchi: {{ ((tn.first ~ ' ' ~ tn.last)|trim) or tn.username }}{% endif %}</p></div>
<button onclick="window.print()">🖨 Chop etish / PDF saqlash</button></body></html>""",
'child.html': P("""{% if not s %}<div class=card>Farzand hali biriktirilmagan. Admin bilan bog'laning.</div>{% else %}
<div class=hero><h2>👪 {{ name(s) }}</h2><p>Farzandingiz natijalari</p></div>
<div class=grid><div class="card stat"><span>💰 Balans</span><div class=big>{{ info.bal }}</div><small>Jami: {{ info.earn }}</small></div><div class="card stat"><span>🏆 O'rin</span><div class=big>{{ info.rank }}<small>/{{ info.total }}</small></div></div>
<a class="card stat" href="/attendance"><span>📋 Davomat</span><div class=big>{{ info.att }}%</div></a><div class="card stat"><span>📝 Bajariladigan</span><div class=big>{{ info.todo }}</div></div>{% if info.debt %}<a class="card stat" href="/my-fees"><span>💳 Qarzdorlik</span><div class=big style="color:var(--bad)">{{ info.debt }}</div><small>so'm</small></a>{% endif %}</div>
<div class=card><h3>🏅 Yutuqlar</h3>{% for e,t,d in badges(s.id) %}<span class=tag title="{{ d }}">{{ e }} {{ t }}</span>{% else %}<span class=mut>Hali yutuq yo'q</span>{% endfor %}</div>
{% if certs %}<div class=card><h3>🎓 Sertifikatlar</h3>{% for c in certs %}<a class=btn href="/certificate/{{ c.id }}" target=_blank>{{ c.name }}</a> {% endfor %}</div>{% endif %}
<p><a class=btn href="/report-card/{{ s.id }}" target=_blank>🧾 Baholar varaqasi</a> <a class=btn href="/my-fees">💳 To'lovlar</a></p><h3>So'nggi ishlar</h3>{% for x in subs %}<div class="card cc" style="--c:{{ x.color }}"><div class=row><div style="flex:1"><small class=mut>{{ x.cname }} · {{ x.at }}</small><h3 style="margin:2px 0">{{ x.title }}</h3><span class="status {{ STAT[x.status][1] }}">{{ STAT[x.status][0] }}</span>{% if x.late %} <span class="tag bad">Kechikkan</span>{% endif %}</div>
{% if x.status=='graded' %}<div class=score>{{ x.score }}<small>/{{ x.maxscore }}</small></div>{% endif %}</div></div>{% else %}<div class=card>Hali ish yuborilmagan</div>{% endfor %}{% endif %}"""),
'messages.html': P("""<h2>✉️ Xabarlar</h2><div class=card><form onsubmit="location='/messages/'+this.u.value;return false"><div class=row><select name=u style="flex:1">{% for u in users_ %}<option value={{ u.id }}>{{ name(u) }} ({{ ROLES[u.role] }})</option>{% endfor %}</select><button>Yangi xabar</button></div></form></div>
{% for p in partners %}<a class=card href="/messages/{{ p.id }}"><div class=row>{{ ava(p) }}<div style="flex:1"><b>{{ name(p) }}</b>{% if p.unr %}<b class=badge>{{ p.unr }}</b>{% endif %}<br><small class=mut>{{ (p.lm or '')[:60] }}</small></div></div></a>{% else %}<div class=card>Hali xabar yo'q</div>{% endfor %}"""),
'thread.html': P("""<h2>{{ ava(o) }} {{ name(o) }} <small class=mut>{{ ROLES[o.role] }}</small></h2><div class=card id=msgs>{% for m in rows %}<div class="msg {{ 'me' if m.from_id==me.id }}">{{ m.text }}<small>{{ m.at }}</small></div>{% else %}<p class=mut>Xabar yozing...</p>{% endfor %}</div>
<form method=post class=row>{{ csrf()|safe }}<input name=text placeholder="Xabar yozing..." required autocomplete=off autofocus><button>Yuborish</button></form><p><a href="/messages">← Barcha xabarlar</a></p>
<script>setInterval(function(){if(document.querySelector('input[name=text]').value)return;fetch(location.href).then(function(r){return r.text()}).then(function(h){var d=new DOMParser().parseFromString(h,'text/html').getElementById('msgs');if(d)document.getElementById('msgs').innerHTML=d.innerHTML})},10000)</script>"""),
'chat.html': P("""<div class=hero style="--c:{{ c.color }}"><h2>💬 {{ c.name }} — kurs chati</h2></div><div class=card id=msgs>{% for m in rows %}<div class="msg {{ 'me' if m.user_id==me.id }}"><small><b>{{ name(m) }}</b> · {{ ROLES[m.role] }}</small>{{ m.text }}<small>{{ m.at }}{% if adm %} <form method=post action="/cmsg/{{ m.id }}/del" style="display:inline">{{ csrf()|safe }}<button class=red style="padding:0 8px">✖</button></form>{% endif %}</small></div>{% else %}<p class=mut>Hali xabar yo'q</p>{% endfor %}</div>
{% if allow('chat_post') %}<form method=post class=row>{{ csrf()|safe }}<input name=text placeholder="Xabar yozing..." required autocomplete=off autofocus><button>Yuborish</button></form>{% endif %}<p><a href="/course/{{ c.id }}">← Kursga qaytish</a></p>
<script>setInterval(function(){if(document.querySelector('input[name=text]')&&document.querySelector('input[name=text]').value)return;fetch(location.href).then(function(r){return r.text()}).then(function(h){var d=new DOMParser().parseFromString(h,'text/html').getElementById('msgs');if(d)document.getElementById('msgs').innerHTML=d.innerHTML})},10000)</script>"""),
'reports.html': P("""<h2>📊 Hisobotlar</h2>
<div class=card style="overflow-x:auto"><div class=row><h3 style="flex:1;margin:0">📘 Kurslar bo'yicha</h3><a class=btn href="/reports/csv?t=courses">⬇ Excel (CSV)</a></div><table><tr><th>Kurs</th><th>O'quvchi</th><th>Uy ishi</th><th>Topshirilgan</th><th>Kechikkan</th><th>O'rtacha</th></tr>
{% for r in cr %}<tr><td><span class=tag style="background:{{ r.color }};color:#fff">{{ r.name }}</span></td><td>{{ r.students }}</td><td>{{ r.hw }}</td><td>{{ r.subs }}</td><td>{{ r.late }}</td><td style="min-width:140px"><div class=bar><i style="width:{{ r.avgp or 0 }}%"></i></div><small>{{ r.avgp or 0 }}%</small></td></tr>{% endfor %}</table></div>
<div class=card style="overflow-x:auto"><div class=row><h3 style="flex:1;margin:0">👨‍🏫 O'qituvchilar</h3><a class=btn href="/reports/csv?t=teachers">⬇ Excel (CSV)</a></div><table><tr><th>Ustoz</th><th>Kurslar</th><th>Baholangan</th><th>Kutilmoqda</th><th>Reyting</th></tr>
{% for t in ts %}<tr><td>{{ name(t) }}</td><td>{{ t.courses }}</td><td>{{ t.graded }}</td><td>{{ t.pending }}</td><td>{{ stars(t.rate) }} {{ t.rate or '—' }}</td></tr>{% endfor %}</table></div>
<div class=card style="overflow-x:auto"><div class=row><h3 style="flex:1;margin:0">👨‍🎓 O'quvchilar</h3><a class=btn href="/reports/csv?t=students">⬇ Excel (CSV)</a></div><table><tr><th>O'quvchi</th><th>Ball</th><th>Davomat</th><th>Topshirgan</th><th>Kechikkan</th></tr>
{% for x in ss %}<tr><td>{{ ava(x.u) }} {{ name(x.u) }}</td><td><b>{{ x.earned }}</b></td><td>{{ x.att }}%</td><td>{{ x.subs }}</td><td>{{ x.late }}</td></tr>{% endfor %}</table></div>"""),
'journal.html': P("""<h2>📒 Jurnal — {{ c.name }}</h2><div class=row><a class=btn href="?csv=1">⬇ Excel (CSV)</a><a href="/course/{{ c.id }}">← Kursga qaytish</a></div><div class=card style="overflow-x:auto"><table><tr><th>O'quvchi</th>{% for h in hws %}<th><a href="/post/{{ h.id }}">{{ h.title[:12] }}</a><br><small class=mut>/{{ h.maxscore }}</small></th>{% endfor %}<th>Jami</th><th>Davomat</th><th></th></tr>
{% for r in rows %}<tr><td>{{ name(r.s) }}</td>{% for x in r.cells %}<td align=center>{{ x }}</td>{% endfor %}<td align=center><b>{{ r.total }}</b></td><td align=center>{{ r.att }}%</td><td><a href="/certificate/{{ c.id }}?s={{ r.s.id }}" target=_blank title="Sertifikat">🎓</a></td></tr>{% else %}<tr><td>Kursda o'quvchi yo'q</td></tr>{% endfor %}</table></div>"""),
'logs.html': P("""<h2>🧾 Harakatlar tarixi</h2><div class=card><table>{% for l in rows %}<tr><td class=mut width=150><small>{{ l.at }}</small></td><td><b>{{ l.uname or '—' }}</b></td><td>{{ l.action }}</td></tr>{% else %}<tr><td>Hali yozuv yo'q</td></tr>{% endfor %}</table></div>"""),
'cal.html': P("""<h2>📆 Kalendar</h2><div class=row><a class=btn href="?m={{ prev }}">←</a><h3 style="margin:0;flex:1;text-align:center">{{ MONS[lang][mo-1] }} {{ y }}</h3><a class=btn href="?m={{ nxt }}">→</a></div>
<div class=cal style="margin-top:12px">{% for d in WDS[lang] %}<div class=h>{{ d }}</div>{% endfor %}{% for w in weeks %}{% for d in w %}<div class="d {{ 'off' if d==0 }} {{ 'today' if d and today.year==y and today.month==mo and today.day==d }}">{% if d %}<b>{{ d }}</b>{% for k,t,l in ev.get(d,[]) %}<a class="chip {{ k }}" href="{{ l }}" title="{{ t }}">{{ t }}</a>{% endfor %}{% endif %}</div>{% endfor %}{% endfor %}</div>
<p class=mut><span class=chip style="display:inline-block">Dars</span> <span class="chip dl" style="display:inline-block">Uy ishi muddati</span></p>"""),
'search.html': P("""<h2>🔍 Qidiruv: {{ k }}</h2>{% if k|length<2 %}<div class=card>Kamida 2 ta belgi kiriting</div>{% endif %}
{% if cs_ %}<h3>Kurslar</h3><div class=grid>{% for c in cs_ %}<a class="card cc" style="--c:{{ c.color }}" href="/course/{{ c.id }}"><b>{{ c.name }}</b><p class=mut>{{ c.info }}</p></a>{% endfor %}</div>{% endif %}
{% if ps %}<h3>Darslar va uy ishlari</h3>{% for p in ps %}<a class=card href="/post/{{ p.id }}"><b>{{ '📝' if p.kind=='hw' else '📖' }} {{ p.title }}</b> <small class=mut>{{ p.cname }}</small></a>{% endfor %}{% endif %}
{% if us %}<h3>Foydalanuvchilar</h3><div class=grid>{% for u in us %}<a class=card href="/messages/{{ u.id }}"><div class=row>{{ ava(u) }}<div><b>{{ name(u) }}</b><br><span class=tag>{{ ROLES[u.role] }}</span></div></div></a>{% endfor %}</div>{% endif %}
{% if not cs_ and not ps and not us and k|length>=2 %}<div class=card>Hech narsa topilmadi</div>{% endif %}"""),
})


T.update({
'403.html': "{% extends 'base' %}{% block c %}<div class='card center'><div style='font-size:54px'>⛔</div><h2>Ruxsat yo'q</h2><p class=mut>Sizda bu amalni bajarish huquqi yo'q. Kerak bo'lsa, Boshliq yoki admin bilan bog'laning.</p><a class=btn href='/'>Bosh sahifa</a> <a class=btn href='/my-permissions'>Mening huquqlarim</a></div>{% endblock %}{% block g %}<div class='card center'><h2>Ruxsat yo'q</h2><a class=btn href='/login'>Kirish</a></div>{% endblock %}",
'perms.html': P("""<h2>🔐 Huquqlar boshqaruvi</h2><p class=mut>Har bir rol nima qila olishini belgilang. Boshliq doim hamma narsani qila oladi. Alohida foydalanuvchi uchun istisno belgilash: Foydalanuvchilar sahifasidagi “🔐 Huquqlar” tugmasi.</p>
<form method=post class=card style="overflow-x:auto">{{ csrf()|safe }}<table><tr><th>Imkoniyat</th>{% for r in roles %}<th style="text-align:center">{{ ROLES[r] }}</th>{% endfor %}</tr>
{% for gname, items in groups %}<tr><td colspan=5 class=gh>{{ gname }}</td></tr>{% for k,label in items %}<tr><td>{{ label }}</td>{% for r in roles %}<td align=center><input type=checkbox name="r_{{ r }}_{{ k }}" {{ 'checked' if cur[r~'|'~k] }}></td>{% endfor %}</tr>{% endfor %}{% endfor %}</table>
<button class=wide>Saqlash</button><button name=reset value=1 class="gray wide" onclick='return confirm("Barcha rol huquqlari standart holatga qaytsinmi?")'>Standartga qaytarish</button></form>"""),
'user_perms.html': P("""<h2>🔐 Huquqlar: {{ name(u) }} <span class=tag>{{ ROLES[u.role] }}</span></h2><p class=mut>“Rol bo'yicha” — foydalanuvchi o'z rolining huquqini oladi. “Ruxsat” yoki “Taqiq” — faqat shu foydalanuvchi uchun istisno.</p>
<form method=post class=card style="overflow-x:auto">{{ csrf()|safe }}<table>{% for gname, items in groups %}<tr><td colspan=3 class=gh>{{ gname }}</td></tr>{% for k,label in items %}<tr><td>{{ label }}</td><td class=mut>{{ 'Rolda: ha' if base[k] else "Rolda: yo'q" }}</td>
<td><select name="u_{{ k }}"><option value="" {{ 'selected' if cur[k]=='' }}>Rol bo'yicha</option><option value=1 {{ 'selected' if cur[k]=='1' }}>✅ Ruxsat</option><option value=0 {{ 'selected' if cur[k]=='0' }}>⛔ Taqiq</option></select></td></tr>{% endfor %}{% endfor %}</table><button class=wide>Saqlash</button></form><a href="/users">← Foydalanuvchilar</a>"""),
'my_perms.html': P("""<h2>🔐 Mening huquqlarim</h2><p class=mut>Rolingiz: <b>{{ ROLES[me.role] }}</b>. Quyida nima qila olishingiz ko'rsatilgan.</p>
{% for gname, items in groups %}<div class=card><h3>{{ gname }}</h3>{% for k,label in items %}<p>{{ '✅' if eff[k] else '⛔' }} {{ label }}</p>{% endfor %}</div>{% endfor %}"""),
'sessions.html': P("""<h2>🔒 Faol qurilmalar</h2><div class=card><table>{% for r in rows %}<tr><td>{{ '📍 Hozirgi qurilma' if r.id==cur else '💻' }}<br><small class=mut>{{ r.ua[:90] }}</small></td><td><small>{{ r.ip }}<br>{{ r.at }}</small></td><td align=right>{% if r.id!=cur %}<form method=post>{{ csrf()|safe }}<input type=hidden name=a value=kill><input type=hidden name=sid value="{{ r.id }}"><button class=red>Chiqish</button></form>{% endif %}</td></tr>{% endfor %}</table>
<form method=post>{{ csrf()|safe }}<input type=hidden name=a value=all><button class="gray wide">Boshqa barcha qurilmalardan chiqish</button></form></div>"""),
'chpw.html': P("""<div class="card center" style="max-width:420px;margin:30px auto"><div style="font-size:48px">🔑</div><h2>Parolni o'zgartiring</h2><p class=mut>Xavfsizlik uchun admin bergan vaqtincha parolni almashtiring (kamida 6 belgi).</p><form method=post>{{ csrf()|safe }}<input type=password name=p1 placeholder="Yangi parol" required autofocus><input type=password name=p2 placeholder="Yangi parolni takrorlang" required><button class=wide>Saqlash</button></form></div>"""),
'payments.html': P("""<h2>💳 To'lov nazorati</h2><div class=row><a class=btn href="?m={{ prev }}">←</a><h3 style="margin:0;flex:1;text-align:center">{{ MONS[lang][mo-1] }} {{ y }}</h3><a class=btn href="?m={{ nxt }}">→</a></div>
<div class=grid style="margin:12px 0"><div class="card stat"><span>Kutilgan</span><div class=big>{{ tot }}</div></div><div class="card stat"><span>To'langan</span><div class=big style="color:var(--ok)">{{ paid }}</div></div><div class="card stat"><span>Qarz</span><div class=big style="color:var(--bad)">{{ tot-paid }}</div></div></div>
<div class=card style="overflow-x:auto"><div class=row><h3 style="flex:1;margin:0">O'quvchilar</h3><a class=btn href="/payments/csv?m={{ m }}">⬇ Excel (CSV)</a><form method=post>{{ csrf()|safe }}<input type=hidden name=m value="{{ m }}"><input type=hidden name=a value=remind_all><button class=gray>🔔 Qarzdorlarga eslatma</button></form></div>
<table>{% for r in rows %}<tr><td>{{ ava(r) }} {{ name(r) }}</td><td><b>{{ r.amount }}</b> so'm</td><td>{% if r.paid %}<span class="status ok">✅ To'langan</span><br><small class=mut>{{ r.paid_at }}</small>{% else %}<span class="status bad">Qarz</span>{% endif %}</td>
<td align=right><form method=post style="display:inline">{{ csrf()|safe }}<input type=hidden name=m value="{{ m }}"><input type=hidden name=sid value="{{ r.student_id }}">{% if r.paid %}<input type=hidden name=a value=unpaid><button class=gray>↩️ Bekor</button>{% else %}<input type=hidden name=a value=paid><button>✅ To'landi</button>{% endif %}</form>
{% if not r.paid %}<form method=post style="display:inline">{{ csrf()|safe }}<input type=hidden name=m value="{{ m }}"><input type=hidden name=sid value="{{ r.student_id }}"><input type=hidden name=a value=remind><button class=gray>🔔</button></form>{% endif %}</td></tr>{% else %}<tr><td>Bu oy uchun yozuv yo'q. Pastda o'quvchilarga oylik to'lov summasini belgilang.</td></tr>{% endfor %}</table></div>
<div class=card style="overflow-x:auto"><h3>⚙️ Oylik to'lov summasi (so'm)</h3><table>{% for s in students %}<tr><td>{{ ava(s) }} {{ name(s) }}</td><td><form method=post class=row>{{ csrf()|safe }}<input type=hidden name=m value="{{ m }}"><input type=hidden name=a value=fee><input type=hidden name=sid value="{{ s.id }}"><input type=number name=fee value="{{ s.fee or 0 }}" min=0 style="max-width:160px"><button>Saqlash</button></form></td></tr>{% endfor %}</table></div>"""),
'my_fees.html': P("""<h2>💳 To'lovlar{% if s %} — {{ name(s) }}{% endif %}</h2>{% if debt %}<div class="flash bad">Jami qarzdorlik: <b>{{ debt }} so'm</b></div>{% else %}<div class="flash" style="background:#dcfce7;color:#166534">Qarzdorlik yo'q 🎉</div>{% endif %}
<div class=card><table>{% for r in rows %}<tr><td><b>{{ r.month }}</b></td><td>{{ r.amount }} so'm</td><td>{% if r.paid %}<span class="status ok">✅ To'langan</span> <small class=mut>{{ r.paid_at }}</small>{% else %}<span class="status bad">Qarz</span>{% endif %}</td></tr>{% else %}<tr><td>Hali to'lov yozuvi yo'q</td></tr>{% endfor %}</table></div>"""),
'groups.html': P("""<h2>🧩 Guruhlar <a class=btn href="/groups/rating" style="font-size:13px;float:right">🏆 Musobaqa</a></h2><div class=card><form method=post class=row>{{ csrf()|safe }}<input type=color name=color value="#6c5ce7"><input name=name placeholder="Guruh nomi (masalan: 7-A)" required><button>Guruh qo'shish</button></form></div>
<div class=grid>{% for g in rows %}<a class="card course" style="--c:{{ g.color }}" href="/groups/{{ g.id }}"><div class=cbar></div><h3>{{ g.name }}</h3><span class=tag>👨‍🎓 {{ g.n }}</span><span class=tag>📘 {{ g.c }}</span></a>{% else %}<div class=card>Hali guruh yo'q</div>{% endfor %}</div>"""),
'group.html': P("""<div class=hero style="--c:{{ g.color }}"><h2>🧩 {{ g.name }}</h2><p>Guruhga biriktirilgan kurslar: {% for c in courses %}<span class="tag light">{{ c.name }}</span>{% else %}yo'q{% endfor %}</p></div>
<form method=post class=card>{{ csrf()|safe }}<div class=row><input type=color name=color value="{{ g.color }}"><input name=name value="{{ g.name }}" required></div><h3>O'quvchilar</h3><div class=chk>{% for s in students %}<label><input type=checkbox name=st value={{ s.id }} {{ 'checked' if s.id in mine }}> {{ name(s) }}</label>{% endfor %}</div>
<button class=wide>Saqlash</button><button name=del value=1 class="red wide" onclick='return confirm("Guruh o’chirilsinmi?")'>Guruhni o'chirish</button></form><p class=mut>Kursni guruhga biriktirish: Kurs sahifasi → Kursni tahrirlash → Guruh. Shunda guruh o'quvchilari kursga avtomatik yoziladi.</p><a href="/groups">← Guruhlar</a>"""),
'groups_rating.html': P("""<h2>🧩 Guruhlar musobaqasi</h2><form method=get><select name=period onchange="this.form.submit()"><option value="">Barcha vaqt</option><option value=week {{ 'selected' if period=='week' }}>Shu hafta</option><option value=month {{ 'selected' if period=='month' }}>Shu oy</option></select></form>
<p class=mut>Reyting guruh o'quvchilarining o'rtacha balliga qarab tuziladi.</p>{% for r in rows %}<div class="card cc" style="--c:{{ r.g.color }}"><div class=row><span style="font-size:26px">{{ ['🥇','🥈','🥉'][loop.index0] if loop.index0<3 else loop.index }}</span><h3 style="margin:0;flex:1">{{ r.g.name }}</h3><b>{{ r.avg }}</b><small class=mut>o'rtacha · jami {{ r.tot }} · {{ r.n }} o'quvchi</small></div><div class=bar style="margin-top:8px"><i style="width:{{ (r.avg*100/mx)|round|int }}%"></i></div></div>{% else %}<div class=card>Hali guruh yo'q</div>{% endfor %}"""),
'import.html': P("""<h2>📥 CSV orqali ommaviy qo'shish</h2><div class=card><form method=post enctype=multipart/form-data>{{ csrf()|safe }}<p class=mut>Har qatorda: <b>Ism, Familiya, login (ixtiyoriy), guruh (ixtiyoriy)</b>. Login bo'sh bo'lsa avtomatik yaratiladi, parol tasodifiy. Foydalanuvchi birinchi kirishda parolni almashtiradi.</p>
<textarea name=data rows=8 placeholder="Ali, Valiyev&#10;Vali, Karimov, vali01, 7-A"></textarea><label>yoki CSV/TXT fayl: <input type=file name=file accept=".csv,.txt"></label>
<div class=row><select name=role><option value=student>O'quvchi<option value=teacher>O'qituvchi<option value=parent>Ota-ona</select><select name=group><option value="">Guruh (ixtiyoriy)</option>{% for g in grps %}<option value={{ g.id }}>{{ g.name }}</option>{% endfor %}</select></div><button class=wide>Qo'shish</button></form></div>
{% if created %}<div class=card><h3>✅ Yaratilgan hisoblar ({{ created|length }})</h3><p class="note warn">Parollar faqat hozir ko'rinadi! Yuklab oling yoki chop eting.</p><button onclick="dl()">⬇ CSV yuklab olish</button><table id=res><tr><th>Ism</th><th>Familiya</th><th>Login</th><th>Parol</th></tr>{% for c in created %}<tr><td>{{ c[0] }}</td><td>{{ c[1] }}</td><td>{{ c[2] }}</td><td><b>{{ c[3] }}</b></td></tr>{% endfor %}</table></div>
<script>function dl(){var nl=String.fromCharCode(10),r=[];document.querySelectorAll('#res tr').forEach(function(tr){r.push([].map.call(tr.children,function(td){return td.textContent}).join(','))});var b=new Blob([String.fromCharCode(65279)+r.join(nl)],{type:'text/csv'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='yangi-hisoblar.csv';a.click()}</script>{% endif %}"""),
'rcard.html': """<!doctype html><html lang=uz><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>Baholar varaqasi</title><style>
body{margin:0;background:#eceefc;font-family:system-ui,Segoe UI,Roboto,sans-serif;color:#1d2136;padding:18px;display:flex;flex-direction:column;align-items:center}
.p{background:#fff;width:min(900px,100%);padding:30px;border-radius:12px;box-sizing:border-box}h1{margin:0;color:#6c5ce7}table{width:100%;border-collapse:collapse;margin:16px 0}th,td{border:1px solid #d9dcef;padding:8px;text-align:center}th{background:#f1efff}td:first-child{text-align:left}
.k{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}.k div{flex:1;min-width:120px;background:#f6f5ff;border-radius:10px;padding:10px;text-align:center}.k b{display:block;font-size:24px;color:#6c5ce7}
button{margin:14px;padding:12px 24px;font-size:16px;border:0;border-radius:10px;background:#6c5ce7;color:#fff;cursor:pointer}@media print{body{background:#fff;padding:0}button{display:none}.p{padding:0}}</style></head><body>
<div class=p><h1>🧾 Baholar varaqasi</h1><p><b>{{ ((s.first ~ ' ' ~ s.last)|trim) or s.username }}</b> · {{ day }}</p>
<div class=k><div><b>{{ total }}</b>Jami ball</div><div><b>{{ rank }}/{{ n }}</b>Reyting o'rni</div><div><b>{{ att }}%</b>Davomat</div></div>
<table><tr><th>Kurs</th><th>Uy ishi</th><th>Ball</th><th>O'rtacha %</th><th>Test %</th><th>Davomat</th><th>Sertifikat</th></tr>
{% for r in rows %}<tr><td>{{ r.c.name }}</td><td>{{ r.done }}/{{ r.hw }}</td><td>{{ r.pts }}</td><td>{{ r.avg if r.avg is not none else '—' }}</td><td>{{ r.qavg if r.qavg is not none else '—' }}</td><td>{{ r.att }}%</td><td>{{ '🎓' if r.cert else '—' }}</td></tr>{% else %}<tr><td colspan=7>Kurs yo'q</td></tr>{% endfor %}</table>
<p>🏅 Yutuqlar: {% for e,t,d in bl %}{{ e }} {{ t }}{{ ', ' if not loop.last }}{% else %}—{% endfor %}</p></div><button onclick="window.print()">🖨 Chop etish / PDF saqlash</button></body></html>""",
'library.html': P("""<h2>📚 Kutubxona</h2>{% if allow('library_upload') %}<div class=card><h3>➕ Material qo'shish</h3><form method=post enctype=multipart/form-data>{{ csrf()|safe }}<input name=title placeholder="Nomi" required><input name=info placeholder="Izoh"><input name=link placeholder="Havola (ixtiyoriy)">
<label>📎 Fayl <input type=file name=file></label><select name=course>{% if allow('library_manage') %}<option value="">Umumiy (hamma uchun)</option>{% endif %}{% for c in courses %}<option value={{ c.id }}>{{ c.name }}</option>{% endfor %}</select><button class=wide>Qo'shish</button></form></div>{% endif %}
<form method=get class=row><input name=q value="{{ kq }}" placeholder="🔍 Qidirish"><select name=course><option value="">Barcha kurslar</option>{% for c in courses %}<option value={{ c.id }} {{ 'selected' if c.id==cid }}>{{ c.name }}</option>{% endfor %}</select><button>Topish</button></form>
{% for r in rows %}<div class="card cc" style="--c:{{ r.color or '#6c5ce7' }}"><div class=row><h3 style="margin:0;flex:1">{{ r.title }}</h3>{% if r.cname %}<span class=tag>{{ r.cname }}</span>{% else %}<span class=tag>Umumiy</span>{% endif %}</div><p class=mut>{{ r.info }}</p>{{ media(r.file) }}{% if r.link %}<a class=btn href="{{ r.link }}" target=_blank rel=noopener>🔗 Havola</a>{% endif %}
<small class=mut> · {{ name(r) if r.username else '' }} · {{ r.at }}</small>{% if r.user_id==me.id or allow('library_manage') %}<form method=post action="/library/del/{{ r.id }}" style="margin-top:8px">{{ csrf()|safe }}<button class=red>O'chirish</button></form>{% endif %}</div>{% else %}<div class=card>Hech narsa topilmadi</div>{% endfor %}"""),
'requests.html': P("""<h2>📥 Kursga yozilish so'rovlari</h2>{% for r in rows %}<div class=card><div class=row><div style="flex:1"><b>{{ name(r) }}</b> → <span class=tag>{{ r.cname }}</span><br><small class=mut>{{ r.at }}</small></div>
<form method=post action="/requests/{{ r.id }}/ok">{{ csrf()|safe }}<button>✅ Tasdiqlash</button></form><form method=post action="/requests/{{ r.id }}/no">{{ csrf()|safe }}<button class=red>❌ Rad etish</button></form></div></div>{% else %}<div class=card>Yangi so'rov yo'q</div>{% endfor %}"""),
'polls.html': P("""<h2>🗳 So'rovnomalar</h2>{% if allow('poll_create') %}<div class=card><h3>➕ Yangi so'rovnoma</h3><form method=post>{{ csrf()|safe }}<input name=question placeholder="Savol" required><textarea name=opts placeholder="Variantlar (har qatorda bittadan, kamida 2 ta)" required></textarea>
<select name=course><option value="">Hamma uchun</option>{% for c in courses %}<option value={{ c.id }}>{{ c.name }}</option>{% endfor %}</select><button class=wide>Joylash</button></form></div>{% endif %}
{% for r in rows %}<div class=card><div class=row><h3 style="margin:0;flex:1">{{ r.p.question }}</h3>{% if r.p.closed %}<span class="tag bad">Yopilgan</span>{% endif %}</div>
{% if r.mine or r.p.closed or allow('poll_create') %}{% for o in r.opts %}<div style="margin:8px 0"><div class=row><span style="flex:1">{{ o.text }}{{ ' ✔' if o.id==r.mine }}</span><b>{{ o.n }}</b></div><div class=bar><i style="width:{{ (o.n*100/r.total)|round|int if r.total else 0 }}%"></i></div></div>{% endfor %}<small class=mut>Jami ovoz: {{ r.total }}</small>
{% else %}<form method=post action="/polls/{{ r.p.id }}/vote">{{ csrf()|safe }}{% for o in r.opts %}<label class=opt><input type=radio name=opt value={{ o.id }} required> {{ o.text }}</label>{% endfor %}{% if allow('poll_vote') %}<button>Ovoz berish</button>{% endif %}</form>{% endif %}
{% if r.p.user_id==me.id or adm %}<div class=row style="margin-top:8px"><form method=post action="/polls/{{ r.p.id }}/close">{{ csrf()|safe }}<button class=gray>{{ 'Qayta ochish' if r.p.closed else 'Yopish' }}</button></form><form method=post action="/polls/{{ r.p.id }}/del" onsubmit='return confirm("O’chirilsinmi?")'>{{ csrf()|safe }}<button class=red>O'chirish</button></form></div>{% endif %}</div>{% else %}<div class=card>Hali so'rovnoma yo'q</div>{% endfor %}"""),
'challenges.html': P("""<h2>🎯 Haftalik vazifalar</h2>{% if allow('challenge_manage') %}<div class=card><h3>➕ Yangi vazifa</h3><form method=post>{{ csrf()|safe }}<input name=title placeholder="Vazifa nomi" required><textarea name=info placeholder="Tavsif"></textarea><div class=row><label>🎯 Ball <input type=number name=points value=10 min=1 max=1000></label><label>Tugash sanasi <input type=date name=ends></label></div><button class=wide>Joylash</button></form></div>
{% if pend %}<div class=card><h3>⏳ Tasdiqlanishi kutilmoqda ({{ pend|length }})</h3>{% for d in pend %}<div class=row style="padding:6px 0"><span style="flex:1"><b>{{ name(d) }}</b> — {{ d.title }} <small class=mut>(+{{ d.points }})</small></span><form method=post action="/challenges/{{ d.challenge_id }}/review/{{ d.student_id }}/ok">{{ csrf()|safe }}<button>✅</button></form><form method=post action="/challenges/{{ d.challenge_id }}/review/{{ d.student_id }}/no">{{ csrf()|safe }}<button class=red>❌</button></form></div>{% endfor %}</div>{% endif %}{% endif %}
<div class=grid>{% for c in rows %}<div class=card><h3>{{ c.title }}</h3><p class=mut>{{ c.info }}</p><span class=tag>🎯 +{{ c.points }} ball</span>{% if c.ends %}<span class="tag {{ 'bad' if c.ends<today else 'warn' }}">⏰ {{ c.ends }}</span>{% endif %}
{% if me.role=='student' %}{% set m=mine.get(c.id) %}{% if m and m.status=='done' %}<br><span class="status ok">✅ Tasdiqlangan</span>{% elif m and m.status=='pending' %}<br><span class="status warn">⏳ Tekshirilmoqda</span>{% elif m %}<br><span class="status bad">❌ Qabul qilinmadi</span>{% elif allow('challenge_claim') and not (c.ends and c.ends<today) %}<form method=post action="/challenges/{{ c.id }}/claim">{{ csrf()|safe }}<button class=wide>✔ Bajardim</button></form>{% endif %}{% endif %}</div>{% else %}<div class=card>Hali vazifa yo'q</div>{% endfor %}</div>"""),
'qr.html': P("""<h2>📲 QR bilan davomat — {{ c.name }}</h2><div class="card center"><p class=mut>O'quvchilar telefon kamerasi bilan skanerlaydi (hisobiga kirgan bo'lishi kerak). Kod 20 daqiqa amal qiladi.</p><div id=qr style="display:inline-block;padding:14px;background:#fff;border-radius:12px"></div>
<p><small class=mut style="word-break:break-all">{{ url }}</small></p><a class=btn href="/course/{{ c.id }}/qr">🔄 Yangi kod</a> <a class=btn href="/course/{{ c.id }}/attendance">📋 Davomat jadvali</a></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script><script>if(window.QRCode){new QRCode(document.getElementById('qr'),{text:"{{ url }}",width:260,height:260})}else{document.getElementById('qr').textContent='QR kutubxonasi yuklanmadi — havolani o\\'quvchilarga yuboring'}</script>"""),
'storage.html': P("""<h2>🗄 Xotira va fayllar</h2><div class=card><div class=row><h3 style="margin:0;flex:1">Jami: {{ (total/1048576)|round(1) }} MB / {{ (limit/1048576)|int }} MB</h3></div><div class=bar style="margin:8px 0"><i style="width:{{ [(total*100/limit)|round|int,100]|min }}%"></i></div>
<span class=tag>📎 Yuklamalar: {{ (up/1048576)|round(1) }} MB ({{ n }} ta)</span><span class=tag>🗃 Baza: {{ (db/1048576)|round(2) }} MB</span><span class=tag>💾 Zaxira: {{ (bk/1048576)|round(2) }} MB</span></div>
<div class=card><h3>🧹 Ortiqcha fayllar</h3><p>Hech qayerda ishlatilmayotgan fayllar: <b>{{ orphans|length }}</b> ta ({{ (osz/1048576)|round(2) }} MB)</p>{% if orphans %}<form method=post onsubmit='return confirm("Ortiqcha fayllar o’chirilsinmi?")'>{{ csrf()|safe }}<input type=hidden name=a value=clean><button class=red>Tozalash</button></form>{% endif %}</div>
<div class=card><h3>📦 Eng katta fayllar</h3><table>{% for f,sz,used in big %}<tr><td><a href="/static/uploads/{{ f }}" target=_blank>{{ f[:50] }}</a></td><td>{{ (sz/1048576)|round(2) }} MB</td><td>{{ 'ishlatilmoqda' if used else 'ortiqcha' }}</td></tr>{% endfor %}</table></div>
<div class=card><h3>💾 Avtomatik zaxira nusxalar (oxirgi 7 kun)</h3>{% for f,sz in bks %}<p><a href="/backups/{{ f }}">⬇ {{ f }}</a> <small class=mut>{{ (sz/1024)|int }} KB</small></p>{% else %}<p class=mut>Hali nusxa yo'q (har kuni birinchi kirishda olinadi)</p>{% endfor %}</div>"""),
})

app.jinja_loader = DictLoader(T)

CSS = """:root{--p:#6c5ce7;--p2:#a363ff;--bg:#f2f3fb;--card:#fff;--tx:#1d2136;--mut:#6a7190;--bd:#e5e7f4;--ok:#16a34a;--bad:#e5484d;--warn:#f59e0b;--sh:0 6px 24px rgba(60,50,140,.08)}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#10121c;--card:#1b1e2d;--tx:#e9ebf8;--mut:#98a0c2;--bd:#2a2e45;--sh:0 6px 24px #0006}}
*{box-sizing:border-box}body{margin:0;font-family:Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg) center/cover fixed;color:var(--tx);line-height:1.5}
a{color:var(--p)}.mut{color:var(--mut)}small{font-size:12.5px}h2{font-size:27px;margin:4px 0 14px;letter-spacing:-.4px}h3{margin:0 0 8px}hr{border:0;border-top:1px solid var(--bd);margin:16px 0}
body.app{display:flex;min-height:100vh}#mn{display:none}.wrap{flex:1;min-width:0}.top{display:none}
.side{width:252px;flex:none;background:linear-gradient(170deg,color-mix(in srgb,var(--p) 45%,#0b0a2a),var(--p) 60%,var(--p2));color:#fff;padding:18px 14px;display:flex;flex-direction:column;gap:10px;position:sticky;top:0;height:100vh;overflow:auto}
.logo{color:#fff;text-decoration:none;font-weight:800;font-size:20px;padding:6px 10px 12px}.side nav{display:flex;flex-direction:column;gap:3px;flex:1}
.side nav a{color:#ffffffd0;text-decoration:none;padding:10px 13px;border-radius:12px;font-weight:500;transition:.15s}.side nav a:hover{background:#ffffff22;color:#fff}.side nav a.on{background:#fff;color:#4a3bc4;font-weight:700}
.badge{background:#ff4d6d;color:#fff;border-radius:99px;padding:1px 7px;font-size:11px;margin-left:6px}
.usercard{display:flex;align-items:center;gap:10px;background:#ffffff22;border-radius:14px;padding:10px;color:#fff;text-decoration:none}.usercard small{display:block;opacity:.75}
.out{color:#fff;text-decoration:none;text-align:center;padding:9px;border-radius:12px;background:#0003}
main{max-width:1040px;margin:0 auto;padding:26px 22px 70px}main.g{max-width:430px;padding-top:9vh}
.card{display:block;background:var(--card);border:1px solid var(--bd);border-radius:18px;padding:18px;margin:14px 0;box-shadow:var(--sh);color:inherit;text-decoration:none;transition:.18s}
a.card:hover{transform:translateY(-3px);box-shadow:0 14px 34px rgba(60,50,140,.16)}.center{text-align:center}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}.grid .card{margin:0}
.cc{border-left:6px solid var(--c,var(--p))}.course{position:relative;overflow:hidden;padding-top:26px}.cbar{position:absolute;top:0;left:0;right:0;height:10px;background:linear-gradient(90deg,var(--c),color-mix(in srgb,var(--c) 50%,#fff))}
.hero{background:linear-gradient(135deg,var(--c,var(--p)),color-mix(in srgb,var(--c,var(--p)) 50%,#ff7ab8));color:#fff;border-radius:22px;padding:24px 26px;margin-bottom:16px;box-shadow:var(--sh)}.hero h2{margin:0;color:#fff}.hero p{margin:6px 0 0;opacity:.92}
.stat span{color:var(--mut);font-weight:600}.big{font-size:34px;font-weight:800;color:var(--p);line-height:1.2;margin:4px 0}.big small{font-size:15px;color:var(--mut);font-weight:500}
input,select,textarea,button{font:inherit;padding:10px 13px;border:1px solid var(--bd);border-radius:12px;margin:4px 0;max-width:100%;background:var(--card);color:var(--tx)}
input:not([type=checkbox]):not([type=color]),textarea{width:100%}textarea{min-height:92px}input:focus,select:focus,textarea:focus{outline:2px solid var(--p2);border-color:transparent}
input[type=checkbox]{accent-color:var(--p);width:18px;height:18px;vertical-align:middle;margin-right:6px}input[type=color]{width:54px;height:42px;padding:3px;flex:none}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.row>input:not([type=checkbox]):not([type=color]){width:auto;flex:1;min-width:130px}.row label{flex:1;min-width:150px}label{display:block}.opt{padding:10px 4px;font-weight:500}
button,.btn{background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:0;cursor:pointer;padding:10px 18px;border-radius:12px;text-decoration:none;display:inline-block;font-weight:600;transition:.15s}button:hover,.btn:hover{filter:brightness(1.08);transform:translateY(-1px)}
.red{background:var(--bad)}.gray{background:#8a90ad}.wide{width:100%;margin-top:8px}
.tag{display:inline-block;background:color-mix(in srgb,var(--p) 14%,transparent);color:var(--p);border-radius:99px;padding:2px 11px;font-size:12.5px;font-weight:600;margin:2px 4px 2px 0}.tag.light{background:#ffffff33;color:#fff}
.info{background:#e0e7ff;color:#3730a3}.ok{background:#dcfce7;color:#166534}.bad{background:#fee2e2;color:#991b1b}.warn{background:#fef3c7;color:#92400e}
.status{display:inline-block;padding:6px 14px;border-radius:99px;font-weight:700;font-size:14px}.note{padding:10px 14px;border-radius:12px;margin:10px 0}
.flash{padding:12px 16px;border-radius:14px;margin:8px 0;background:#fff3c4;color:#6b4e00;font-weight:500}.flash a{color:inherit}
.score{font-size:48px;font-weight:800;color:var(--ok);line-height:1}.score small{font-size:18px;color:var(--mut)}.ans{background:color-mix(in srgb,var(--p) 6%,transparent);border-radius:12px;padding:12px;margin:10px 0}
.av{width:38px;height:38px;border-radius:50%;object-fit:cover;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;font-weight:700;flex:none;vertical-align:middle}.av.lg{width:72px;height:72px;font-size:28px}.side .av{background:#ffffff40}
.podium{display:flex;gap:12px;align-items:flex-end;justify-content:center;margin:18px 0}.pod{flex:1;max-width:240px;text-align:center;background:var(--card);border:1px solid var(--bd);border-radius:22px;padding:18px;box-shadow:var(--sh)}
.p1{order:2;padding-top:30px;background:linear-gradient(180deg,#fff2c2,var(--card))}.p2{order:1}.p3{order:3}.meRow{background:color-mix(in srgb,var(--p) 12%,transparent)}.stars{color:#f5a623;letter-spacing:2px;font-size:18px}
table{width:100%;border-collapse:collapse}td{padding:10px 8px;border-bottom:1px solid var(--bd);vertical-align:middle}.chk{columns:2;margin:10px 0}
video,.pic{max-width:100%;border-radius:14px;margin:8px 0}audio{width:100%;margin:6px 0}
.toasts{position:fixed;top:14px;right:14px;z-index:99;display:flex;flex-direction:column;gap:8px;max-width:min(380px,92vw)}
.toast{background:#1d2136;color:#fff;padding:13px 18px;border-radius:14px;box-shadow:0 10px 30px #0005;cursor:pointer;animation:tt 6s forwards}@keyframes tt{0%{opacity:0;transform:translateY(-14px)}6%,88%{opacity:1;transform:none}100%{opacity:0;visibility:hidden}}
@media(max-width:860px){body.app{display:block}.side{position:fixed;left:-280px;top:0;z-index:50;width:262px;transition:.25s}#mn:checked~.side{left:0}#mn:checked~.wrap::before{content:"";position:fixed;inset:0;background:#0007;z-index:40}
.top{display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:20;background:var(--card);padding:11px 14px;border-bottom:1px solid var(--bd)}.burger{font-size:26px;cursor:pointer}main{padding:16px 14px 70px}.chk{columns:1}
.podium{flex-direction:column;align-items:stretch}.p1,.p2,.p3{order:0;max-width:none}}
.sq{margin:0 0 6px}.sq input{background:#ffffff26;border:0;color:#fff;margin:0}.sq input::placeholder{color:#ffffffb0}
.lang{display:flex;gap:6px;justify-content:center}.lang a{color:#fff;text-decoration:none;font-size:12px;padding:3px 9px;border-radius:8px;background:#ffffff26}.guestlang{margin-top:16px}.guestlang a{background:var(--card);color:var(--p);border:1px solid var(--bd)}
input[type=radio]{width:auto!important;margin-right:6px}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}.cal .h{text-align:center;font-weight:700;color:var(--mut)}.cal .d{background:var(--card);border:1px solid var(--bd);border-radius:12px;min-height:92px;padding:6px;font-size:12px;overflow:hidden}
.cal .d.today{outline:2px solid var(--p)}.cal .d.off{opacity:.3}.chip{display:block;border-radius:8px;padding:2px 6px;margin-top:3px;background:color-mix(in srgb,var(--p) 14%,transparent);color:var(--p);font-weight:600;text-decoration:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.chip.dl{background:#fee2e2;color:#991b1b}
.msg{width:fit-content;max-width:82%;padding:9px 14px;border-radius:16px;margin:6px 0;background:var(--card);border:1px solid var(--bd)}.msg.me{margin-left:auto;background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border:0}.msg small{opacity:.7;display:block}
.bar{height:10px;border-radius:99px;background:var(--bd);overflow:hidden}.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--p),var(--p2))}
th{padding:8px;text-align:left;color:var(--mut);font-size:13px}
:root[data-theme=dark]{--bg:#10121c;--card:#1b1e2d;--tx:#e9ebf8;--mut:#98a0c2;--bd:#2a2e45;--sh:0 6px 24px #0006}
:root[data-theme=light]{--bg:#f2f3fb;--card:#fff;--tx:#1d2136;--mut:#6a7190;--bd:#e5e7f4}
:root[data-accent=blue]{--p:#2f80ed;--p2:#56ccf2}:root[data-accent=green]{--p:#16a34a;--p2:#4ade80}:root[data-accent=pink]{--p:#e11d74;--p2:#fb7185}:root[data-accent=orange]{--p:#f97316;--p2:#fbbf24}
.gh{background:color-mix(in srgb,var(--p) 10%,transparent);font-weight:700;color:var(--p);padding:10px}
@media(max-width:700px){.cal .d{min-height:58px;font-size:10px}}"""

os.makedirs(os.path.join(B, 'static'), exist_ok=True)
open(os.path.join(B, 'static', 'style.css'), 'w').write(CSS)

if __name__ == '__main__': app.run(debug=True)
