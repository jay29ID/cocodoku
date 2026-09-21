#!/usr/bin/env python3
"""Build the web (self-hosted) copies of the games.

Runs AFTER make.sh. Takes the artifact builds and makes three changes:

1. The leaderboard talks to /api/records on our own server instead of the
   dormant claude.use("db") path, so the board is genuinely shared.
2. The Records screen becomes per-level: each level keeps its own top five
   rather than a single record, which is what Jason asked for on 2026-09-21.
3. Each game is wrapped in a real HTML document, because the originals were
   written as Artifact bodies and carry no doctype, head or viewport meta.

Output goes in web/ and is committed to the repo Railway builds from.
"""
import pathlib, shutil

# ---------------------------------------------------------------- leaderboard

OLD_START = '''function startLeaderboard(){
  if(!window.claude||!claude.use) return;
  Promise.resolve(claude.use("db")).then(function(db){
    DB=db||null;
    if(!DB) return;
    try{
      DB.collection("records").onSnapshot(function(snap){
        snap.docs.forEach(function(d){
          var v=d.data();
          if(v&&typeof v.sc==="number") shared[d.id]=v;
        });
      },function(){});
    }catch(e){}
  }).catch(function(){});
  Promise.resolve(claude.use("user")).then(function(u){
    if(u&&u.id) return u.id();
  }).then(function(id){UID=id||null}).catch(function(){});
}'''

NEW_START = '''var GAME=KEY.split(".")[0],LIVE=false,boardSeq=0,boardLv=null;
function onWeb(){return location.protocol==="http:"||location.protocol==="https:"}
function pullBoard(cb){
  if(!onWeb()) return;
  fetch("/api/records?game="+encodeURIComponent(GAME),{cache:"no-store"})
    .then(function(r){return r.ok?r.json():null})
    .then(function(j){
      if(j&&j.records){LIVE=true;shared=j.records;if(cb)cb()}
    }).catch(function(){});
}
function startLeaderboard(){pullBoard()}
function openBoard(){
  var s=++boardSeq;
  leaderboard();
  pullBoard(function(){if(s===boardSeq&&$("#boardCard"))leaderboard()});
}'''

OLD_WRITE = '''  if(DB){
    var cur=shared[k];
    if(!cur||rec.sc>cur.sc){
      try{DB.doc("records/"+k).set(rec).catch(function(){})}catch(e){}
    }
  }'''

NEW_WRITE = '''  if(onWeb()){
    fetch("/api/records",{method:"POST",headers:{"content-type":"application/json"},
      body:JSON.stringify({game:GAME,level:k,ini:rec.ini,sc:rec.sc,t:rec.t})})
      .then(function(r){return r.ok?r.json():null})
      .then(function(j){if(j&&j.records){LIVE=true;shared=j.records}})
      .catch(function(){});
  }'''

# A level's scores arrive from the server as a list. Older saves, and the
# device's own fallback, hold a single record, so read both shapes.
OLD_RECORDFOR = '''function recordFor(k){
  var a=shared[k],b=prog.rec&&prog.rec[k];
  if(a&&b) return a.sc>=b.sc?a:b;
  return a||b||null;
}'''

NEW_RECORDFOR = '''var KEEP=5;
function scoresFor(k){
  var v=shared[k];
  if(v&&v.length!==undefined) return v.slice(0,KEEP);
  if(v) return [v];
  var b=prog.rec&&prog.rec[k];
  return b?[b]:[];
}
function recordFor(k){var a=scoresFor(k);return a.length?a[0]:null}
function makesBoard(k,sc){
  var a=scoresFor(k);
  return a.length<KEEP||sc>a[a.length-1].sc;
}'''

