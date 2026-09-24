#!/usr/bin/env python3
"""Add accounts, profiles, avatars and badges to the served games.

Runs AFTER add_server.py and patches its output in web/. Everything here only
makes sense on our own host, where server.ts keeps the accounts, so it is not
part of the artifact builds.

What it adds:
  * a profile button in the header, which opens sign in / sign up when nobody
    is signed in and the player's profile when somebody is;
  * a profile with a display name, initials, a line about themselves, an
    avatar (one of the presets, or a photo the player uploads) and badges;
  * scores posted while signed in carry the account, so the board shows names
    and pictures instead of three letters;
  * progress (stars, best times, clean runs) syncs to the account, so a player
    picks up where they left off on another phone.
"""
import pathlib, sys

# ------------------------------------------------------------------- markup

OLD_HEAD = '''      <div class="chip"><span>Best</span><b id="best">&mdash;</b></div>
    </div>
  </header>'''
NEW_HEAD = '''      <div class="chip"><span>Best</span><b id="best">&mdash;</b></div>
    </div>
    <button class="me" id="meBtn" aria-label="Your profile"></button>
  </header>'''

# The dash is written either way round depending on the build; try both.
OLD_HEAD_ALT = OLD_HEAD.replace('&mdash;', '—')
NEW_HEAD_ALT = NEW_HEAD.replace('&mdash;', '—')

CSS = '''
.me{width:36px;height:36px;border-radius:50%;padding:0;border:2px solid var(--edge);background:var(--surface);
  cursor:pointer;flex:0 0 auto;display:grid;place-items:center;overflow:hidden}
.ava{display:grid;place-items:center;width:32px;height:32px;border-radius:50%;overflow:hidden;
  background:var(--surface2);flex:0 0 auto}
.ava img{width:100%;height:100%;object-fit:cover;display:block}
.ava b{font-weight:400;font-size:17px;line-height:1}
.ava u{text-decoration:none;font-family:Chewy,cursive;font-size:13px;letter-spacing:1px;color:#1d2a16}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .ava u{color:#F2F7EC}}
.ava.big{width:66px;height:66px}
.ava.big b{font-size:34px}
.ava.big u{font-size:24px;letter-spacing:2px}
.ava.sm{width:25px;height:25px}
.ava.sm b{font-size:13px}
.ava.sm u{font-size:10px;letter-spacing:.5px}
.prof{display:flex;gap:12px;align-items:center;text-align:left;margin:0 0 14px}
.pmeta{min-width:0}
.pmeta b{font-size:13px;color:var(--muted);font-weight:800}
.pmeta p{margin:3px 0 0;font-size:12.5px;font-weight:600;color:var(--ink)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:0 0 14px}
.stat{background:var(--surface2);border:2px solid var(--edge);border-radius:12px;padding:5px 2px}
.stat b{display:block;font-family:Chewy,cursive;font-weight:400;font-size:19px;line-height:1.15}
.stat span{display:block;font-size:8.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px;max-height:26vh;overflow:auto}
.badge{display:flex;align-items:center;gap:5px;background:var(--surface2);border:2px solid var(--edge);
  border-radius:11px;padding:4px 8px;font-size:11.5px;font-weight:800;opacity:.4}
.badge.on{opacity:1;background:var(--grass);border-color:var(--grass-deep);color:#16210F}
.badge b{font-weight:400;font-size:14px}
.form{display:flex;flex-direction:column;gap:8px;margin:0 0 12px}
.card input[type=text],.card input[type=password]{font-family:inherit;font-weight:700;font-size:15px;
  padding:9px 11px;border-radius:12px;border:2px solid var(--edge);background:var(--surface2);color:var(--ink);
  -webkit-user-select:text;user-select:text;width:100%;box-sizing:border-box}
.card input::placeholder{color:var(--muted);font-weight:600}
.tabs{display:flex;gap:6px;justify-content:center;margin:0 0 12px}
.err{color:var(--barn);font-size:12.5px;font-weight:800;margin:0 0 12px;line-height:1.4}
.ok{color:var(--grass-deep);font-size:12.5px;font-weight:800;margin:0 0 12px}
.avpick{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin:0 0 12px}
.avopt{padding:3px;border-radius:50%;border:2px solid var(--edge);background:var(--surface);cursor:pointer;line-height:0}
.avopt.on{border-color:var(--grass-deep);background:var(--grass)}
.linkbtn{font-family:inherit;font-weight:800;font-size:12px;color:var(--muted);background:none;border:0;
  text-decoration:underline;cursor:pointer;padding:2px 4px}
.who{display:flex;align-items:center;gap:6px;min-width:0}
.who b{font-family:Chewy,cursive;font-weight:400;font-size:16px;letter-spacing:1px;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* The profile button is a fourth thing in a header that was already full, so
   the chrome shrinks earlier than it used to and the title gives way first. */
h1{overflow:hidden;text-overflow:ellipsis}
@media (max-width:439px){
  h1{font-size:20px}
  .logo{width:28px;height:28px}
  .chip{min-width:46px;padding:3px 6px}
  .chip b{font-size:14px}
  header{gap:6px}
  .me{width:30px;height:30px}
  .me .ava{width:26px;height:26px}
  .me .ava b{font-size:14px}
  .me .ava u{font-size:11px;letter-spacing:.5px}
}
'''

