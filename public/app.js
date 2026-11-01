const $=id=>document.getElementById(id);
const palettes=[['#ccd9b9','#e6ba72','#6c825a','#39543a','✦'],['#d9d2e6','#e7bba9','#8c79a4','#64527f','◒'],['#c5dadd','#f1d7a7','#59868d','#2d5b63','≈'],['#e8d2b3','#c9754e','#a99064','#754c35','☼'],['#d1d7c2','#b8c399','#637a57','#38513d','⌁']];
const demo=[
 {id:'demo-devops-1',title:'A quieter day on call',source:'DevOps · Demo',category:'DevOps',excerpt:'Imagine opening your dashboard and seeing a clear picture of what matters: service health, recent changes, and actionable alerts. This fictional preview shows how a short feed excerpt looks in Storyleaf. Connect FreshRSS to read your real DevOps stories.'},
 {id:'demo-devops-2',title:'Small releases, clearer changes',source:'DevOps · Demo',category:'DevOps',excerpt:'One change at a time. A smaller release can make it easier to follow the path from a code change to its effect in production. This is illustrative demo copy, not a live article or an AI summary.'},
 {id:'demo-tech-1',title:'A fresh perspective on your everyday tools',source:'Tech · Demo',category:'Tech',excerpt:'A small collection of useful ideas can be more valuable than a never-ending stream of updates. This fictional preview demonstrates the Tech category; connect FreshRSS to see your own latest articles.'},
 {id:'demo-nature-1',title:'The secret life beneath the forest',source:'Nature · Demo',category:'Nature',excerpt:'Under the forest floor, fungi form partnerships with plant roots. A small glimpse into a complex ecosystem. This standalone sample demonstrates the typography and story reader; it is not an article from your feeds.'},
 {id:'demo-design-1',title:'A different way to look at the city',source:'Design · Demo',category:'Design',excerpt:'Look up. Slow down. Find a doorway, a shadow, or a pattern you have never noticed. This fictional story demonstrates the reader. Your connected feed’s own image and text will appear here.'}
].map(a=>({...a,url:'',image:'',textKind:'Demo preview'}));
let stored={};try{const value=JSON.parse(localStorage.getItem('storyleaf')||'{}');if(value&&typeof value==='object')stored=value}catch{}
let saves=stored.saves&&typeof stored.saves==='object'?stored.saves:{},selected=typeof stored.category==='string'?stored.category:'',articles=[],isDemo=false,savedView=false,readerArticles=[],position=0,loadVersion=0,seen=new Set(Array.isArray(stored.seen)?stored.seen:[]);
function persist(){try{localStorage.setItem('storyleaf',JSON.stringify({saves,category:selected,seen:[...seen].slice(-500)}))}catch{}}
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
async function api(path){const r=await fetch(path);if(r.status===401)throw Error('Login required. Reload this page to sign in.');const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data}
function setCategories(categories){
 $('category').replaceChildren(new Option('All categories',''),...categories.map(c=>new Option(c.name,c.id)));
 if(!categories.some(c=>c.id===selected))selected='';$('category').value=selected;persist();renderCategories();
}
function demoArticles(){return demo.filter(a=>!selected||a.category===selected.split('/label/')[1]).slice(0,10)}
function mode(){ $('mode').textContent=(isDemo?'DEMO LIBRARY':'LATEST FROM FRESHRSS')+` · ${articles.length} STORIES` }
async function load(){
 const version=++loadVersion;$('message').textContent='Connecting to your library…';$('refresh').disabled=true;categoryBusy(true);
 try{const status=await api('/api/status');if(version!==loadVersion)return;
 $('connection').textContent=status.configured?'FreshRSS is configured. Stories use your feed’s preview text and images. No AI service is needed.':'Demo mode is active. Add your FreshRSS username and API password to .env, then restart the app.';
 isDemo=!status.configured;
 if(isDemo){setCategories(['DevOps','Tech','Nature','Design'].map(name=>({name,id:'user/-/label/'+name})));articles=demoArticles();$('message').textContent='Demo stories. Connect FreshRSS to explore your own categories.'}
 else{const data=await api('/api/categories');if(version!==loadVersion)return;setCategories(data.categories);const result=await api('/api/articles?category='+encodeURIComponent(selected));if(version!==loadVersion)return;articles=result.articles;$('message').textContent=''}mode();render()}
 catch(e){if(version!==loadVersion)return;articles=[];$('message').textContent=e.message+' Open ⓘ to explore the demo.';$('mode').textContent='CONNECTION UNAVAILABLE';render()}
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
$('settings').onclick=()=>$('info').showModal();$('info-close').onclick=()=>$('info').close();$('demo-toggle').onclick=()=>{loadVersion++;isDemo=true;savedView=false;setCategories(['DevOps','Tech','Nature','Design'].map(name=>({name,id:'user/-/label/'+name})));articles=demoArticles();$('refresh').disabled=false;categoryBusy(false);mode();$('message').textContent='Demo stories. Refresh feeds to reconnect to FreshRSS.';$('info').close();render()};
document.addEventListener('keydown',e=>{if($('reader').open&&e.key==='ArrowRight')move(1);if($('reader').open&&e.key==='ArrowLeft')move(-1)});
let touch=null;$('slide').addEventListener('touchstart',e=>{touch={x:e.changedTouches[0].clientX,y:e.changedTouches[0].clientY}},{passive:true});$('slide').addEventListener('touchend',e=>{if(!touch)return;const dx=e.changedTouches[0].clientX-touch.x,dy=e.changedTouches[0].clientY-touch.y;if(Math.abs(dx)>60&&Math.abs(dx)>Math.abs(dy)*1.5)move(dx<0?1:-1);touch=null},{passive:true});
load();
