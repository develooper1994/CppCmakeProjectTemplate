# Project Plans (Priority Order)

---

## P1 — toollib: Header-only & Interface scaffolding ← NEXT

**Durum:** Pending  
**Neden önce:** En kısa iş. Harici URL desteği (P2) header-only lib'leri de çekecek,
önce scaffold tarafının tam olması gerekiyor.

- `toollib.py add <n> --header-only` — sadece `include/`, kaynak dosya yok
- `toollib.py add <n> --interface`   — CMake INTERFACE target (sadece prop/dep geçişi)

---

## P2 — toollib: CMake export kuralları (`toollib export`)

**Durum:** Pending  
**Neden erken:** Multi-repo çalışması için `find_package` desteği şart.
Şu an `install()` var ama `<LibName>Config.cmake` üretilmiyor.

- `toollib.py export <n>` — `cmake/LibraryConfig.cmake.in` şablonunu kullanarak
  install + export kurallarını lib CMakeLists.txt'e ekler
- `find_package(my_lib REQUIRED)` ile dışarıdan kullanılabilir hale getirir

---

## P3 — toollib: URL dep desteği (`toollib deps --add-url`) ✅ DONE

---

## P4 — toolsolution: Multi-repo yönetimi (`toolsolution repo`)

**Durum:** Pending  
**Neden P3 sonrası:** FetchContent altyapısı kurulduktan sonra submodule desteği eklemek mantıklı.

```bash
toolsolution.py repo add-fetch     --name fmt --url https://github.com/fmtlib/fmt --tag 10.2.1
toolsolution.py repo add-submodule --url https://github.com/org/core-lib --dest libs/core
toolsolution.py repo sync          # tüm submodülleri güncelle
toolsolution.py repo versions      # her component'ın versiyonunu göster
```

---

## P5 — toollib: Pattern-based scaffolding şablonları

**Durum:** Pending

```bash
toollib.py add my_lib --template singleton
toollib.py add my_lib --template pimpl
toollib.py add my_lib --template observer
toollib.py add my_lib --template factory
```

Her şablon, başlangıç implementasyonu + test + README üretir.

---

## P6 — toolsolution: CI simülasyonu (`toolsolution ci`)

**Durum:** Pending  
Tüm platform presetlerini sırayla çalıştırır, sonucu raporlar.

```bash
toolsolution.py ci                     # mevcut platformdaki tüm presetler
toolsolution.py ci --preset-filter gcc # sadece gcc presetleri
toolsolution.py ci --fail-fast         # ilk hatada dur
```

---

## P7 — GUI (Merkezi Yönetim Arayüzü)

**Durum:** Pending  
**Neden en sonda:** CLI araçlar stabil olunca GUI sadece wrapper olur.

**Seçenekler:**
- **VS Code WebView** — extension içinde panel (en uygun)
- **TUI (Textual/Rich)** — terminal tabanlı Python, hızlı başlangıç

**Kural:** Tüm işlemler arka planda CLI araçları çalıştırır, GUI sadece wrapper.
