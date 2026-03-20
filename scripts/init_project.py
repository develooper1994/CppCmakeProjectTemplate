#!/usr/bin/env python3
import os
import sys
import argparse

def rename_project(new_name):
    old_name = "CppCmakeProjectTemplate"
    print(f"--> Renaming project from {old_name} to {new_name}...")
    
    # List of files/dirs to skip
    skip_dirs = {'.git', 'build', '.cache', 'coverage_report'}
    
    for root, dirs, files in os.walk('.', topdown=True):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            if file == 'init_project.py' or file.endswith('.pyc'):
                continue
                
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                if old_name in content:
                    print(f"    Updating: {file_path}")
                    new_content = content.replace(old_name, new_name)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            except Exception as e:
                print(f"    Error processing {file_path}: {e}")

    print("--> Project renamed successfully.")
    print("Note: You may still want to update the LICENSE file manually.")

def main():
    parser = argparse.ArgumentParser(description="Initialize/Rename C++ Project")
    parser.add_argument("--name", required=True, help="New project name")
    args = parser.parse_args()
    rename_project(args.name)

if __name__ == "__main__":
    main()
