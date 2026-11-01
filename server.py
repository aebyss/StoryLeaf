import os, json, secrets, base64, re, signal
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
def login():
    raw=request(API+'/accounts/ClientLogin',urlencode({'Email':os.environ['FRESHRSS_USER'],'Passwd':os.environ['FRESHRSS_API_PASSWORD']}).encode())
    token=next((x[5:] for x in raw.decode().splitlines() if x.startswith('Auth=')),None)
    if not token: raise ValueError('FreshRSS login failed')
    return {'Authorization':'GoogleLogin auth='+token}
def categories():
    data=json.loads(request(API+'/reader/api/0/tag/list?output=json',headers=login()))
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
def feeds(category=''):
    # Filter upstream before taking ten; never filter a limited global reading list.
    if category and not category.startswith('user/-/label/'): raise ValueError('Invalid category')
    path='user/-/label/'+quote(category.split('/label/',1)[1],safe='') if category else 'reading-list'
    data=json.loads(request(API+'/reader/api/0/stream/contents/'+path+'?'+urlencode({'n':10,'r':'n','output':'json'}),headers=login()))
    return [article(a) for a in data.get('items',[])[:10]]
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'public'),**kwargs)
    def authorized(self):
        user=os.getenv('APP_USER',''); password=os.getenv('APP_PASSWORD','')
        if not user or not password: return True
        want='Basic '+base64.b64encode((user+':'+password).encode()).decode()
        if secrets.compare_digest(self.headers.get('Authorization',''),want): return True
        self.send_response(401); self.send_header('WWW-Authenticate','Basic realm="Storyleaf"'); self.end_headers(); return False
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','no-referrer'); super().end_headers()
    def reply(self,value,status=200):
        body=json.dumps(value).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        if not self.authorized(): return
        parsed=urlsplit(self.path); path=parsed.path
        if path=='/api/status': return self.reply({'configured':bool(os.getenv('FRESHRSS_USER') and os.getenv('FRESHRSS_API_PASSWORD'))})
        if path in ('/api/categories','/api/articles'):
            try:
                if path=='/api/categories': return self.reply({'categories':categories()})
                category=parse_qs(parsed.query).get('category',[''])[0]
                if len(category)>500: return self.reply({'error':'Invalid category'},400)
                return self.reply({'articles':feeds(category)})
            except ValueError: return self.reply({'error':'FreshRSS returned an invalid response or category.'},502)
            except Exception: return self.reply({'error':'Could not connect to FreshRSS. Check its API URL, username, API password, and network access.'},502)
        if path.startswith('/api/'): return self.reply({'error':'Not found'},404)
        super().do_GET()
    def do_POST(self):
        if not self.authorized(): return
        return self.reply({'error':'Not found'},404)
if __name__=='__main__':
    # Python as container PID 1 needs an explicit SIGTERM handler.
    def stop(*_): raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    ThreadingHTTPServer(('0.0.0.0',8080),Handler).serve_forever()
