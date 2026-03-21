# Build Info & Feature Flags — Plan Notları

## Şu anki durum

- `cmake/FeatureFlags.h.in` + `cmake/FeatureFlags.cmake` → her CMake option → `#define FEATURE_X 0/1`
- `cmake/BuildInfo.h.in` + `cmake/BuildInfo.cmake` → git hash, branch, timestamp, compiler, arch
- İki ayrı header: `FeatureFlags.h` ve `BuildInfo.h`

---

## Plan: Tek Header'da Toplama

**Hedef:** `ProjectInfo.h` — hem build info (git, compiler, arch) hem feature flags tek dosyada.

**Zorluk:** `BuildInfo.cmake` her target için ayrı çağrılıyor (`target_generate_build_info`)
çünkü target type (Static/Shared/Executable) per-target bilgi gerektiriyor.
`FeatureFlags.cmake` ise proje genelinde tek sefer çağrılıyor.

**Yaklaşım:**
```
ProjectInfo.h   ← configure_file ile üretilir
├── #include "FeatureFlags.h"     (project-wide, sabit)
└── #include "BuildInfo.h"        (per-target, target-specific namespace ile)
```

Ya da her şeyi `ProjectInfo.h.in`'e `@...@` substitution ile:
```cpp
// ProjectInfo.h — AUTO-GENERATED
// Build info + feature flags combined
namespace @NAMESPACE@ {
  constexpr std::string_view version = "@PROJECT_VERSION@";
  constexpr bool asan_enabled = @FEATURE_ASAN@;
  // ...
}
```

**Risk:** Target-specific bilgiler (library_type) per-target namespace gerektirir,
bu yüzden feature flags (proje geneli) ve build info (target-specific) tam birleştirme
mümkün ama namespace yönetimi karmaşıklaşır.

**Karar:** Şimdilik iki ayrı header. `ProjectInfo.h` ileride wrapper olabilir:
```cpp
// Planlanan: cmake/ProjectInfo.h (el yazısı wrapper, generate edilmez)
#pragma once
#include "BuildInfo.h"
#include "FeatureFlags.h"
```

---

## Plan: Dinamik Feature Listesi

**Sorun:** `FeatureFlags.h.in` içindeki `features` array'i hardcode edilmiş.
Yeni bir option eklenince hem `.cmake` hem `.h.in` güncellenmeli.

**Hedef:** CMake tarafı `FEATURE_FLAGS_LIST` değişkenine yaz, `.h.in` onu okusun.

**Zorluk:** `configure_file` liste/loop bilmiyor, sadece `@VAR@` substitution yapıyor.
CMake'de `file(WRITE ...)` ile doğrudan kod generate etmek gerekir.

**Yaklaşım:**
```cmake
# cmake/FeatureFlags.cmake içinde:
set(_feature_entries "")
foreach(_opt ${ALL_OPTIONS})
    string(APPEND _feature_entries
        "    Feature{\"${_opt}\", bool(FEATURE_${_opt})},\n")
endforeach()
# Sonra configure_file yerine file(CONFIGURE ...) kullan (CMake 3.18+)
file(CONFIGURE OUTPUT "${GENERATED_DIR}/FeatureFlags.h"
     CONTENT "${_header_content}" @ONLY)
```

Bu yaklaşımla `ALL_OPTIONS` listesi tek yerde (`ProjectConfigs.cmake`) tutulur,
header otomatik güncellenir.

**Durum:** Planlandı — `ProjectConfigs.cmake`'e `ALL_OPTIONS` list eklenince uygulanabilir.
