#!/usr/bin/env python3
"""Challenge modes, and the boards and progress that come with them.

Runs LAST, over add_accounts.py's output in web/. Jason asked for this on
2026-09-25: "we need way more achievements, people are blowing through
content, need to come up with some sort of different modes, maybe a mode with
no x marking".

Three challenges play the same eighty levels under different rules, so the
ladder is worth four times as much without a single new puzzle:

  No marks          you cannot rule a square out, so a tap places the piece
  One life          one wrong placement ends the round
  Against the clock the three-star time is the whole budget, counting down

Each challenge keeps its own leaderboard (the server takes a mode alongside
the game) and its own stars, and scores are worth more in the harder ones.
The badges in add_accounts.py read the progress this step records.
"""
import pathlib, sys

# --------------------------------------------------------------- the module

MODULE = '''
/* ---------------- challenge modes ---------------- */
// The same levels under different rules. `chal` is the one being played,
// `pickChal` the one the level screen is showing, `boardChal` the one the
// Records screen is showing; all three are keys from this table.
var CHALS=[
  {k:"",n:"Normal",sn:"Normal",s:"Three lives, and you can rule squares out as you go.",m:1},
  {k:"nomark",n:"No marks",sn:"No marks",s:"No X marks at all. Nowhere to keep your thinking but your head.",m:1.6},
  {k:"onelife",n:"One life",sn:"One life",s:"One wrong __NAME__ and the round is over.",m:1.5},
  {k:"rush",n:"Against the clock",sn:"Clock",s:"The three-star time is the whole budget, counting down.",m:1.4}
];
var chal="",pickChal="",boardChal="";
function chalOf(k){var i;for(i=0;i<CHALS.length;i++) if(CHALS[i].k===(k||"")) return CHALS[i];return CHALS[0]}
function lives(){return chal==="onelife"?1:3}
function budget(){return par(n)}
function noMarks(){return chal==="nomark"}
function modeProg(c){var m=prog.mode||(prog.mode={});return m[c]||(m[c]={})}
function doneIn(k,c){return c?(modeProg(c)[k]||0):(prog.star[k]||0)}
function clearedAny(k){
  if(prog.star[k]) return true;
  var m=prog.mode||{},c;
  for(c in m) if(m[c][k]) return true;
  return false;
}
function chalChips(sel,act){
  var h='<div class="lvpick modes">',i,c;
  for(i=0;i<CHALS.length;i++){
    c=CHALS[i];
    h+='<button class="lvchip'+(c.k===sel?" on":"")+'" data-act="'+act+'" data-ck="'+c.k+'">'+c.n+'</button>';
  }
  return h+'</div>';
}
// Everything a finished level says about how it was played. The badges read
// these; nothing else does.
function noteRun(){
  prog.clean=prog.clean||{};prog.fast=prog.fast||{};prog.nohint=prog.nohint||{};
  prog.days=prog.days||{};prog.flags=prog.flags||{};
  if(strikes===0) prog.clean[level]=1;
  if(hints===0) prog.nohint[level]=1;
  if(elapsed<=Math.round(par(n)/2)) prog.fast[level]=1;
  if(lives()>1&&strikes===lives()-1) prog.flags.comeback=1;
  var d=new Date();
  prog.days[d.getFullYear()+"-"+(d.getMonth()+1)+"-"+d.getDate()]=1;
  if(d.getHours()<6) prog.flags.night=1;
}
function bestTime(){
  if(mode!=="level") return stats.best[n];
  if(chal) return (prog.mbest&&prog.mbest[chal]&&prog.mbest[chal][level])||0;
  return prog.best[level];
}
function paintTime(){
  var e=$("#time");
  if(!e) return;
  if(chal==="rush"&&mode==="level"){
    var left=Math.max(0,budget()-elapsed);
    e.textContent=fmt(left);
    e.classList.toggle("low",left<=10);
  }else{
    e.textContent=fmt(elapsed);
    e.classList.remove("low");
  }
}
'''

# ------------------------------------------------------- leaderboard, by mode

