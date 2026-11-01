import os, json, secrets, re, signal, sqlite3, hashlib, time, threading
from contextlib import contextmanager
from http.cookies import SimpleCookie
from urllib.error import HTTPError
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlsplit, urljoin, quote, parse_qs
from pathlib import Path

ROOT = Path(__file__).parent
BASE = os.getenv('FRESHRSS_URL', 'http://192.168.178.53:30080').rstrip('/')
API = os.getenv('FRESHRSS_API_URL', BASE + '/api/greader.php').rstrip('/')
class Content(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.images=[]; self.hidden=0
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag in ('script','style'): self.hidden += 1
        if self.hidden: return
        if tag in ('p','br','div','li','h1','h2','h3'): self.parts.append(' ')
        if tag=='img':
            if attrs.get('width') in ('0','1') or attrs.get('height') in ('0','1'): return
            src=attrs.get('src') or attrs.get('data-src') or attrs.get('data-original')
            if src: self.images.append(src)
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.hidden=max(0,self.hidden-1)
        if tag in ('p','div','li'): self.parts.append(' ')
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)
def plain(value):
    p=Content(); p.feed(value); return re.sub(r'\s+',' ',''.join(p.parts)).strip()
def safe_url(value, base=''):
    if not isinstance(value,str) or not value.strip(): return ''
    value=urljoin(base,value.strip())
    parts=urlsplit(value)
    return value if parts.scheme in ('http','https') and parts.netloc and not parts.username and not parts.password else ''
def excerpt(text, limit=560):
    if len(text)<=limit: return text
    return text[:limit].rsplit(' ',1)[0].rstrip('.,;:')+'…'
def request(url, data=None, headers=None, timeout=30):
    with urlopen(Request(url,data=data,headers=headers or {}),timeout=timeout) as r: return r.read()
SESSION_DB = os.getenv('SESSION_DB', str(ROOT/'data'/'sessions.sqlite'))
COOKIE_SECURE = os.getenv('COOKIE_SECURE','true').lower() != 'false'
SESSION_SECONDS = 30 * 24 * 3600
ATTEMPTS = {}
ATTEMPT_LOCK = threading.Lock()
@contextmanager
def database():
    path=Path(SESSION_DB); path.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path,timeout=15)
    try:
        os.chmod(path,0o600)
        with con:
            con.execute('CREATE TABLE IF NOT EXISTS sessions (key TEXT PRIMARY KEY, account TEXT, username TEXT, upstream TEXT, expires REAL)')
            con.execute('CREATE TABLE IF NOT EXISTS preferences (account TEXT PRIMARY KEY, content TEXT NOT NULL)')
            con.execute('DELETE FROM sessions WHERE expires <= ?', (time.time(),))
            yield con
    finally: con.close()
def session_key(value): return hashlib.sha256(value.encode()).hexdigest()
def find_session(value):
    if not value: return None
    with database() as con:
        row=con.execute('SELECT account,username,upstream FROM sessions WHERE key=? AND expires>?',(session_key(value),time.time())).fetchone()
    return dict(zip(('account','username','upstream'),row)) if row else None
def revoke(value):
    if value:
        with database() as con: con.execute('DELETE FROM sessions WHERE key=?',(session_key(value),))
def login(username,password):
    raw=request(API+'/accounts/ClientLogin',urlencode({'Email':username,'Passwd':password}).encode())
    token=next((x[5:] for x in raw.decode().splitlines() if x.startswith('Auth=')),None)
    if not token: raise ValueError('Invalid login')
    profile=json.loads(request(API+'/reader/api/0/user-info?output=json',headers={'Authorization':'GoogleLogin auth='+token}))
    identity=str(profile.get('userId') or profile.get('userName') or '').strip()
    if not identity: raise ValueError('Invalid user profile')
    account=hashlib.sha256((API+'\0'+identity).encode()).hexdigest()
    value=secrets.token_urlsafe(32)
    with database() as con:
        # Keep a bounded number of active device sessions per account.
        con.execute('DELETE FROM sessions WHERE key IN (SELECT key FROM sessions WHERE account=? ORDER BY expires DESC LIMIT -1 OFFSET 19)',(account,))
        con.execute('INSERT INTO sessions VALUES (?,?,?,?,?)',(session_key(value),account,identity,token,time.time()+SESSION_SECONDS))
    return value