OLD_BOARD = '''function boardRows(){
  var rows=[],k;
  for(k=0;k<LEVELS.length;k++){
    var r=recordFor(k);
    if(r) rows.push({k:k,ini:r.ini||"---",sc:r.sc,t:r.t});
  }
  return rows;
}
function leaderboard(){
  var rows=boardRows(),h='<h2>Records</h2>';
  if(!rows.length){
    h+='<p>No records yet. Finish a level and the first one is yours.</p>';
  }else{
    var tot={},i;
    for(i=0;i<rows.length;i++) tot[rows[i].ini]=(tot[rows[i].ini]||0)+rows[i].sc;
    var names=Object.keys(tot).sort(function(a,b){return tot[b]-tot[a]});
    h+='<div class="tot">';
    for(i=0;i<names.length&&i<6;i++) h+='<span><b>'+names[i]+'</b> '+tot[names[i]]+'</span>';
    h+='</div><div class="recs">';
    for(i=0;i<rows.length;i++)
      h+='<div class="rec"><span>'+(rows[i].k+1)+'</span><b>'+rows[i].ini+'</b><i>'+fmt(rows[i].t)+'</i><em>'+rows[i].sc+'</em></div>';
    h+='</div>';
  }
  h+='<div class="acts"><button class="btn" data-act="levels">Levels</button>'+
     '<button class="btn primary" data-act="close">Back</button></div>';
  modal(h,true);
}'''

NEW_BOARD = '''function playedLevels(){
  var o=[],k;
  for(k=0;k<LEVELS.length;k++) if(scoresFor(k).length) o.push(k);
  return o;
}
function overallTotals(){
  var tot={},k,i,a;
  for(k=0;k<LEVELS.length;k++){
    a=scoresFor(k);
    if(a.length) tot[a[0].ini||"---"]=(tot[a[0].ini||"---"]||0)+a[0].sc;
  }
  return tot;
}
function leaderboard(){
  var have=playedLevels(),i;
  if(have.length&&have.indexOf(boardLv)<0)
    boardLv=have.indexOf(level)>=0?level:have[0];
  var h='<h2 id="boardCard">Records</h2>';
  if(!have.length){
    h+='<p>No scores yet. Finish a level and the first one is yours.</p>';
  }else{
    h+='<div class="lvpick">';
    for(i=0;i<have.length;i++)
      h+='<button class="lvchip'+(have[i]===boardLv?" on":"")+'" data-act="board" data-bl="'+have[i]+'">'+(have[i]+1)+'</button>';
    h+='</div><div class="lvhead">Level '+(boardLv+1)+'</div><div class="recs">';
    var rows=scoresFor(boardLv);
    for(i=0;i<rows.length;i++)
      h+='<div class="rec"><span>'+(i+1)+'</span><b>'+(rows[i].ini||"---")+'</b><i>'+fmt(rows[i].t)+'</i><em>'+rows[i].sc+'</em></div>';
    h+='</div>';
    var tot=overallTotals();
    var names=Object.keys(tot).sort(function(a,b){return tot[b]-tot[a]});
    if(names.length){
      h+='<div class="lvhead">Overall</div><div class="tot">';
      for(i=0;i<names.length&&i<6;i++) h+='<span><b>'+names[i]+'</b> '+tot[names[i]]+'</span>';
      h+='</div>';
    }
  }
  h+='<p class="note">'+(LIVE?"Everyone who plays shares this board.":"Offline \\u2014 showing this device only.")+'</p>';
  h+='<div class="acts"><button class="btn" data-act="levels">Levels</button>'+
     '<button class="btn primary" data-act="close">Back</button></div>';
  modal(h,true);
}'''

BOARD_CSS = '''
.lvpick{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin:0 0 10px;max-height:104px;overflow:auto}
.lvchip{font-family:inherit;font-weight:900;font-size:13px;min-width:36px;padding:5px 8px;border-radius:10px;
  border:2px solid var(--edge);background:var(--surface2);color:var(--muted);cursor:pointer}
.lvchip.on{background:var(--grass);border-color:var(--grass-deep);color:#fff}
.lvhead{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
  text-align:left;margin:0 0 4px;padding:0 4px}
.note{font-size:11.5px;font-weight:600;color:var(--muted);margin:10px 0 14px;line-height:1.4}
'''