# ----------------------------------------------------------------- the code

JS = '''
/* ---------------- accounts ---------------- */
var ME=null,MESTATS=null,syncT=null,lastPush="";
var PIECE="__PIECE__";
var PRESETS=["coco","paw","bone","ball","star","heart","leaf","moon"];
var GLYPH={paw:"\\ud83d\\udc3e",bone:"\\ud83e\\uddb4",ball:"\\ud83c\\udfbe",star:"\\u2b50",
  heart:"\\ud83d\\udc9a",leaf:"\\ud83c\\udf43",moon:"\\ud83c\\udf19"};
var TINTS=["--c1","--c2","--c3","--c4","--c5","--c6","--c7","--c8","--c9","--c10","--c11","--c12"];
function esc(s){
  return String(s==null?"":s).replace(/[&<>"']/g,function(c){
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
  });
}
function tint(s){
  var h=0,i;s=String(s||"?");
  for(i=0;i<s.length;i++) h=(h*31+s.charCodeAt(i))|0;
  return TINTS[Math.abs(h)%TINTS.length];
}
function avaHTML(a,ini,cls){
  var open='<span class="ava'+(cls?" "+cls:"")+'"';
  if(a&&a.indexOf("f:")===0) return open+'><img src="/avatars/'+encodeURIComponent(a.slice(2))+'" alt=""></span>';
  if(a==="p:coco") return open+'><img src="'+PIECE+'" alt=""></span>';
  if(a&&a.indexOf("p:")===0&&GLYPH[a.slice(2)]) return open+'><b>'+GLYPH[a.slice(2)]+'</b></span>';
  return open+' style="background:var('+tint(ini)+')"><u>'+esc(ini||"?")+'</u></span>';
}
function api(p,body,method){
  var o={method:method||(body?"POST":"GET"),credentials:"same-origin",headers:{}};
  if(body){o.headers["content-type"]="application/json";o.body=JSON.stringify(body)}
  return fetch(p,o).then(function(r){
    return r.json().catch(function(){return {}}).then(function(j){
      if(!r.ok) throw new Error((j&&j.error)||"Something went wrong. Try again.");
      return j;
    });
  });
}
function setMe(j){
  ME=(j&&j.user)||null;
  if(j&&j.stats) MESTATS=j.stats;
  if(!ME) MESTATS=null;
  paintMe();
}
function paintMe(){
  var b=$("#meBtn");if(!b)return;
  b.innerHTML=ME?avaHTML(ME.avatar,(ME.ini||ME.name||"?").charAt(0),""):'<span class="ava"><b>\\ud83d\\udc64</b></span>';
}
function startAccount(){
  if(!onWeb()) {var b=$("#meBtn");if(b)b.hidden=true;return}
  var b=$("#meBtn");if(b) b.addEventListener("click",function(){accountCard()});
  paintMe();
  api("/api/me").then(function(j){setMe(j);if(ME) pullProgress()}).catch(function(){});
}

/* ---------------- badges ---------------- */
function badges(){
  var st=prog.star||{},cl=prog.clean||{},done=0,three=0,big=0,k;
  for(k in st){done++;if(st[k]>=3)three++;if(LEVELS[k]&&LEVELS[k].n>=10)big++}
  var clean=Object.keys(cl).length,firsts=(MESTATS&&MESTATS.firsts)||0;
  return [
    {i:"\\ud83c\\udf31",n:"First one",d:"Finish a level",got:done>=1},
    {i:"\\ud83d\\udd1f",n:"Ten down",d:"Finish ten levels",got:done>=10},
    {i:"\\ud83c\\udfc3",n:"Regular",d:"Finish forty levels",got:done>=40},
    {i:"\\ud83c\\udfc1",n:"The lot",d:"Finish every level",got:done>=LEVELS.length},
    {i:"\\u2b50",n:"Three stars",d:"Three stars on a level",got:three>=1},
    {i:"\\u2728",n:"Star collector",d:"Three stars on twenty-five levels",got:three>=25},
    {i:"\\ud83d\\udee1",n:"No mistakes",d:"Finish a level without losing a life",got:clean>=1},
    {i:"\\ud83e\\udde0",n:"Steady hand",d:"Ten levels without losing a life",got:clean>=10},
    {i:"\\ud83d\\udd0d",n:"Big board",d:"Finish a 10x10 or bigger",got:big>=1},
    {i:"\\ud83c\\udfc6",n:"Top score",d:"Hold the best score on a level",got:firsts>=1},
    {i:"\\ud83d\\udc51",n:"Board hog",d:"Best score on five levels",got:firsts>=5}
  ];
}

/* ---------------- cards ---------------- */
function statCell(v,label){return '<div class="stat"><b>'+v+'</b><span>'+label+'</span></div>'}
function accountCard(msg,quiet){
  if(!ME) return signCard("in","");
  var s=MESTATS||{total:0,firsts:0};
  var st=prog.star||{},done=0,stars=0,k;
  for(k in st){done++;stars+=st[k]}
  var list=badges(),got=0,i;
  for(i=0;i<list.length;i++) if(list[i].got) got++;
  var h='<h2 id="profCard">'+esc(ME.name)+'</h2>'+
    '<div class="prof">'+avaHTML(ME.avatar,ME.ini,"big")+
      '<div class="pmeta"><b>@'+esc(ME.handle)+'</b>'+(ME.bio?'<p>'+esc(ME.bio)+'</p>':'')+'</div></div>'+
    '<div class="stats">'+statCell(done,"levels")+statCell(stars,"stars")+
      statCell(s.total||0,"points")+statCell(s.firsts||0,"top scores")+'</div>'+
    (msg?'<p class="ok">'+esc(msg)+'</p>':'')+
    '<div class="lvhead">Badges '+got+' of '+list.length+'</div><div class="badges">';
  for(i=0;i<list.length;i++)
    h+='<span class="badge'+(list[i].got?" on":"")+'" title="'+esc(list[i].d)+'"><b>'+list[i].i+'</b>'+esc(list[i].n)+'</span>';
  h+='</div><div class="acts"><button class="btn" data-act="editprof">Edit profile</button>'+
     '<button class="btn" data-act="records">Records</button>'+
     '<button class="btn primary" data-act="close">Back</button></div>'+
     '<p class="note"><button class="linkbtn" data-act="signout">Sign out</button></p>';
  modal(h,true);
  // The points and top scores come from the server, and a level finished since
  // the page loaded has moved them. Fetch once and redraw if anything changed.
  if(!quiet) api("/api/me").then(function(j){
    if(!$("#profCard")||!j.user) return;
    var was=JSON.stringify(MESTATS);
    setMe(j);
    if(JSON.stringify(MESTATS)!==was) accountCard(msg,true);
  }).catch(function(){});
}
function signCard(mode,err){
  var up=mode==="up";
  var h='<h2>'+(up?"New player":"Welcome back")+'</h2>'+
    '<div class="tabs"><button class="lvchip'+(up?"":" on")+'" data-act="tabin">Sign in</button>'+
    '<button class="lvchip'+(up?" on":"")+'" data-act="tabup">Create account</button></div>'+
    '<div class="form">'+
    '<input type="text" id="uHandle" placeholder="username" autocomplete="username" '+
      'autocapitalize="none" autocorrect="off" spellcheck="false" maxlength="20">'+
    '<input type="password" id="uPass" placeholder="password" maxlength="200" '+
      'autocomplete="'+(up?"new-password":"current-password")+'">'+
    (up?'<input type="text" id="uName" placeholder="name on the board" maxlength="24" autocomplete="nickname">':'')+
    '</div>'+
    (err?'<p class="err">'+esc(err)+'</p>':
      '<p class="note">'+(up?"Your username and password are all this keeps. No email, nothing else."
        :"Your levels, stars and scores follow your account to any phone.")+'</p>')+
    '<div class="acts"><button class="btn" data-act="close">Not now</button>'+
    '<button class="btn primary" data-act="'+(up?"dosignup":"dosignin")+'">'+(up?"Create account":"Sign in")+'</button></div>';
  modal(h);
  var f=$("#uHandle");
  if(f){
    setTimeout(function(){try{f.focus()}catch(e){}},60);
    f.oninput=function(){this.value=this.value.toLowerCase().replace(/[^a-z0-9_]/g,"")};
    var p=$("#uPass");
    if(p) p.onkeydown=function(e){if(e.key==="Enter") doSign(up)};
  }
}
function editCard(msg,err){
  var h='<h2>Your profile</h2><div class="avpick">';
  var i,a;
  for(i=0;i<PRESETS.length;i++){
    a="p:"+PRESETS[i];
    h+='<button class="avopt'+(ME.avatar===a?" on":"")+'" data-act="avpick" data-av="'+a+'">'+avaHTML(a,ME.ini,"")+'</button>';
  }
  h+='</div><div class="form">'+
    '<input type="text" id="pName" placeholder="name on the board" maxlength="24" value="'+esc(ME.name)+'">'+
    '<input type="text" id="pIni" placeholder="AAA" maxlength="3" value="'+esc(ME.ini)+'">'+
    '<input type="text" id="pBio" placeholder="a line about you" maxlength="140" value="'+esc(ME.bio||"")+'">'+
    '</div>'+
    (err?'<p class="err">'+esc(err)+'</p>':msg?'<p class="ok">'+esc(msg)+'</p>':
      '<p class="note">The initials show on small score rows. Pictures stay under 2MB and are squared off.</p>')+
    '<input type="file" id="avFile" accept="image/png,image/jpeg,image/webp,image/gif" hidden>'+
    '<div class="acts"><button class="btn" data-act="pickfile">Upload a picture</button>'+
    '<button class="btn primary" data-act="saveprof">Save</button></div>'+
    '<p class="note"><button class="linkbtn" data-act="pwcard">Change password</button> &middot; '+
    '<button class="linkbtn" data-act="me">Back to profile</button></p>';
  modal(h,true);
  var fi=$("#avFile");
  if(fi) fi.onchange=function(){uploadAvatar(fi.files&&fi.files[0])};
}
function passCard(err,msg){
  modal('<h2>Change password</h2><div class="form">'+
    '<input type="password" id="pwOld" placeholder="current password" autocomplete="current-password">'+
    '<input type="password" id="pwNew" placeholder="new password" autocomplete="new-password">'+
    '</div>'+
    (err?'<p class="err">'+esc(err)+'</p>':msg?'<p class="ok">'+esc(msg)+'</p>':
      '<p class="note">Changing it signs out any other phone you are on.</p>')+
    '<div class="acts"><button class="btn" data-act="editprof">Back</button>'+
    '<button class="btn primary" data-act="dopw">Change it</button></div>');
}

/* ---------------- actions ---------------- */
function val(id){var e=$(id);return e?e.value:""}
function doSign(up){
  var handle=val("#uHandle").trim(),pass=val("#uPass");
  if(handle.length<3) return signCard(up?"up":"in","Usernames are at least three characters.");
  if(pass.length<1) return signCard(up?"up":"in","Put your password in.");
  var body=up?{handle:handle,pass:pass,name:val("#uName").trim()||handle,ini:(val("#uName")||handle).slice(0,3)}
             :{handle:handle,pass:pass};
  api(up?"/api/signup":"/api/login",body).then(function(j){
    setMe(j);
    pullProgress();
    accountCard(up?"Profile created. Add a picture whenever you like.":"Signed in.");
  }).catch(function(e){signCard(up?"up":"in",e.message)});
}
function saveProfile(){
  api("/api/profile",{name:val("#pName").trim(),ini:val("#pIni"),bio:val("#pBio").trim()})
    .then(function(j){setMe(j);prog.ini=ME.ini;save();accountCard("Profile saved.")})
    .catch(function(e){editCard("",e.message)});
}
function pickAvatar(a){
  api("/api/profile",{avatar:a}).then(function(j){setMe(j);editCard("Avatar set.")})
    .catch(function(e){editCard("",e.message)});
}
// Photos come off a phone camera at several thousand pixels. Square and shrink
// them here, so what goes up is a small PNG whatever the player picked.
function uploadAvatar(file){
  if(!file) return;
  if(file.size>20*1024*1024) return editCard("","That picture is too big.");
  var url=URL.createObjectURL(file),img=new Image();
  img.onload=function(){
    var m=256,side=Math.min(img.width,img.height),c=document.createElement("canvas");
    c.width=c.height=Math.min(m,side)||m;
    var x=c.getContext("2d");
    x.drawImage(img,(img.width-side)/2,(img.height-side)/2,side,side,0,0,c.width,c.height);
    URL.revokeObjectURL(url);
    c.toBlob(function(bl){
      if(!bl) return editCard("","Could not read that picture.");
      fetch("/api/avatar",{method:"POST",credentials:"same-origin",
        headers:{"content-type":"image/png"},body:bl})
        .then(function(r){return r.json().catch(function(){return {}}).then(function(j){
          if(!r.ok) throw new Error(j.error||"Could not upload that picture.");
          return j})})
        .then(function(j){setMe(j);editCard("Picture saved.")})
        .catch(function(e){editCard("",e.message)});
    },"image/png");
  };
  img.onerror=function(){URL.revokeObjectURL(url);editCard("","Could not read that picture.")};
  img.src=url;
}
function signOut(){
  api("/api/logout",{}).then(function(){setMe(null);hideModal();toast("Signed out.")}).catch(function(){});
}

/* ---------------- progress sync ---------------- */
function progBody(){
  return {star:prog.star||{},best:prog.best||{},rec:prog.rec||{},clean:prog.clean||{},ini:prog.ini||""};
}
function mergeProg(r){
  if(!r) return false;
  var ch=false,k;
  prog.star=prog.star||{};prog.best=prog.best||{};prog.rec=prog.rec||{};prog.clean=prog.clean||{};
  for(k in (r.star||{})) if(!prog.star[k]||r.star[k]>prog.star[k]){prog.star[k]=r.star[k];ch=true}
  for(k in (r.best||{})) if(!prog.best[k]||r.best[k]<prog.best[k]){prog.best[k]=r.best[k];ch=true}
  for(k in (r.rec||{})) if(r.rec[k]&&(!prog.rec[k]||r.rec[k].sc>prog.rec[k].sc)){prog.rec[k]=r.rec[k];ch=true}
  for(k in (r.clean||{})) if(!prog.clean[k]){prog.clean[k]=1;ch=true}
  return ch;
}
function pullProgress(){
  if(!ME) return;
  api("/api/progress?game="+encodeURIComponent(GAME)).then(function(j){
    var ch=mergeProg(j&&j.data);
    if(ME.ini) prog.ini=ME.ini;
    if(ch){save();paintChrome();paint();if($("#profCard")) accountCard("",true)}
    pushProgress(true);
  }).catch(function(){});
}
function pushProgress(soon){
  if(!ME||!onWeb()) return;
  var s=JSON.stringify(progBody());
  if(s===lastPush) return;
  clearTimeout(syncT);
  syncT=setTimeout(function(){
    lastPush=s;
    api("/api/progress",{game:GAME,data:JSON.parse(s)}).catch(function(){lastPush=""});
  },soon?80:4000);
}
'''

