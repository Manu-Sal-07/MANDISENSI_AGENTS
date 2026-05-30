import re
path='presentation/ppt1.tex'
with open(path, encoding='utf-8') as f:
    lines=f.readlines()
frames=[]
cur=None
for i,line in enumerate(lines):
    m=re.match(r'\\begin\{frame\}(?:\[.*?\])?(?:\{(.*?)\})?', line)
    if m:
        title=m.group(1) or ''
        cur={'start':i,'title':title,'content':[]}
        frames.append(cur)
    elif cur is not None and re.match(r'\\end\{frame\}', line):
        cur['end']=i
        cur=None
    elif cur is not None:
        cur['content'].append(line.rstrip('\n'))
with open('slide_parse.txt','w', encoding='utf-8') as out:
    for idx,f in enumerate(frames,1):
        out.write('--- FRAME %d: %s\n' % (idx, f['title']))
        for line in f['content']:
            out.write(line + '\n')
        out.write('\n')
print('written', len(frames), 'frames')
