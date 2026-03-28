from __future__ import annotations

from pathlib import Path
import shutil
import re


def pascal_case(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def render_text(text: str, name: str) -> str:
    """Apply simple token replacements for library templates.

    Replacements supported (intentionally small and predictable):
    - 'dummy_lib' -> provided `name`
    - 'DUMMY_LIB' -> `name.upper()`
    - 'DummyLib'  -> PascalCase(name)
    - '{{name}}'  -> name
    - '{{NAME}}'  -> name.upper()
    """
    pascal = pascal_case(name)
    mapping = {
        'dummy_lib': name,
        'DUMMY_LIB': name.upper(),
        'DummyLib': pascal,
        '{{name}}': name,
        '{{NAME}}': name.upper(),
    }
    out = text
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out


def apply_template_dir(template_dir: Path, dest_dir: Path, name: str, dry_run: bool = False) -> None:
    """Copy a template directory into `dest_dir`, applying token replacements.

    File/directory names containing the literal 'dummy_lib' are renamed to the new `name`.
    Text files are token-replaced using `render_text`. Binary files are copied as-is.
    """
    template_dir = Path(template_dir)
    dest_dir = Path(dest_dir)
    for src in sorted(template_dir.rglob("*")):
        rel = src.relative_to(template_dir)
        # replace 'dummy_lib' in the path
        rel_text = str(rel).replace('dummy_lib', name)
        dest_path = dest_dir / rel_text
        if src.is_dir():
            if not dry_run:
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                print("Dry-run: mkdir", dest_path)
            continue
        # file
        try:
            txt = src.read_text(encoding="utf-8")
            new_txt = render_text(txt, name)
            if dry_run:
                print("Dry-run: write", dest_path)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                dest_path.write_text(new_txt, encoding="utf-8")
        except UnicodeDecodeError:
            # binary -> copy
            if dry_run:
                print("Dry-run: copy (binary)", src, "->", dest_path)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest_path)


def _word_re(token: str) -> re.Pattern:
    return re.compile(r"(?<!\w)" + re.escape(token) + r"(?!\w)")


def contains_token(text: str, token: str) -> bool:
    return bool(_word_re(token).search(text))


def replace_token(text: str, old: str, new: str) -> str:
    return _word_re(old).sub(new, text)