ACTS = '''  else if(a==="me"){accountCard();return}
  else if(a==="tabin"){signCard("in","");return}
  else if(a==="tabup"){signCard("up","");return}
  else if(a==="dosignin"){doSign(false);return}
  else if(a==="dosignup"){doSign(true);return}
  else if(a==="editprof"){editCard("","");return}
  else if(a==="saveprof"){saveProfile();return}
  else if(a==="avpick"){pickAvatar(b.dataset.av);return}
  else if(a==="pickfile"){var fi=$("#avFile");if(fi)fi.click();return}
  else if(a==="pwcard"){passCard("","");return}
  else if(a==="dopw"){
    api("/api/password",{old:val("#pwOld"),pass:val("#pwNew")})
      .then(function(){passCard("","Password changed.")})
      .catch(function(e){passCard(e.message,"")});
    return;
  }
  else if(a==="signout"){signOut();return}
'''


def swap(s, old, new, what):
    assert s.count(old) == 1, what + ' anchor missing or ambiguous'
    return s.replace(old, new, 1)


def build(path, piece):
    s = pathlib.Path(path).read_text(encoding='utf-8')

    if OLD_HEAD in s:
        s = swap(s, OLD_HEAD, NEW_HEAD, 'header')
    else:
        s = swap(s, OLD_HEAD_ALT, NEW_HEAD_ALT, 'header')

    s = swap(s, '@media (max-width:379px){', CSS.strip() + '\n@media (max-width:379px){', 'css')

    s = swap(s, '/* ---------------- persistence ---------------- */',
             JS.replace('__PIECE__', piece).strip() +
             '\n\n/* ---------------- persistence ---------------- */', 'accounts module')

    # Every local save is a candidate for the cloud copy; pushProgress drops
    # the ones where nothing actually changed.
    s = swap(s, '''    }));
  }catch(e){}
}''', '''    }));
  }catch(e){}
  pushProgress();
}''', 'save hook')

    s = swap(s, '  else if(a==="close") hideModal();', ACTS + '  else if(a==="close") hideModal();', 'actions')

    s = swap(s, '  startLeaderboard();', '  startLeaderboard();\n  startAccount();', 'start hook')

    # A level finished without losing a life is worth a badge, so remember it.
    s = swap(s, '''    if(!prog.best[level]||elapsed<prog.best[level]) prog.best[level]=elapsed;''',
             '''    if(!prog.best[level]||elapsed<prog.best[level]) prog.best[level]=elapsed;
    if(strikes===0){prog.clean=prog.clean||{};prog.clean[level]=1}''', 'clean run')

    # Signed in, the score is already the account's: post it and skip the
    # three-letter prompt. Signed out, nothing changes.
    s = swap(s, '''    pending=isRec?{k:level,ini:prog.ini||"",sc:sc,t:elapsed}:null;''',
             '''    pending=isRec?{k:level,ini:(ME?ME.ini:prog.ini)||"",sc:sc,t:elapsed}:null;
    if(isRec&&ME){saveRecord(level,{ini:ME.ini,sc:sc,t:elapsed,at:Date.now()});pending=null}''',
             'auto record')

    s = swap(s, """        (isRec?'<div class="ini"><input id="iniIn" maxlength="3" autocomplete="off" spellcheck="false" '+
               'placeholder="AAA" value="'+(prog.ini||"")+'"><button class="btn primary" data-act="saveini">Save</button></div>':'')+""",
             """        (isRec&&ME?'<p class="ok">Saved to '+esc(ME.name)+'</p>':'')+
        (isRec&&!ME?'<div class="ini"><input type="text" id="iniIn" maxlength="3" autocomplete="off" spellcheck="false" '+
               'placeholder="AAA" value="'+(prog.ini||"")+'"><button class="btn primary" data-act="saveini">Save</button></div>'+
               '<p class="note">A profile keeps your scores, stars and badges on every phone. '+
               '<button class="linkbtn" data-act="me">Create one</button></p>':'')+""",
             'win card')

    # Score rows carry a name and a picture once there is an account behind them.
    s = swap(s, """      h+='<div class="rec"><span>'+(i+1)+'</span><b>'+(rows[i].ini||"---")+'</b><i>'+fmt(rows[i].t)+'</i><em>'+rows[i].sc+'</em></div>';""",
             """      h+=recRow(i+1,rows[i]);""", 'record row')

    s = swap(s, 'function leaderboard(){', '''function recRow(place,r){
  var who=r.name?avaHTML(r.av,r.name.slice(0,1).toUpperCase(),"sm")+'<b>'+esc(r.name)+'</b>'
                :'<b>'+esc(r.ini||"---")+'</b>';
  return '<div class="rec"><span>'+place+'</span><div class="who">'+who+'</div><i>'+
    fmt(r.t)+'</i><em>'+r.sc+'</em></div>';
}
function leaderboard(){''', 'recRow')

    pathlib.Path(path).write_text(s, encoding='utf-8')
    print(path, len(s), 'bytes')


build('web/trixdoku.html', 'art/trix-piece.png')
build('web/cocodoku.html', 'art/coco-piece.png')
import shutil
shutil.copy('web/cocodoku.html', 'web/index.html')
print('accounts added')
