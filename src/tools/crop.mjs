import {chromium} from 'playwright';
import fs from 'fs';
const d='/tmp/claude-0/-home-claude/78581df9-f987-5ccf-b006-1024f92877f1/scratchpad/art/';
const [inp,outp,maxW]=process.argv.slice(2);
const b=await chromium.launch({executablePath:'/opt/pw-browsers/chromium'});
const p=await b.newPage();
const src='data:image/png;base64,'+fs.readFileSync(d+inp).toString('base64');
const out=await p.evaluate(async([s,MW])=>{
  const im=new Image(); im.src=s; await im.decode();
  const c0=document.createElement('canvas'); c0.width=im.width; c0.height=im.height;
  const x0=c0.getContext('2d'); x0.drawImage(im,0,0);
  const d0=x0.getImageData(0,0,im.width,im.height).data;
  let x1=im.width,y1=im.height,x2=-1,y2=-1;
  for(let y=0;y<im.height;y++)for(let x=0;x<im.width;x++){
    if(d0[(y*im.width+x)*4+3]>12){if(x<x1)x1=x;if(x>x2)x2=x;if(y<y1)y1=y;if(y>y2)y2=y;}
  }
  const cw=x2-x1+1, ch=y2-y1+1;
  const W=Math.min(MW,cw), H=Math.round(ch*W/cw);
  const cv=document.createElement('canvas'); cv.width=W; cv.height=H;
  const x=cv.getContext('2d'); x.imageSmoothingQuality='high';
  x.drawImage(im,x1,y1,cw,ch,0,0,W,H);
  return {src:[im.width,im.height],crop:[cw,ch],out:[W,H],data:cv.toDataURL('image/png')};
},[src,Number(maxW)]);
fs.writeFileSync(d+outp, Buffer.from(out.data.split(',')[1],'base64'));
console.log(inp,'src',out.src.join('x'),'cropped',out.crop.join('x'),'->',out.out.join('x'),fs.statSync(d+outp).size+'B');
await b.close();
