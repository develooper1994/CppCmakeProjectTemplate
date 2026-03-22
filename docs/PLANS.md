# Project Plans (Priority Order)

---

## Kalan Planlar

### P7 — GUI (Merkezi Yönetim Arayüzü)

**Durum:** Pending

**Seçenekler (öncelik sırasıyla):**
- **VS Code WebView** — extension içinde panel, toollib/toolsolution komutlarını form UI ile çalıştırır
- **TUI (Textual/Rich)** — terminal tabanlı Python, hızlı başlangıç

**Kural:** Tüm işlemler CLI araçlarına delegasyon yapar. GUI sadece wrapper.

---

## Tamamlanan Planlar (arşiv)

- P1 ✅ Header-only + Interface scaffolding (`toollib add --header-only/--interface`)
- P2 ✅ CMake export kuralları (`toollib export` — find_package desteği)
- P3 ✅ URL dep desteği (`toollib deps --add-url` — FetchContent/vcpkg/conan)
- P4 ✅ Multi-repo yönetimi (`toolsolution repo add-submodule/add-fetch/sync/versions/list`)
- P5 ✅ Pattern-based scaffolding (`toollib add --template singleton/pimpl/observer/factory`)
- P6 ✅ CI simülasyonu (`toolsolution ci --preset-filter gcc --fail-fast`)
- toolsolution --lib delegasyonu ✅ (`toolsolution --lib <toollib args>`)
- x86 toolchain ✅ (`linux-x86.cmake` — çift -m32 düzeltildi, gcc-multilib kontrolü eklendi)
- CI yml ✅ (matrix strategy, tüm presetler, output-on-failure)
- .clang-tidy ✅ (project-aware naming conventions, gereksiz noisy checks devre dışı)
- .vscode/c_cpp_properties.json ✅ (3 platform config, compile_commands.json bağlantısı)
- AGENTS.md / GEMINI.md / .cursor/rules ✅ (tüm AI araçları için güncel proje özeti)
