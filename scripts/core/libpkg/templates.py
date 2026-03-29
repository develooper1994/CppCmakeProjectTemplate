from __future__ import annotations

from typing import List, Optional

try:
    from .jinja_helpers import render_template_file
    _USE_JINJA = True
except Exception:
    render_template_file = None
    _USE_JINJA = False


def lib_cmakelists(name: str, version: str, namespace: Optional[str], deps: List[str], cxx_standard: str = "") -> str:
    if _USE_JINJA:
        return render_template_file(
            "lib_cmakelists.jinja2",
            name=name,
            version=version,
            namespace=namespace,
            deps=deps,
            cxx_standard=cxx_standard,
        )

    lines: List[str] = []
    if cxx_standard:
        lines.append(f"set_target_properties({name} PROPERTIES CXX_STANDARD {cxx_standard})")
    lines.append(f"add_library({name} src/{name}.cpp)")
    lines.append(f"target_include_directories({name} PUBLIC include)")
    if deps:
        lines.append(f"target_link_libraries({name} PUBLIC {' '.join(deps)})")
    return "\n".join(lines) + "\n"


def lib_cmakelists_header_only(name: str, version: str, namespace: Optional[str], deps: List[str], cxx_standard: str = "") -> str:
    if _USE_JINJA:
        return render_template_file(
            "lib_cmakelists_header_only.jinja2",
            name=name,
            version=version,
            namespace=namespace,
            deps=deps,
            cxx_standard=cxx_standard,
        )

    lines: List[str] = []
    lines.append(f"add_library({name} INTERFACE)")
    lines.append(f"target_include_directories({name} INTERFACE include)")
    if deps:
        lines.append(f"target_link_libraries({name} INTERFACE {' '.join(deps)})")
    return "\n".join(lines) + "\n"


def lib_header(name: str, namespace: Optional[str]) -> str:
    if _USE_JINJA:
        return render_template_file("lib_header.jinja2", name=name, namespace=namespace)

    if namespace:
        return f"#pragma once\n\nnamespace {namespace} {{\n\nvoid hello();\n\n}} // namespace {namespace}\n"
    else:
        return "#pragma once\n\nvoid hello();\n"


def lib_source(name: str, namespace: Optional[str]) -> str:
    if _USE_JINJA:
        return render_template_file("lib_source.jinja2", name=name, namespace=namespace)

    inc = f'#include "{name}/{name}.h"\n\n'
    if namespace:
        return inc + f"namespace {namespace} {{\n\nvoid hello() {{\n    // TODO: implement\n}}\n\n}} // namespace {namespace}\n"
    else:
        return inc + "void hello() {\n    // TODO: implement\n}\n"


# Templates for patterns
def lib_header_singleton(name: str, namespace: Optional[str]) -> str:
    cls = name.capitalize()
    if _USE_JINJA:
        return render_template_file("lib_header_singleton.jinja2", name=name, namespace=namespace)

    if namespace:
        return (
            f"#pragma once\n\nnamespace {namespace} {{\n\nclass {cls} {{\npublic:\n    static {cls}& instance();\n    void do_something();\nprivate:\n    {cls}() = default;\n}};\n\n}} // namespace {namespace}\n"
        )
    else:
        return (
            f"#pragma once\n\nclass {cls} {{\npublic:\n    static {cls}& instance();\n    void do_something();\nprivate:\n    {cls}() = default;\n}};\n"
        )


def lib_source_singleton(name: str, namespace: Optional[str]) -> str:
    cls = name.capitalize()
    if _USE_JINJA:
        return render_template_file("lib_source_singleton.jinja2", name=name, namespace=namespace)

    inc = f'#include "{name}/{name}.h"\n\n'
    if namespace:
        return (
            inc +
            f"namespace {namespace} {{\n\n{cls}& {cls}::instance() {{ static {cls} i; return i; }}\n\nvoid {cls}::do_something() {{ /* noop */ }}\n\n}} // namespace {namespace}\n"
        )
    else:
        return (
            inc +
            f"{cls}& {cls}::instance() {{ static {cls} i; return i; }}\n\nvoid {cls}::do_something() {{ /* noop */ }}\n"
        )


