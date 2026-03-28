# CppCmakeProjectTemplate — Plans & Capabilities

Bu belge, projenin mevcut yeteneklerini, yönetim politikalarını ve gelecek vizyonunu öncelik sırasına göre listeler.

---

## ✅ Mevcut Özellikler (What This Repo Can Do)

### Unified CLI & Tooling Framework

- **Unified CLI (`tool.py`):** Tüm komutların (`build`, `lib`, `sol`) ve dinamik eklentileri (`plugins/`) yöneten merkezi giriş noktası.
- **Modern Dizin Mimarisi:** Altyapı (`core/utils`), iş mantığı (`core/commands`) ve eklentiler (`plugins/`) arasında net ayrım.
- **Structured Logging:** Standart seviyeli loglama ve kalıcı log kayıtları.
- **Standardized Results:** Tüm komutların `CLIResult` dönmesi ve `--json` desteği ile otomasyona tam uyum.
- **Clean Environment:** Tüm eski scriptler temizlendi, sistem tek bir profesyonel arayüzde birleşti.

### Build System

- **Modern CMake 3.25+:** Saf target-based mimari, global flag içermez.
- **Preset Matrisi:** Linux, Windows, macOS ve Embedded (ARM) için hazır konfigürasyonlar.
- **MSVC Consistency:** Otomatik `/MT` veya `/MD` seçimi.

### Compile-time Build Metadata

- **Per-Target BuildInfo:** Bağımsız versiyon ve git metadata desteği.
- **Dinamik FeatureFlags:** Derleme anında özellik kontrolü.

### Quality & CI/CD

- **Testing:** GoogleTest, Catch2, Boost.Test ve QTest desteği.
- **Quality Gates:** ASan, UBSan, TSan, Clang-Tidy ve Cppcheck entegrasyonu.
- **CI/CD:** GitHub Actions multi-platform matrix build süreçleri.

---

## 🚀 Yol Haritası (Roadmap)

### Faz 1: Foundation & Unified CLI ✅ TAMAMLANDI

- **Modular Dispatcher:** ✅ DONE

- **Command Contracts:** ✅ DONE
- **Structured Logging:** ✅ DONE
- **Plugin Discovery:** ✅ DONE
- **Migration & Cleanup:** ✅ DONE (Eski scriptler tamamen temizlendi)
- **Refactoring & Core Migration:** ✅ DONE (İş mantığı `core/commands` altına taşındı)

### Faz 2: Distribution & Template Engine (Sıradaki)

- **Jinja2 Migration:** f-string tabanlı şablonların Jinja2'ye taşınması.

- **Packaging:** `tool` komutunun `pip package` olması.
- **Bootstrap (`tool setup`):** Bağımlılıkların ve Python ortamının otomatik kurulumu.
- **Rollback & Recovery:** Hatalı dosya işlemlerinde state geri alma.

### Faz 3: Test Strategy & Structured CI

- **Comprehensive Testing:** CLI araçları için Unit ve Fixture testleri.

- **Deterministic CI:** Frozen environment gereksinimleri.
- **Template Smoke Tests:** Farklı derleyicilerde otomatik şablon doğrulaması.

### Faz 4: Safety, Hardening & Sanitizers

- **Sanitizer Profiles:** `tool build --profile sanitized` desteği.

- **Security Audit:** CVE taraması (`osv-scanner` entegrasyonu).

### Faz 5: Performance & Optimization

- **Performance Tracking:** Benchmark history ve regresyon takibi.

- **Performance Budget:** Threshold kontrolleri.

### Faz 6: Ecosystem & UI

- **TUI as Wrapper:** `scripts/tui.py`'nin merkezi `tool` yapısına tam entegrasyonu.

- **Live Doc Server:** `tool doc serve` ile anlık dokümantasyon.

### Faz 7: Configuration & State Management

- **`tool.toml`:** Merkezi konfigürasyon dosyası.

- **State Persistence:** `.tool/state.json` ile çalışma anı tarihçesi.
- **Lock Files:** Deterministik bağımlılık yönetimi.

---

## 📜 Yönetim Politikaları (Governance)

- **SemVer:** CLI ve Şablon için Semantic Versioning.
- **LTS Support:** En güncel (Latest) ve Kararlı (LTS) sürüm akışı.

---

## 💡 Stratejik Öneriler (Agent Recommendations)

1. **Template Logic Minimal:** Şablon dosyaları basit kalmalı; iş mantığı Python tarafında çözülmelidir.
2. **Atomic Operations:** Dosya mutasyonlarının rollback destekli olması sağlanmalıdır.
3. **Static Analysis Integration:** `clang-tidy --fix` desteğinin `check` komutuna entegrasyonu kaliteyi artıracaktır.
