// Difficulty rating: re-runs the game's own solving rules and records how hard
// the reasoning had to work. Mirrors logicSolve in trixdoku.html.
export function rate(n,reg){
  const N=n*n,cand=new Array(N).fill(true),piece=new Array(N).fill(false);
  let placed=0;
  const byReg=[],groups=[];
  for(let i=0;i<n;i++) byReg.push([]);
  for(let i=0;i<N;i++) byReg[reg[i]].push(i);
  for(let r=0;r<n;r++){const g=[];for(let c=0;c<n;c++)g.push(r*n+c);groups.push(g);}
  for(let c=0;c<n;c++){const g=[];for(let r=0;r<n;r++)g.push(r*n+c);groups.push(g);}
  for(let i=0;i<n;i++) groups.push(byReg[i]);
  function attacks(i){
    const out=[],r=(i/n)|0,c=i%n;
    for(let k=0;k<n;k++){if(k!==c)out.push(r*n+k);if(k!==r)out.push(k*n+c);}
    for(let dr=-1;dr<=1;dr++)for(let dc=-1;dc<=1;dc++){
      const y=r+dr,x=c+dc;
      if(y<0||x<0||y>=n||x>=n||(dr===0&&dc===0))continue;
      out.push(y*n+x);
    }
    byReg[reg[i]].forEach(j=>{if(j!==i)out.push(j)});
    return out;
  }
  function place(i){
    if(piece[i])return;
    piece[i]=true;placed++;cand[i]=false;
    attacks(i).forEach(j=>{cand[j]=false});
  }
  let rounds=0,inter=0,singles=0,changed=true;
  while(changed&&placed<n){
    changed=false;rounds++;
    for(let gi=0;gi<groups.length;gi++){
      const grp=groups[gi],cs=[];let has=false;
      for(const i of grp){ if(piece[i])has=true; else if(cand[i])cs.push(i); }
      if(has)continue;
      if(!cs.length)return null;
      if(cs.length===1){place(cs[0]);singles++;changed=true;continue}
      let ix=null;
      for(const cell of cs){
        const s={};for(const a of attacks(cell))s[a]=1;
        if(ix===null)ix=s;
        else{const nx={};let any=false;
          for(const k of Object.keys(ix)) if(s[k]){nx[k]=1;any=true}
          ix=nx;if(!any)break;}
      }
      if(ix)for(const v of Object.keys(ix)){
        if(cand[v|0]){cand[v|0]=false;changed=true;inter++}
      }
    }
  }
  if(placed!==n) return null;
  return {rounds,inter,singles,score:rounds*n+inter};
}
