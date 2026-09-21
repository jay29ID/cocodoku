import json, pathlib, re

def load(fn):
    p=pathlib.Path(fn)
    return json.loads(p.read_text()) if p.exists() else {}

data={}
for fn in ['levels-6.json','levels-7-8-9.json','levels-10.json','levels-10-11.json']:
    for k,v in load(fn).items(): data[k]=v

order=[]
for size in ['6','7','8','9','10','11']:
    for lv in data.get(size,[]): order.append(lv)

def enc(a):
    return ''.join(format(x,'x') if x<16 else '?' for x in a)   # n<=11 so 0..a

levels=[{'n':lv['n'],'r':enc(lv['reg']),'s':enc(lv['sol'])} for lv in order]
js='var LEVELS='+json.dumps(levels,separators=(',',':'))+';'
print('levels:',len(levels),'bytes:',len(js))
print('sizes:',[l['n'] for l in levels])

base=pathlib.Path('trixdoku.base.html')
src=pathlib.Path('trixdoku.html')
s=base.read_text(encoding='utf-8')

# ---------- data ----------
anchor='var SIZES=[6,7,8,9];'
assert anchor in s
s=s.replace(anchor, anchor+'\n'+js+'''
var mode="free",level=-1,prog={star:{},best:{}};
function decodeLevel(k){
  var L=LEVELS[k],i,reg=[],sol=[];
  for(i=0;i<L.r.length;i++) reg.push(parseInt(L.r[i],16));
  for(i=0;i<L.s.length;i++) sol.push(parseInt(L.s[i],16));
  return {n:L.n,reg:reg,sol:sol};
}
function unlocked(k){return k===0||!!prog.star[k-1]}
function par(size){return 12+Math.round(size*size*1.2)}
function starsFor(secs,size,usedHint){
  var p=par(size),st=secs<=p?3:secs<=p*1.8?2:1;
  return usedHint?Math.min(st,2):st;
}
function starRow(st){var o="",i;for(i=0;i<3;i++)o+=i<st?"\\u2605":"\\u2606";return o}''')

# ---------- css ----------
css_anchor='.rules li{margin-bottom:5px}'
assert css_anchor in s
s=s.replace(css_anchor, css_anchor+'''
.card.wide{max-width:400px}
.levels{display:grid;grid-template-columns:repeat(5,1fr);gap:7px;margin:2px 0 14px;max-height:52vh;overflow:auto;padding:2px}
.lv{aspect-ratio:1;border-radius:11px;border:2px solid var(--edge);background:var(--surface2);color:var(--ink);
  font-family:inherit;font-weight:900;font-size:15px;line-height:1;cursor:pointer;padding:0;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px}
.lv.done{background:var(--grass);border-color:var(--grass-deep);color:#16210F}
.lv[disabled]{opacity:.34;cursor:default}
.lv i{font-style:normal;font-size:9px;letter-spacing:.5px;opacity:.85}''')

# ---------- level lifecycle ----------
s=s.replace('''function restart(){''','''function startLevel(k){
  if(k<0||k>=LEVELS.length) return;
  var L=decodeLevel(k);
  mode="level";level=k;
  n=L.n;reg=L.reg;sol=L.sol;
  colorOf=pickTerrains(n,reg);
  marks=new Array(n*n).fill(0);undoStack=[];elapsed=0;hints=0;won=false;lost=false;strikes=0;cursor=-1;
  hideModal();buildBoard();layout();paint();paintChrome();runTimer(true);save();
  $("#foot").innerHTML="Level "+(k+1)+", "+n+"&times;"+n+". Tap to rule a square out, hold or double-tap to place <b>Trix</b>.";
}
function levelPicker(){
  var h='<h2>Levels</h2><div class="levels">',k;
  for(k=0;k<LEVELS.length;k++){
    var st=prog.star[k]||0,ok=unlocked(k);
    h+='<button class="lv'+(st?' done':'')+'"'+(ok?'':' disabled')+' data-lv="'+k+'">'+(k+1)+
       '<i>'+(st?starRow(st):LEVELS[k].n+"\\u00d7"+LEVELS[k].n)+'</i></button>';
  }
  h+='</div><div class="acts"><button class="btn" data-act="free">Free play</button>'+
     '<button class="btn" data-act="close">Back</button></div>';
  modal(h,true);
}
function paintChrome(){
  var lvl=mode==="level";
  $("#sizes").hidden=lvl;
  $("#newBtn").textContent=lvl?"Retry":"New";
  $("#levelsBtn").textContent=lvl?"Level "+(level+1):"Levels";
}
function restart(){''')

# ---------- modal takes a wide flag ----------
s=s.replace('function modal(html){$("#card").innerHTML=html;$("#overlay").hidden=false}',
            'function modal(html,wide){var c=$("#card");c.className="card"+(wide?" wide":"");c.innerHTML=html;$("#overlay").hidden=false}')

# ---------- best time chip follows the mode ----------
s=s.replace('  $("#best").textContent=stats.best[n]?fmt(stats.best[n]):"\u2014";',
            '  $("#best").textContent=mode==="level"?(prog.best[level]?fmt(prog.best[level]):"\u2014"):(stats.best[n]?fmt(stats.best[n]):"\u2014");')