OLD_START = '''var GAME=KEY.split(".")[0],LIVE=false,boardSeq=0,boardLv=null;
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

NEW_START = '''var GAME=KEY.split(".")[0],LIVE=false,boardSeq=0,boardLv=null,boards={};
function onWeb(){return location.protocol==="http:"||location.protocol==="https:"}
function bkey(c){return c||""}
function pullBoard(c,cb){
  if(!onWeb()) return;
  c=bkey(c);
  fetch("/api/records?game="+encodeURIComponent(GAME)+"&mode="+encodeURIComponent(c),{cache:"no-store"})
    .then(function(r){return r.ok?r.json():null})
    .then(function(j){
      if(j&&j.records){LIVE=true;boards[c]=j.records;if(cb)cb()}
    }).catch(function(){});
}
function startLeaderboard(){pullBoard(chal)}
function openBoard(){
  boardChal=chal;
  var s=++boardSeq;
  leaderboard();
  pullBoard(boardChal,function(){if(s===boardSeq&&$("#boardCard"))leaderboard()});
}
function showBoard(c){
  boardChal=bkey(c);
  var s=++boardSeq;
  boardLv=null;
  leaderboard();
  pullBoard(boardChal,function(){if(s===boardSeq&&$("#boardCard"))leaderboard()});
}'''

OLD_SCORESFOR = '''var KEEP=5;
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

NEW_SCORESFOR = '''var KEEP=5;
// Every challenge has its own board, so a level's scores are only ever read
// for one mode at a time: the one being played, or the one being looked at.
function rkey(k,c){return c?c+":"+k:""+k}
function scoresFor(k,c){
  c=bkey(c===undefined?chal:c);
  var v=(boards[c]||{})[k];
  if(v&&v.length!==undefined) return v.slice(0,KEEP);
  if(v) return [v];
  var b=prog.rec&&prog.rec[rkey(k,c)];
  return b?[b]:[];
}
function recordFor(k,c){var a=scoresFor(k,c);return a.length?a[0]:null}
function makesBoard(k,sc,c){
  var a=scoresFor(k,c);
  return a.length<KEEP||sc>a[a.length-1].sc;
}'''

OLD_SAVEREC = '''function saveRecord(k,rec){
  prog.rec=prog.rec||{};prog.rec[k]=rec;prog.ini=rec.ini;save();
  if(onWeb()){
    fetch("/api/records",{method:"POST",headers:{"content-type":"application/json"},
      body:JSON.stringify({game:GAME,level:k,ini:rec.ini,sc:rec.sc,t:rec.t})})
      .then(function(r){return r.ok?r.json():null})
      .then(function(j){if(j&&j.records){LIVE=true;shared=j.records}})
      .catch(function(){});
  }
}'''

NEW_SAVEREC = '''function saveRecord(k,rec){
  var c=bkey(chal);
  prog.rec=prog.rec||{};prog.rec[rkey(k,c)]=rec;prog.ini=rec.ini;save();
  if(onWeb()){
    fetch("/api/records",{method:"POST",headers:{"content-type":"application/json"},
      body:JSON.stringify({game:GAME,mode:c,level:k,ini:rec.ini,sc:rec.sc,t:Math.max(1,rec.t)})})
      .then(function(r){return r.ok?r.json():null})
      .then(function(j){if(j&&j.records){LIVE=true;boards[c]=j.records}})
      .catch(function(){});
  }
}'''

OLD_BOARDROWS = '''function playedLevels(){
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
}'''

NEW_BOARDROWS = '''function playedLevels(){
  var o=[],k;
  for(k=0;k<LEVELS.length;k++) if(scoresFor(k,boardChal).length) o.push(k);
  return o;
}
function overallTotals(){
  var tot={},k,a,who;
  for(k=0;k<LEVELS.length;k++){
    a=scoresFor(k,boardChal);
    if(a.length){who=a[0].name||a[0].ini||"---";tot[who]=(tot[who]||0)+a[0].sc}
  }
  return tot;
}'''

OLD_BOARDHEAD = '''  var h='<h2 id="boardCard">Records</h2>';
  if(!have.length){
    h+='<p>No scores yet. Finish a level and the first one is yours.</p>';
  }else{'''

NEW_BOARDHEAD = '''  var h='<h2 id="boardCard">Records</h2>'+chalChips(boardChal,"bmode");
  if(!have.length){
    h+='<p>Nothing on this board yet. Finish a level in this mode and the first one is yours.</p>';
  }else{'''

# ------------------------------------------------------------ the level screen

OLD_PICKER = '''function levelPicker(){
  var h='<h2>Levels</h2><div class="levels">',k;
  for(k=0;k<LEVELS.length;k++){
    var st=prog.star[k]||0,ok=unlocked(k);'''

NEW_PICKER = '''function levelPicker(keep){
  if(!keep) pickChal=chal;
  var h='<h2>Levels</h2>'+chalChips(pickChal,"pmode")+
    '<p class="note">'+chalOf(pickChal).s+'</p><div class="levels">',k;
  for(k=0;k<LEVELS.length;k++){
    var st=doneIn(k,pickChal),ok=unlocked(k);'''

