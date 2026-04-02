"""Tuning subcommands: promote, hw-recommend, autotune."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from core.utils.common import CLIResult, Logger, PROJECT_ROOT, run_capture
from ._helpers import (
    BUILD_DIR,
    LOGS_DIR,
    _detect_available_tools,
    _find_active_build_dir,
    _find_binaries,
)


def _cmd_promote(args) -> CLIResult:
    """Promote autotune-winning flags into a CMakePresets.json entry.

    Reads ``build_logs/autotune_results.json`` (output of ``tool perf autotune``),
    extracts the best flag combination, and writes a new configure preset
    named ``<base>-perf-tuned-<oracle>`` into ``CMakePresets.json``.

    Use ``--min-improvement`` to require a minimum score delta versus baseline
    before promoting.  ``--dry-run`` previews the preset without writing.
    """
    results_file = LOGS_DIR / "autotune_results.json"
    if not results_file.exists():
        return CLIResult(
            success=False, code=1,
            message="No autotune results found. Run 'tool perf autotune' first.",
        )

    data = json.loads(results_file.read_text(encoding="utf-8"))
    best_flags = data.get("best_flags", [])
    best_score = data.get("best_score")
    oracle = data.get("oracle", "speed")
    trials = data.get("trials", [])

    if best_score is None:
        return CLIResult(success=False, code=1, message="No valid best score in autotune results.")

    # Check minimum improvement vs baseline
    min_improvement = float(getattr(args, "min_improvement", 0))
    baseline_trial = next((t for t in trials if t.get("trial") == "baseline"), None)
    if baseline_trial and min_improvement > 0:
        baseline_score = baseline_trial.get("score", best_score)
        if baseline_score > 0:
            improvement_pct = (1.0 - best_score / baseline_score) * 100.0
            if improvement_pct < min_improvement:
                return CLIResult(
                    success=False, code=0,
                    message=f"Improvement {improvement_pct:.1f}% is below threshold "
                            f"{min_improvement:.1f}%. Not promoting.",
                )

    # Build the preset entry
    flags_str = " ".join(f for f in best_flags if f)
    base_preset = getattr(args, "base_preset", "gcc-release-static-x86_64")
    preset_name = f"{base_preset}-perf-tuned-{oracle}"

    new_preset = {
        "name": preset_name,
        "displayName": f"Perf-Tuned ({oracle}): {flags_str or '(defaults)'}",
        "inherits": base_preset,
        "cacheVariables": {
            "CMAKE_CXX_FLAGS": flags_str,
        },
        "vendor": {
            "tool-perf-promote": {
                "oracle": oracle,
                "best_score": best_score,
                "flags": best_flags,
                "promoted_from": str(results_file),
            },
        },
    }

    dry_run = getattr(args, "dry_run", False)
    as_json = getattr(args, "json", False)

    if dry_run or as_json:
        Logger.info("Preset to promote:")
        print(json.dumps(new_preset, indent=2))
        if dry_run:
            return CLIResult(
                success=True,
                message="Dry-run: preset shown above (not written).",
                data=new_preset,
            )

    # Read, update, write CMakePresets.json
    presets_file = PROJECT_ROOT / "CMakePresets.json"
    if not presets_file.exists():
        return CLIResult(success=False, code=1, message="CMakePresets.json not found.")

    presets_data = json.loads(presets_file.read_text(encoding="utf-8"))
    configure_presets = presets_data.get("configurePresets", [])

    # Remove existing preset with same name (replace)
    configure_presets = [p for p in configure_presets if p.get("name") != preset_name]
    configure_presets.append(new_preset)
    presets_data["configurePresets"] = configure_presets

    presets_file.write_text(json.dumps(presets_data, indent=2) + "\n", encoding="utf-8")
    Logger.success(f"[Promote] Preset '{preset_name}' written to CMakePresets.json")
    Logger.info(f"  CXX_FLAGS: {flags_str or '(defaults)'}")
    Logger.info(f"  Oracle: {oracle}  Score: {best_score:.1f}")

    return CLIResult(success=True, message=f"Preset '{preset_name}' promoted.", data=new_preset)


# ---------------------------------------------------------------------------
# Hardware-aware flag recommendations
# ---------------------------------------------------------------------------


def _cmd_hw_recommend(args) -> CLIResult:
    """Recommend compiler flags based on host CPU capabilities.

    Reads ``/proc/cpuinfo`` (Linux) or ``sysctl`` (macOS) to determine the
    CPU architecture, vendor, model, and supported ISA extensions.  Produces
    a recommended set of ``-march=``, ``-mtune=``, and ISA-specific flags.

    Output: table + optional ``--json``.
    """
    import platform
    import re

    as_json = getattr(args, "json", False)

    cpu_info: dict = {
        "arch": platform.machine(),
        "vendor": "",
        "model": "",
        "flags": [],
        "cores": os.cpu_count() or 1,
    }

    # ── Parse CPU info ─────────────────────────────────────────────────────
    cpuinfo_path = Path("/proc/cpuinfo")
    if cpuinfo_path.exists():
        text = cpuinfo_path.read_text(encoding="utf-8", errors="replace")
        # Vendor
        m = re.search(r"vendor_id\s*:\s*(.+)", text)
        if m:
            cpu_info["vendor"] = m.group(1).strip()
        # Model name
        m = re.search(r"model name\s*:\s*(.+)", text)
        if m:
            cpu_info["model"] = m.group(1).strip()
        # Flags (all unique)
        flag_lines = re.findall(r"flags\s*:\s*(.+)", text)
        if flag_lines:
            all_flags = set()
            for line in flag_lines:
                all_flags.update(line.strip().split())
            cpu_info["flags"] = sorted(all_flags)
    elif sys.platform == "darwin":
        # macOS: use sysctl
        try:
            brand, _ = run_capture(["sysctl", "-n", "machdep.cpu.brand_string"])
            cpu_info["model"] = brand.strip()
            vendor, _ = run_capture(["sysctl", "-n", "machdep.cpu.vendor"])
            cpu_info["vendor"] = vendor.strip()
            features, _ = run_capture(["sysctl", "-n", "machdep.cpu.features"])
            leaf7, _ = run_capture(["sysctl", "-n", "machdep.cpu.leaf7_features"])
            all_flags = set(
                features.strip().lower().split() + leaf7.strip().lower().split()
            )
            cpu_info["flags"] = sorted(all_flags)
        except Exception:
            pass

    if not cpu_info["model"]:
        return CLIResult(
            success=False, code=1,
            message="Could not detect CPU info. "
                    "Ensure /proc/cpuinfo or sysctl is available.",
        )

    # ── Generate recommendations ───────────────────────────────────────────
    flags_set = set(cpu_info["flags"])
    recommendations: list[dict] = []

    # -march= / -mtune=
    recommendations.append({
        "flag": "-march=native",
        "reason": "Auto-detect all ISA extensions of the host CPU",
        "priority": "high",
    })
    recommendations.append({
        "flag": "-mtune=native",
        "reason": f"Tune scheduling for {cpu_info['model'][:40]}",
        "priority": "high",
    })

    # ISA extension flags
    isa_map = {
        "avx": ("-mavx", "AVX 256-bit vector support"),
        "avx2": ("-mavx2", "AVX2 extended integer vectors"),
        "avx512f": ("-mavx512f", "AVX-512 Foundation"),
        "avx512bw": ("-mavx512bw", "AVX-512 Byte/Word operations"),
        "avx512vl": ("-mavx512vl", "AVX-512 Vector Length extensions"),
        "fma": ("-mfma", "Fused Multiply-Add"),
        "bmi": ("-mbmi", "Bit Manipulation Instructions"),
        "bmi2": ("-mbmi2", "Bit Manipulation Instructions 2"),
        "popcnt": ("-mpopcnt", "Population count instruction"),
        "lzcnt": ("-mlzcnt", "Leading zero count"),
        "aes": ("-maes", "AES-NI hardware encryption"),
        "pclmulqdq": ("-mpclmul", "Carry-less multiplication (for CRC/GCM)"),
        "sse4_1": ("-msse4.1", "SSE 4.1"),
        "sse4_2": ("-msse4.2", "SSE 4.2 (string/CRC)"),
        "f16c": ("-mf16c", "Half-precision float conversions"),
    }

    for cpu_flag, (compiler_flag, desc) in isa_map.items():
        if cpu_flag in flags_set:
            recommendations.append({
                "flag": compiler_flag,
                "reason": f"{desc} (detected)",
                "priority": "medium",
            })

    # Parallelism
    if cpu_info["cores"] >= 4:
        recommendations.append({
            "flag": f"-j{cpu_info['cores']}",
            "reason": f"Parallel build ({cpu_info['cores']} cores)",
            "priority": "info",
        })

    # Build the output
    output = {
        "cpu": cpu_info,
        "recommendations": recommendations,
    }

    # Print table
    Logger.info(f"CPU: {cpu_info['model']}")
    Logger.info(
        f"Arch: {cpu_info['arch']}  Vendor: {cpu_info['vendor']}  "
        f"Cores: {cpu_info['cores']}"
    )
    Logger.info(f"ISA flags detected: {len(cpu_info['flags'])}")
    Logger.info("")
    Logger.info(f"{'Priority':<10} {'Flag':<22} {'Reason'}")
    Logger.info("-" * 70)
    for rec in recommendations:
        Logger.info(f"{rec['priority']:<10} {rec['flag']:<22} {rec['reason']}")

    if as_json:
        print(json.dumps(output, indent=2))

    return CLIResult(success=True, message="Hardware recommendations shown above.", data=output)


# ---------------------------------------------------------------------------
# Compiler-flag auto-tuner — multi-oracle, multi-strategy
# ---------------------------------------------------------------------------


def _impl_cmd_autotune(args) -> CLIResult:
    """Sweep compiler flags to find the best combination for the chosen oracle.

    Reads ``tool.toml [autotuner].flag_candidates`` (list of lists of strings)
    for the ``speed`` / ``instructions`` oracles, or ``size_flag_candidates``
    for the ``size`` oracle.  Each inner list is a *flag group* — at most one
    flag from each group is active at a time.  Empty string ``""`` means
    "no flag" (the baseline choice).

    Oracles
    -------
    speed        (default) Sums Google Benchmark ``cpu_time`` across all
                 benchmark binaries.  Lower is better (ns).
    size         Sums ``.text + .data`` bytes from ``size --format=berkeley``
                 over built ELF binaries.  Lower is better (bytes).
    instructions Counts instructions executed via ``perf stat -e instructions``
                 (fallback: ``valgrind --tool=callgrind``).  Lower is better.
                 Falls back to ``speed`` when neither tool is available.

    Strategies
    ----------
    hill  (default)
        Start with the first flag in every group.  Flip one group per
        iteration; keep the change if it lowers the score.  Repeat until no
        improvement or ``--rounds`` budget is exhausted.
    grid
        Enumerate the cartesian product of all flag groups up to ``--rounds``
        trials; pick the combination with the lowest score.
    random
        Sample ``--rounds`` random combinations from the flag space without
        exhaustive enumeration.  Good for large search spaces.
    anneal
        Simulated annealing: accept worse solutions with probability
        exp(-delta / T).  T decreases by ``--T-alpha`` each round.
        Escapes local optima that hill-climb misses.

    Output: ``build_logs/autotune_results.json`` + terminal summary table.
    """
    import itertools
    import math
    import random as _random
    import statistics as _statistics

    from core.utils.config_loader import load_tool_config

    rounds = int(getattr(args, "rounds", 16))
    strategy = getattr(args, "strategy", "hill")
    oracle = getattr(args, "oracle", "speed")
    bench_filter = getattr(args, "filter", None)
    as_json = getattr(args, "json", False)
    list_tools = getattr(args, "list_tools", False)
    t_init = float(getattr(args, "T_init", 1.0))
    t_alpha = float(getattr(args, "T_alpha", 0.92))
    repeat = max(1, int(getattr(args, "repeat", 1)))

    # ── Tool detection ─────────────────────────────────────────────────────
    available = _detect_available_tools()

    if list_tools:
        Logger.info("Available analysis tools:")
        for name, path in sorted(available.items()):
            status = path if path else "(not found)"
            Logger.info(f"  {name:<12} {status}")
        return CLIResult(success=True, message="Tool list shown above", data=available)

    # ── Oracle validation / fallback ───────────────────────────────────────
    if oracle == "size":
        if not available.get("size") and not available.get("bloaty"):
            Logger.error(
                "oracle=size requires 'size' (binutils) or 'bloaty'. "
                "Neither was found on PATH."
            )
            return CLIResult(success=False, code=1, message="No size tool available")
    elif oracle == "instructions":
        if not available.get("perf") and not available.get("valgrind"):
            Logger.warn(
                "oracle=instructions: neither 'perf' nor 'valgrind' found — "
                "falling back to speed oracle"
            )
            oracle = "speed"

    # ── Load [autotuner] from tool.toml ────────────────────────────────────
    cfg = load_tool_config()
    at_cfg: dict = cfg.get("autotuner", {})

    # Honour T_init / T_alpha from tool.toml when not overridden
    t_init = float(at_cfg.get("T_init", t_init))
    t_alpha = float(at_cfg.get("T_alpha", t_alpha))

    # Select flag candidates based on oracle
    if oracle == "size":
        flag_groups: list[list[str]] = at_cfg.get(
            "size_flag_candidates", at_cfg.get("flag_candidates", [])
        )
    else:
        flag_groups = at_cfg.get("flag_candidates", [])

    if not flag_groups:
        Logger.error(
            "No flag_candidates defined in tool.toml [autotuner]. "
            'Add a section like:\n  [autotuner]\n  flag_candidates = [["-O2","-O3"],[...]]'
        )
        return CLIResult(success=False, code=1, message="No flag_candidates configured")

    AUTOTUNE_DIR = BUILD_DIR / "autotune"
    AUTOTUNE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Oracle implementations ──────────────────────────────────────────────

    def _oracle_speed(bench_bins: list, bench_filter) -> float | None:
        """Sum cpu_time across all benchmarks. Lower is better (ns)."""
        total = 0.0
        for bb in bench_bins:
            bench_cmd = [str(bb), "--benchmark_format=json", "--benchmark_min_time=0.1"]
            if bench_filter:
                bench_cmd.append(f"--benchmark_filter={bench_filter}")
            try:
                r = subprocess.run(bench_cmd, capture_output=True, text=True, timeout=180)
                if r.returncode == 0 and r.stdout.strip():
                    data = json.loads(r.stdout)
                    for bm in data.get("benchmarks", []):
                        total += bm.get("cpu_time", 0.0)
            except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
                Logger.warn(f"    Benchmark error: {exc}")
        return total if total > 0.0 else None

    def _oracle_size(trial_dir: Path, bench_bins: list) -> float | None:
        """Sum .text+.data bytes. Lower is better (bytes)."""
        size_bin = available.get("size")
        bloaty_bin = available.get("bloaty")
        targets = list(bench_bins)

        # Fall back to all ELF executables in the trial dir when bench bins absent
        if not targets:
            for p in trial_dir.rglob("*"):
                if p.is_file() and (p.stat().st_mode & 0o111):
                    try:
                        with open(p, "rb") as fh:
                            if fh.read(4) == b"\x7fELF":
                                targets.append(p)
                    except OSError:
                        pass

        total_bytes = 0
        for t in targets:
            if size_bin:
                try:
                    r = subprocess.run(
                        [size_bin, "--format=berkeley", str(t)],
                        capture_output=True, text=True, timeout=15,
                    )
                    if r.returncode == 0:
                        for line in r.stdout.splitlines():
                            parts = line.split()
                            # berkeley output: text  data  bss  dec  hex  filename
                            if len(parts) >= 4 and parts[0].isdigit():
                                total_bytes += int(parts[0]) + int(parts[1])
                except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
                    Logger.warn(f"    size error: {exc}")
            elif bloaty_bin:
                try:
                    r = subprocess.run(
                        [bloaty_bin, "-n", "0", "--csv", str(t)],
                        capture_output=True, text=True, timeout=30,
                    )
                    if r.returncode == 0:
                        for line in r.stdout.splitlines()[1:]:  # skip header
                            parts = line.split(",")
                            if len(parts) >= 2:
                                try:
                                    total_bytes += int(parts[-1])
                                except ValueError:
                                    pass
                except (subprocess.TimeoutExpired, OSError) as exc:
                    Logger.warn(f"    bloaty error: {exc}")

        return float(total_bytes) if total_bytes > 0 else None

    def _oracle_instructions(bench_bins: list, bench_filter) -> float | None:
        """Count instructions executed. Lower is better."""
        perf_bin = available.get("perf")
        valgrind_bin = available.get("valgrind")
        total_insn = 0.0

        for bb in bench_bins:
            bench_args = [str(bb), "--benchmark_min_time=0.05"]
            if bench_filter:
                bench_args.append(f"--benchmark_filter={bench_filter}")

            if perf_bin:
                cmd = [perf_bin, "stat", "-e", "instructions", "--"] + bench_args
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                    combined = r.stderr + r.stdout
                    for line in combined.splitlines():
                        if "instructions" in line:
                            for token in line.split():
                                cleaned = token.replace(",", "")
                                if cleaned.isdigit():
                                    total_insn += float(cleaned)
                                    break
                except (subprocess.TimeoutExpired, OSError) as exc:
                    Logger.warn(f"    perf stat error: {exc}")
            elif valgrind_bin:
                cmd = [
                    valgrind_bin, "--tool=callgrind",
                    "--callgrind-out-file=/dev/null", "--",
                ] + bench_args
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    for line in (r.stderr + r.stdout).splitlines():
                        if "I refs:" in line or "Ir " in line:
                            for token in line.split():
                                cleaned = token.replace(",", "")
                                if cleaned.isdigit():
                                    total_insn += float(cleaned)
                                    break
                except (subprocess.TimeoutExpired, OSError) as exc:
                    Logger.warn(f"    valgrind error: {exc}")

        return total_insn if total_insn > 0.0 else None

    # ── Build + score helper ───────────────────────────────────────────────

    def _score_flags(flags: list, trial_name: str) -> float | None:
        """Configure, build, then evaluate with the selected oracle."""
        trial_dir = AUTOTUNE_DIR / trial_name
        flags_str = " ".join(f for f in flags if f)
        Logger.info(
            f"  [{trial_name}] oracle={oracle} "
            f"CXX_FLAGS=[{flags_str or '(defaults)'}]"
        )

        cfg_cmd = [
            "cmake",
            "-S", str(PROJECT_ROOT),
            "-B", str(trial_dir),
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_CXX_FLAGS={flags_str}",
            "-DENABLE_BENCHMARKS=ON",
            "-DBUILD_TESTING=OFF",
            "-DBUILD_SHARED_LIBS=OFF",
        ]
        r = subprocess.run(cfg_cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if r.returncode != 0:
            Logger.warn(f"    Configure failed: {r.stderr[-300:].strip()}")
            return None

        bld_cmd = ["cmake", "--build", str(trial_dir), "--parallel"]
        r = subprocess.run(bld_cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
        if r.returncode != 0:
            Logger.warn(f"    Build failed: {r.stderr[-300:].strip()}")
            return None

        # Discover ELF benchmark binaries
        bench_bins: list[Path] = []
        for p in trial_dir.rglob("*"):
            if not p.is_file():
                continue
            name = p.name.lower()
            if ("bench" in name or "benchmark" in name) and (p.stat().st_mode & 0o111):
                try:
                    with open(p, "rb") as fh:
                        if fh.read(4) == b"\x7fELF":
                            bench_bins.append(p)
                except OSError:
                    pass

        if oracle in ("speed", "instructions") and not bench_bins:
            Logger.warn("    No benchmark binaries found. Build with ENABLE_BENCHMARKS=ON.")
            return None

        def _run_oracle_once():
            if oracle == "speed":
                return _oracle_speed(bench_bins, bench_filter)
            elif oracle == "size":
                return _oracle_size(trial_dir, bench_bins)
            elif oracle == "instructions":
                return _oracle_instructions(bench_bins, bench_filter)
            return None

        # Run oracle `repeat` times and take the median for noise reduction
        if repeat <= 1 or oracle == "size":
            # Size oracle is deterministic — repeating is pointless
            return _run_oracle_once()

        scores = []
        for run_idx in range(repeat):
            s = _run_oracle_once()
            if s is not None:
                scores.append(s)
        if not scores:
            return None
        median_score = _statistics.median(scores)
        if repeat > 1:
            Logger.info(
                f"    Repeat {repeat}x → scores={[f'{s:.1f}' for s in scores]} "
                f"median={median_score:.1f}"
            )
        return median_score

    # ── Run selected strategy ──────────────────────────────────────────────
    results: list[dict] = []
    best_flags: list[str] = [g[0] for g in flag_groups]
    best_score: float = float("inf")
    oracle_unit = {
        "speed": "ns (cpu_time, ↓)",
        "size": "bytes (.text+.data, ↓)",
        "instructions": "insn (↓)",
    }.get(oracle, "score (↓)")

    if strategy == "hill":
        Logger.info(f"Autotune: hill-climb  oracle={oracle}")
        score = _score_flags(best_flags, "baseline")
        if score is None:
            return CLIResult(success=False, code=1, message="Baseline build/run failed")
        best_score = score
        results.append({"trial": "baseline", "flags": list(best_flags), "score": best_score})
        Logger.info(f"  Baseline: {best_score:.1f} {oracle_unit}")

        iteration = 0
        improved = True
        while improved and iteration < rounds:
            improved = False
            for gi, group in enumerate(flag_groups):
                for alt_flag in group[1:]:
                    if iteration >= rounds:
                        break
                    trial_flags = list(best_flags)
                    trial_flags[gi] = alt_flag
                    trial_name = f"hill_{iteration:02d}"
                    new_score = _score_flags(trial_flags, trial_name)
                    iteration += 1
                    if new_score is not None:
                        results.append({
                            "trial": trial_name,
                            "flags": trial_flags,
                            "score": new_score,
                        })
                        if new_score < best_score:
                            best_score = new_score
                            best_flags = trial_flags
                            improved = True
                            Logger.info(
                                f"  ↑ Improved → {best_score:.1f}  flags={trial_flags}"
                            )

    elif strategy == "grid":
        Logger.info(f"Autotune: grid search  oracle={oracle}")
        combos = list(itertools.product(*flag_groups))[:rounds]
        for i, combo in enumerate(combos):
            trial_flags = list(combo)
            new_score = _score_flags(trial_flags, f"grid_{i:02d}")
            if new_score is not None:
                results.append({
                    "trial": f"grid_{i:02d}",
                    "flags": trial_flags,
                    "score": new_score,
                })
                if new_score < best_score:
                    best_score = new_score
                    best_flags = trial_flags
                    Logger.info(f"  Best so far → {best_score:.1f}  flags={trial_flags}")

    elif strategy == "random":
        Logger.info(f"Autotune: random sampling  oracle={oracle}  rounds={rounds}")
        seen: set = set()
        attempts = 0
        max_attempts = rounds * 5
        while len(results) < rounds and attempts < max_attempts:
            attempts += 1
            combo = [_random.choice(g) for g in flag_groups]
            key = tuple(combo)
            if key in seen:
                continue
            seen.add(key)
            trial_name = f"rand_{len(results):02d}"
            new_score = _score_flags(combo, trial_name)
            if new_score is not None:
                results.append({"trial": trial_name, "flags": combo, "score": new_score})
                if new_score < best_score:
                    best_score = new_score
                    best_flags = combo
                    Logger.info(f"  ↑ New best → {best_score:.1f}  flags={combo}")

    elif strategy == "anneal":
        Logger.info(
            f"Autotune: simulated annealing  oracle={oracle}  "
            f"T={t_init}  α={t_alpha}"
        )
        current_flags = [_random.choice(g) for g in flag_groups]
        score = _score_flags(current_flags, "anneal_init")
        if score is None:
            return CLIResult(
                success=False, code=1,
                message="Initial build/run failed for annealing",
            )
        current_score = score
        best_score = current_score
        best_flags = list(current_flags)
        results.append({
            "trial": "anneal_init",
            "flags": list(current_flags),
            "score": current_score,
        })
        T = t_init
        for i in range(rounds):
            gi = _random.randrange(len(flag_groups))
            new_flags = list(current_flags)
            new_flags[gi] = _random.choice(flag_groups[gi])
            trial_name = f"anneal_{i:02d}"
            new_score = _score_flags(new_flags, trial_name)
            if new_score is None:
                T *= t_alpha
                continue
            results.append({"trial": trial_name, "flags": new_flags, "score": new_score})
            delta = new_score - current_score
            # Accept if better, or with Boltzmann probability if worse
            if delta < 0 or _random.random() < math.exp(
                -delta / (T * current_score + 1e-9)
            ):
                current_flags = new_flags
                current_score = new_score
                if new_score < best_score:
                    best_score = new_score
                    best_flags = new_flags
                    Logger.info(
                        f"  ↑ New best (T={T:.3f}) → {best_score:.1f}  flags={new_flags}"
                    )
            T *= t_alpha

    else:
        return CLIResult(
            success=False, code=1,
            message=f"Unknown strategy: {strategy!r}. "
                    "Use hill, grid, random, or anneal.",
        )

    # ── Persist + report ───────────────────────────────────────────────────
    results.sort(key=lambda e: e.get("score", float("inf")))
    best_flag_str = " ".join(f for f in best_flags if f) or "(defaults)"
    output = {
        "strategy": strategy,
        "oracle": oracle,
        "best_flags": best_flags,
        "best_score": best_score if best_score < float("inf") else None,
        "trials": results,
    }
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = LOGS_DIR / "autotune_results.json"
    out_file.write_text(json.dumps(output, indent=2), encoding="utf-8")

    Logger.info(f"\nAutotune complete — {len(results)} trial(s) run.")
    Logger.info(f"Oracle     : {oracle} ({oracle_unit})")
    Logger.info(f"Best flags : {best_flag_str}")
    if best_score < float("inf"):
        Logger.info(f"Best score : {best_score:.1f} {oracle_unit}")
    else:
        Logger.info("Best score : N/A (all trials failed)")
    Logger.info(f"Results    → {out_file}")

    Logger.info(f"\n{'Trial':<15} {'Flags':<45} {'Score':>12}")
    Logger.info("-" * 75)
    for entry in results[:10]:
        flag_str = " ".join(f for f in entry["flags"] if f) or "(defaults)"
        score_s = f"{entry['score']:.1f}" if entry.get("score") is not None else "N/A"
        Logger.info(f"{entry['trial']:<15} {flag_str:<45} {score_s:>12}")

    if as_json:
        print(json.dumps(output, indent=2))

    return CLIResult(success=True, message="Autotune complete", data=output)
