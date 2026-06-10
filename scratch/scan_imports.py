import os
import ast
import re

target_prefixes = {"core", "data", "config", "ensemble", "utils"}

def scan_file(file_path):
    violations = []
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    # Parse with AST
    try:
        tree = ast.parse(content, filename=file_path)
    except SyntaxError as e:
        # Fallback to regex if syntax error (e.g. template files)
        return scan_file_regex(file_path, content)
        
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split('.')
                if parts[0] in target_prefixes:
                    violations.append({
                        "line": node.lineno,
                        "current": f"import {alias.name}",
                        "correct": f"import mandisense_ai.{alias.name}"
                    })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                parts = node.module.split('.')
                if parts[0] in target_prefixes:
                    # Reconstruct the import from statement
                    # Let's get the exact line from the file to be safe
                    lines = content.splitlines()
                    lineno = node.lineno
                    # We might have multi-line import, let's show the statement
                    violations.append({
                        "line": lineno,
                        "current": f"from {node.module} import ...",
                        "correct": f"from mandisense_ai.{node.module} import ..."
                    })
    return violations

def scan_file_regex(file_path, content):
    violations = []
    lines = content.splitlines()
    for idx, line in enumerate(lines):
        # Match "import x" or "from x import y"
        import_match = re.match(r'^\s*import\s+([\w\.]+)', line)
        from_match = re.match(r'^\s*from\s+([\w\.]+)\s+import', line)
        if import_match:
            module = import_match.group(1)
            parts = module.split('.')
            if parts[0] in target_prefixes:
                violations.append({
                    "line": idx + 1,
                    "current": line.strip(),
                    "correct": line.replace(module, f"mandisense_ai.{module}").strip()
                })
        elif from_match:
            module = from_match.group(1)
            parts = module.split('.')
            if parts[0] in target_prefixes:
                violations.append({
                    "line": idx + 1,
                    "current": line.strip(),
                    "correct": line.replace(f"from {module}", f"from mandisense_ai.{module}").strip()
                })
    return violations

def main():
    root_dir = "d:\\BMS COLL\\PROJECT\\MS-AI\\MS-AI"
    # We want to scan files in mandisense_ai/ and api/ and the root folder
    all_violations = {}
    for root, dirs, files in os.walk(root_dir):
        # Skip directories like .git, .pytest_cache, ms_env, node_modules, .next
        dirs[:] = [d for d in dirs if d not in {".git", ".pytest_cache", "ms_env", "node_modules", ".next", "artifacts", "logs"}]
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_dir)
                violations = scan_file(full_path)
                if violations:
                    all_violations[rel_path] = violations
                    
    # Print the report
    total_violations = 0
    with open("scratch/broken_imports_report.txt", "w", encoding="utf-8") as f:
        for path, vios in all_violations.items():
            f.write(f"\nFile: {path}\n")
            for v in vios:
                f.write(f"  Line {v['line']}:\n")
                f.write(f"    BAD:  {v['current']}\n")
                f.write(f"    GOOD: {v['correct']}\n")
                total_violations += 1
        f.write(f"\nSummary:\n")
        f.write(f"  Total broken imports: {total_violations}\n")
        f.write(f"  Total files affected: {len(all_violations)}\n")
    print(f"Report written to scratch/broken_imports_report.txt. Total: {total_violations}")

if __name__ == "__main__":
    main()
