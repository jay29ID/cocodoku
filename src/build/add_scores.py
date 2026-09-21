#!/usr/bin/env python3
"""Scores, records and the (dormant) shared leaderboard.

Runs AFTER add_levels.py, on trixdoku.html. The db/user code is written but the
capability is NOT declared at publish time, so claude.use("db") resolves null
and the game falls back to records kept on the device. Declaring
capabilities:{db:{},user:{}} turns the shared board on with no code change.
"""
import pathlib
p=pathlib.Path('trixdoku.html')
s=p.read_text(encoding='utf-8')

# ---------- scoring + record state ----------
anchor='function starRow(st){'
assert anchor in s
s=s.replace(anchor,'''function scoreFor(secs,size,strikes,hintsUsed){
  var base=size*size*10;
  var p=par(size);
  var tf=Math.max(.3,Math.min(2,p/Math.max(secs,p*0.5)));
  var lf=1-0.2*Math.min(strikes,2);
  var hf=Math.max(.4,1-0.15*hintsUsed);
  return Math.max(1,Math.round(base*tf*lf*hf));
}
var DB=null,UID=null,shared={};
function cleanIni(v){return (v||"").toUpperCase().replace(/[^A-Z0-9]/g,"").slice(0,3)}
function recordFor(k){
  var a=shared[k],b=prog.rec&&prog.rec[k];
  if(a&&b) return a.sc>=b.sc?a:b;
  return a||b||null;
}
function saveRecord(k,rec){
  prog.rec=prog.rec||{};prog.rec[k]=rec;prog.ini=rec.ini;save();
  if(DB){
    var cur=shared[k];
    if(!cur||rec.sc>cur.sc){
      try{DB.doc("records/"+k).set(rec).catch(function(){})}catch(e){}
    }
  }
}
function startLeaderboard(){
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
}
function boardRows(){
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
}
function starRow(st){''')

# ---------- css ----------
css='.card.wide{max-width:400px}'
assert css in s
s=s.replace(css,css+'''
.tot{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin:0 0 12px}
.tot span{background:var(--surface2);border:2px solid var(--edge);border-radius:10px;padding:3px 9px;font-size:12px}
.tot b{font-family:Chewy,cursive;font-weight:400;font-size:15px;letter-spacing:1px;margin-right:4px}
.recs{max-height:44vh;overflow:auto;margin:0 0 14px;text-align:left}
.rec{display:grid;grid-template-columns:34px 1fr auto auto;gap:8px;align-items:baseline;
  padding:5px 4px;border-bottom:1px solid var(--edge);font-size:13px}
.rec span{color:var(--muted);font-size:11px}
.rec b{font-family:Chewy,cursive;font-weight:400;font-size:17px;letter-spacing:2px}
.rec i{font-style:normal;color:var(--muted);font-variant-numeric:tabular-nums}
.rec em{font-style:normal;font-weight:900;min-width:52px;text-align:right;font-variant-numeric:tabular-nums}
.score{font-family:Chewy,cursive;font-size:30px;line-height:1;color:var(--grass-deep);margin:2px 0 0}
.ini{display:flex;gap:8px;justify-content:center;align-items:center;margin:0 0 14px}
.ini input{font-family:Chewy,cursive;font-size:30px;letter-spacing:9px;text-align:center;width:130px;
  padding:6px 0 6px 9px;border-radius:12px;border:2px solid var(--edge);background:var(--surface2);color:var(--ink);text-transform:uppercase}''')

# ---------- the level win card ----------
old='''    var st=starsFor(elapsed,n,hints>0);
    if(!prog.star[level]||prog.star[level]<st) prog.star[level]=st;
    if(!prog.best[level]||elapsed<prog.best[level]) prog.best[level]=elapsed;
    save();paint();buzz([20,50,20,50,30]);
    var last=level>=LEVELS.length-1;'''
