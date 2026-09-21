import * as g from './gencore.mjs';
import {rate} from './rate.mjs';
import fs from 'fs';

// Keep trying until a puzzle is unique AND solvable by the game's own rules.
function makeStrict(n,budgetMs){
  const t0=Date.now(),minS=2,maxS=Math.round(n*1.9);
  while(Date.now()-t0<budgetMs){
    const cols=g.genSolution(n); if(!cols) continue;
    const reg=g.growBalanced(n,cols); if(!reg) continue;
    const fixed=g.repair(n,reg,cols,minS,maxS,400); if(!fixed) continue;
    const r=rate(n,fixed); if(!r) continue;
    return {n,reg:fixed,sol:cols,...r};
  }
  return null;
}

const PLAN=JSON.parse(process.argv[2]); // [{n, want, pool, budget}]
const all={};
for(const {n,want,pool,budget} of PLAN){
  const cands=[];
  const t0=Date.now();
  while(cands.length<pool && Date.now()-t0 < budget*pool*3){
    const p=makeStrict(n,budget);
    if(p) cands.push(p);
  }
  cands.sort((a,b)=>a.score-b.score);
  const picked=[];
  for(let k=0;k<want;k++){
    const idx=Math.round(k*(cands.length-1)/(want-1||1));
    picked.push(cands[idx]);
  }
  all[n]=picked.map(p=>({n:p.n,reg:p.reg,sol:p.sol,score:p.score,rounds:p.rounds,inter:p.inter}));
  console.log(`${n}x${n}: ${cands.length} candidates in ${Math.round((Date.now()-t0)/1000)}s, scores ${cands[0].score}..${cands[cands.length-1].score}, picked ${picked.map(p=>p.score).join(',')}`);
}
fs.writeFileSync('levels-'+PLAN.map(p=>p.n).join('-')+'.json',JSON.stringify(all));
