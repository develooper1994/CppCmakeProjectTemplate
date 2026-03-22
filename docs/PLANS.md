# Project Plans (Priority Order)

---

## P5 — toollib: Pattern-based scaffolding şablonları ✅ DONE

---

## P6 — toolsolution: CI simülasyonu (`toolsolution ci`) ✅ DONE

---

## P7 — GUI (Merkezi Yönetim Arayüzü)

**Durum:** Pending
**Neden en sonda:** CLI araçlar stabil olunca GUI sadece wrapper olur.

**Seçenekler:**

- **VS Code WebView** — extension içinde panel (en uygun)
- **TUI (Textual/Rich)** — terminal tabanlı Python, hızlı başlangıç
  - **TUI session priority**: (interactive > cli args > session) was started but needs the main() CLI arg plumbing + saving session on widget changes — can continue in next session.

**Kural:** Tüm işlemler arka planda CLI araçları çalıştırır, GUI sadece wrapper.
