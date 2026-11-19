"""US-05: business rewards and auditable points ledger (stdlib + Flask)."""
import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
from flask import render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

DB = os.path.join('instance', 'cleanup.db')
ATTENDANCE_POINTS = 100
MONTHLY_BONUS = 150  # Awarded once for every three distinct events in a calendar month
EXTRA_POINTS = 50


def db():
    c = sqlite3.connect(DB, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c


def init_rewards():
    os.makedirs('instance', exist_ok=True)
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS businesses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            approved INTEGER NOT NULL DEFAULT 0 CHECK(approved IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL REFERENCES businesses(id),
            title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
            cost INTEGER NOT NULL CHECK(cost>0),
            stock INTEGER NOT NULL CHECK(stock>=0),
            active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS point_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount INTEGER NOT NULL CHECK(amount != 0),
            reason TEXT NOT NULL,
            registration_id INTEGER,
            event_month TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_points_user ON point_transactions(user_id);
        CREATE INDEX IF NOT EXISTS idx_points_registration ON point_transactions(registration_id);
        CREATE TABLE IF NOT EXISTS redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            reward_id INTEGER NOT NULL REFERENCES rewards(id),
            points_spent INTEGER NOT NULL CHECK(points_spent>0),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        ''')


def points_balance(connection=None, user_id=None):
    if user_id is None:
        return 0
    own = connection is None
    c = connection if connection is not None else db()
    try:
        return int(c.execute('SELECT COALESCE(SUM(amount),0) FROM point_transactions WHERE user_id=?', (user_id,)).fetchone()[0])
    finally:
        if own:
            c.close()


def record_attendance_points(c, user_id, registration_id, attended):
    # Called only when attendance actually changes, inside the same transaction.
    net = c.execute('''SELECT COALESCE(SUM(amount),0) FROM point_transactions
                       WHERE user_id=? AND registration_id=? AND reason IN ('attendance','attendance_reversed')''',
                    (user_id, registration_id)).fetchone()[0]
    desired = ATTENDANCE_POINTS if attended else 0
    difference = desired - net
    if difference:
        c.execute('INSERT INTO point_transactions(user_id,amount,reason,registration_id) VALUES(?,?,?,?)',
                  (user_id, difference, 'attendance' if difference>0 else 'attendance_reversed', registration_id))
    if not attended:
        extra_net = c.execute("""SELECT COALESCE(SUM(amount),0) FROM point_transactions
            WHERE user_id=? AND registration_id=? AND reason IN ('extra_effort','extra_effort_reversed')""",
            (user_id, registration_id)).fetchone()[0]
        if extra_net > 0:
            c.execute('INSERT INTO point_transactions(user_id,amount,reason,registration_id) VALUES(?,?,?,?)',
                      (user_id, -extra_net, 'extra_effort_reversed', registration_id))


def reconcile_monthly_bonus(c, user_id, month):
    # Exactly one +150 bonus per three distinct confirmed events in a month.
    count = c.execute('''SELECT COUNT(DISTINCT r.event_id) FROM registrations r
        JOIN events e ON e.id=r.event_id
        WHERE r.user_id=? AND r.attended=1 AND substr(e.date,1,7)=?''', (user_id, month)).fetchone()[0]
    desired = (count // 3) * MONTHLY_BONUS
    current = c.execute('''SELECT COALESCE(SUM(amount),0) FROM point_transactions
        WHERE user_id=? AND reason IN ('monthly_bonus','monthly_bonus_reversed') AND event_month=?''',
        (user_id, month)).fetchone()[0]
    if desired != current:
        difference = desired-current
        c.execute('INSERT INTO point_transactions(user_id,amount,reason,event_month) VALUES(?,?,?,?)',
                  (user_id, difference, 'monthly_bonus' if difference>0 else 'monthly_bonus_reversed', month))


def csrf():
    if 'rewards_csrf' not in session:
        session['rewards_csrf'] = secrets.token_urlsafe(32)
    return session['rewards_csrf']


def verify_csrf():
    if not secrets.compare_digest(request.form.get('csrf_token',''), csrf()):
        abort(400, 'Invalid form token. Refresh the page and try again.')


def participant_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('participant_id'):
            return redirect(url_for('participant_login'))
        return f(*args, **kwargs)
    return wrapped


def business_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('business_id'):
            return redirect(url_for('business_login'))
        return f(*args, **kwargs)
    return wrapped


def register_reward_routes(app):
    @app.route('/rewards')
    def rewards_shop():
        c=db()
        rewards=c.execute('''SELECT r.*,b.name AS business_name FROM rewards r JOIN businesses b ON b.id=r.business_id
            WHERE r.active=1 AND b.approved=1 ORDER BY r.id DESC''').fetchall()
        uid=session.get('participant_id')
        balance=points_balance(c,uid) if uid else None
        history=c.execute('''SELECT x.created_at,x.points_spent,r.title FROM redemptions x JOIN rewards r ON r.id=x.reward_id
            WHERE x.user_id=? ORDER BY x.id DESC LIMIT 20''',(uid,)).fetchall() if uid else []
        c.close()
        return render_template('rewards.html', rewards=rewards,balance=balance,history=history,csrf_token=csrf())

    @app.route('/rewards/<int:reward_id>/redeem',methods=['POST'])
    @participant_required
    def redeem_reward(reward_id):
        verify_csrf()
        uid=session['participant_id']; c=db()
        try:
            c.execute('BEGIN IMMEDIATE')
            reward=c.execute('''SELECT r.id,r.cost,r.stock FROM rewards r JOIN businesses b ON b.id=r.business_id
                WHERE r.id=? AND r.active=1 AND b.approved=1''',(reward_id,)).fetchone()
            if not reward or reward['stock']<1:
                flash('This reward is unavailable.'); return redirect(url_for('rewards_shop'))
            if points_balance(c,uid)<reward['cost']:
                flash('You do not have enough points yet.'); return redirect(url_for('rewards_shop'))
            c.execute('UPDATE rewards SET stock=stock-1 WHERE id=? AND stock>0',(reward_id,))
            c.execute('INSERT INTO redemptions(user_id,reward_id,points_spent) VALUES(?,?,?)',(uid,reward_id,reward['cost']))
            c.execute('INSERT INTO point_transactions(user_id,amount,reason) VALUES(?,?,?)',(uid,-reward['cost'],'redemption'))
            c.commit(); flash('Reward redeemed! Show your redemption history to the business to arrange collection.')
        except sqlite3.Error:
            c.rollback(); app.logger.exception('Reward redemption failed'); abort(500)
        finally:
            c.close()
        return redirect(url_for('rewards_shop'))

    @app.route('/business/register',methods=['GET','POST'])
    def business_register():
        error=None
        if request.method=='POST':
            verify_csrf()
            name=request.form.get('name','').strip(); email=request.form.get('email','').strip().lower()
            password=request.form.get('password','')
            if not name or '@' not in email or len(password)<8:
                error='Enter a business name, valid email and password of at least 8 characters.'
            else:
                c=db()
                try:
                    c.execute('INSERT INTO businesses(name,email,password_hash) VALUES(?,?,?)',(name,email,generate_password_hash(password)))
                    c.commit(); flash('Account created. An administrator must approve your business before rewards go live.')
                    return redirect(url_for('business_login'))
                except sqlite3.IntegrityError:
                    error='That email is already registered.'
                finally:
                    c.close()
        return render_template('business_auth.html',mode='register',error=error,csrf_token=csrf())

    @app.route('/business/login',methods=['GET','POST'])
    def business_login():
        error=None
        if request.method=='POST':
            verify_csrf()
            email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
            c=db(); business=c.execute('SELECT * FROM businesses WHERE email=?',(email,)).fetchone(); c.close()
            if business is None or not check_password_hash(business['password_hash'],password):
                error='Incorrect email or password.'
            else:
                session.clear();session['business_id']=business['id'];return redirect(url_for('business_dashboard'))
        return render_template('business_auth.html',mode='login',error=error,csrf_token=csrf())

    @app.route('/business/logout',methods=['POST'])
    @business_required
    def business_logout():
        verify_csrf();session.clear();return redirect(url_for('home'))

    @app.route('/business/dashboard',methods=['GET','POST'])
    @business_required
    def business_dashboard():
        c=db(); business=c.execute('SELECT * FROM businesses WHERE id=?',(session['business_id'],)).fetchone()
        if not business:
            c.close();session.clear();return redirect(url_for('business_login'))
        error=None
        if request.method=='POST':
            verify_csrf()
            if not business['approved']:
                c.close();abort(403,'Business approval required.')
            action=request.form.get('action')
            if action=='create':
                title=request.form.get('title','').strip();description=request.form.get('description','').strip()
                try:
                    cost=int(request.form.get('cost',''));stock=int(request.form.get('stock',''))
                except ValueError:
                    cost=0;stock=-1
                if not title or cost<1 or stock<0:
                    error='Enter a title, positive point cost and stock of zero or more.'
                else:
                    c.execute('INSERT INTO rewards(business_id,title,description,cost,stock) VALUES(?,?,?,?,?)',
                              (business['id'],title,description,cost,stock));c.commit()
                    return redirect(url_for('business_dashboard'))
            elif action=='update':
                try:
                    reward_id=int(request.form.get('reward_id',''));stock=int(request.form.get('stock',''))
                except ValueError:
                    reward_id=0;stock=-1
                if stock<0:
                    error='Stock must be zero or more.'
                else:
                    c.execute('UPDATE rewards SET stock=?,active=? WHERE id=? AND business_id=?',
                              (stock,1 if request.form.get('active')=='on' else 0,reward_id,business['id']))
                    c.commit();return redirect(url_for('business_dashboard'))
        rewards=c.execute('SELECT * FROM rewards WHERE business_id=? ORDER BY id DESC',(business['id'],)).fetchall()
        claims=c.execute('''SELECT x.id,x.created_at,x.points_spent,r.title,u.name AS participant_name
            FROM redemptions x JOIN rewards r ON r.id=x.reward_id JOIN users u ON u.id=x.user_id
            WHERE r.business_id=? ORDER BY x.id DESC''',(business['id'],)).fetchall() if business['approved'] else []
        c.close()
        return render_template('business_dashboard.html',business=business,rewards=rewards,claims=claims,error=error,csrf_token=csrf())

    @app.route('/organiser/extra-points',methods=['POST'])
    def award_extra_points():
        oid=session.get('organiser_id')
        if not oid:return redirect(url_for('organiser_login'))
        verify_csrf()
        try: rid=int(request.form.get('registration_id',''))
        except ValueError:abort(400)
        c=db()
        try:
            c.execute('BEGIN IMMEDIATE')
            organiser=c.execute("SELECT is_admin FROM users WHERE id=? AND role='organiser' AND approved=1",(oid,)).fetchone()
            if not organiser:abort(403)
            registration=c.execute('''SELECT r.id,r.user_id,r.attended,e.organiser_id FROM registrations r
                JOIN events e ON e.id=r.event_id WHERE r.id=?''',(rid,)).fetchone()
            if not registration or not registration['attended'] or not registration['user_id'] or (registration['organiser_id']!=oid and not organiser['is_admin']):
                abort(403)
            existing=c.execute("""SELECT COALESCE(SUM(amount),0) FROM point_transactions
                WHERE registration_id=? AND reason IN ('extra_effort','extra_effort_reversed')""",(rid,)).fetchone()[0]
            if existing > 0:
                flash('Extra effort points were already awarded for this registration.')
            else:
                c.execute('INSERT INTO point_transactions(user_id,amount,reason,registration_id) VALUES(?,?,?,?)',
                          (registration['user_id'],EXTRA_POINTS,'extra_effort',rid))
                c.commit();flash('50 extra effort points awarded.')
        finally:c.close()
        return redirect(url_for('organiser_attendance'))
