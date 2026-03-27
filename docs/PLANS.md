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
1.3. **Command Contracts:** Her komut için standart giriş/çıkış ve hata davranışı.
1.4. **Migration & Compatibility:** Eski scriptlerin (`build.py` vb.) 2 sürüm boyunca `deprecated` olarak desteklenmesi.
1.5. **Observability & Diagnostics:** Standart exit code'lar, verbose loglama ve structured error messages.
1.6. **Workspace / Multi-root Support:** Birden fazla projeyi yönetme desteği (Roadmap).

### 🛠️ Faz 1 Uygulama Stratejisi

1. **Dispatcher Mimari:** `scripts/tool.py` ana giriş noktası olacak. `argparse.add_subparsers()` ile hiyerarşik komutlar tanımlanacak.
2. **Dynamic Command Discovery:** `scripts/commands/` dizinindeki `tool_*.py` dosyaları otomatik taranarak komut listesine eklenecek.
3. **Internal API:** Mevcut scriptler birer `Command` sınıfına dönüştürülecek. `execute(self, args)` metodunu implemente edecekler.
4. **Result Wrapper:** Her komut bir `CLIResult` (status, code, message, data) objesi döndürecek.
5. **Standardized Exit Codes:** 0: Success, 1: Runtime Error, 2: Config Error, 3: Validation Error.

---

## 📦 Faz 2: Distribution & Template Engine

**Amaç:** Dağıtımın profesyonelleşmesi ve şablon üretiminin esnekleşmesi.

2.1. **Packaging & Distribution:** `tool` komutunun `pip package` olması.
2.2. **Template Rendering Layer:** Jinja2 motoruna geçiş.
2.3. **Supply Chain Security:** SHA-256 doğrulama ve pinned versions.
2.4. **Validation Layer:** Scaffold sonrası CMake ve dizin tutarlılık kontrolü.
2.5. **Rollback & Recovery:** Başarısız işlemlerde otomatik geri alma.

### 🛠️ Faz 2 Uygulama Stratejisi

1. **Jinja2 Manager:** `TemplateEngine` sınıfı oluşturulacak. Dosya yazılmadan önce bellek üzerinde render edilecek.
2. **Packaging:** `pyproject.toml` ile build-system tanımlanacak. `entry_points` üzerinden `tool` terminale bağlanacak.
3. **Atomic Writes:** Dosya güncellemeleri önce `.tmp` dosyasına yapılacak, başarılı olursa orijinaliyle yer değiştirecek.
4. **Rollback System:** İşlem başlamadan önce `git stash` veya geçici bir `.tool/snapshot` dizini oluşturularak hata anında geri yükleme yapılacak.
5. **Metadata Sync:** Eklenti şablonları (`extension/templates`) ile ana proje arasındaki senkronizasyon, bir `Manifest` dosyası üzerinden otomatikleştirilecek.

---

## 🧪 Faz 3: Test Strategy & Structured CI

**Amaç:** Deterministik kalite kontrolü.

3.1. **Comprehensive Testing:** Unit, Integration ve Fixture testleri.
3.2. **Template-generation Smoke Tests:** Üretilen projelerin farklı platformlarda Smoke testleri.
3.3. **Structured CI Pipeline:** `format -> lint -> build -> test -> package -> validate`.
3.4. **Deterministic CI:** Frozen environment (Docker/DevContainer).

### 🛠️ Faz 3 Uygulama Stratejisi

1. **Fixture System:** `pytest` fixture'ları ile her test için izole, boş bir çalışma dizini (sandbox) oluşturulacak.
2. **Golden Master Testing:** Şablon çıktılarının beklenen dosya içeriğiyle karakter-karakter karşılaştırılması.
3. **CI Pipeline Orchestrator:** CI adımlarını yöneten bir `StageRunner` sınıfı ile her aşamanın logu ve exit code'u bağımsız izlenecek.
4. **Environment Pinning:** `requirements.lock` ve `tool.lock` dosyaları CI'da `pip install --frozen` ile kullanılacak.