OLD_UNLOCK = 'function unlocked(k){return k===0||!!prog.star[k-1]}'
NEW_UNLOCK = 'function unlocked(k){return k===0||clearedAny(k-1)}'

OLD_STARTLEVEL = '''function startLevel(k){
  if(k<0||k>=LEVELS.length) return;
  var L=decodeLevel(k);
  mode="level";level=k;'''

NEW_STARTLEVEL = '''function startLevel(k,c){
  if(k<0||k>=LEVELS.length) return;
  var L=decodeLevel(k);
  if(c!==undefined) chal=chalOf(c).k;
  if(!boards[bkey(chal)]) pullBoard(chal);
  mode="level";level=k;'''

# ------------------------------------------------------------------ gameplay

OLD_LIVES = '''function paintLives(){
  var h="",i;
  for(i=0;i<3;i++) h+=heart(i<3-strikes);
  $("#hearts").innerHTML=h;
}'''
NEW_LIVES = '''function paintLives(){
  var h="",i,L=lives();
  for(i=0;i<L;i++) h+=heart(i<L-strikes);
  $("#hearts").innerHTML=h;
}'''

OLD_STRIKETXT = '''+" &mdash; strike "+strikes+" of 3");'''
NEW_STRIKETXT = '''+" &mdash; strike "+strikes+" of "+lives());'''

OLD_STRIKEMAX = '''  if(strikes>=3){
    lost=true;runTimer(false);save();paint();
    setTimeout(loseGame,900);
  }'''
NEW_STRIKEMAX = '''  if(strikes>=lives()){
    lost=true;runTimer(false);save();paint();
    setTimeout(loseGame,900);
  }'''

OLD_TICK = '''function tick(){elapsed++;$("#time").textContent=fmt(elapsed);if(elapsed%5===0)save()}'''
NEW_TICK = '''function tick(){
  elapsed++;
  paintTime();
  if(chal==="rush"&&mode==="level"&&elapsed>=budget()){
    lost=true;runTimer(false);save();paint();
    setTimeout(loseGame,400);
    return;
  }
  if(elapsed%5===0)save();
}'''

OLD_PAINTTIME = '''  $("#time").textContent=fmt(elapsed);
}'''
NEW_PAINTTIME = '''  paintTime();
}'''

OLD_BESTCHIP = '''  $("#best").textContent=mode==="level"?(prog.best[level]?fmt(prog.best[level]):"—"):(stats.best[n]?fmt(stats.best[n]):"—");'''
NEW_BESTCHIP = '''  $("#best").textContent=bestTime()?fmt(bestTime()):"—";'''

OLD_LOSE = '''    modal('<h2>Bad Dog! You failed!</h2>'+
      '<p>Three placements that could never be right. The board is the same every time, so you keep what you worked out.</p>'+'''
NEW_LOSE = '''    modal('<h2>Bad Dog! You failed!</h2>'+
      '<p>'+(chal==="rush"?"The clock ran out."
        :lives()===1?"One placement that could never be right, and that was the one life."
        :"Three placements that could never be right.")+
      ' The board is the same every time, so you keep what you worked out.</p>'+'''

# Tapping an empty square rules it out, which is the whole thing No marks takes
# away: there a tap places the piece and a tap on a piece takes it back.
OLD_DOWN = '''  if(marks[i]===0){setMark(i,1);p.pushed=true;afterMove();}
  else paint();'''
NEW_DOWN = '''  if(!noMarks()&&marks[i]===0){setMark(i,1);p.pushed=true;afterMove();}
  else paint();'''

OLD_DRAG = '''  if(!press.moved||press.from!==0||press.fired) return;'''
NEW_DRAG = '''  if(!press.moved||press.from!==0||press.fired||noMarks()) return;'''

OLD_TAP = '''  if(p.fired||p.moved){lastTap.i=-1;return}
  var now=Date.now();'''
NEW_TAP = '''  if(p.fired||p.moved){lastTap.i=-1;return}
  if(noMarks()){
    lastTap.i=-1;
    if(marks[p.i]===2){setMark(p.i,0);afterMove()}
    else putCow(p.i);
    return;
  }
  var now=Date.now();'''

OLD_KEY = '''  if(k===" "){setMark(cursor,marks[cursor]?0:1);afterMove();e.preventDefault()}'''
NEW_KEY = '''  if(k===" "){if(!noMarks()){setMark(cursor,marks[cursor]?0:1);afterMove()}e.preventDefault()}'''

