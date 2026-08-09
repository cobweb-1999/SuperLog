import base64
import datetime as dt
import hashlib
import hmac
import html
import json
import os
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import main as core


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STYLE_PATH = os.path.join(BASE_DIR, 'static', 'style.css')
AUTH_STORE_PATH = os.path.join(BASE_DIR, 'users.json')
DATA_DIR = os.path.join(BASE_DIR, 'data')
SECRET_KEY = os.environ.get('SUPERLOG_SECRET_KEY', 'change-me-in-production')
SESSION_COOKIE_NAME = 'superlog_session'
CSRF_COOKIE_NAME = 'superlog_csrf'
SESSION_TTL_SECONDS = 60 * 60 * 8


class AuthStore:
    def __init__(self, path=None):
        self.path = path or AUTH_STORE_PATH
        self.users = self._load()

    def _load(self):
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return {}

        if isinstance(data, dict):
            return data

        users = {}
        for item in data:
            username = item.get('username')
            if username:
                users[username] = item
        return users

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as fh:
            json.dump(list(self.users.values()), fh, indent=2)

    def _hash_password(self, password):
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200000)
        return {
            'salt': base64.b64encode(salt).decode('ascii'),
            'hash': base64.b64encode(digest).decode('ascii'),
            'iterations': 200000,
        }

    def _verify_password(self, password, stored):
        try:
            salt = base64.b64decode(stored['salt'].encode('ascii'))
            digest = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                int(stored.get('iterations', 200000)),
            )
            return hmac.compare_digest(base64.b64encode(digest).decode('ascii'), stored['hash'])
        except Exception:
            return False

    def create_user(self, username, password):
        username = username.strip().lower()
        if not username:
            raise ValueError('Username is required.')
        if username in self.users:
            raise ValueError('That username already exists.')
        self.users[username] = {
            'username': username,
            'password': self._hash_password(password),
            'created_at': dt.datetime.utcnow().isoformat(),
        }
        self._save()
        return self.users[username]

    def authenticate(self, username, password):
        username = username.strip().lower()
        user = self.users.get(username)
        if not user:
            return None
        if self._verify_password(password, user['password']):
            return user
        return None


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _unb64url(value):
    if not value:
        return b''
    padding = '=' * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode('ascii'))


def _sign_payload(payload):
    payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')
    signature = hmac.new(SECRET_KEY.encode('utf-8'), payload_json, hashlib.sha256).digest()
    return f'{_b64url(payload_json)}.{_b64url(signature)}'


def _verify_signed_payload(token):
    try:
        payload_b64, sig_b64 = token.split('.', 1)
        payload_json = _unb64url(payload_b64)
        expected_sig = _unb64url(sig_b64)
        actual_sig = hmac.new(SECRET_KEY.encode('utf-8'), payload_json, hashlib.sha256).digest()
        if not hmac.compare_digest(actual_sig, expected_sig):
            return None
        return json.loads(payload_json.decode('utf-8'))
    except Exception:
        return None


def _make_session_token(username, csrf_token):
    return _sign_payload({
        'username': username,
        'csrf_token': csrf_token,
        'exp': int(dt.datetime.now().timestamp()) + SESSION_TTL_SECONDS,
    })


def _parse_session_token(token):
    return _verify_signed_payload(token)


def _user_data_dir(username):
    safe_name = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in username)
    path = os.path.join(DATA_DIR, safe_name)
    os.makedirs(path, exist_ok=True)
    return path


def _user_session_paths(username):
    base_dir = _user_data_dir(username)
    return (
        os.path.join(base_dir, 'work_sessions.json'),
        os.path.join(base_dir, 'supervision_sessions.json'),
    )


def _load_user_sessions(username):
    work_path, supervision_path = _user_session_paths(username)
    work_sessions = []
    supervision_sessions = []

    if os.path.exists(work_path):
        try:
            with open(work_path, 'r', encoding='utf-8') as fh:
                work_sessions = [core.dict_to_work_session(item) for item in json.load(fh)]
        except Exception:
            work_sessions = []

    if os.path.exists(supervision_path):
        try:
            with open(supervision_path, 'r', encoding='utf-8') as fh:
                supervision_sessions = [core.dict_to_supervision_session(item) for item in json.load(fh)]
        except Exception:
            supervision_sessions = []

    return work_sessions, supervision_sessions


