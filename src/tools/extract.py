import re,sys,pathlib
src=pathlib.Path('trixdoku.html').read_text(encoding='utf-8')
lines=src.split('\n')
def grab(name):
    start=None
    for i,l in enumerate(lines):
        if l.startswith('function '+name+'(') or l.startswith('var '+name+'='):
            start=i;break
    if start is None: raise SystemExit('missing '+name)
    if lines[start].startswith('var '): return lines[start]
    # single-line function?
    if lines[start].rstrip().endswith('}') and lines[start].count('{')==lines[start].count('}'):
        return lines[start]
    for j in range(start+1,len(lines)):
        if lines[j]=='}':
            return '\n'.join(lines[start:j+1])
    raise SystemExit('unterminated '+name)
names=['D','shuffle','genSolution','growBalanced','solutions','connectedWithout','repair','logicSolve','makePuzzle']
out='\n'.join(grab(n) for n in names)
pathlib.Path('gencore.mjs').write_text(out+'\nexport {shuffle,genSolution,growBalanced,solutions,connectedWithout,repair,logicSolve,makePuzzle};\n',encoding='utf-8')
print('extracted', len(out), 'chars')