assert old in s
s=s.replace(old,'''    var st=starsFor(elapsed,n,hints>0);
    if(!prog.star[level]||prog.star[level]<st) prog.star[level]=st;
    if(!prog.best[level]||elapsed<prog.best[level]) prog.best[level]=elapsed;
    var sc=scoreFor(elapsed,n,strikes,hints);
    var held=recordFor(level);
    var isRec=!held||sc>held.sc;
    pending=isRec?{k:level,ini:prog.ini||"",sc:sc,t:elapsed}:null;
    save();paint();buzz([20,50,20,50,30]);
    var last=level>=LEVELS.length-1;''')

old2='''      modal('<h2>Level '+(level+1)+' done</h2><div class="bigtime">'+fmt(elapsed)+'</div>'+
        '<div class="sub">'+starRow(st)+(prog.best[level]===elapsed?" &middot; best yet":"")+'</div>'+
        '<p>'+(last?"That is the last level. Free play never runs out.":(st<3?"Beat "+fmt(par(n))+" for three stars.":"Nothing faster to ask for."))+'</p>'+
        '<div class="acts">'+(last?'':'<button class="btn primary" data-act="next">Next level</button>')+
        '<button class="btn" data-act="levels">Levels</button></div>');'''
assert old2 in s
s=s.replace(old2,'''      modal('<h2>Level '+(level+1)+' done</h2><div class="bigtime">'+fmt(elapsed)+'</div>'+
        '<div class="sub">'+starRow(st)+' &middot; '+strikes+' of 3 lives left'+'</div>'+
        '<div class="score">'+sc+' points</div>'+
        '<div class="sub">'+(isRec?"new record":(held?"record "+held.ini+" "+held.sc:""))+'</div>'+
        (isRec?'<div class="ini"><input id="iniIn" maxlength="3" autocomplete="off" spellcheck="false" '+
               'placeholder="AAA" value="'+(prog.ini||"")+'"><button class="btn primary" data-act="saveini">Save</button></div>':'')+
        '<p>'+(last?"That is the last level. Free play never runs out.":(st<3?"Beat "+fmt(par(n))+" for three stars.":"Nothing faster to ask for."))+'</p>'+
        '<div class="acts">'+(last?'':'<button class="btn primary" data-act="next">Next level</button>')+
        '<button class="btn" data-act="records">Records</button>'+
        '<button class="btn" data-act="levels">Levels</button></div>');
      var f=$("#iniIn");if(f){f.focus();f.oninput=function(){this.value=cleanIni(this.value)}}''')

# lives left is strikes used, not remaining - fix the wording
s=s.replace("' &middot; '+strikes+' of 3 lives left'","' &middot; '+(3-strikes)+' of 3 lives left'")

# ---------- pending record + overlay actions ----------
s=s.replace('var DB=null,UID=null,shared={};','var DB=null,UID=null,shared={},pending=null;')
s=s.replace('''  else if(a==="levels") levelPicker();''','''  else if(a==="levels") levelPicker();
  else if(a==="records") leaderboard();
  else if(a==="saveini"){
    var el=$("#iniIn"),v=cleanIni(el?el.value:"");
    if(v.length<1){if(el)el.focus();return}
    if(pending){pending.ini=v;saveRecord(pending.k,{ini:v,sc:pending.sc,t:pending.t,at:Date.now()});pending=null}
    if(el){el.parentNode.innerHTML='<span class="sub" style="margin:0">saved as '+v+'</span>'}
    return;
  }''')

# ---------- the level picker gets a Records button ----------
s=s.replace("""  h+='</div><div class="acts"><button class="btn" data-act="free">Free play</button>'+""",
            """  h+='</div><div class="acts"><button class="btn" data-act="free">Free play</button>'+
     '<button class="btn" data-act="records">Records</button>'+""")

# ---------- persistence already carries prog; make sure the new fields survive ----------
s=s.replace('''    if(!prog.star)prog.star={};if(!prog.best)prog.best={};''',
            '''    if(!prog.star)prog.star={};if(!prog.best)prog.best={};if(!prog.rec)prog.rec={};''')

# ---------- boot ----------
s=s.replace('''  window.addEventListener("resize",layout);''','''  startLeaderboard();
  window.addEventListener("resize",layout);''')

p.write_text(s,encoding='utf-8')
print('scores patched,',len(s),'bytes')
