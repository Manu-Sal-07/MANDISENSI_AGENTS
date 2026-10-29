import re

s = open(r"D:\BMS COLL\PROJECT\MS-AI\CICPS2027\MandiSense_CICPS2027.tex", encoding="utf-8").read()
ab = s.split("\\begin{abstract}")[1].split("\\keywords")[0]
ab = re.sub(r"\$[^$]*\$", "X", ab)
print("abstract words:", len(re.findall(r"[A-Za-z0-9][A-Za-z0-9.,%-]*", ab)))
cited = set(k.strip() for grp in re.findall(r"\\cite\{([^}]*)\}", s) for k in grp.split(","))
items = re.findall(r"\\bibitem\{([^}]*)\}", s)
print("bibitems:", len(items), "uncited:", [i for i in items if i not in cited], "missing:", [c for c in cited if c not in items])
body = s.split("\\begin{thebibliography}")[0]
for lab in re.findall(r"\\label\{([^}]*)\}", body):
    if lab.startswith(("fig", "tab", "alg")) and ("ref{%s}" % lab) not in body:
        print("float never referenced:", lab)