def _save_user_sessions(username, work_sessions, supervision_sessions):
    work_path, supervision_path = _user_session_paths(username)
    with open(work_path, 'w', encoding='utf-8') as fh:
        json.dump([core.work_session_to_dict(item) for item in work_sessions], fh, indent=2)
    with open(supervision_path, 'w', encoding='utf-8') as fh:
        json.dump([core.supervision_session_to_dict(item) for item in supervision_sessions], fh, indent=2)


def _load_css():
    try:
        with open(STYLE_PATH, 'r', encoding='utf-8') as fh:
            return fh.read()
    except FileNotFoundError:
        return 'body{font-family:sans-serif;margin:2rem;}'


CSS_TEXT = _load_css()


def _escape(value):
    return html.escape(str(value), quote=True)


def _month_name(year, month):
    return dt.date(year, month, 1).strftime('%B %Y')


def _parse_int(values, key, fallback):
    try:
        return int(values.get(key, [fallback])[0])
    except (TypeError, ValueError, IndexError):
        return fallback


def _parse_month_year(query, fallback_year, fallback_month):
    year = _parse_int(query, 'year', fallback_year)
    month = _parse_int(query, 'month', fallback_month)
    if month < 1 or month > 12:
        month = fallback_month
    return year, month


def _parse_index(query, fallback=None):
    try:
        return int(query.get('index', [fallback])[0])
    except (TypeError, ValueError, IndexError):
        return fallback


def _parse_datetime_field(form, field_name):
    raw_value = form.get(field_name, [''])[0].strip()
    if not raw_value:
        raise ValueError(f'{field_name} is required')
    return dt.datetime.fromisoformat(raw_value)


def _parse_form_data(body):
    raw_body = body.decode('utf-8') if body else ''
    if not raw_body:
        return {}
    return {key: values for key, values in parse_qs(raw_body, keep_blank_values=True).items()}


def _current_month_filtered(session_list, year, month):
    return [item for item in session_list if item.start_time.year == year and item.start_time.month == month]


def _current_month_indexed(session_list, year, month):
    return [
        (index, session)
        for index, session in enumerate(session_list)
        if session.start_time.year == year and session.start_time.month == month
    ]


def _nav_html(current_user=None):
    auth_link = (
        f'<a href="/logout">Logout ({_escape(current_user["username"])})</a>'
        if current_user
        else '<a href="/login">Login</a>'
    )
    return f'''
      <nav class="nav-links">
        <a href="/">Dashboard</a>
        <a href="/work/new">Log Work</a>
        <a href="/supervision/new">Log Supervision</a>
        <a href="/reports/month">Month</a>
        <a href="/reports/year">Year</a>
        {auth_link}
      </nav>
    '''


def _page_shell(title, body_html, current_user=None):
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)}</title>
  <style>{CSS_TEXT}</style>
</head>
<body>
  <div class="page-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">RBT supervision tracker</p>
        <h1>SuperLog</h1>
      </div>
      {_nav_html(current_user)}
    </header>
    {body_html}
  </div>
