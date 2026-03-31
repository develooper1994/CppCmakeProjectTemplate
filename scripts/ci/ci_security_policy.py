#!/usr/bin/env python3
"""Simple CI policy evaluator for security scan outputs.

Usage: scripts/ci/ci_security_policy.py <log-or-json-file>
Exits with:
 - 2 if CRITICAL findings present
 - 1 if HIGH findings present
 - 0 otherwise
"""
import sys
import json
from pathlib import Path

def extract_severities_from_json(obj, out):
    if isinstance(obj, dict):
        for k,v in obj.items():
            if k.lower() in ("severity","level") and isinstance(v, str):
                out.append(v.upper())
            else:
                extract_severities_from_json(v, out)
    elif isinstance(obj, list):
        for item in obj:
            extract_severities_from_json(item, out)

def main():
    if len(sys.argv) < 2:
        print("Usage: ci_security_policy.py <scan-file>")
        return 3
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        return 3
    text = path.read_text(encoding='utf-8', errors='ignore')
    severities = []
    try:
        j = json.loads(text)
        extract_severities_from_json(j, severities)
    except Exception:
        # fallback: simple text search
        up = text.upper()
        for s in ("CRITICAL","HIGH","MEDIUM","LOW"):
            if s in up:
                severities.append(s)

    if "CRITICAL" in severities:
        print("CRITICAL findings detected")
        return 2
    if "HIGH" in severities:
        print("HIGH severity findings detected")
        return 1
    print("No CRITICAL/HIGH findings detected")
    return 0

if __name__ == '__main__':
    sys.exit(main())