---

## 🛡️ Faz 4: Safety, Hardening & Sanitizers

**Amaç:** Güvenlik ve bellek yönetimi standartları.

4.1. **Safety Profiles:** Normal, Safe, Hardened profilleri.
4.2. **Sanitizer Profiles:** ASAN, UBSAN, TSAN desteği.
4.3. **Security Audit:** Bağımlılık taraması.

### 🛠️ Faz 4 Uygulama Stratejisi

1. **Profile Injector:** `ProjectOptions.cmake` dosyasına dinamik olarak dahil edilen `Profiles.cmake` oluşturulacak.
2. **Sanitizer Toggle:** `tool build --profile sanitized` komutu, CMake'e `-DENABLE_SANITIZERS=ON` ve `-DSANITIZER_TYPE=address,undefined` gibi flagleri geçecek.
3. **Static Analysis gatekeeper:** `Hardened` profilinde `clang-tidy` hataları uyarı değil, "error" olarak kabul edilecek.

---

## ⚡ Faz 5: Performance & Optimization

**Amaç:** Performans bütçesi ve takip sistemi.

5.1. **Release Optimization:** LTO, PGO, `march=native`.
5.2. **Benchmark Integration:** Google Benchmark ve regresyon takibi.
5.3. **Performance Budget:** Threshold politikası.

### 🛠️ Faz 5 Uygulama Stratejisi

1. **Performance Tracker:** `.tool/benchmarks/` dizininde JSON formatında tarihçe tutulacak.
2. **Regression Analyzer:** Yeni benchmark sonuçlarını `HEAD~1` veya `main` branch sonuçlarıyla karşılaştıran bir analiz motoru yazılacak.
3. **PGO Automation:** `tool build --pgo` komutu önce `instrumented` build yapacak, örnek datayı koşturacak ve ardından `optimized` build'i tamamlayacak.

---

## 🌟 Faz 6: Ecosystem & UI

**Amaç:** Geliştirici arayüzleri.

6.1. **TUI as a Wrapper:** Görsel kabuk.
6.2. **Non-Interactive Mode:** `--yes` desteği.
6.3. **Documentation as Code:** `tool doc serve`.

### 🛠️ Faz 6 Uygulama Stratejisi

1. **TUI Architecture:** `Textual` kullanılarak `App` sınıfı oluşturulacak. Her buton veya input alanı arka planda bir `subprocess.run(["tool", ...])` tetikleyecek.
2. **Structured CLI Help:** Tüm komut yardım çıktıları Markdown veya JSON olarak export edilebilecek şekilde tasarlanacak.
3. **Doc Server:** Doxygen çıktısını izleyen bir `watchdog` ile dosya değişiminde dokümantasyonu otomatik yenileyen (hot-reload) bir yapı kurulacak.

---

## ⚙️ Faz 7: Configuration & State Management

**Amaç:** Determinizm ve yönetilebilirlik.

7.1. **Configuration System:** `tool.toml` merkezi yönetimi.
7.2. **Schema Versioning:** Versiyonlu şema yapısı.
7.3. **Migration Framework:** `tool migrate`.
7.4. **State Persistence:** `.tool/state.json`.
7.5. **Lock Files:** `tool.lock`.

### 🛠️ Faz 7 Uygulama Stratejisi

1. **Config Resolver:** Öncelik sırasını (CLI > Env > Local TOML > Global TOML > Default) yöneten bir `ConfigManager` sınıfı.
2. **Schema Validator:** `jsonschema` benzeri bir yapı ile config ve state dosyalarının doğruluğu her açılışta kontrol edilecek.
3. **Migration Runner:** `v1_to_v2.py` gibi scriptleri içeren bir klasör üzerinden eski versiyon verileri otomatik yükseltilecek.
4. **State Manager:** Başarılı build tarihi, kullanılan şablon sürümü ve kullanıcı tercihleri `.tool/state.json` içinde "persistent" (kalıcı) olarak tutulacak.

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