# ---------------------------------------------------------------------- win

OLD_WIN = '''    var st=starsFor(elapsed,n,hints>0);
    if(!prog.star[level]||prog.star[level]<st) prog.star[level]=st;
    if(!prog.best[level]||elapsed<prog.best[level]) prog.best[level]=elapsed;
    if(strikes===0){prog.clean=prog.clean||{};prog.clean[level]=1}
    var sc=scoreFor(elapsed,n,strikes,hints);'''
NEW_WIN = '''    var st=starsFor(elapsed,n,hints>0);
    if(chal){
      var mp=modeProg(chal);
      if(!mp[level]||mp[level]<st) mp[level]=st;
      prog.mbest=prog.mbest||{};prog.mbest[chal]=prog.mbest[chal]||{};
      if(!prog.mbest[chal][level]||elapsed<prog.mbest[chal][level]) prog.mbest[chal][level]=elapsed;
    }else{
      if(!prog.star[level]||prog.star[level]<st) prog.star[level]=st;
      if(!prog.best[level]||elapsed<prog.best[level]) prog.best[level]=elapsed;
    }
    noteRun();
    var sc=Math.round(scoreFor(elapsed,n,strikes,hints)*chalOf(chal).m);'''

OLD_WINSUB = '''        '<div class="sub">'+starRow(st)+' &middot; '+(3-strikes)+' of 3 lives left'+'</div>'+'''
NEW_WINSUB = '''        '<div class="sub">'+starRow(st)+' &middot; '+(chal?chalOf(chal).n:(lives()-strikes)+' of '+lives()+' lives left')+'</div>'+'''

# --------------------------------------------------------------- persistence

OLD_SAVE = '''      mode:mode,level:level,prog:prog'''
NEW_SAVE = '''      mode:mode,level:level,chal:chal,prog:prog'''

OLD_LOAD = '''    mode=s.mode==="level"?"level":"free";level=typeof s.level==="number"?s.level:-1;'''
NEW_LOAD = '''    mode=s.mode==="level"?"level":"free";level=typeof s.level==="number"?s.level:-1;
    chal=chalOf(s.chal).k;'''

OLD_FREE = '''  mode="free";level=-1;'''
NEW_FREE = '''  mode="free";level=-1;chal="";'''

# ------------------------------------------------------------------- actions

OLD_ACTS = '''  else if(a==="board"){boardLv=b.dataset.bl|0;leaderboard();return}'''
NEW_ACTS = '''  else if(a==="board"){boardLv=b.dataset.bl|0;leaderboard();return}
  else if(a==="bmode"){showBoard(b.dataset.ck);return}
  else if(a==="pmode"){pickChal=chalOf(b.dataset.ck).k;levelPicker(true);return}'''

OLD_LVCLICK = '''  if(lb&&!lb.disabled){startLevel(lb.dataset.lv|0);return}'''
NEW_LVCLICK = '''  if(lb&&!lb.disabled){startLevel(lb.dataset.lv|0,pickChal);return}'''

# ----------------------------------------------------------------- the news

OLD_NEWS = '''var NEWS="lv"+LEVELS.length;
function newsCard(){
  if(prog.news===NEWS) return;'''
NEW_NEWS = '''function newsId(){return "lv"+LEVELS.length+"c"+CHALS.length}
function newsCard(){
  if(prog.news===newsId()) return;'''

OLD_NEWSSET = '''  prog.news=NEWS;save();'''
NEW_NEWSSET = '''  prog.news=newsId();save();'''

OLD_NEWSCARD = '''  var top=LEVELS[LEVELS.length-1].n;
  modal('<h2>New levels</h2><p>The ladder is longer: '+LEVELS.length+
    ' levels now, up to '+top+'x'+top+'. Your progress is where you left it.</p>'+
    '<div class="acts"><button class="btn" data-act="close">Later</button>'+
    '<button class="btn primary" data-act="levels">Show me</button></div>');'''
NEW_NEWSCARD = '''  modal('<h2>Three new ways to play</h2><p>Every level can now be played with '+
    '<b>no marks</b>, on <b>one life</b>, or <b>against the clock</b>. Each one keeps its own '+
    'scores and stars, and the harder the rules the more the points are worth. '+
    'There are new badges to go with them on your profile.</p>'+
    '<div class="acts"><button class="btn" data-act="close">Later</button>'+
    '<button class="btn primary" data-act="levels">Show me</button></div>');'''

# ------------------------------------------------------------------ the foot

