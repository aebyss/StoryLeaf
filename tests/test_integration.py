import unittest, os, sys, json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
class Integration(unittest.TestCase):
    def setUp(self):
        self.urls=[]
        self.env=patch.dict(os.environ,{'FRESHRSS_USER':'alice','FRESHRSS_API_PASSWORD':'secret','APP_USER':'','APP_PASSWORD':''});self.env.start()
        self.mock=patch.object(server,'request',side_effect=self.upstream);self.mock.start()
    def tearDown(self): self.mock.stop();self.env.stop()
    def upstream(self,url,data=None,headers=None,timeout=30):
        self.urls.append(url)
        if url.endswith('ClientLogin'):
            self.assertIn(b'Email=alice',data);self.assertIn(b'Passwd=secret',data);return b'Auth=test-token\n'
        self.assertEqual(headers['Authorization'],'GoogleLogin auth=test-token')
        if '/tag/list' in url:
            return json.dumps({'tags':[{'id':'user/-/label/DevOps','type':'folder'},{'id':'user/-/label/Art & Design','type':'folder'},{'id':'user/-/label/Personal tag','type':'tag'},{'id':'user/-/state/com.google/starred'}]}).encode()
        self.assertEqual(parse_qs(urlsplit(url).query)['n'],['10']);self.assertEqual(parse_qs(urlsplit(url).query)['r'],['n'])
        return json.dumps({'items':[{'id':str(i),'title':'Forest <b>life</b>','summary':{'content':'<p>'+('A detailed forest article. '*30)+'</p><script>bad()</script><img src="/hero.jpg">'},'origin':{'title':'Nature'},'alternate':[{'href':'https://example.org/article'}]} for i in range(12)]}).encode()
    def handler(self,path):
        h=object.__new__(server.Handler);h.path=path;h.headers={};h.reply=lambda value,status=200:(status,value);return h
    def test_categories_exclude_tags_and_states(self):
        result=server.categories();self.assertEqual([c['name'] for c in result],['Art & Design','DevOps'])
    def test_category_filtered_upstream_and_limit(self):
        result=server.feeds('user/-/label/DevOps');self.assertEqual(len(result),10);self.assertIn('/stream/contents/user/-/label/DevOps?',self.urls[-1]);self.assertEqual(result[0]['title'],'Forest life');self.assertNotIn('bad()',result[0]['excerpt']);self.assertEqual(result[0]['image'],'https://example.org/hero.jpg')
    def test_category_encoding(self):
        server.feeds('user/-/label/Art & Design/Cloud');self.assertIn('Art%20%26%20Design%2FCloud',self.urls[-1])
    def test_invalid_category(self):
        with self.assertRaises(ValueError):server.feeds('not-a-category')
    def test_all_categories(self):
        server.feeds();self.assertIn('/stream/contents/reading-list?',self.urls[-1])
    def test_excerpt_word_boundary(self):
        text=server.excerpt('hello world test',10);self.assertEqual(text,'hello…');self.assertEqual(server.excerpt('Short'),'Short')
    def test_images_enclosure_and_unsafe_urls(self):
        a={'id':'x','summary':{'content':'<img width="1" src="https://example.com/tracker"><img src="javascript:bad()"><img src="/cover.png">'},'alternate':[{'href':'https://example.org/post'}],'enclosure':[{'type':'image/jpeg','href':'https://images.example.org/hero.jpg'}]}
        self.assertEqual(server.article(a)['image'],'https://images.example.org/hero.jpg');a['enclosure']=[];self.assertEqual(server.article(a)['image'],'https://example.org/cover.png')
        self.assertEqual(server.safe_url('data:image/png,x'),'');self.assertEqual(server.safe_url('https://user:pass@example.com'),'')
    def test_no_image_or_text(self):
        a=server.article({'id':'x'});self.assertEqual(a['image'],'');self.assertEqual(a['excerpt'],'')
    def test_category_http_route(self):
        status,result=self.handler('/api/articles?category=user%2F-%2Flabel%2FDevOps').do_GET();self.assertEqual(status,200);self.assertEqual(len(result['articles']),10);self.assertIn('/label/DevOps?',self.urls[-1])
    def test_ollama_route_removed(self):
        self.assertEqual(self.handler('/api/story').do_POST()[0],404)
    def test_authentication(self):
        h=self.handler('/');responses=[];h.send_response=responses.append;h.send_header=lambda *args:None;h.end_headers=lambda:None
        with patch.dict(os.environ,{'APP_USER':'reader','APP_PASSWORD':'pass'}):
            self.assertFalse(h.authorized());self.assertEqual(responses,[401]);h.headers['Authorization']='Basic cmVhZGVyOnBhc3M=';self.assertTrue(h.authorized())
if __name__=='__main__':unittest.main()
