"""
core/commands/sbom.py — Software Bill of Materials generation
=============================================================

Generates SBOM in SPDX or CycloneDX JSON format from project metadata
and detected dependencies.

Usage:
  tool sbom [--format spdx|cyclonedx] [--output FILE]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from core.utils.common import Logger, PROJECT_ROOT, get_project_name, get_project_version

COMMAND_META = {
    "name": "sbom",
    "description": "Generate Software Bill of Materials (SPDX/CycloneDX)",
}


def _detect_dependencies() -> list[dict[str, str]]:
    """Detect project dependencies from vcpkg.json, conanfile.py, and CMake FetchContent."""
    deps = []

    # vcpkg.json
    vcpkg_file = PROJECT_ROOT / "vcpkg.json"
    if vcpkg_file.exists():
        try:
            data = json.loads(vcpkg_file.read_text(encoding="utf-8"))
            for dep in data.get("dependencies", []):
                if isinstance(dep, str):
                    deps.append({"name": dep, "source": "vcpkg", "version": "latest"})
                elif isinstance(dep, dict):
                    name = dep.get("name", "")
                    version = dep.get("version>=", dep.get("version", "latest"))
                    deps.append({"name": name, "source": "vcpkg", "version": str(version)})
        except (json.JSONDecodeError, OSError):
            Logger.warn("Failed to parse vcpkg.json")

    # conanfile.py — simple regex extraction
    conan_file = PROJECT_ROOT / "conanfile.py"
    if conan_file.exists():
        import re
        try:
            content = conan_file.read_text(encoding="utf-8")
            for match in re.finditer(r'self\.requires\(["\']([^"\']+)["\']\)', content):
                pkg = match.group(1)
                parts = pkg.split("/")
                name = parts[0]
                version = parts[1] if len(parts) > 1 else "latest"
                deps.append({"name": name, "source": "conan", "version": version})
        except OSError:
            Logger.warn("Failed to parse conanfile.py")

    # requirements-dev.txt
    req_file = PROJECT_ROOT / "requirements-dev.txt"
    if req_file.exists():
        try:
            for line in req_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    # Handle ==, >=, etc.
                    import re
                    match = re.match(r'^([a-zA-Z0-9_-]+)\s*([><=!~]+\s*[\d.]+)?', line)
                    if match:
                        deps.append({
                            "name": match.group(1),
                            "source": "pip",
                            "version": (match.group(2) or "latest").strip(),
                        })
        except OSError:
            pass

    return deps


def _gen_spdx(name: str, version: str, deps: list[dict]) -> dict:
    """Generate SPDX 2.3 JSON document."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    packages = [
        {
            "SPDXID": "SPDXRef-Package",
            "name": name,
            "versionInfo": version,
            "downloadLocation": "NOASSERTION",
            "primaryPackagePurpose": "APPLICATION",
        }
    ]
    relationships = []

    for i, dep in enumerate(deps):
        pkg_id = f"SPDXRef-Dep-{i}"
        packages.append({
            "SPDXID": pkg_id,
            "name": dep["name"],
            "versionInfo": dep["version"],
            "downloadLocation": "NOASSERTION",
            "supplier": f"Organization: {dep['source']}",
        })
        relationships.append({
            "spdxElementId": "SPDXRef-Package",
            "relationshipType": "DEPENDS_ON",
            "relatedSpdxElement": pkg_id,
        })

    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{name}-sbom",
        "documentNamespace": f"https://spdx.org/spdxdocs/{name}-{version}",
        "creationInfo": {
            "created": now,
            "creators": ["Tool: tool.py sbom"],
        },
        "packages": packages,
        "relationships": relationships,
    }


def _gen_cyclonedx(name: str, version: str, deps: list[dict]) -> dict:
    """Generate CycloneDX 1.5 JSON document."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    components = []

    for dep in deps:
        components.append({
            "type": "library",
            "name": dep["name"],
            "version": dep["version"],
            "purl": f"pkg:{dep['source']}/{dep['name']}@{dep['version']}",
        })

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "component": {
                "type": "application",
                "name": name,
                "version": version,
            },
            "tools": [{"name": "tool.py", "version": version}],
        },
        "components": components,
    }


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(
        prog="tool sbom",
        description="Generate Software Bill of Materials",
    )
    parser.add_argument(
        "--format", choices=["spdx", "cyclonedx"], default="spdx",
        help="SBOM format (default: spdx)",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output file (default: stdout)",
    )
    args = parser.parse_args(argv)

    name = get_project_name()
    version = get_project_version()
    deps = _detect_dependencies()

    Logger.info(f"Detected {len(deps)} dependencies")
    for dep in deps:
        Logger.info(f"  {dep['source']}: {dep['name']}@{dep['version']}")

    if args.format == "cyclonedx":
        doc = _gen_cyclonedx(name, version, deps)
    else:
        doc = _gen_spdx(name, version, deps)

    output = json.dumps(doc, indent=2) + "\n"

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        Logger.success(f"SBOM written to {args.output}")
    else:
        print(output)
