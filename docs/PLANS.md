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
1.3. **Migration & Compatibility:** Eski scriptlerin (`build.py` vb.) 2 sürüm boyunca `deprecated` olarak desteklenmesi ve ardından kaldırılması.
1.4. **Observability & Diagnostics:**
    - Standart exit code'lar.
    - `--verbose`, `--debug`, `--quiet` bayrakları.
    - `build_logs/tool.log` içinde yapılandırılmış (structured) hata raporları.
1.5. **CLI Arg Parsing:** `argparse` veya `click` ile gelişmiş hata mesajları ve otomatik tamamlama.

### 🛠️ Faz 1 Uygulama Stratejisi

Faz 1'i hayata geçirmek için şu teknik yol haritası izlenecektir:

1. **Central Dispatcher (`scripts/tool.py`):** `argparse` subparsers kullanılarak hiyerarşik bir komut yapısı kurulacak.
2. **Lazy Import Modeli:** Komut modülleri (build, lib vb.) sadece çağrıldıklarında `import` edilecek. Bu, CLI açılış hızını artıracak ve dairesel bağımlılıkları önleyecektir.
3. **Library Refactoring:** Mevcut scriptlerin (`build.py`, `toollib.py` vb.) `main()` fonksiyonları, argümanları dışarıdan alabilecek (`def main(args=None)`) şekilde güncellenerek kütüphane gibi kullanılabilir hale getirilecek.
4. **Deprecation Layer:** Eski scriptler doğrudan çalıştırıldığında `tool` komutuna yönlendiren renkli uyarı mesajları eklenecek.
5. **Unified Logging:** Tüm modüller için ortak bir `Logger` ve `Result` objesi tanımlanarak hata raporlama standartlaştırılacak.

---

## 📦 Faz 2: Distribution & Template Engine

**Amaç:** Projenin dağıtımını profesyonelleştirmek ve şablon üretim motorunu standartlaştırmak.

2.1. **Packaging & Distribution:** `tool` komutunun `pip package` veya `standalone script` olarak dağıtılabilmesi (`pyproject.toml` entegrasyonu).
2.2. **Template Rendering Layer:** Şablon üretiminde `token replacement` yerine Jinja2 benzeri profesyonel bir rendering motoruna geçiş.
2.3. **Supply Chain Security:** Bootstrap aşamasında indirilen bağımlılıkların `checksum` doğrulaması ve `pinned versions` kullanımı.
2.4. **Validation Layer:** Proje scaffold edildikten sonra otomatik doğrulama (CMake parse, build tree tutarlılığı).

### 🛠️ Faz 2 Uygulama Stratejisi

Faz 2'de ürünleşme süreci şu adımlarla ilerleyecektir:

1. **Jinja2 Entegrasyonu:** Şablon üretim katmanı mantıksal blokları (if/else, for) destekleyecek şekilde güncellenecek. Bu, "opsiyonel" özelliklerin (test framework seçimi, header-only seçeneği vb.) yönetimini kolaylaştıracaktır.
2. **Python Packaging:** Proje köküne `pyproject.toml` eklenerek `tool` komutu bir console script olarak tanımlanacak. `pip install -e .` ile sistem genelinde kullanılabilir hale getirilecek.
3. **Post-Gen Health Check:** Her `scaffold` işleminden sonra üretilen dosyaların tutarlılığını (CMake syntax check, path resolution) denetleyen bir doğrulama katmanı eklenecek.
4. **Checksum Verification:** `tool setup` (Bootstrap) sırasında indirilen tüm harici araçlar ve scriptler için SHA-256 hash doğrulaması yapılarak tedarik zinciri güvenliği sağlanacak.
5. **Extension Sync Automation:** VS Code extension şablonları ile ana proje arasındaki dosya senkronizasyonu `tool` üzerinden tek bir `sync-templates` komutuyla hatasız hale getirilecek.

---

## 🧪 Faz 3: Test Strategy & Structured CI

**Amaç:** Hem CLI araçlarının hem de üretilen projelerin kalitesini garanti altına almak.

3.1. **Comprehensive Testing:**
    - **Unit/Integration:** CLI fonksiyonlarının testi.
    - **Fixture-based:** `toollib` ve `toolsolution` için izole ortam testleri.
    - **Template-generation:** Üretilen projelerin derlenebilirlik ve çalışma testleri (Smoke tests).
3.2. **Structured CI Pipeline:** CI sürecinin net aşamalara bölünmesi:
    `format` -> `lint` -> `build` -> `test` -> `package` -> `artifact validation`.

### 🛠️ Faz 3 Uygulama Stratejisi

Faz 3'te kalite kontrol süreçleri şu şekilde kurgulanacaktır:

1. **Fixture Isolation:** `pytest` kullanılarak testlerin birbirini etkilemediği, geçici dosya sistemlerinde çalışan izole bir test altyapısı kurulacak.
2. **Smoke Test Automation:** Her şablon değişikliğinde, `tool scaffold` ile üretilen örnek bir projenin `gcc`, `clang` ve `msvc` ile derlenip derlenmediği otomatik doğrulanacak.
3. **CI Stage Gatekeeper:** CI pipeline aşamaları bağımsız `exit code` kontrolü ile çalışacak; bir aşama başarısız olursa sonraki adımlar durdurulacak (fail-fast).

