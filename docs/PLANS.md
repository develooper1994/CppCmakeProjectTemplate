# Project Plans (Pending)

---

## P3: Multi-Repo / Modular Project

**Durum:** Pending
**Önerilen mimari:** Hibrit (yerel lib + git submodule + FetchContent + vcpkg/conan)

```
orchestrator-repo/
├── libs/
│   ├── dummy_lib/       ← yerel
│   ├── core/            ← git submodule VEYA FetchContent
│   └── third_party.cmake
├── apps/
└── external/            ← vcpkg/conan paketleri
```

**toolsolution entegrasyonu (planlanan):**
```bash
toolsolution.py repo add-submodule --url <url> --dest libs/core
toolsolution.py repo add-fetch --name core --url <url> --tag v2.1.0
toolsolution.py repo sync       # tüm submodülleri güncelle
toolsolution.py repo versions   # her lib versiyonu
```

**toollib entegrasyonu (planlanan):**
```bash
toollib.py deps my_lib --add-url https://github.com/org/core@v2.1.0 --via fetchcontent
# → external/fetch_deps.cmake günceller
# → libs/my_lib/CMakeLists.txt target_link_libraries ekler
```

**Uygulama önceliği:** FetchContent → submodule → vcpkg/conan

---

## P4: toollib Kapasite Genişletme (kalan)

**Durum:** Pending (info, test tamamlandı)

- `--add-url` ile harici dep (FetchContent/vcpkg/conan)
- `toollib.py export <n>` — CMake install/export kuralları üret
- Header-only lib scaffold (`--header-only`)
- Interface lib scaffold (`--interface`)

---

## P5: toolsolution Kapasite Genişletme (kalan)

**Durum:** Pending (test, upgrade-std tamamlandı)

- `toolsolution.py repo ...` — multi-repo yönetimi (bkz. P3)
- `toolsolution.py ci` — CI pipeline simülasyonu (tüm presetleri sırayla dene)

---

## P6: GUI (Merkezi Yönetim Arayüzü)

**Durum:** Pending
**Kapsam:** Tüm araçları (toollib, toolsolution, build.py) tek GUI üzerinden yönet.

**Seçenekler:**
- **VS Code WebView** — extension içinde panel (en uygun, zaten extension var)
- **TUI (Textual/Rich)** — terminal tabanlı Python, en hızlı başlangıç

**Kural:** Tüm işlemler arka planda CLI araçları çalıştırır, GUI sadece wrapper.