</body>
</html>'''


def _message_html(message):
    if not message:
        return ''
    return f'<section class="flash-stack"><div class="flash-message">{_escape(message)}</div></section>'


def _metric_card(label, value, state_class=''):
    class_attr = f' metric {state_class}'.strip()
    return f'''<article class="card {class_attr}"><span>{_escape(label)}</span><strong>{_escape(value)}</strong></article>'''


def _render_session_rows(indexed_sessions, session_type='work', include_actions=False, csrf_token=''):
    rows = []
    for index, session in indexed_sessions:
        if session_type == 'work':
            cells = [
                f'<td>{_escape(session.start_time.strftime("%Y-%m-%d %H:%M"))}</td>',
                f'<td>{_escape(session.end_time.strftime("%Y-%m-%d %H:%M"))}</td>',
            ]
        else:
            cells = [
                f'<td>{_escape(session.start_time.strftime("%Y-%m-%d %H:%M"))}</td>',
                f'<td>{_escape(session.session_type.name)}</td>',
                f'<td>{_escape(session.format.name)} / {"Yes" if session.is_direct_observation else "No"}</td>',
            ]

        if include_actions:
            edit_href = f'/{session_type}/edit?index={index}'
            delete_action = f'/{session_type}/delete?index={index}'
            cells.append(
                '<td class="table-actions">'
                f'<a class="button secondary" href="{_escape(edit_href)}">Edit</a>'
                f'<form method="post" action="{_escape(delete_action)}" class="inline-action-form" onsubmit="return confirm(\'Delete this session?\');">'
                f'<input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">'
                '<button type="submit" class="danger">Delete</button>'
                '</form>'
                '</td>'
            )

        rows.append('<tr>' + ''.join(cells) + '</tr>')
    return ''.join(rows)


def _render_login_page(message='', next_path='/'):
    body_html = f'''
    {_message_html(message)}
    <section class="card form-card">
      <p class="eyebrow">Authentication</p>
      <h2>Sign in</h2>
      <p class="muted">Use your company account to continue.</p>
      <form method="post" action="/login" class="stack-form">
        <input type="hidden" name="next" value="{_escape(next_path)}">
        <label>Username<input type="text" name="username" required></label>
        <label>Password<input type="password" name="password" required></label>
        <button type="submit">Sign in</button>
      </form>
      <p class="muted" style="margin-top: 12px;">No account yet? <a href="/register">Create one</a>.</p>
    </section>
    '''
    return _page_shell('Sign in', body_html)


def _render_register_page(message=''):
    body_html = f'''
    {_message_html(message)}
    <section class="card form-card">
      <p class="eyebrow">Authentication</p>
      <h2>Create account</h2>
      <p class="muted">Create the first account to start using SuperLog.</p>
      <form method="post" action="/register" class="stack-form">
        <label>Username<input type="text" name="username" required></label>
        <label>Password<input type="password" name="password" required></label>
        <button type="submit">Create account</button>
      </form>
      <p class="muted" style="margin-top: 12px;">Already have an account? <a href="/login">Sign in</a>.</p>
    </section>
    '''
    return _page_shell('Create account', body_html)


def _session_form_values(session, kind):
    values = {
        'start_time': session.start_time.strftime('%Y-%m-%dT%H:%M'),
        'end_time': session.end_time.strftime('%Y-%m-%dT%H:%M'),
    }
    if kind == 'supervision':
        values.update({
            'observation_format': str(session.format.value),
            'session_type': str(session.session_type.value),
            'direct_observation': 'checked' if session.is_direct_observation else '',
        })
    return values


def _get_session_by_index(session_list, index):
    if index is None or index < 0 or index >= len(session_list):
        raise IndexError('Session not found.')
    return session_list[index]


def _render_form(kind, message='', values=None, action_path=None, submit_label='Save session', title=None, csrf_token='', current_user=None):
    values = values or {}
    start_time = values.get('start_time', '')
    end_time = values.get('end_time', '')
    observation_format = values.get('observation_format', '')
    session_type = values.get('session_type', '')
    direct_checked = 'checked' if values.get('direct_observation') else ''
    action_path = action_path or ('/work/new' if kind == 'work' else '/supervision/new')

    if kind == 'work':
        extra_fields = ''
        title = title or 'Log Work Session'
    else:
        extra_fields = f'''
        <label>
          Observation format
          <select name="observation_format" required>
            <option value="">Choose one</option>
            <option value="1" {'selected' if observation_format == '1' else ''}>In person</option>
            <option value="0" {'selected' if observation_format == '0' else ''}>Remote</option>
          </select>
        </label>
        <label>
          Session type
          <select name="session_type" required>
            <option value="">Choose one</option>
            <option value="1" {'selected' if session_type == '1' else ''}>Individual</option>
            <option value="0" {'selected' if session_type == '0' else ''}>Group</option>
          </select>
        </label>
        <label class="checkbox-row">
          <input type="checkbox" name="direct_observation" {direct_checked}>
          Direct observation included
        </label>
        '''
        title = title or 'Log Supervision Session'

    body_html = f'''
    {_message_html(message)}
    <section class="card form-card">
      <p class="eyebrow">Browser entry form</p>
      <h2>{_escape(title)}</h2>
      <p class="muted">Use a phone or desktop browser to add sessions directly.</p>
      <form method="post" action="{_escape(action_path)}" class="stack-form">
        <input type="hidden" name="csrf_token" value="{_escape(csrf_token)}">
        <label>
          Start time
          <input type="datetime-local" name="start_time" value="{_escape(start_time)}" required>
        </label>
        <label>
          End time
          <input type="datetime-local" name="end_time" value="{_escape(end_time)}" required>
        </label>
        {extra_fields}
        <button type="submit">{_escape(submit_label)}</button>
      </form>
    </section>
    '''
    return _page_shell(title, body_html, current_user)


def _render_dashboard(year, month, message='', current_user=None, csrf_token=''):
    report = core.generate_compliance_report(core.sessions, core.supervision_sessions, year, month)
    month_label = _month_name(year, month)
    work_rows = _render_session_rows(_current_month_indexed(core.sessions, year, month), 'work', True, csrf_token)
    supervision_rows = _render_session_rows(_current_month_indexed(core.supervision_sessions, year, month), 'supervision', True, csrf_token)

    body_html = f'''
    {_message_html(message)}
    <section class="hero card">
      <div>
        <p class="eyebrow">Current month</p>
        <h2>{_escape(month_label)}</h2>
        <p class="muted">Track sessions, check compliance, and review what still needs to be logged.</p>
      </div>
      <form class="inline-form" method="get" action="/">
        <label>Year<input type="number" name="year" value="{year}" min="2000" max="2100"></label>
        <label>Month<input type="number" name="month" value="{month}" min="1" max="12"></label>
        <button type="submit">View</button>
      </form>
    </section>

    <section class="grid cards-4">
      {_metric_card('Work hours', f"{report['work_hours']:.2f}")}
      {_metric_card('Supervision hours', f"{report['supervised_hours']:.2f}")}
      {_metric_card('5% rule', 'Compliant' if report['is_compliant'] else 'Not compliant', 'good' if report['is_compliant'] else 'warn')}
      {_metric_card('Hours still needed', f"{report['hours_still_needed']:.2f}")}
    </section>

    <section class="grid two-up">
      <article class="card">
        <h3>Quick actions</h3>
        <div class="button-row">
          <a class="button" href="/work/new">Log work session</a>
          <a class="button" href="/supervision/new">Log supervision session</a>
          <a class="button secondary" href="/reports/month?year={year}&month={month}">Open month report</a>
        </div>
      </article>

      <article class="card">
        <h3>Compliance checks</h3>
        <ul class="checklist">
          <li>{'Yes' if report['has_individual'] else 'No'} individual session recorded</li>
          <li>{'Yes' if report['has_direct_observation'] else 'No'} direct observation recorded</li>
          <li>{report['percent_achieved']:.2f}% of the monthly requirement met</li>
        </ul>
      </article>
    </section>

    <section class="grid two-up">
      <article class="card">
        <h3>Work sessions</h3>
        {f'<div class="table-wrap"><table><thead><tr><th>Start</th><th>End</th><th>Actions</th></tr></thead><tbody>{work_rows}</tbody></table></div>' if work_rows else '<p class="muted">No work sessions in this month yet.</p>'}
      </article>

      <article class="card">
        <h3>Supervision sessions</h3>
        {f'<div class="table-wrap"><table><thead><tr><th>Start</th><th>Type</th><th>Observation</th><th>Actions</th></tr></thead><tbody>{supervision_rows}</tbody></table></div>' if supervision_rows else '<p class="muted">No supervision sessions in this month yet.</p>'}
      </article>
    </section>
    '''

    return _page_shell('SuperLog Dashboard', body_html, current_user)


def _render_month_report(year, month, message='', current_user=None, csrf_token=''):
    report = core.generate_compliance_report(core.sessions, core.supervision_sessions, year, month)
    month_label = _month_name(year, month)
    work_rows = _render_session_rows(_current_month_indexed(core.sessions, year, month), 'work', True, csrf_token)
    supervision_rows = _render_session_rows(_current_month_indexed(core.supervision_sessions, year, month), 'supervision', True, csrf_token)

    body_html = f'''
    {_message_html(message)}
    <section class="card">
      <p class="eyebrow">Monthly report</p>
      <h2>{_escape(month_label)}</h2>
      <p class="muted">Compliance is based on the saved JSON data in your private folder.</p>
    </section>

    <section class="grid cards-4">
      {_metric_card('Worked hours', f"{report['work_hours']:.2f}")}
      {_metric_card('Supervised hours', f"{report['supervised_hours']:.2f}")}
      {_metric_card('5% rule', 'Met' if report['is_compliant'] else 'Not met', 'good' if report['is_compliant'] else 'warn')}
      {_metric_card('Remaining hours', f"{report['hours_still_needed']:.2f}")}
    </section>

    <section class="grid two-up">
      <article class="card">
        <h3>Work sessions</h3>
        {f'<div class="table-wrap"><table><thead><tr><th>Start</th><th>End</th><th>Actions</th></tr></thead><tbody>{work_rows}</tbody></table></div>' if work_rows else '<p class="muted">No work sessions found.</p>'}
      </article>

      <article class="card">
        <h3>Supervision sessions</h3>
        {f'<div class="table-wrap"><table><thead><tr><th>Start</th><th>Type</th><th>Observation</th><th>Actions</th></tr></thead><tbody>{supervision_rows}</tbody></table></div>' if supervision_rows else '<p class="muted">No supervision sessions found.</p>'}
      </article>
    </section>
    '''
    return _page_shell('Monthly Report', body_html, current_user)


def _render_year_report(year, message='', current_user=None):
    rows_html = []
    for month in range(1, 13):
        report = core.generate_compliance_report(core.sessions, core.supervision_sessions, year, month)
        if report['work_hours'] > 0 or report['supervised_hours'] > 0:
            rows_html.append(
                '<tr>'
                f'<td>{_escape(dt.date(year, month, 1).strftime("%B"))}</td>'
                f'<td>{report["work_hours"]:.2f}</td>'
                f'<td>{report["supervised_hours"]:.2f}</td>'
                f'<td>{"Yes" if report["is_compliant"] else "No"}</td>'
                f'<td>{"Yes" if report["has_individual"] else "No"}</td>'
                f'<td>{"Yes" if report["has_direct_observation"] else "No"}</td>'
                '</tr>'
            )

    body_html = f'''
    {_message_html(message)}
    <section class="card">
      <p class="eyebrow">Year summary</p>
      <h2>{year}</h2>
      <p class="muted">Only months with logged activity are shown here.</p>
    </section>

    <section class="card">
      {('<div class="table-wrap"><table><thead><tr><th>Month</th><th>Work hours</th><th>Supervision hours</th><th>Compliant</th><th>Individual</th><th>Direct obs</th></tr></thead><tbody>' + ''.join(rows_html) + '</tbody></table></div>') if rows_html else '<p class="muted">No activity found for this year.</p>'}
    </section>
    '''
    return _page_shell('Year Summary', body_html, current_user)


class SuperLogHandler(BaseHTTPRequestHandler):
    server_version = 'SuperLogHTTP/1.0'

    def _send_html(self, html_text, status=HTTPStatus.OK, extra_headers=None):
        encoded = html_text.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        for header_name, header_value in (extra_headers or []):
            self.send_header(header_name, header_value)
        self.end_headers()
        self.wfile.write(encoded)

    def _send_css(self):
        encoded = CSS_TEXT.encode('utf-8')
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'text/css; charset=utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _redirect(self, location, extra_headers=None):
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header('Location', location)
        for header_name, header_value in (extra_headers or []):
            self.send_header(header_name, header_value)
        self.end_headers()

    def _get_cookie(self, name):
        cookie_header = self.headers.get('Cookie', '')
        for part in cookie_header.split(';'):
            if '=' in part:
                key, value = part.split('=', 1)
                if key.strip() == name:
                    return value.strip()
        return None

    def _set_cookie(self, name, value, max_age=None):
        cookie = f'{name}={value}; Path=/; HttpOnly; SameSite=Lax'
        if max_age is not None:
            cookie += f'; Max-Age={max_age}'
        return ('Set-Cookie', cookie)

    def _get_current_user(self, auth_store):
        token = self._get_cookie(SESSION_COOKIE_NAME)
        if not token:
            return None
        payload = _parse_session_token(token)
        if not payload:
            return None
        if payload.get('exp', 0) < int(dt.datetime.now().timestamp()):
            return None
        username = payload.get('username')
        if not username or username not in auth_store.users:
            return None
        return {'username': username}

    def _get_or_create_csrf_token(self):
        token = self._get_cookie(CSRF_COOKIE_NAME)
        if token:
            return token, []
        token = secrets.token_urlsafe(24)
        return token, [self._set_cookie(CSRF_COOKIE_NAME, token, max_age=SESSION_TTL_SECONDS)]

    def do_GET(self):
        auth_store = AuthStore()
        current_user = self._get_current_user(auth_store)
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        now = dt.datetime.now()

        if parsed.path in ('/static/style.css', '/style.css'):
            return self._send_css()

        public_paths = {'/login', '/register', '/logout'}
        if parsed.path not in public_paths and not current_user:
            return self._redirect('/login?' + urlencode({'next': parsed.path if parsed.path else '/'}))

        if current_user:
            work_sessions, supervision_sessions = _load_user_sessions(current_user['username'])
            core.sessions = work_sessions
            core.supervision_sessions = supervision_sessions
            csrf_token, csrf_headers = self._get_or_create_csrf_token()
        else:
            csrf_token = ''
            csrf_headers = []

        message = query.get('msg', [''])[0]

        if parsed.path == '/login':
            if current_user:
                return self._redirect('/')
            return self._send_html(_render_login_page(message, query.get('next', [''])[0]), extra_headers=csrf_headers)

        if parsed.path == '/register':
            if current_user:
                return self._redirect('/')
            return self._send_html(_render_register_page(message), extra_headers=csrf_headers)

        if parsed.path == '/logout':
            return self._redirect('/login', extra_headers=[
                self._set_cookie(SESSION_COOKIE_NAME, '', max_age=0),
                self._set_cookie(CSRF_COOKIE_NAME, '', max_age=0),
            ])

        if parsed.path == '/':
            year, month = _parse_month_year(query, now.year, now.month)
            return self._send_html(_render_dashboard(year, month, message, current_user, csrf_token), extra_headers=csrf_headers)

        if parsed.path == '/work/new':
            return self._send_html(_render_form('work', message, None, None, 'Save session', 'Log Work Session', csrf_token, current_user), extra_headers=csrf_headers)

        if parsed.path == '/work/edit':
            index = _parse_index(query)
            try:
                session = _get_session_by_index(core.sessions, index)
            except IndexError:
                return self._send_html(_page_shell('Not Found', '<section class="card"><h2>Page not found</h2><p class="muted">The requested route does not exist.</p></section>', current_user), HTTPStatus.NOT_FOUND, extra_headers=csrf_headers)
            return self._send_html(_render_form('work', message, _session_form_values(session, 'work'), action_path=f'/work/edit?index={index}', submit_label='Update session', title='Edit Work Session', csrf_token=csrf_token, current_user=current_user), extra_headers=csrf_headers)

        if parsed.path == '/supervision/new':
            return self._send_html(_render_form('supervision', message, None, None, 'Save session', 'Log Supervision Session', csrf_token, current_user), extra_headers=csrf_headers)

        if parsed.path == '/supervision/edit':
            index = _parse_index(query)
            try:
                session = _get_session_by_index(core.supervision_sessions, index)
            except IndexError:
                return self._send_html(_page_shell('Not Found', '<section class="card"><h2>Page not found</h2><p class="muted">The requested route does not exist.</p></section>', current_user), HTTPStatus.NOT_FOUND, extra_headers=csrf_headers)
            return self._send_html(_render_form('supervision', message, _session_form_values(session, 'supervision'), action_path=f'/supervision/edit?index={index}', submit_label='Update session', title='Edit Supervision Session', csrf_token=csrf_token, current_user=current_user), extra_headers=csrf_headers)

        if parsed.path == '/reports/month':
            year, month = _parse_month_year(query, now.year, now.month)
            return self._send_html(_render_month_report(year, month, message, current_user, csrf_token), extra_headers=csrf_headers)

        if parsed.path == '/reports/year':
            year = _parse_int(query, 'year', now.year)
            return self._send_html(_render_year_report(year, message, current_user), extra_headers=csrf_headers)

        self._send_html(_page_shell('Not Found', '<section class="card"><h2>Page not found</h2><p class="muted">The requested route does not exist.</p></section>', current_user), HTTPStatus.NOT_FOUND, extra_headers=csrf_headers)

    def do_POST(self):
        auth_store = AuthStore()
        current_user = self._get_current_user(auth_store)
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length)
        form = _parse_form_data(body)

        if parsed.path == '/login':
            username = form.get('username', [''])[0].strip().lower()
            password = form.get('password', [''])[0]
            user = auth_store.authenticate(username, password)
            if user:
                csrf_token = secrets.token_urlsafe(24)
                session_token = _make_session_token(user['username'], csrf_token)
                redirect_target = form.get('next', [''])[0] or '/'
                return self._redirect(
                    redirect_target,
                    extra_headers=[
                        self._set_cookie(SESSION_COOKIE_NAME, session_token, max_age=SESSION_TTL_SECONDS),
                        self._set_cookie(CSRF_COOKIE_NAME, csrf_token, max_age=SESSION_TTL_SECONDS),
                    ],
                )
            return self._send_html(_render_login_page('Invalid username or password.', form.get('next', [''])[0]))

        if parsed.path == '/register':
            username = form.get('username', [''])[0].strip().lower()
            password = form.get('password', [''])[0]
            try:
                auth_store.create_user(username, password)
                user = auth_store.authenticate(username, password)
                if user:
                    csrf_token = secrets.token_urlsafe(24)
                    session_token = _make_session_token(user['username'], csrf_token)
                    return self._redirect('/', extra_headers=[
                        self._set_cookie(SESSION_COOKIE_NAME, session_token, max_age=SESSION_TTL_SECONDS),
                        self._set_cookie(CSRF_COOKIE_NAME, csrf_token, max_age=SESSION_TTL_SECONDS),
                    ])
            except ValueError as error:
                return self._send_html(_render_register_page(str(error)))
            return self._send_html(_render_register_page('Unable to create account.'))

        if parsed.path == '/logout':
            return self._redirect('/login', extra_headers=[
                self._set_cookie(SESSION_COOKIE_NAME, '', max_age=0),
                self._set_cookie(CSRF_COOKIE_NAME, '', max_age=0),
            ])

        if not current_user:
            return self._send_html(_page_shell('Forbidden', '<section class="card"><h2>Access denied</h2><p class="muted">Please sign in first.</p></section>'), HTTPStatus.FORBIDDEN)

        expected_csrf = self._get_cookie(CSRF_COOKIE_NAME)
        submitted_csrf = form.get('csrf_token', [''])[0]
        if not expected_csrf or submitted_csrf != expected_csrf:
            return self._send_html(_page_shell('Forbidden', '<section class="card"><h2>Invalid request</h2><p class="muted">The request did not include a valid security token.</p></section>'), HTTPStatus.FORBIDDEN)

        work_sessions, supervision_sessions = _load_user_sessions(current_user['username'])
        core.sessions = work_sessions
        core.supervision_sessions = supervision_sessions

        try:
            if parsed.path == '/work/new':
                start_time = _parse_datetime_field(form, 'start_time')
                end_time = _parse_datetime_field(form, 'end_time')
                session = core.WorkSession(start_time, end_time)
                if not core.check_overlap(session, core.sessions):
                    raise ValueError('This work session overlaps an existing session.')
                core.sessions.append(session)
                _save_user_sessions(current_user['username'], core.sessions, core.supervision_sessions)
                self._redirect(f'/?{urlencode({"year": start_time.year, "month": start_time.month, "msg": "Work session saved."})}')
                return

            if parsed.path == '/work/edit':
                index = _parse_index(query)
                current_session = _get_session_by_index(core.sessions, index)
                start_time = _parse_datetime_field(form, 'start_time')
                end_time = _parse_datetime_field(form, 'end_time')
                updated_session = core.WorkSession(start_time, end_time)
                remaining_sessions = [session for session_index, session in enumerate(core.sessions) if session_index != index]
                if not core.check_overlap(updated_session, remaining_sessions):
                    raise ValueError('This work session overlaps an existing session.')
                current_session.start_time = start_time
                current_session.end_time = end_time
                _save_user_sessions(current_user['username'], core.sessions, core.supervision_sessions)
                self._redirect(f'/?{urlencode({"year": start_time.year, "month": start_time.month, "msg": "Work session updated."})}')
                return

            if parsed.path == '/work/delete':
                index = _parse_index(query)
                current_session = _get_session_by_index(core.sessions, index)
                start_time = current_session.start_time
                del core.sessions[index]
                _save_user_sessions(current_user['username'], core.sessions, core.supervision_sessions)
                self._redirect(f'/?{urlencode({"year": start_time.year, "month": start_time.month, "msg": "Work session deleted."})}')
                return

            if parsed.path == '/supervision/new':
                start_time = _parse_datetime_field(form, 'start_time')
                end_time = _parse_datetime_field(form, 'end_time')
                observation_format = int(form.get('observation_format', [''])[0])
                session_type = int(form.get('session_type', [''])[0])
                direct_observation = 'direct_observation' in form
                session = core.SupervisionSession(
                    start_time,
                    end_time,
                    core.ObservationType(observation_format),
                    core.SupervisionType(session_type),
                    direct_observation,
                )
                if not core.check_overlap(session, core.supervision_sessions):
                    raise ValueError('This supervision session overlaps an existing session.')
                core.supervision_sessions.append(session)
                _save_user_sessions(current_user['username'], core.sessions, core.supervision_sessions)
                self._redirect(f'/?{urlencode({"year": start_time.year, "month": start_time.month, "msg": "Supervision session saved."})}')
                return

            if parsed.path == '/supervision/edit':
                index = _parse_index(query)
                current_session = _get_session_by_index(core.supervision_sessions, index)
                start_time = _parse_datetime_field(form, 'start_time')
                end_time = _parse_datetime_field(form, 'end_time')
                observation_format = int(form.get('observation_format', [''])[0])
                session_type = int(form.get('session_type', [''])[0])
                direct_observation = 'direct_observation' in form
                updated_session = core.SupervisionSession(
                    start_time,
                    end_time,
                    core.ObservationType(observation_format),
                    core.SupervisionType(session_type),
                    direct_observation,
                )
                remaining_sessions = [session for session_index, session in enumerate(core.supervision_sessions) if session_index != index]
                if not core.check_overlap(updated_session, remaining_sessions):
                    raise ValueError('This supervision session overlaps an existing session.')
                current_session.start_time = start_time
                current_session.end_time = end_time
                current_session.format = core.ObservationType(observation_format)
                current_session.session_type = core.SupervisionType(session_type)
                current_session.is_direct_observation = direct_observation
                _save_user_sessions(current_user['username'], core.sessions, core.supervision_sessions)
                self._redirect(f'/?{urlencode({"year": start_time.year, "month": start_time.month, "msg": "Supervision session updated."})}')
                return

            if parsed.path == '/supervision/delete':
                index = _parse_index(query)
                current_session = _get_session_by_index(core.supervision_sessions, index)
                start_time = current_session.start_time
                del core.supervision_sessions[index]
                _save_user_sessions(current_user['username'], core.sessions, core.supervision_sessions)
                self._redirect(f'/?{urlencode({"year": start_time.year, "month": start_time.month, "msg": "Supervision session deleted."})}')
                return

        except (ValueError, KeyError, IndexError) as error:
            message = str(error)
            csrf_token = self._get_cookie(CSRF_COOKIE_NAME) or ''
            if parsed.path == '/work/new':
                return self._send_html(_render_form('work', message, form, None, 'Save session', 'Log Work Session', csrf_token, current_user))
            if parsed.path == '/work/edit':
                index = _parse_index(query)
                try:
                    session = _get_session_by_index(core.sessions, index)
                except IndexError:
                    return self._send_html(_page_shell('Not Found', '<section class="card"><h2>Page not found</h2><p class="muted">The requested route does not exist.</p></section>', current_user), HTTPStatus.NOT_FOUND)
                return self._send_html(_render_form('work', message, form or _session_form_values(session, 'work'), action_path=f'/work/edit?index={index}', submit_label='Update session', title='Edit Work Session', csrf_token=csrf_token, current_user=current_user))
            if parsed.path == '/supervision/new':
                return self._send_html(_render_form('supervision', message, form, None, 'Save session', 'Log Supervision Session', csrf_token, current_user))
            if parsed.path == '/supervision/edit':
                index = _parse_index(query)
                try:
                    session = _get_session_by_index(core.supervision_sessions, index)
                except IndexError:
                    return self._send_html(_page_shell('Not Found', '<section class="card"><h2>Page not found</h2><p class="muted">The requested route does not exist.</p></section>', current_user), HTTPStatus.NOT_FOUND)
                return self._send_html(_render_form('supervision', message, form or _session_form_values(session, 'supervision'), action_path=f'/supervision/edit?index={index}', submit_label='Update session', title='Edit Supervision Session', csrf_token=csrf_token, current_user=current_user))

        self._send_html(_page_shell('Not Found', '<section class="card"><h2>Page not found</h2><p class="muted">The requested route does not exist.</p></section>', current_user), HTTPStatus.NOT_FOUND)


def run(host='127.0.0.1', port=5001):
    os.makedirs(DATA_DIR, exist_ok=True)
    server = ThreadingHTTPServer((host, port), SuperLogHandler)
    print(f'SuperLog running at http://{host}:{port}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping SuperLog...')
    finally:
        server.server_close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run the SuperLog browser app.')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', default=5001, type=int)
    args = parser.parse_args()
    run(args.host, args.port)
