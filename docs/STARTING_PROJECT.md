# Starting a New Project

## Option A — Interactive Wizard (recommended)

```bash
python3 scripts/tool.py new MyProject
```

The wizard prompts for:
- Project name, description, author, contact
- License (MIT, Apache-2.0, GPL-3.0, etc.)
- C++ standard (11, 14, 17, 20, 23)
- Profile (`full`, `minimal`, `library`, `app`, `embedded`)
- Libraries and applications to scaffold
- Feature toggles (CI, Docker, VS Code, extension, docs, fuzz)

For automation (CI, scripting), use non-interactive mode:

```bash
python3 scripts/tool.py new MyProject --non-interactive
```

## Option B — Generator with Profiles

```bash
python3 scripts/tool.py generate --target-dir ./MyProject --profile library --license MIT
```

Profiles control which components are generated:

| Profile    | Description                                    |
|------------|------------------------------------------------|
| `full`     | Everything enabled (default)                   |
| `minimal`  | Libs + apps only — no CI, Docker, extension    |
| `library`  | Libs + tests — no apps, CI, Docker, extension  |
| `app`      | Libs + apps — no extension                     |
| `embedded` | Libs + apps — no extension, Docker, docs       |

Fine-tune with `--with` / `--without`:

```bash
python3 scripts/tool.py generate --profile minimal --with ci --without fuzz
```

Preview effective settings before generating:

```bash
python3 scripts/tool.py generate --profile library --explain
```

## Option C — VS Code Extension

1. `Ctrl+Shift+P` → *CppTemplate: Create New Project*
2. Select target folder, enter project name.

## Option D — Manual Clone

```bash
git clone https://github.com/develooper1994/CppCmakeProjectTemplate.git MyProject
cd MyProject
python3 scripts/tool.py init --name MyProject
```

## License Selection

Use the license engine to choose the right license:

```bash
python3 scripts/tool.py license recommend   # Interactive decision tree
python3 scripts/tool.py license list         # Show all 7 supported licenses
python3 scripts/tool.py license recommend --apply  # Write to tool.toml
```
