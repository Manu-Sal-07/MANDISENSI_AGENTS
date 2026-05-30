import re

def extract_slides():
    filepath = r"d:\BMS COLL\PROJECT\MS-AI\ppt\ppt1.tex"
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We find \frametitle{...} blocks or comments that define frames
    # Let's search for \frametitle{...} or \begin{frame}{...} or similar
    # Sometimes Beamer frames are defined as \begin{frame}{Title} or \begin{frame}\frametitle{Title}
    titles = []
    
    # Pattern for \frametitle{Title}
    frametitle_matches = re.finditer(r'\\frametitle\{([^}]+)\}', content)
    
    # Alternatively, parse frames step-by-step
    # Let's find frame headers
    frame_blocks = re.findall(r'\\begin\{frame\}(?:\[.*?\])?(?:\{([^}]+)\})?', content)
    
    # Let's do a precise scan
    lines = content.split('\n')
    frame_count = 0
    current_title = None
    slide_info = []
    
    in_frame = False
    for line in lines:
        if '\\begin{frame}' in line:
            in_frame = True
            frame_count += 1
            # Check if title is on the begin line, e.g. \begin{frame}{Title}
            m = re.search(r'\\begin\{frame\}(?:\[.*?\])?(?:\{([^}]+)\})?', line)
            if m and m.group(1):
                current_title = m.group(1)
        elif '\\frametitle' in line:
            m = re.search(r'\\frametitle\{([^}]+)\}', line)
            if m:
                current_title = m.group(1)
        elif '\\end{frame}' in line:
            slide_info.append((frame_count, current_title or "[No Title]"))
            current_title = None
            in_frame = False
            
    print(f"Total slides compiled: {len(slide_info)}")
    for num, t in slide_info[:40]:
        print(f"Slide {num}: {t}")
        
    # Write all to a file for reference
    with open(r"d:\BMS COLL\PROJECT\MS-AI\MS-AI\scratch\slide_titles.txt", "w", encoding="utf-8") as out:
        for num, t in slide_info:
            out.write(f"Slide {num}: {t}\n")

if __name__ == "__main__":
    extract_slides()
