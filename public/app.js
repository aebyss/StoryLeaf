const $=id=>document.getElementById(id);
const palettes=[['#ccd9b9','#e6ba72','#6c825a','#39543a','✦'],['#d9d2e6','#e7bba9','#8c79a4','#64527f','◒'],['#c5dadd','#f1d7a7','#59868d','#2d5b63','≈'],['#e8d2b3','#c9754e','#a99064','#754c35','☼'],['#d1d7c2','#b8c399','#637a57','#38513d','⌁']];
const demo=[
 {id:'demo-devops-1',title:'A quieter day on call',source:'DevOps · Demo',category:'DevOps',excerpt:'Imagine opening your dashboard and seeing a clear picture of what matters: service health, recent changes, and actionable alerts. This fictional preview shows how a short feed excerpt looks in Storyleaf. Connect FreshRSS to read your real DevOps stories.'},
 {id:'demo-devops-2',title:'Small releases, clearer changes',source:'DevOps · Demo',category:'DevOps',excerpt:'One change at a time. A smaller release can make it easier to follow the path from a code change to its effect in production. This is illustrative demo copy, not a live article or an AI summary.'},
 {id:'demo-tech-1',title:'A fresh perspective on your everyday tools',source:'Tech · Demo',category:'Tech',excerpt:'A small collection of useful ideas can be more valuable than a never-ending stream of updates. This fictional preview demonstrates the Tech category; connect FreshRSS to see your own latest articles.'},
 {id:'demo-nature-1',title:'The secret life beneath the forest',source:'Nature · Demo',category:'Nature',excerpt:'Under the forest floor, fungi form partnerships with plant roots. A small glimpse into a complex ecosystem. This standalone sample demonstrates the typography and story reader; it is not an article from your feeds.'},
 {id:'demo-design-1',title:'A different way to look at the city',source:'Design · Demo',category:'Design',excerpt:'Look up. Slow down. Find a doorway, a shadow, or a pattern you have never noticed. This fictional story demonstrates the reader. Your connected feed’s own image and text will appear here.'}
].map(a=>({...a,url:'',image:'',textKind:'Demo preview'}));
let currentUser=null,saveTimer=null,saveQueue=Promise.resolve();
// The old shared browser cache had no owner; never assign it to a signed-in user.
// Legacy bookmarks remain untouched for manual recovery; this app never reads them.
let saves={},selected='',articles=[],isDemo=false,savedView=false,readerArticles=[],position=0,loadVersion=0,seen=new Set();
function persist(){
 if(!currentUser||isDemo)return;
 clearTimeout(saveTimer);saveTimer=setTimeout(savePreferences,250);
}
function savePreferences(){
 clearTimeout(saveTimer);saveTimer=null;if(!currentUser||isDemo)return saveQueue;
 const account=currentUser.id,body=JSON.stringify({saves,category:selected,seen:[...seen].slice(-500)});
 saveQueue=saveQueue.catch(()=>{}).then(async()=>{if(currentUser?.id!==account)return;await api('/api/preferences',{method:'POST',headers:{'X-Storyleaf-Account':account},body})}).catch(e=>{$('message').textContent='Could not save your preferences: '+e.message});return saveQueue;
}
function clearAccount(){
 clearTimeout(saveTimer);saveTimer=null;loadVersion++;currentUser=null;saves={};seen=new Set();selected='';articles=[];readerArticles=[];savedView=false;
 for(const id of ['reader','info'])if($(id).open)$(id).close();
 $('slide').replaceChildren();$('reader-source').textContent='';$('original').removeAttribute('href');$('original').hidden=true;
 $('grid').replaceChildren();$('story-circles').replaceChildren();$('category-chips').replaceChildren();$('category').replaceChildren(new Option('All categories',''));$('message').textContent='';$('connection').textContent='';
}
function announceSession(){try{localStorage.setItem('storyleaf-session-change',Date.now()+':'+Math.random())}catch{}}
window.addEventListener('storage',event=>{if(event.key==='storyleaf-session-change'){showLogin();load()}});
function showLogin(message=''){
 clearAccount();isDemo=false;$('login-panel').hidden=false;$('app-main').hidden=true;$('account-button').textContent='Sign in';$('login-error').textContent=message;$('api-password').value='';
}
function showDemo(){
 clearAccount();isDemo=true;$('login-panel').hidden=true;$('app-main').hidden=false;$('account-button').textContent='Sign in';
 setCategories(['DevOps','Tech','Nature','Design'].map(name=>({name,id:'user/-/label/'+name})));articles=demoArticles();categoryBusy(false);$('refresh').disabled=false;mode();$('message').textContent='Demo stories. Sign in to read your own feeds.';render();
}
function el(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node}
function palette(node,index){const p=palettes[index%palettes.length];['--bg','--shape','--land','--ink-art'].forEach((k,i)=>node.style.setProperty(k,p[i]));return p}
function imageArt(a,index,reader=false){
 const art=el('div',undefined,reader?'slide-art':'art'),p=palette(art,index);art.setAttribute('aria-hidden','true');
 if(!reader)art.append(el('span',a.id.startsWith('demo-')?'DEMO STORY':'FROM YOUR FEEDS','badge'),el('span',p[4],'symbol'));
 if(a.image&&/^https?:\/\//i.test(a.image)){const img=el('img');img.alt='';img.referrerPolicy='no-referrer';img.loading=reader?'eager':'lazy';img.onload=()=>art.classList.add('has-image');img.onerror=()=>{img.remove();art.classList.remove('has-image')};img.src=a.image;art.append(img)}return art;
}
function visible(){return savedView?Object.values(saves).filter(a=>a&&typeof a.id==='string'):articles}
function renderCategories(){
 $('category-chips').replaceChildren(...[...$('category').options].map(option=>{const chip=el('button',option.value?option.textContent:'For you','category-chip');chip.type='button';chip.classList.toggle('selected',option.value===selected);chip.setAttribute('aria-pressed',String(option.value===selected));chip.disabled=$('category').disabled;chip.onclick=()=>{if(selected===option.value&&!savedView)return;$('category').value=option.value;changeCategory()};return chip}));
}
function categoryBusy(busy){$('category').disabled=busy;renderCategories()}
function renderCircles(list){
 $('story-circles').replaceChildren();
 if(!list.length){$('story-circles').append(el('p','Stories will appear here when your feeds are ready.','stories-empty'));return}
 list.forEach((a,i)=>{const button=el('button',undefined,'story-circle');button.type='button';button.setAttribute('aria-label','Read '+a.title);button.title=a.title;button.classList.toggle('seen',seen.has(a.id));const ring=el('span',undefined,'story-ring'),art=imageArt(a,i,true);art.className='story-avatar';ring.append(art);button.append(ring,el('span',a.source||a.title,'circle-label'));button.onclick=()=>openStory(i);$('story-circles').append(button)});
}
function render(){
 const list=visible();renderCategories();renderCircles(list);$('grid').replaceChildren();$('discover').classList.toggle('active',!savedView);$('saved').classList.toggle('active',savedView);
 const name=$('category').selectedOptions[0]?.textContent||'All categories';$('library-title').textContent=savedView?'Your little collection':selected?name:'Latest stories';$('start-stories').disabled=!list.length;
 if(!list.length)$('grid').append(el('p',savedView?'Save a story while reading to find it here.':'No articles in this category yet. Try another category or refresh your feeds.','empty'));
 list.forEach((a,i)=>{const card=el('button',undefined,'card'),copy=el('div',undefined,'card-copy');copy.append(el('span',a.source,'source'),el('h3',a.title),el('p',a.excerpt||'No preview text in this feed. Open the original article to read more.'));const meta=el('div',undefined,'card-meta');meta.append(el('span',saves[a.id]?'♥ Saved':a.textKind||'Feed excerpt'),el('b','↗'));copy.append(meta);card.append(imageArt(a,i),copy);card.onclick=()=>openStory(i);$('grid').append(card)});
}
async function api(path,options={}){
 const r=await fetch(path,{...options,headers:{'Content-Type':'application/json','X-Storyleaf-Request':'1',...options.headers}});
 const data=await r.json();
 if(r.status===401&&path!='/api/login'){showLogin(data.error||'Please sign in again.');throw Error('Please sign in again.')}
 if(!r.ok)throw Error(data.error||'Request failed');return data;
}
function setCategories(categories){
 $('category').replaceChildren(new Option('All categories',''),...categories.map(c=>new Option(c.name,c.id)));
 if(!categories.some(c=>c.id===selected))selected='';$('category').value=selected;persist();renderCategories();
}
function demoArticles(){return demo.filter(a=>!selected||a.category===selected.split('/label/')[1]).slice(0,10)}
function mode(){ $('mode').textContent=(isDemo?'DEMO LIBRARY':'LATEST FROM FRESHRSS')+` · ${articles.length} STORIES` }
async function load(){
 const version=++loadVersion;$('refresh').disabled=true;categoryBusy(true);
 try{
  const status=await api('/api/session');if(version!==loadVersion)return;
  if(!status.authenticated){showLogin();return}
  if(currentUser?.id!==status.user.id){
   const result=await api('/api/preferences');if(version!==loadVersion)return;
   currentUser=status.user;const state=result.preferences;
   saves=state.saves||{};selected=state.category||'';seen=new Set(state.seen||[]);
  }
  isDemo=false;$('login-panel').hidden=true;$('app-main').hidden=false;$('account-button').textContent='Sign out · '+currentUser.name;
  $('connection').textContent='Signed in to FreshRSS as '+currentUser.name+'. Saved stories and preferences are private to this account.';
  $('message').textContent='Loading your stories…';
  const data=await api('/api/categories');if(version!==loadVersion)return;setCategories(data.categories);
  const result=await api('/api/articles?category='+encodeURIComponent(selected));if(version!==loadVersion)return;
  articles=result.articles;mode();$('message').textContent='';render();
 }catch(e){if(version!==loadVersion)return;articles=[];if(!currentUser)showLogin(e.message);else{$('message').textContent=e.message;render()}}
 finally{if(version===loadVersion){$('refresh').disabled=false;categoryBusy(false)}}
}
async function changeCategory(){
 selected=$('category').value;persist();savedView=false;const version=++loadVersion;articles=[];render();$('message').textContent='Loading the latest stories…';$('refresh').disabled=true;
 try{if(isDemo)articles=demoArticles();else{const result=await api('/api/articles?category='+encodeURIComponent(selected));if(version!==loadVersion)return;articles=result.articles}mode();$('message').textContent=isDemo?'Demo stories. Refresh feeds to reconnect to FreshRSS.':'';render()}
 catch(e){if(version!==loadVersion)return;articles=[];$('message').textContent=e.message;$('mode').textContent='CONNECTION UNAVAILABLE';render()}
 finally{if(version===loadVersion)$('refresh').disabled=false}
}
function openStory(index){readerArticles=[...visible()];if(!readerArticles.length)return;position=index;showStory();$('reader').showModal()}
function showStory(){
 const a=readerArticles[position];seen.delete(a.id);seen.add(a.id);persist();palette($('reader'),position);$('reader-source').textContent=a.source;
 $('original').hidden=!a.url||!/^https?:\/\//i.test(a.url);if(!$('original').hidden)$('original').href=a.url;else $('original').removeAttribute('href');
 $('slide').replaceChildren(imageArt(a,position,true),el('span',a.textKind||'Feed excerpt','source'),el('h2',a.title),el('p',a.excerpt||'This feed has no preview text. Open the original article to read it.'));
 $('progress').replaceChildren(...readerArticles.map((_,i)=>el('span',undefined,i<=position?'done':'')));$('page').textContent=`${position+1} / ${readerArticles.length}`;$('prev').disabled=position===0;$('next').disabled=position===readerArticles.length-1;$('bookmark').textContent=saves[a.id]?'♥ Saved':'♡ Save story';
}
function move(delta){if(!readerArticles.length)return;position=Math.max(0,Math.min(readerArticles.length-1,position+delta));showStory()}
$('prev').onclick=()=>move(-1);$('next').onclick=()=>move(1);$('close').onclick=()=>$('reader').close();$('reader').addEventListener('close',render);
$('bookmark').onclick=()=>{const a=readerArticles[position];if(saves[a.id])delete saves[a.id];else saves[a.id]=a;persist();showStory()};
$('discover').onclick=()=>{savedView=false;render()};$('saved').onclick=()=>{savedView=true;render()};$('refresh').onclick=load;$('category').onchange=changeCategory;$('start-stories').onclick=()=>openStory(0);
$('settings').onclick=()=>$('info').showModal();$('info-close').onclick=()=>$('info').close();$('demo-toggle').onclick=showDemo;$('login-demo').onclick=showDemo;
$('account-button').onclick=async()=>{
 if(!currentUser){showLogin();return}
 $('account-button').disabled=true;
 try{await savePreferences();await api('/api/logout',{method:'POST',body:'{}'});showLogin();announceSession()}
 catch(e){$('message').textContent=e.message}finally{$('account-button').disabled=false}
};
$('login-form').onsubmit=async event=>{
 event.preventDefault();$('login-submit').disabled=true;$('login-error').textContent='';
 try{await api('/api/login',{method:'POST',body:JSON.stringify({username:$('username').value,password:$('api-password').value})});$('api-password').value='';clearAccount();announceSession();await load()}
 catch(e){$('login-error').textContent=e.message}finally{$('login-submit').disabled=false}
};
window.addEventListener('pageshow',event=>{if(event.persisted){showLogin();load()}});
document.addEventListener('keydown',e=>{if($('reader').open&&e.key==='ArrowRight')move(1);if($('reader').open&&e.key==='ArrowLeft')move(-1)});
let touch=null;$('slide').addEventListener('touchstart',e=>{touch={x:e.changedTouches[0].clientX,y:e.changedTouches[0].clientY}},{passive:true});$('slide').addEventListener('touchend',e=>{if(!touch)return;const dx=e.changedTouches[0].clientX-touch.x,dy=e.changedTouches[0].clientY-touch.y;if(Math.abs(dx)>60&&Math.abs(dx)>Math.abs(dy)*1.5)move(dx<0?1:-1);touch=null},{passive:true});
load();