# The win card offers the initials prompt whenever the score reaches the board,
# not only when it beats the top of it, or fourth place could never be saved.
OLD_ISREC = '''    var held=recordFor(level);
    var isRec=!held||sc>held.sc;'''
NEW_ISREC = '''    var held=recordFor(level);
    var isRec=makesBoard(level,sc);'''

OLD_LABEL = """        '<div class="sub">'+(isRec?"new record":(held?"record "+held.ini+" "+held.sc:""))+'</div>'+"""
NEW_LABEL = """        '<div class="sub">'+(!held||sc>held.sc?"new record":(isRec?"on the board":(held?"best "+held.ini+" "+held.sc:"")))+'</div>'+"""

# ------------------------------------------------------------------- document

# The game files were written as Artifact bodies: they start at <title> with no
# doctype, head or body, because the Artifact runtime supplies all of that. A
# plain web server does not, and a page with no viewport meta is laid out by
# mobile Safari at 980px and then scaled down, which is why the board came out
# tiny on a phone. Served copies get a real document around them.
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#E9F0DC" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#141D18" media="(prefers-color-scheme: dark)">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="icon" href="{icon}">
<link rel="apple-touch-icon" href="{icon}">
"""


def wrap(body, icon):
    anchor = '<div id="app">'
    assert body.count(anchor) == 1, 'expected exactly one ' + anchor
    body = body.replace(anchor, '</head>\n<body>\n' + anchor, 1)
    return HEAD.format(icon=icon) + body.rstrip() + '\n</body>\n</html>\n'


def swap(s, old, new, what):
    assert old in s, what + ' anchor missing'
    return s.replace(old, new, 1)


def build(src, dst, icon):
    s = pathlib.Path(src).read_text(encoding='utf-8')
    s = swap(s, OLD_START, NEW_START, 'startLeaderboard')
    s = swap(s, OLD_WRITE, NEW_WRITE, 'saveRecord')
    s = swap(s, OLD_RECORDFOR, NEW_RECORDFOR, 'recordFor')
    s = swap(s, OLD_BOARD, NEW_BOARD, 'leaderboard')
    s = swap(s, OLD_ISREC, NEW_ISREC, 'isRec')
    s = swap(s, OLD_LABEL, NEW_LABEL, 'win card label')
    s = swap(s, 'else if(a==="records") leaderboard();',
             'else if(a==="records") openBoard();\n'
             '  else if(a==="board"){boardLv=b.dataset.bl|0;leaderboard();return}',
             'records action')
    s = swap(s, '.recs{', BOARD_CSS.strip() + '\n.recs{', 'records css')
    s = wrap(s, icon)
    pathlib.Path(dst).write_text(s, encoding='utf-8')
    print(dst, len(s), 'bytes')


web = pathlib.Path('web'); web.mkdir(exist_ok=True)
(web / 'art').mkdir(exist_ok=True)
build('trixdoku.html', 'web/trixdoku.html', 'art/trix-piece.png')
build('cocodoku.html', 'web/cocodoku.html', 'art/coco-piece.png')
shutil.copy('art/trix-web.png', 'web/art/trix-piece.png')
shutil.copy('art/coco-web.png', 'web/art/coco-piece.png')
pathlib.Path('web/cowdoku.html').write_text(
    wrap(pathlib.Path('cowdoku.html').read_text(encoding='utf-8'), 'tiles/grass-1.png'),
    encoding='utf-8')
shutil.copytree('tiles', 'web/tiles', dirs_exist_ok=True)
# Jason wants Cocodoku to be the game people land on, so it is the index.
# The three-game page (landing.html) stays reachable at /games.
shutil.copy('landing.html', 'web/games.html')
shutil.copy('web/cocodoku.html', 'web/index.html')
print('web build ready')
