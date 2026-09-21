var D=[[-1,0],[1,0],[0,-1],[0,1]];
function shuffle(a){for(var i=a.length-1;i>0;i--){var j=Math.floor(Math.random()*(i+1));var t=a[i];a[i]=a[j];a[j]=t;}return a}
function genSolution(n){
  var cols=new Array(n).fill(-1),used=new Array(n).fill(false);
  function bt(r){
    if(r===n) return true;
    var o=shuffle(Array.from({length:n},function(_,i){return i}));
    for(var k=0;k<n;k++){
      var c=o[k];
      if(used[c]) continue;
      if(r>0&&Math.abs(cols[r-1]-c)<=1) continue;
      used[c]=true;cols[r]=c;
      if(bt(r+1)) return true;
      used[c]=false;cols[r]=-1;
    }
    return false;
  }
  return bt(0)?cols:null;
}
function growBalanced(n,cols){
  var N=n*n,reg=new Array(N).fill(-1),sizes=new Array(n).fill(1),left=N-n,r;
  for(r=0;r<n;r++) reg[r*n+cols[r]]=r;
  while(left>0){
    var bi=-1,bg=-1,bw=-1;
    for(var i=0;i<N;i++){
      if(reg[i]>=0) continue;
      var rr=(i/n)|0,cc=i%n,seen=0;
      for(var d=0;d<4;d++){
        var y=rr+D[d][0],x=cc+D[d][1];
        if(y<0||x<0||y>=n||x>=n) continue;
        var g=reg[y*n+x];
        if(g<0||(seen>>g)&1) continue;
        seen|=1<<g;
        var w=Math.random()/(sizes[g]*sizes[g]);
        if(w>bw){bw=w;bi=i;bg=g;}
      }
    }
    if(bi<0) return null;
    reg[bi]=bg;sizes[bg]++;left--;
  }
  return reg;
}
function solutions(n,reg,limit){
  var out=[],uc=new Array(n).fill(false),ur=new Array(n).fill(false),cur=new Array(n);
  function bt(r,p){
    if(out.length>=limit) return;
    if(r===n){out.push(cur.slice());return}
    for(var c=0;c<n;c++){
      if(uc[c]) continue;
      if(r>0&&Math.abs(p-c)<=1) continue;
      var g=reg[r*n+c];
      if(ur[g]) continue;
      uc[c]=true;ur[g]=true;cur[r]=c;
      bt(r+1,c);
      uc[c]=false;ur[g]=false;
      if(out.length>=limit) return;
    }
  }
  bt(0,-9);
  return out;
}
function connectedWithout(n,reg,g,x){
  var cells=[],i;
  for(i=0;i<n*n;i++) if(reg[i]===g&&i!==x) cells.push(i);
  if(!cells.length) return false;
  var seen={},stack=[cells[0]],cnt=1;seen[cells[0]]=1;
  while(stack.length){
    var j=stack.pop(),r=(j/n)|0,c=j%n;
    for(var d=0;d<4;d++){
      var y=r+D[d][0],xx=c+D[d][1];
      if(y<0||xx<0||y>=n||xx>=n) continue;
      var k=y*n+xx;
      if(k===x||reg[k]!==g||seen[k]) continue;
      seen[k]=1;cnt++;stack.push(k);
    }
  }
  return cnt===cells.length;
}
function repair(n,reg,sol,minS,maxS,maxIter){
  var sizes=new Array(n).fill(0),stuck=0,i;
  reg.forEach(function(g){sizes[g]++});
  for(var it=0;it<maxIter;it++){
    var sols=solutions(n,reg,6);
    if(sols.length===1) return reg;
    var alt=null;
    for(i=0;i<sols.length;i++){
      var s=sols[i],diff=false;
      for(var r0=0;r0<n;r0++) if(s[r0]!==sol[r0]){diff=true;break}
      if(diff){alt=s;break}
    }
    if(!alt) return null;
    var rows=[];
    for(i=0;i<n;i++) if(alt[i]!==sol[i]) rows.push(i);
    shuffle(rows);
    var done=false;
    for(var ri=0;ri<rows.length&&!done;ri++){
      var r=rows[ri],x=r*n+alt[r],g=reg[x];
      if(sizes[g]<=minS) continue;
      var rr=(x/n)|0,cc=x%n,opts=[];
      for(var d=0;d<4;d++){
        var y=rr+D[d][0],xx=cc+D[d][1];
        if(y<0||xx<0||y>=n||xx>=n) continue;
        var g2=reg[y*n+xx];
        if(g2===g||sizes[g2]>=maxS) continue;
        if(opts.indexOf(g2)<0) opts.push(g2);
      }
      if(!opts.length) continue;
      if(!connectedWithout(n,reg,g,x)) continue;
      var kill=[];
      for(var r2=0;r2<n;r2++){
        if(r2===r) continue;
        var g3=reg[r2*n+alt[r2]];
        if(opts.indexOf(g3)>=0&&kill.indexOf(g3)<0) kill.push(g3);
      }
      var pool=kill.length?kill:opts,pick=pool[Math.floor(Math.random()*pool.length)];
      reg[x]=pick;sizes[g]--;sizes[pick]++;done=true;
    }
    if(!done){
      stuck++;
      if(stuck>14) return null;
      var moved=false,pool2=[];
      for(var i2=0;i2<n*n;i2++){
        var gg=reg[i2];
        if(sizes[gg]<=minS) continue;
        var y2=(i2/n)|0,x2=i2%n;
        for(var d2=0;d2<4;d2++){
          var yy=y2+D[d2][0],xx2=x2+D[d2][1];
          if(yy<0||xx2<0||yy>=n||xx2>=n) continue;
          var g4=reg[yy*n+xx2];
          if(g4!==gg&&sizes[g4]<maxS) pool2.push([i2,g4]);
        }
      }
      shuffle(pool2);
      for(var pi=0;pi<pool2.length;pi++){
        var ci=pool2[pi][0],cg=pool2[pi][1],isSol=false;
        for(var r3=0;r3<n;r3++) if(r3*n+sol[r3]===ci){isSol=true;break}
        if(isSol) continue;
        if(!connectedWithout(n,reg,reg[ci],ci)) continue;
        sizes[reg[ci]]--;reg[ci]=cg;sizes[cg]++;moved=true;break;
      }
      if(!moved) return null;
    } else stuck=0;
  }
  return null;
}
function logicSolve(n,reg){
  var N=n*n,cand=new Array(N).fill(true),cow=new Array(N).fill(false),placed=0,i;
  var byReg=[],groups=[];
  for(i=0;i<n;i++) byReg.push([]);
  for(i=0;i<N;i++) byReg[reg[i]].push(i);
  for(var r=0;r<n;r++){var g=[];for(var c=0;c<n;c++)g.push(r*n+c);groups.push(g);}
  for(var c2=0;c2<n;c2++){var g2=[];for(var r2=0;r2<n;r2++)g2.push(r2*n+c2);groups.push(g2);}
  for(i=0;i<n;i++) groups.push(byReg[i]);
  function attacks(i){
    var out=[],r=(i/n)|0,c=i%n,k;
    for(k=0;k<n;k++){if(k!==c)out.push(r*n+k);if(k!==r)out.push(k*n+c);}
    for(var dr=-1;dr<=1;dr++)for(var dc=-1;dc<=1;dc++){
      var y=r+dr,x=c+dc;
      if(y<0||x<0||y>=n||x>=n||(dr===0&&dc===0)) continue;
      out.push(y*n+x);
    }
    byReg[reg[i]].forEach(function(j){if(j!==i)out.push(j)});
    return out;
  }
  function place(i){
    if(cow[i]) return;
    cow[i]=true;placed++;cand[i]=false;
    attacks(i).forEach(function(j){cand[j]=false});
  }
  var changed=true;
  while(changed&&placed<n){
    changed=false;
    for(var gi=0;gi<groups.length;gi++){
      var grp=groups[gi],cs=[],hasCow=false;
      for(i=0;i<grp.length;i++){ if(cow[grp[i]]) hasCow=true; else if(cand[grp[i]]) cs.push(grp[i]); }
      if(hasCow) continue;
      if(!cs.length) return false;
      if(cs.length===1){place(cs[0]);changed=true;continue}
      var inter=null;
      for(var k2=0;k2<cs.length;k2++){
        var s={},a=attacks(cs[k2]);
        for(i=0;i<a.length;i++) s[a[i]]=1;
        if(inter===null) inter=s;
        else{var nx={},keys=Object.keys(inter),any=false;
          for(i=0;i<keys.length;i++) if(s[keys[i]]){nx[keys[i]]=1;any=true}
          inter=nx; if(!any) break;}
      }
      if(inter) Object.keys(inter).forEach(function(v){
        if(cand[v|0]){cand[v|0]=false;changed=true}
      });
    }
  }
  return placed===n;
}
function makePuzzle(n){
  var minS=2,maxS=Math.round(n*1.9),t0=Date.now();
  while(Date.now()-t0<2500){
    var cols=genSolution(n);
    if(!cols) continue;
    var reg=growBalanced(n,cols);
    if(!reg) continue;
    var fixed=repair(n,reg,cols,minS,maxS,400);
    if(!fixed) continue;
    if(!logicSolve(n,fixed)) continue;
    return {n:n,reg:fixed,sol:cols};
  }
  var cols2=genSolution(n),reg2=growBalanced(n,cols2),f2=repair(n,reg2,cols2,minS,maxS,600);
  return {n:n,reg:f2||reg2,sol:cols2};
}
export {shuffle,genSolution,growBalanced,solutions,connectedWithout,repair,logicSolve,makePuzzle};