OLD_FOOT = '''  $("#foot").innerHTML="Level "+(k+1)+", "+n+"&times;"+n+". Tap to rule a square out, hold or double-tap to place <b>__NAME__</b>.";'''
NEW_FOOT = '''  $("#foot").innerHTML="Level "+(k+1)+", "+n+"&times;"+n+". "+
    (noMarks()?"Tap to place <b>__NAME__</b>. No marks in this one."
      :"Tap to rule a square out, hold or double-tap to place <b>__NAME__</b>.")+
    (chal==="rush"?" "+fmt(budget())+" on the clock.":chal==="onelife"?" One life.":"");'''

CSS = '''
.lvpick.modes{max-height:none;margin-bottom:8px}
.lvpick.modes .lvchip{min-width:0;font-size:12px;padding:5px 10px}
.chip b.low{color:var(--barn)}
'''


def swap(s, old, new, what, count=1):
    assert s.count(old) == count, what + ' anchor missing or ambiguous (%d)' % s.count(old)
    return s.replace(old, new, count)


def build(path, name):
    s = pathlib.Path(path).read_text(encoding='utf-8')

    s = swap(s, '/* ---------------- accounts ---------------- */',
             MODULE.replace('__NAME__', name).strip() +
             '\n\n/* ---------------- accounts ---------------- */', 'module')

    s = swap(s, OLD_START, NEW_START, 'leaderboard start')
    s = swap(s, OLD_SCORESFOR, NEW_SCORESFOR, 'scoresFor')
    s = swap(s, OLD_SAVEREC, NEW_SAVEREC, 'saveRecord')
    s = swap(s, OLD_BOARDROWS, NEW_BOARDROWS, 'board rows')
    s = swap(s, OLD_BOARDHEAD, NEW_BOARDHEAD, 'board head')
    # the rows themselves have to follow the board being looked at, not the
    # mode being played
    s = swap(s, '    var rows=scoresFor(boardLv);', '    var rows=scoresFor(boardLv,boardChal);', 'board rows read')
    s = swap(s, OLD_PICKER, NEW_PICKER, 'level picker')
    s = swap(s, OLD_UNLOCK, NEW_UNLOCK, 'unlocked')
    s = swap(s, OLD_STARTLEVEL, NEW_STARTLEVEL, 'startLevel')
    s = swap(s, OLD_LIVES, NEW_LIVES, 'paintLives')
    s = swap(s, OLD_STRIKETXT, NEW_STRIKETXT, 'strike text')
    s = swap(s, OLD_STRIKEMAX, NEW_STRIKEMAX, 'strike limit')
    s = swap(s, OLD_TICK, NEW_TICK, 'tick')
    s = swap(s, OLD_PAINTTIME, NEW_PAINTTIME, 'paint time')
    s = swap(s, OLD_BESTCHIP, NEW_BESTCHIP, 'best chip')
    s = swap(s, OLD_LOSE, NEW_LOSE, 'lose card')
    s = swap(s, OLD_DOWN, NEW_DOWN, 'pointerdown')
    s = swap(s, OLD_DRAG, NEW_DRAG, 'drag marking')
    s = swap(s, OLD_TAP, NEW_TAP, 'tap')
    s = swap(s, OLD_KEY, NEW_KEY, 'space key')
    s = swap(s, OLD_WIN, NEW_WIN, 'win recording')
    s = swap(s, OLD_WINSUB, NEW_WINSUB, 'win card sub')
    s = swap(s, OLD_SAVE, NEW_SAVE, 'save')
    s = swap(s, OLD_LOAD, NEW_LOAD, 'load')
    s = swap(s, OLD_FREE, NEW_FREE, 'free play')
    s = swap(s, OLD_ACTS, NEW_ACTS, 'actions')
    s = swap(s, OLD_LVCLICK, NEW_LVCLICK, 'level click')
    s = swap(s, OLD_NEWS, NEW_NEWS, 'news id')
    s = swap(s, OLD_NEWSSET, NEW_NEWSSET, 'news set')
    s = swap(s, OLD_NEWSCARD, NEW_NEWSCARD, 'news card')
    s = swap(s, OLD_FOOT.replace('__NAME__', name), NEW_FOOT.replace('__NAME__', name), 'foot')
    s = swap(s, '@media (max-width:439px){', CSS.strip() + '\n@media (max-width:439px){', 'css')

    pathlib.Path(path).write_text(s, encoding='utf-8')
    print(path, len(s), 'bytes')


build('web/trixdoku.html', 'Trix')
build('web/cocodoku.html', 'Coco')
import shutil
shutil.copy('web/cocodoku.html', 'web/index.html')
print('modes added')
