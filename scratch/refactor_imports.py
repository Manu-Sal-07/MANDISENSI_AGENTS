import os
import re

target_prefixes = {"core", "data", "config", "ensemble", "utils"}

# Regex patterns to find absolute imports of the target packages
from_pattern = re.compile(r'^(\s*)from\s+(core|data|config|ensemble|utils)(\b)(.*)$')
import_pattern = re.compile(r'^(\s*)import\s+(core|data|config|ensemble|utils)(\b)(.*)$')

def refactor_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    modified = False
    new_lines = []
    fixed_count = 0
    
    for idx, line in enumerate(lines):
        new_line = line
        
        # Check from ... import ...
        m_from = from_pattern.match(line)
        if m_from:
            leading_space, prefix, separator, suffix = m_from.groups()
            new_line = f"{leading_space}from mandisense_ai.{prefix}{separator}{suffix}\n"
            
        # Check import ...
        m_import = import_pattern.match(line)
        if m_import:
            leading_space, prefix, separator, suffix = m_import.groups()
            new_line = f"{leading_space}import mandisense_ai.{prefix}{separator}{suffix}\n"
            
        if new_line != line:
            modified = True
            fixed_count += 1
            print(f"  [{os.path.basename(file_path)}:{idx+1}]")
            print(f"    - BAD:  {line.strip()}")
            print(f"    - GOOD: {new_line.strip()}")
            
        new_lines.append(new_line)
        
    if modified:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
    return fixed_count

def main():
    root_dir = "d:\\BMS COLL\\PROJECT\\MS-AI\\MS-AI"
    # We want to scan and refactor files in mandisense_ai/ and api/ and the root folder, excluding tests
    modified_files = 0
    total_fixed = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Skip directories like .git, .pytest_cache, ms_env, node_modules, .next, and also skip tests!
        # The user requested: "Modify source files only. Do not modify tests unless required."
        # So we skip "tests" directory.
        dirs[:] = [d for d in dirs if d not in {".git", ".pytest_cache", "ms_env", "node_modules", ".next", "artifacts", "logs", "tests"}]
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_dir)
                
                # We skip scratch scripts (except run_agents.py or others at root)
                if rel_path.startswith("scratch\\") or rel_path.startswith("scratch/"):
                    continue
                    
                fixed = refactor_file(full_path)
                if fixed > 0:
                    modified_files += 1
                    total_fixed += fixed
                    
    print(f"\nRefactoring complete:")
    print(f"  Total files modified: {modified_files}")
    print(f"  Total imports fixed: {total_fixed}")

if __name__ == "__main__":
    main()