---

## 🛡️ Faz 4: Safety & Hardening

**Amaç:** Güvenlik odaklı C++ geliştirme pratiklerini otomatize etmek.

4.1. **Safety Profiles:** CLI üzerinden dinamik profil seçimi:
    - `Normal`: Standart C++.
    - `Safe`: Sıkı statik analiz, `_GLIBCXX_ASSERTIONS`.
    - `Hardened`: Stack smashing protection, Control-flow integrity.
4.2. **Supply Chain Protection:** Harici bağımlılıkların (vcpkg/conan) güvenlik taramaları.

### 🛠️ Faz 4 Uygulama Stratejisi

Faz 4'te güvenlik katmanı şu detaylarla zenginleştirilecek:

1. **Hidden Presets:** `CMakePresets.json` içinde kullanıcıdan gizlenen "safety" presetleri tanımlanacak. Seçilen profile göre derleyici bayrakları (`-fstack-protector-all` vb.) dinamik olarak enjekte edilecek.
2. **Security Audit:** `tool safety audit` komutu ile projedeki harici kütüphaneler için CVE taramaları (`osv-scanner` vb.) entegre edilecek.

---

## ⚡ Faz 5: Performance & Optimization

**Amaç:** Endüstriyel seviyede performans takibi ve optimizasyon.

5.1. **Release Optimization:** LTO, PGO ve `march=native` seçeneklerinin CLI'dan yönetimi.
5.2. **Benchmark Integration:** `Google Benchmark` entegrasyonu ve commit-bazlı performans kaybı (regression) takibi.

### 🛠️ Faz 5 Uygulama Stratejisi

Faz 5'te performans yönetimi şu şekilde optimize edilecek:

1. **Benchmark History:** `.benchmarks/history.json` dosyası üzerinden commit-bazlı karşılaştırma yapılacak. %5'ten fazla performans kaybı durumunda uyarı raporu üretilecek.
2. **PGO Workflow:** Profile-Guided Optimization süreci (Enstrümante et -> Veri topla -> Re-optimize et) tek komutla otomatize edilecek.

---

## 🌟 Faz 6: Ecosystem & UI

**Amaç:** Geliştirici etkileşimini artırmak.

6.1. **GUI / TUI:** `Textual` tabanlı TUI ve VS Code WebView paneli.
6.2. **Documentation as Code:** CLI yardım çıktılarından ve README'lerden otomatik döküman üretimi ve `tool doc serve` ile sunumu.
6.3. **Python API:** Otomasyonlar için dahili Python kütüphanesi.

### 🛠️ Faz 6 Uygulama Stratejisi

Faz 6'da kullanıcı arayüzü ve ekosistem şu adımlarla tamamlanacak:

1. **TUI as a Wrapper:** TUI (`scripts/tui.py`), merkezi `tool` yapısının üzerine giydirilmiş bir "kabuk" görevi görecek. TUI içinde hiçbir iş mantığı (business logic) bulunmayacak; her kullanıcı hareketi arka planda ilgili `tool` komutunu (`tool build`, `tool lib add` vb.) tetikleyecek ve çıktıyı görsel olarak sunacaktır. Bu, CLI ve TUI arasında tam davranış tutarlılığı sağlar.
2. **TUI Dashboard:** `Textual` ile terminal içinde tüm projeyi, kütüphaneleri ve build durumlarını izleyebileceğiniz interaktif bir pano oluşturulacak.
3. **VS Code Integration:** Extension tarafına eklenecek bir WebView ile kütüphane ekleme ve bağımlılık yönetimi "Form" tabanlı bir arayüzle kolaylaştırılacak.
4. **Live Doc Server:** `tool doc serve` komutu arka planda Doxygen çalıştırıp anlık üretilen dokümantasyonu yerel bir HTTP sunucusu üzerinden sunacak.

---

## 📜 Yönetim Politikaları (Governance)

### Versioning Policy

- **SemVer:** CLI ve Şablon için Semantic Versioning uygulanır.
- **Template vs Generated:** Şablon sürümü (v1.2.0) ile üretilen projenin sürümü (v0.1.0) birbirinden bağımsız yönetilir.

### Platform Matrix

- **Birinci Sınıf Destek:** Linux (Ubuntu/Debian), Windows (MSVC), macOS.
- **Embedded:** ARM-none-eabi (Cortex-M serisi).

### Release Process

- Otomatik `changelog` üretimi.
- Git tag + Artifact (VSIX, tar.gz) yayınlama.
- Release checklist (Testlerden geçme zorunluluğu).

---

## 💡 Stratejik Öneriler (Agent Recommendations)

1. **Template Sync:** Şablon güncellendiğinde, mevcut projelerin bu güncellemeleri alabilmesi için `tool update` komutu.
2. **Docker Dev Containers:** Geliştiriciler için hazır `.devcontainer` ortamı.
3. **Lint Gatekeeper:** `clang-tidy --fix` desteğinin `check` komutuna entegrasyonu.
