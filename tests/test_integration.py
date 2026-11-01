import unittest,tempfile,os,sys,json,io
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs,urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
class Integration(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=server.SESSION_DB;server.SESSION_DB=self.tmp.name+'/sessions.sqlite';self.headers=[];server.ATTEMPTS.clear()
  self.mock=patch.object(server,'request',side_effect=self.upstream);self.mock.start()
 def tearDown(self):self.mock.stop();server.SESSION_DB=self.old;self.tmp.cleanup()
 def upstream(self,url,data=None,headers=None,timeout=30):
  if url.endswith('/accounts/ClientLogin'):
   fields=parse_qs(data.decode());name=fields['Email'][0]
   if fields['Passwd']!=['api-secret']:raise ValueError('invalid')
   return ('Auth=token-'+name+'\n').encode()
  token=headers['Authorization'];name=token.removeprefix('GoogleLogin auth=token-');self.headers.append(token)
  if '/user-info' in url:return json.dumps({'userId':name}).encode()
  if '/tag/list' in url:return json.dumps({'tags':[{'id':'user/-/label/'+name,'type':'folder'},{'id':'user/-/label/tag','type':'tag'}]}).encode()
  self.assertEqual(parse_qs(urlsplit(url).query)['n'],['10'])
  return json.dumps({'items':[{'id':'same-id','title':name+' article','summary':{'content':'<p>Private '+name+' text.</p><img src="/cover.jpg">'},'alternate':[{'href':'https://example.com/article'}]}]}).encode()
 def handler(self,path,cookie='',body=None,extra=None):
  h=object.__new__(server.Handler);h.path=path;h.client_address=('127.0.0.1',1234);raw=json.dumps(body or {}).encode();h.rfile=io.BytesIO(raw)
  h.headers={'Cookie':'storyleaf_session='+cookie,'Host':'reader.example.com','Origin':'https://reader.example.com','X-Storyleaf-Request':'1','Content-Type':'application/json','Content-Length':str(len(raw)),**(extra or {})}
  h.reply=lambda value,status=200,cookie=None:(status,value,cookie);return h
 def sign_in(self,user):return server.login(user,'api-secret')
 def test_two_accounts_are_isolated(self):
  alice=self.sign_in('alice');bob=self.sign_in('bob')
  for user,cookie in [('alice',alice),('bob',bob)]:
   status,result,_=self.handler('/api/categories',cookie).do_GET();self.assertEqual(status,200);self.assertEqual(result['categories'][0]['name'],user)
   status,result,_=self.handler('/api/articles',cookie).do_GET();self.assertEqual(result['articles'][0]['title'],user+' article')
 def test_preferences_are_private_and_persistent(self):
  alice=self.sign_in('alice');bob=self.sign_in('bob');account=server.find_session(alice)['account']
  status,_,_=self.handler('/api/preferences',alice,{'saves':{'one':{'title':'private'}},'category':'DevOps','seen':[]},{'X-Storyleaf-Account':account}).do_POST();self.assertEqual(status,200)
  self.assertEqual(self.handler('/api/preferences',bob).do_GET()[1]['preferences'],{})
  other=server.login('alice','api-secret');self.assertEqual(self.handler('/api/preferences',other).do_GET()[1]['preferences']['saves']['one']['title'],'private')
 def test_stale_account_writes_rejected(self):
  alice=self.sign_in('alice');bob=self.sign_in('bob')
  self.assertEqual(self.handler('/api/preferences',bob,{'saves':{}},{'X-Storyleaf-Account':server.find_session(alice)['account']}).do_POST()[0],409)
 def test_unauthenticated_endpoints(self):
  for path in ['/api/articles','/api/categories','/api/preferences']:self.assertEqual(self.handler(path).do_GET()[0],401)
  self.assertFalse(self.handler('/api/session').do_GET()[1]['authenticated'])
 def test_login_cookie_and_logout(self):
  status,data,cookie=self.handler('/api/login',body={'username':'alice','password':'api-secret'}).do_POST();self.assertEqual(status,200)
  for attribute in ('HttpOnly','Secure','SameSite=Strict','Max-Age=2592000'):self.assertIn(attribute,cookie)
  value=cookie.split(';')[0].split('=',1)[1];self.assertIsNotNone(server.find_session(value))
  self.assertEqual(self.handler('/api/logout',value).do_POST()[0],200);self.assertIsNone(server.find_session(value))
 def test_password_not_stored_and_cookie_hashed(self):
  cookie=self.sign_in('alice')
  with server.database() as con:row=con.execute('SELECT * FROM sessions').fetchone()
  self.assertNotIn(cookie,row);self.assertNotIn('api-secret',row);self.assertEqual(row[0],server.session_key(cookie))
 def test_session_survives_reopen_and_expires(self):
  cookie=self.sign_in('alice');self.assertIsNotNone(server.find_session(cookie))
  with server.database() as con:con.execute('UPDATE sessions SET expires=0')
  self.assertIsNone(server.find_session(cookie))
 def test_cross_origin_rejected(self):
  for path in ('/api/login','/api/logout','/api/preferences'):self.assertEqual(self.handler(path,extra={'Origin':'https://evil.example'}).do_POST()[0],403)
 def test_failed_login_and_rate_limit(self):
  for _ in range(10):self.assertEqual(self.handler('/api/login',body={'username':'alice','password':'wrong'}).do_POST()[0],401)
  self.assertEqual(self.handler('/api/login',body={'username':'alice','password':'api-secret'}).do_POST()[0],429)
 def test_shared_env_credentials_never_grant_access(self):
  with patch.dict(os.environ,{'FRESHRSS_USER':'owner','FRESHRSS_API_PASSWORD':'api-secret','APP_USER':'ignored','APP_PASSWORD':'ignored'}):self.assertEqual(self.handler('/api/articles').do_GET()[0],401)
 def test_images_and_sanitization(self):
  a=server.article({'id':'one','title':'<b>Title</b>','summary':{'content':'<script>bad</script><p>hello</p><img src="/image.jpg">'},'alternate':[{'href':'https://example.com/post'}]})
  self.assertEqual(a['title'],'Title');self.assertEqual(a['excerpt'],'hello');self.assertEqual(a['image'],'https://example.com/image.jpg');self.assertEqual(server.safe_url('javascript:bad()'),'')
if __name__=='__main__':unittest.main()
