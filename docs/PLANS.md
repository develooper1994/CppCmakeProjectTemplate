# Project Plans (Pending)

---

## P1: Tek Header'da BuildInfo + FeatureFlags

**Durum:** Pending  
**Hedef:** `ProjectInfo.h` — build bilgisi ve feature flags tek dosyada.

**Tasarım:**
```
cmake/ProjectInfo.h   (el yazısı wrapper, generate edilmez)
├── #include "BuildInfo.h"     ← per-target namespace (git, compiler, arch...)
└── #include "FeatureFlags.h"  ← proje geneli (FEATURE_ASAN, FEATURE_QT...)
```

**Zorluk:** `BuildInfo.cmake` her target için ayrı çağrılıyor (target type per-target).
Full merge mümkün ama namespace yönetimi karmaşıklaşır. Wrapper yeterli.

**Adımlar:**
1. `cmake/ProjectInfo.h` el yazısı wrapper oluştur
2. Tüm targetlara `project_feature_flags` gibi otomatik bağla

---

## P2: Dinamik Feature Listesi

**Durum:** Pending  
**Sorun:** `FeatureFlags.h.in` içindeki `features[]` hardcode. Yeni option → hem `.cmake` hem `.h.in` güncellenmeli.

**Çözüm:** `file(CONFIGURE ...)` ile header'ı dinamik üret:
```cmake
# ProjectConfigs.cmake — tek kaynak
set(PROJECT_ALL_OPTIONS
    UNIT_TESTS GTEST CATCH2 BOOST_TEST QTEST
    ASAN UBSAN TSAN CLANG_TIDY CPPCHECK COVERAGE
    QT QML BOOST DOCS
)

# FeatureFlags.cmake — loop ile üret
set(_entries "")
foreach(_opt ${PROJECT_ALL_OPTIONS})
    string(APPEND _entries "    Feature{\"${_opt}\", bool(FEATURE_${_opt})},\n")
endforeach()
file(CONFIGURE OUTPUT "${GENERATED_DIR}/FeatureFlags.h" CONTENT "..." @ONLY)
```

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

**toolsolution entegrasyonu (planlanan komutlar):**
```bash
toolsolution.py repo add-submodule --url <url> --dest libs/core
toolsolution.py repo add-fetch --name core --url <url> --tag v2.1.0
toolsolution.py repo sync          # tüm submodülleri güncelle
toolsolution.py repo versions      # her lib versiyonu
```

**toollib entegrasyonu (planlanan):**
```bash
toollib.py deps my_lib --add-url https://github.com/org/core@v2.1.0 --via fetchcontent
# → external/fetch_deps.cmake günceller
# → libs/my_lib/CMakeLists.txt target_link_libraries ekler
```

**Uygulama önceliği:** FetchContent → submodule → vcpkg/conan

---

## P4: toollib Kapasite Genişletme

**Durum:** Pending

- `--add-url` ile harici dep (FetchContent/vcpkg/conan)
- `toollib.py info <name>` — lib hakkında detaylı bilgi (deps tree, cmake vars, CXX standard)
- `toollib.py check <name>` — tek lib doctor
- `toollib.py export <name>` — CMake install/export kuralları üret
- `toollib.py test <name>` — sadece bir lib'in testlerini çalıştır
- Header-only lib scaffold desteği (`--header-only`)
- Interface lib scaffold desteği (`--interface`)

---

## P5: toolsolution Kapasite Genişletme

**Durum:** Pending

- `toolsolution.py repo ...` — multi-repo yönetimi (bkz. P3)
- `toolsolution.py build <target>` — tek target build (mevcut `target build` geliştirilecek)
- `toolsolution.py test [target]` — belirli veya tüm testleri çalıştır
- `toolsolution.py ci` — CI pipeline simülasyonu (tüm presetleri sırayla dene)
- `toolsolution.py upgrade-std --std 20` — tüm targets için CXX_STANDARD güncelle

---

## P6: GUI (Merkezi Yönetim Arayüzü)

**Durum:** Pending  
**Kapsam:** Tüm araçları (toollib, toolsolution, build.py) tek GUI üzerinden yönet.

**Seçenekler:**
- **VS Code WebView** — extension içinde panel (en uygun, zaten extension var)
- **Electron** — bağımsız masaüstü uygulama
- **TUI (Textual/Rich)** — terminal tabanlı (Python, en basit)

**Kural:** Tüm işlemler arka planda CLI araçları çalıştırır, GUI sadece wrapper.

---

## P7: MSVC buildPreset Eksik Kombinasyonlar

**Durum:** Pending  
**Eksik:** `msvc-relwithdebinfo-*-x86` presetleri (şu an sadece x64 RelWithDebInfo mevcut)
