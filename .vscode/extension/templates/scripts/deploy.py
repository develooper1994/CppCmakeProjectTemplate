#!/usr/bin/env python3
import os
import sys
import subprocess
import argparse

def deploy_to_remote(target_host, target_path, source_dir):
    print(f"--> Deploying artifacts from {source_dir} to {target_host}:{target_path}")
    
    # We use rsync for efficient transfer, falling back to scp if needed
    try:
        # Transfer only the 'bin' and 'lib' folders if they exist
        for folder in ['apps', 'libs']:
            path = os.path.join(source_dir, folder)
            if os.path.exists(path):
                print(f"    Syncing {folder}...")
                subprocess.run([
                    "rsync", "-avz", "--delete",
                    path, f"{target_host}:{target_path}"
                ], check=True)
        print("--> Deployment completed successfully.")
    except Exception as e:
        print(f"Error during deployment: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Remote Deployment Script")
    parser.add_argument("--host", required=True, help="Remote host (user@host)")
    parser.add_argument("--path", default="/tmp/cpp_project", help="Remote target path")
    parser.add_argument("--preset", default="gcc-debug-static-x86_64", help="Build preset to deploy")
    
    args = parser.parse_args()
    source_dir = f"build/{args.preset}"
    
    if not os.path.exists(source_dir):
        print(f"Error: Build directory {source_dir} not found. Build the project first.")
        sys.exit(1)
        
    deploy_to_remote(args.host, args.path, source_dir)

if __name__ == "__main__":
    main()
