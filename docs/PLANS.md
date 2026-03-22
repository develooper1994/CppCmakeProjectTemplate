# Project Plans (Priority Order)

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

**Durum:** In Progress (VS Code Extension Basic)
**Neden en sonda:** CLI araçlar stabil olunca GUI sadece wrapper olur.

**Seçenekler:**
- **VS Code WebView** — extension içinde panel (en uygun)
- **TUI (Textual/Rich)** — terminal tabanlı Python, hızlı başlangıç

**Kural:** Tüm işlemler arka planda CLI araçları çalıştırır, GUI sadece wrapper.
