#!/usr/bin/env python3
"""Build the web (self-hosted) copies of the games.

Runs AFTER make.sh. Takes the artifact builds and swaps the dormant
claude.use("db") leaderboard for one that talks to /api/records on our own
server, so the board is genuinely shared by everyone who opens the link.
Output goes in web/ and is uploaded to the Railway service.
"""
import pathlib, shutil

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

NEW_START = '''var GAME=KEY.split(".")[0],LIVE=false,boardSeq=0;
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

def build(src, dst):
    s = pathlib.Path(src).read_text(encoding='utf-8')
    assert OLD_START in s, 'startLeaderboard anchor missing in ' + src
    s = s.replace(OLD_START, NEW_START)
    assert OLD_WRITE in s, 'saveRecord anchor missing in ' + src
    s = s.replace(OLD_WRITE, NEW_WRITE)

    # the Records card needs a marker so a late fetch only redraws its own card
    assert "var rows=boardRows(),h='<h2>Records</h2>';" in s
    s = s.replace("var rows=boardRows(),h='<h2>Records</h2>';",
                  "var rows=boardRows(),h='<h2 id=\"boardCard\">Records</h2>';")

    # Records buttons open the live board
    assert 'else if(a==="records") leaderboard();' in s
    s = s.replace('else if(a==="records") leaderboard();', 'else if(a==="records") openBoard();')

    # say whose board it is
    assert "h+='<p>No records yet. Finish a level and the first one is yours.</p>';" in s
    s = s.replace("h+='<p>No records yet. Finish a level and the first one is yours.</p>';",
                  "h+='<p>No records yet. Finish a level and the first one is yours.</p>';")
    assert "h+='</div>';" in s
    s = s.replace("""    h+='</div>';
  }""",
                  """    h+='</div>';
  }
  h+='<p class="sub" style="margin:0 0 12px">'+(LIVE?"Everyone who plays shares this board.":"Offline — showing this device only.")+'</p>';""", 1)

    pathlib.Path(dst).write_text(s, encoding='utf-8')
    print(dst, len(s), 'bytes')

web = pathlib.Path('web'); web.mkdir(exist_ok=True)
(web / 'art').mkdir(exist_ok=True)
build('trixdoku.html', 'web/trixdoku.html')
build('cocodoku.html', 'web/cocodoku.html')
shutil.copy('art/trix-web.png', 'web/art/trix-piece.png')
shutil.copy('art/coco-web.png', 'web/art/coco-piece.png')
shutil.copy('cowdoku.html', 'web/cowdoku.html')
shutil.copytree('tiles', 'web/tiles', dirs_exist_ok=True)
# Jason wants Cocodoku to be the game people land on, so it is the index.
# The three-game page (landing.html) stays reachable at /games.
shutil.copy('landing.html', 'web/games.html')
shutil.copy('web/cocodoku.html', 'web/index.html')
print('web build ready')
