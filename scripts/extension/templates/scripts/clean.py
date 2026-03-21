#!/usr/bin/env python3
import shutil
import os

def clean_project():
    print("--> Cleaning build artifacts...")
    
    dirs_to_clean = ['build', '.cache', 'coverage_report']
    
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"    Removing: {d}/")
            shutil.rmtree(d)
        else:
            print(f"    Skipping: {d}/ (not found)")

    print("--> Clean completed.")

if __name__ == "__main__":
    clean_project()
