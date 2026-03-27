# CppCmakeProjectTemplate - Roadmap & Plans

Bu belge, projenin mevcut yeteneklerini, gelecek vizyonunu ve yönetim politikalarını listeler.

---

## ✅ Tamamlanan Özellikler (Current Features)

- **Target-based CMake:** Bağımsız kütüphane ve uygulama yönetimi.
- **Library CRUD:** `toollib.py` ile kütüphane yaşam döngüsü yönetimi.
- **Unified Build:** `build.py` ile build/test/clean otomasyonu.
- **CI Simülasyonu:** Yerel GitHub Actions simülasyonu.
- **Scaffolding:** Pattern-based şablon üretimi.
- **P12 - Flexible Clean:** Hedef bazlı temizlik otomasyonu. ✅

---

## 🚀 Faz 1: Foundation & Unified CLI (Kritik)

**Amaç:** Dağınık scriptleri modüler, genişleyebilir ve gözlemlenebilir bir ana giriş noktası (`tool`) altında toplamak.

1.1. **Modular Dispatcher (`tool`):** `cargo` benzeri bir yapı ile komutları bağımsız modüllere (`build`, `lib`, `solution`) yönlendiren dispatcher.
1.2. **Plugin & Discovery Model:** Dahili ve harici komutların/eklentilerin otomatik keşfedilmesi (`tool-xxx` plugin desteği).
1.3. **Command Contracts:** Her komut için standart giriş/çıkış ve hata davranışı (Plugin ekosistemi için şart).
1.4. **Migration & Compatibility:** Eski scriptlerin 2 sürüm boyunca `deprecated` olarak desteklenmesi.
1.5. **Observability & Diagnostics:**
    - Standart exit code'lar ve actionable error messages.
    - `--verbose`, `--debug`, `--quiet` bayrakları.
    - `build_logs/tool.log` içinde yapılandırılmış hata raporları.
1.6. **Workspace / Multi-root Support:** Birden fazla projeyi veya iç içe geçmiş repository'leri yönetme desteği (Gelecek vizyonu).

### 🛠️ Faz 1 Uygulama Stratejisi

1. **Central Dispatcher:** `scripts/tool.py` oluşturulacak.
2. **Lazy Import:** Modüller sadece çağrıldığında yüklenecek.
3. **Library Refactoring:** Scriptlerin `main(args=None)` olarak güncellenmesi.
4. **Standardized IO:** Komutların JSON veya düz metin çıktı verme yeteneği.

---

## 📦 Faz 2: Distribution & Template Engine

**Amaç:** Projenin dağıtımını profesyonelleştirmek ve şablon üretim motorunu standartlaştırmak.

2.1. **Packaging & Distribution:** `tool` komutunun `pip package` veya `standalone script` olarak dağıtılması.
2.2. **Template Rendering Layer:** Jinja2 motoruna geçiş. **Kural:** İş mantığı Python'da, render şablonda.
2.3. **Supply Chain Security:** `tool setup` aşamasında SHA-256 doğrulaması ve pinned versions.
2.4. **Validation Layer:** Scaffold sonrası otomatik doğrulama (CMake parse, build tree tutarlılığı).
2.5. **Rollback & Recovery:** `scaffold` veya `update` işlemleri başarısız olursa otomatik geri alma (rollback) mekanizması.

---

## 🧪 Faz 3: Test Strategy & Structured CI

**Amaç:** CLI araçlarının ve üretilen projelerin kalitesini, deterministik bir ortamda garanti altına almak.

3.1. **Comprehensive Testing:**
    - **Unit/Integration:** CLI fonksiyonlarının testi.
    - **Fixture-based:** İzole dosya sisteminde fixture tabanlı testler.
    - **Template-generation:** Üretilen projelerin farklı platformlarda Smoke testleri.
3.2. **Structured CI Pipeline:** `format` -> `lint` -> `build` -> `test` -> `package` -> `artifact validation`.
3.3. **Deterministic CI:** Frozen environment, pinned tool ve compiler versiyonları kullanımı.

---

## 🛡️ Faz 4: Safety, Hardening & Sanitizers

**Amaç:** Güvenlik odaklı C++ pratiklerini ve dinamik analiz araçlarını otomatize etmek.

4.1. **Safety Profiles:** CLI üzerinden dinamik profil seçimi (Normal, Safe, Hardened).
4.2. **Sanitizer Profiles:** `tool build --profile sanitized` ile ASAN, UBSAN, TSAN veya MSAN desteği.
4.3. **Security Audit:** Harici bağımlılıklar için CVE taramaları (`osv-scanner` vb.).

---

## ⚡ Faz 5: Performance & Optimization

**Amaç:** Endüstriyel performans takibi ve "Performance Budget" yönetimi.

5.1. **Release Optimization:** LTO, PGO ve `march=native` seçeneklerinin yönetimi.
5.2. **Benchmark Integration:** `Google Benchmark` entegrasyonu ve regresyon takibi.
5.3. **Performance Budget:** Threshold politikası (örn: Regresyon > %10 -> Fail).

---

## 🌟 Faz 6: Ecosystem & UI

**Amaç:** Geliştirici etkileşimini artırmak ve otomasyonu kolaylaştırmak.

6.1. **TUI as a Wrapper:** `scripts/tui.py` merkezi `tool` yapısını kullanan görsel bir kabuk olacak.
6.2. **Non-Interactive Mode:** Otomasyon ve CI için `--yes` bayrağı desteği.
6.3. **Documentation as Code:** Otomatik döküman üretimi ve `tool doc serve` ile sunumu.

---

## ⚙️ Faz 7: Configuration & State Management

**Amaç:** Tool davranışının deterministik, reproducible ve yönetilebilir olması.

7.1. **Configuration System:** Tool davranışının `tool.toml` ile merkezi yönetimi.
7.2. **Schema Versioning:** `tool.toml` ve `.tool/state.json` için şema sürümü tanımlanması.
7.3. **Migration Framework:** State veya konfigürasyon formatı değiştiğinde veriyi taşıyacak `tool migrate` sistemi.
7.4. **State Persistence:** `.tool/` klasöründe çalışma anı bilgilerinin (history, versions) saklanması.
7.5. **Lock Files:** Reproducibility için `tool.lock` kullanımı.

---

## 📜 Yönetim Politikaları (Governance)

### Versioning Policy

- **SemVer:** CLI ve Şablon için Semantic Versioning uygulanır.
- **Template vs Generated:** Şablon ve üretilen proje sürümleri bağımsızdır.

### Platform Matrix (Minimum Versions)

- **Linux:** Ubuntu 22.04+, GCC 10+, Clang 12+.
- **Windows:** MSVC 2019+.
- **Core:** CMake 3.21+, Python 3.10+.

### Support Policy (LTS)

- **Latest / LTS / Deprecated / EOL** akışı uygulanır.

---

## 💡 Stratejik Öneriler (Agent Recommendations)

1. **Atomic Operations:** Dosya yazma işlemlerinin atomic (ya tam başarı ya tam rollback) olması.
2. **Template Sync:** Şablon güncellendiğinde mevcut projelerin güncellenmesi için `tool update`.
3. **Lint Gatekeeper:** `clang-tidy --fix` desteğinin `check` komutuna entegrasyonu.