def lib_header_pimpl(name: str, namespace: Optional[str]) -> str:
    cls = name.capitalize()
    if _USE_JINJA:
        return render_template_file("lib_header_pimpl.jinja2", name=name, namespace=namespace)

    ns_open = f"namespace {namespace} {{\n\n" if namespace else ""
    ns_close = f"\n}} // namespace {namespace}\n" if namespace else ""
    return (
        f"#pragma once\n\n{ns_open}class {cls}Impl;\n\nclass {cls} {{\npublic:\n    {cls}();\n    ~{cls}();\n    void do_work();\nprivate:\n    struct Impl;\n    Impl* pImpl;\n}};\n{ns_close}"
    )


def lib_source_pimpl(name: str, namespace: Optional[str]) -> str:
    cls = name.capitalize()
    if _USE_JINJA:
        return render_template_file("lib_source_pimpl.jinja2", name=name, namespace=namespace)

    inc = f'#include "{name}/{name}.h"\n\n'
    ns_open = f"namespace {namespace} {{\n\n" if namespace else ""
    ns_close = f"\n}} // namespace {namespace}\n" if namespace else ""
    return (
        inc
        + ns_open
        + f"struct {cls}::Impl {{\n    // implementation details\n}};\n\n{cls}::{cls}() : pImpl(new Impl()) {{}}\n{cls}::~{cls}() {{ delete pImpl; }}\nvoid {cls}::do_work() {{ /* TODO */ }}\n"
        + ns_close
    )


def lib_header_factory(name: str, namespace: Optional[str]) -> str:
    cls = name.capitalize()
    if _USE_JINJA:
        return render_template_file("lib_header_factory.jinja2", name=name, namespace=namespace)

    if namespace:
        return (
            f"#pragma once\n\nnamespace {namespace} {{\n\nstruct I{cls} {{\n    virtual ~I{cls}() = default;\n    virtual void run() = 0;\n}};\n\nstd::unique_ptr<I{cls}> make_{name}();\n\n}} // namespace {namespace}\n"
        )
    else:
        return (
            f"#pragma once\n\nstruct I{cls} {{\n    virtual ~I{cls}() = default;\n    virtual void run() = 0;\n}};\n\nstd::unique_ptr<I{cls}> make_{name}();\n"
        )


def lib_source_factory(name: str, namespace: Optional[str]) -> str:
    cls = name.capitalize()
    if _USE_JINJA:
        return render_template_file("lib_source_factory.jinja2", name=name, namespace=namespace)

    inc = f'#include "{name}/{name}.h"\n#include <memory>\n\n'
    if namespace:
        return inc + f"namespace {namespace} {{\n\nstruct Impl : I{cls} {{ void run() override {{ /* noop */ }} }};\nstd::unique_ptr<I{cls}> make_{name}() {{ return std::make_unique<Impl>(); }}\n\n}} // namespace {namespace}\n"
    else:
        return inc + f"struct Impl : I{cls} {{ void run() override {{ /* noop */ }} }};\nstd::unique_ptr<I{cls}> make_{name}() {{ return std::make_unique<Impl>(); }}\n"


def lib_header_observer(name: str, namespace: Optional[str]) -> str:
    if _USE_JINJA:
        return render_template_file("lib_header_observer.jinja2", name=name, namespace=namespace)

    if namespace:
        return (
            f"#pragma once\n\nnamespace {namespace} {{\n\nclass Observer {{ public: virtual ~Observer() = default; virtual void notify() = 0; }};\nclass Subject {{ public: void add(Observer*) {{}} void notify_all() {{}} }};\n\n}} // namespace {namespace}\n"
        )
    else:
        return (
            "#pragma once\n\nclass Observer { public: virtual ~Observer() = default; virtual void notify() = 0; };\nclass Subject { public: void add(Observer*) {} void notify_all() {} };\n"
        )


def lib_source_observer(name: str, namespace: Optional[str]) -> str:
    if _USE_JINJA:
        return render_template_file("lib_source_observer.jinja2", name=name, namespace=namespace)

    return f"#include \"{name}/{name}.h\"\n\n// Minimal observer implementation (no-op)\n"