def categories(session):
    data=json.loads(request(API+'/reader/api/0/tag/list?output=json',headers={'Authorization':'GoogleLogin auth='+session['upstream']}))
    folders={t['id']: {'id':t['id'],'name':t['id'].split('/label/',1)[1]} for t in data.get('tags',[]) if '/label/' in t.get('id','') and t.get('type','folder')=='folder'}
    return sorted(folders.values(),key=lambda t:t['name'].casefold())
def article(a):
    url=safe_url(next((x.get('href','') for x in a.get('alternate',[]) if x.get('href')),''))
    html=a.get('summary',a.get('content',{})).get('content','')
    parsed=Content(); parsed.feed(html)
    candidates=[]
    for x in a.get('enclosure',[]):
        if x.get('type','').startswith('image/'): candidates.append(x.get('href',''))
    candidates+=parsed.images
    image=next((u for x in candidates if (u:=safe_url(x,url or BASE))), '')
    text=plain(html)
    return {'id':a['id'],'title':plain(a.get('title','Untitled')),'source':plain(a.get('origin',{}).get('title','FreshRSS')),'url':url,'image':image,'excerpt':excerpt(text),'textKind':'Feed excerpt','published':a.get('published',0)}
def feeds(session, category=''):
    # Filter upstream before taking ten; never filter a limited global reading list.
    if category and not category.startswith('user/-/label/'): raise ValueError('Invalid category')
    path='user/-/label/'+quote(category.split('/label/',1)[1],safe='') if category else 'reading-list'
    data=json.loads(request(API+'/reader/api/0/stream/contents/'+path+'?'+urlencode({'n':10,'r':'n','output':'json'}),headers={'Authorization':'GoogleLogin auth='+session['upstream']}))
    return [article(a) for a in data.get('items',[])[:10]]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'public'),**kwargs)
    def cookie_value(self):
        try:
            cookie=SimpleCookie(); cookie.load(self.headers.get('Cookie',''))
            return cookie['storyleaf_session'].value if 'storyleaf_session' in cookie else ''
        except Exception: return ''
    def get_session(self): return find_session(self.cookie_value())
    def cookie_header(self,value,age=SESSION_SECONDS):
        return 'storyleaf_session='+value+'; Path=/; HttpOnly; SameSite=Strict; Max-Age='+str(age)+('; Secure' if COOKIE_SECURE else '')
    def origin_valid(self):
        expected=('https' if COOKIE_SECURE else 'http')+'://'+self.headers.get('Host','')
        return self.headers.get('Origin')==expected and self.headers.get('Sec-Fetch-Site')!='cross-site' and self.headers.get('X-Storyleaf-Request')=='1'
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); super().end_headers()
    def reply(self,value,status=200,cookie=None):
        body=json.dumps(value).encode(); self.send_response(status)
        if cookie is not None: self.send_header('Set-Cookie',cookie)
        self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        parsed=urlsplit(self.path); path=parsed.path
        if path in ('/api/status','/api/session'):
            session=self.get_session()
            return self.reply({'authenticated':bool(session),'user':{'id':session['account'],'name':session['username']} if session else None})
        if path in ('/api/categories','/api/articles','/api/preferences'):
            session=self.get_session()
            if not session: return self.reply({'error':'Please sign in to FreshRSS.'},401)
            try:
                if path=='/api/preferences':
                    with database() as con: row=con.execute('SELECT content FROM preferences WHERE account=?',(session['account'],)).fetchone()
                    return self.reply({'preferences':json.loads(row[0]) if row else {}})
                if path=='/api/categories': return self.reply({'categories':categories(session)})
                category=parse_qs(parsed.query).get('category',[''])[0]
                if len(category)>500: return self.reply({'error':'Invalid category'},400)
                return self.reply({'articles':feeds(session,category)})
            except HTTPError as e:
                if e.code in (401,403):
                    revoke(self.cookie_value())
                    return self.reply({'error':'FreshRSS access expired. Please sign in again.'},401,cookie=self.cookie_header('',0))
                return self.reply({'error':'FreshRSS could not complete this request.'},502)
            except Exception: return self.reply({'error':'Could not read FreshRSS. Check server access and try again.'},502)
        if path.startswith('/api/'): return self.reply({'error':'Not found'},404)
        super().do_GET()
    def do_POST(self):
        if self.path not in ('/api/login','/api/logout','/api/preferences'): return self.reply({'error':'Not found'},404)
        if not self.origin_valid(): return self.reply({'error':'Request origin rejected.'},403)
        if self.path=='/api/preferences':
            session=self.get_session()
            if not session: return self.reply({'error':'Please sign in.'},401)
            if self.headers.get('X-Storyleaf-Account')!=session['account']: return self.reply({'error':'Account changed. Refresh the page.'},409)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.reply({'error':'JSON required.'},415)
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=524288: return self.reply({'error':'Saved stories exceed the storage limit. Remove some saved stories.'},413)
                state=json.loads(self.rfile.read(size))
                if not isinstance(state,dict) or not isinstance(state.get('saves',{}),dict) or not isinstance(state.get('category',''),str) or not isinstance(state.get('seen',[]),list): raise ValueError()
                state={key:state[key] for key in ('saves','category','seen') if key in state}
                with database() as con: con.execute('INSERT OR REPLACE INTO preferences VALUES (?,?)',(session['account'],json.dumps(state)))
                return self.reply({'ok':True})
            except (ValueError,TypeError): return self.reply({'error':'Invalid preferences.'},400)
        if self.path=='/api/logout':
            revoke(self.cookie_value())
            return self.reply({'ok':True},cookie=self.cookie_header('',0))
        if self.headers.get('Content-Type','').split(';')[0]!='application/json': return self.reply({'error':'JSON required.'},415)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<8192: return self.reply({'error':'Invalid request size.'},400)
            data=json.loads(self.rfile.read(size)); username=data.get('username',''); password=data.get('password','')
            if not isinstance(username,str) or not isinstance(password,str) or not username.strip() or not password or len(username)>200 or len(password)>4096:
                return self.reply({'error':'Enter your FreshRSS username and API password.'},400)
            username=username.strip()
        except (ValueError,AttributeError): return self.reply({'error':'Invalid login request.'},400)
        throttle=self.client_address[0]+'|'+username.casefold()
        with ATTEMPT_LOCK:
            now=time.time()
            for key in list(ATTEMPTS):
                if ATTEMPTS[key][0]<now-300: del ATTEMPTS[key]
            start,count=ATTEMPTS.get(throttle,(now,0))
            if count>=10 or len(ATTEMPTS)>2000: return self.reply({'error':'Too many attempts. Try again in five minutes.'},429)
            ATTEMPTS[throttle]=(start,count+1)
        try: value=login(username,password)
        except HTTPError as e:
            return self.reply({'error':'Invalid username or API password.' if e.code in (400,401,403) else 'FreshRSS is unavailable.'},401 if e.code in (400,401,403) else 502)
        except ValueError: return self.reply({'error':'Invalid username or API password.'},401)
        except Exception: return self.reply({'error':'Could not reach FreshRSS. Please try again.'},502)
        revoke(self.cookie_value())
        with ATTEMPT_LOCK: ATTEMPTS.pop(throttle,None)
        return self.reply({'ok':True},cookie=self.cookie_header(value))
if __name__=='__main__':
    def stop(*_): raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