# ---------- win ----------
old_win_head='''function win(){
  won=true;runTimer(false);
  stats.solved=(stats.solved||0)+1;'''
assert old_win_head in s
s=s.replace(old_win_head,'''function win(){
  won=true;runTimer(false);
  stats.solved=(stats.solved||0)+1;
  if(mode==="level"){
    var st=starsFor(elapsed,n,hints>0);
    if(!prog.star[level]||prog.star[level]<st) prog.star[level]=st;
    if(!prog.best[level]||elapsed<prog.best[level]) prog.best[level]=elapsed;
    save();paint();buzz([20,50,20,50,30]);
    var last=level>=LEVELS.length-1;
    setTimeout(function(){
      modal('<h2>Level '+(level+1)+' done</h2><div class="bigtime">'+fmt(elapsed)+'</div>'+
        '<div class="sub">'+starRow(st)+(prog.best[level]===elapsed?" &middot; best yet":"")+'</div>'+
        '<p>'+(last?"That is the last level. Free play never runs out.":(st<3?"Beat "+fmt(par(n))+" for three stars.":"Nothing faster to ask for."))+'</p>'+
        '<div class="acts">'+(last?'':'<button class="btn primary" data-act="next">Next level</button>')+
        '<button class="btn" data-act="levels">Levels</button></div>');
    },420);
    return;
  }''')

# ---------- lose ----------
old_lose='''function loseGame(){
  modal('<h2>Bad Dog! You failed!</h2>'''
assert old_lose in s
s=s.replace(old_lose,'''function loseGame(){
  if(mode==="level"){
    modal('<h2>Bad Dog! You failed!</h2>'+
      '<p>Three placements that could never be right. The board is the same every time, so you keep what you worked out.</p>'+
      '<div class="acts"><button class="btn primary" data-act="restart">Try again</button>'+
      '<button class="btn" data-act="levels">Levels</button></div>');
    return;
  }
  modal('<h2>Bad Dog! You failed!</h2>''')

# ---------- restart in level mode keeps the level ----------
# (restart() only clears marks, which is exactly right for both modes)

# ---------- free play resets mode ----------
s=s.replace('''function newPuzzle(size){
  hideModal();
  n=size||n;''','''function newPuzzle(size){
  hideModal();
  mode="free";level=-1;
  n=size||n;''')

# ---------- controls ----------
s=s.replace('''      <button class="btn" id="hint">Hint</button>
      <button class="btn primary" id="newBtn">New</button>''','''      <button class="btn" id="hint">Hint</button>
      <button class="btn" id="levelsBtn">Levels</button>
      <button class="btn primary" id="newBtn">New</button>''')
s=s.replace('$("#hint").onclick=hint;','$("#hint").onclick=hint;\n$("#levelsBtn").onclick=levelPicker;')
s=s.replace('$("#newBtn").onclick=function(){','$("#newBtn").onclick=function(){\n  if(mode==="level"){restart();return}\n  ')

# ---------- overlay actions ----------
s=s.replace('''  var b=e.target.closest("[data-act]");if(!b)return;
  var a=b.dataset.act;''','''  var lb=e.target.closest("[data-lv]");
  if(lb&&!lb.disabled){startLevel(lb.dataset.lv|0);return}
  var b=e.target.closest("[data-act]");if(!b)return;
  var a=b.dataset.act;''')
s=s.replace('''  if(a==="new") newPuzzle();
  else if(a==="restart") restart();''','''  if(a==="new") newPuzzle();
  else if(a==="next") startLevel(level+1);
  else if(a==="levels") levelPicker();
  else if(a==="free"){hideModal();newPuzzle();}
  else if(a==="restart") restart();''')

# ---------- persistence ----------
s=s.replace('''      hints:hints,won:won,lost:lost,strikes:strikes,stats:stats''',
            '''      hints:hints,won:won,lost:lost,strikes:strikes,stats:stats,
      mode:mode,level:level,prog:prog''')
s=s.replace('''    stats=s.stats||{best:{},solved:0};
    buildBoard();paintSizes();layout();paint();''','''    stats=s.stats||{best:{},solved:0};
    prog=s.prog||{star:{},best:{}};
    if(!prog.star)prog.star={};if(!prog.best)prog.best={};
    mode=s.mode==="level"?"level":"free";level=typeof s.level==="number"?s.level:-1;
    if(mode==="level"&&(level<0||level>=LEVELS.length)){mode="free";level=-1}
    buildBoard();paintSizes();paintChrome();layout();paint();''')
s=s.replace('''  }else{
    paintSizes();
    newPuzzle(8);''','''  }else{
    paintSizes();paintChrome();
    newPuzzle(8);''')

# ---------- intro card mentions levels ----------
s=s.replace('''<div class="acts"><button class="btn primary" data-act="close">Start playing</button></div>''',
            '''<div class="acts"><button class="btn primary" data-act="close">Free play</button>'''
            '''<button class="btn" data-act="levels">Levels</button></div>''')

src.write_text(s,encoding='utf-8')
print('patched', len(s), 'bytes')
