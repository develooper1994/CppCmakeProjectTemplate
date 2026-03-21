# Multi-Repo / Modular Project Plan

## Sorun

Tek büyük repo ("monorepo") her proje için uygun değildir:
- `libs/` içindeki kütüphanelerin bağımsız geçmişi ve versiyonu olabilir
- `apps/` farklı ekiplerle farklı hızda gelişebilir
- Üçüncü taraf kütüphaneler kendi URL'leriyle dahil edilmek istenebilir

---

## Yaklaşım Seçenekleri

### A) Git Submodule (önerilen başlangıç noktası)

Her bağımsız repo, ana repoya submodule olarak eklenir.

```
CppCmakeProjectTemplate/          ← ana repo (orchestrator)
├── libs/
│   ├── core/                     ← submodule: github.com/org/core-lib
│   └── math_utils/               ← submodule: github.com/org/math-lib
├── apps/
│   └── main_app/                 ← yerel veya submodule
```

```bash
# Submodule ekle
git submodule add https://github.com/org/core-lib libs/core
git submodule update --init --recursive

# Tüm submodülleri güncelle
git submodule update --remote --merge
```

**Avantaj:** Basit, yaygın, CMake doğrudan destekler.
**Dezavantaj:** `git submodule` karmaşık olabilir, detached HEAD sorunu.

---

### B) CMake FetchContent (URL/tag ile pin)

Kütüphane kendi reposunda, ana proje onu FetchContent ile çeker.

```cmake
# libs/core/CMakeLists.txt yerine doğrudan:
FetchContent_Declare(
    core
    GIT_REPOSITORY https://github.com/org/core-lib.git
    GIT_TAG        v2.1.0   # sabit tag veya commit hash
)
FetchContent_MakeAvailable(core)
```

**Avantaj:** Submodule dosyası gerekmez, tamamen CMake tarafından yönetilir.
**Dezavantaj:** Her configure'da network erişimi (cache'lenir ama ilk seferde yavaş).

---

### C) Vcpkg / Conan (package manager)

Kütüphaneler merkezi registry üzerinden çekilir.

```json
// vcpkg.json
{
  "dependencies": [
    "fmt",
    { "name": "boost-filesystem", "version>=": "1.82.0" }
  ]
}
```

```python
# conanfile.py
def requirements(self):
    self.requires("fmt/10.2.1")
    self.requires("spdlog/1.13.0")
```

**Avantaj:** Versiyonlama, binary cache, cross-platform.
**Dezavantaj:** Özel/internal kütüphaneler için registry gerekmez.

---

### D) Hibrit (önerilen hedef mimari)

```
orchestrator-repo/
├── CMakeLists.txt           ← ana cmake, hepsini toplar
├── CMakePresets.json
├── scripts/                 ← build.py, toollib.py, toolsolution.py
│
├── libs/
│   ├── dummy_lib/           ← yerel (bu repoda)
│   ├── core/                ← git submodule VEYA FetchContent
│   └── third_party.cmake    ← FetchContent tanımları
│
├── apps/
│   ├── main_app/            ← yerel
│   └── mobile_app/          ← git submodule
│
└── external/                ← vcpkg/conan yönetimindeki paketler
```

---

## toolsolution ile entegrasyon (planlanan)

```bash
# Submodule olarak lib ekle
python3 scripts/toolsolution.py repo add-submodule \
    --url https://github.com/org/core-lib \
    --dest libs/core

# FetchContent kaydı oluştur
python3 scripts/toolsolution.py repo add-fetch \
    --name core \
    --url https://github.com/org/core-lib \
    --tag v2.1.0

# Tüm submodülleri güncelle
python3 scripts/toolsolution.py repo sync

# Her lib'in versiyonunu göster
python3 scripts/toolsolution.py repo versions
```

---

## Versiyonlama — Her Repo İçin

Her bağımsız lib reposu kendi `CMakeLists.txt` versiyonuna sahip olur:

```cmake
project(core VERSION 2.1.0 LANGUAGES CXX)
```

Ana orchestrator repo bu versiyonu `FetchContent_MakeAvailable` sonrası
`core_VERSION` değişkeniyle okuyabilir:

```cmake
message(STATUS "core version: ${core_VERSION}")
```

---

## Uygulama Önceliği

1. **Şimdi:** FetchContent desteği `toolsolution.py repo add-fetch` (yakında)
2. **Yakın:** Git submodule yardımcıları
3. **İleri:** Vcpkg/Conan entegrasyonu `toollib deps --url`

---

## Not: toollib deps ile URL desteği (planlanan)

```bash
# Mevcut: sadece yerel lib
python3 scripts/toollib.py deps my_lib --add core

# Planlanan: URL ile harici dep
python3 scripts/toollib.py deps my_lib \
    --add-url https://github.com/org/core-lib@v2.1.0 \
    --via fetchcontent   # veya --via vcpkg, --via conan
```

Bu komut:
1. `external/fetch_deps.cmake` dosyasına FetchContent tanımı ekler
2. `libs/my_lib/CMakeLists.txt`'e `target_link_libraries` ekler
3. Root `CMakeLists.txt`'e `include(external/fetch_deps.cmake)` ekler
