# cleanyourcarplay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a public, agent-driven toolkit that diagnoses why an Android CarPlay AI Box crashes or reboots, then safely disables everything it does not need to be a wireless CarPlay adapter.

**Architecture:** Markdown is the product (`PROMPT.md` is the user interface, pasted into Claude Code); Python 3.9+ tools are the agent's hands. Everything runs over ADB — USB first, home Wi-Fi as the default, the box's own AP only as a fallback. Read-only probe and diagnosis come first and are shippable on their own (M0); nothing is disabled until restore is proven on real hardware.

**Tech Stack:** Python 3.9+ (stdlib only), POSIX shell wrappers, Markdown. No Java, no launcher, no root, no flashing.

**Spec:** `docs/superpowers/specs/2026-11-26-cleanyourcarplay-design.md`

## Global Constraints

- Disable only, via `pm disable-user --user 0`. Never `pm uninstall`, never root, never flash, never touch `/system`.
- `adb shell sync` + wait before every reboot, or the batch is lost.
- NEVER list is absolute and the tools refuse it: mirroring stack (the accessibility service that injects touch), APEX packages on Android 13+, Wi-Fi/Bluetooth/network, `systemui`, `shell`, `settings`, essential providers.
- An unknown package is RISKY by default, never SAFE.
- No box is sacrificial. M0 is read-only. No disabling before a restore round-trip is proven on hardware.
- Bugreports and raw dumps are gitignored. Committed profiles carry derived facts only — no IP, SSID, serial, Android ID, MAC, paired phone names.
- English is canonical; `README.fr.md` and `PROMPT.fr.md` must land in the same PR as their English source.
- Python 3.9+, stdlib only.
- Linux CarPlay dongles are out of scope: detect, explain, stop.
- EDL recovery is Qualcomm-only and never automated. No firmware or loader redistributed.

## Review Focus

Tests are deferred by the repo owner; these are the input classes the fixtures must eventually cover, and until then the code must degrade gracefully rather than crash:

1. A device that is not Android at all (Linux dongle) — must be named and refused, not probed into a traceback.
2. A missing diagnostic source (`pstore` absent, no thermal zones, unknown boot-reason property name) — the report must drop that line, not fail.
3. `pm disable-user` refused for every package — stop and say so, never loop.
4. A package on the NEVER list requested by the user — refused with the reason, no override flag.
5. ADB reachable but the device reboots mid-batch — the state file must survive and `restore.sh` must still replay it.

---

### Task 1: Repo skeleton and the honest README

**Files:** Create `LICENSE`, `.gitignore`, `README.md`, `README.fr.md`, `CONTRIBUTING.md`

- [ ] MIT licence, 2026 Killian Stein.
- [ ] `.gitignore` excludes `profiles/*/raw/`, `*.bugreport.zip`, `__pycache__/`, `.venv/`.
- [ ] README states what it is, what it is NOT (no launcher, no root, no Linux dongles), the hardware it has actually been tested on (**none yet** — say so), the ADB-root security warning, and attribution to cleanyourtv (MIT).
- [ ] `CONTRIBUTING.md` explains how to submit an anonymised profile.

### Task 2: `tools/box.py` — ADB client and probe

**Files:** Create `tools/box.py`

**Produces:** `Box(host, port)` with `.shell(cmd) -> str`, `.getprop(name) -> str`, `.packages() -> list[str]`, `.screencap(path)`, `.family() -> "android" | "linux-dongle" | "unknown"`, `.probe() -> dict`

- [ ] Prefer the `adb` binary when present; fall back to a direct TCP ADB client so the SDK is not required.
- [ ] `--probe` prints model, brand, SoC, Android version, build, RAM, storage, and whether ADB is reachable over USB.
- [ ] `--probe` detects the Linux-dongle family and exits 2 with the out-of-scope message from `references/families.md`.
- [ ] Redact IP, SSID, serial, Android ID, MAC from everything it prints.

### Task 3: `references/` — the classification is the product

**Files:** Create `references/classify.md`, `references/families.md`, `references/diag.md`, `references/power-test.md`

- [ ] `classify.md`: NEVER / RISKY / SAFE with the reason for each entry, the two documented bricking cases (touch loss via the accessibility-service package, APEX on Android 13+), and the `sync`-before-reboot rule.
- [ ] `families.md`: how to tell an Android AI Box from a Linux dongle, and where to send people with a Linux one.
- [ ] `diag.md`: each evidence source, what it proves, and what it does NOT prove.
- [ ] `power-test.md`: the optional manual USB-meter / bench-supply procedure.

### Task 4: `tools/diag.py` — M0, strictly read-only

**Files:** Create `tools/diag.py`

**Consumes:** `Box` from Task 2.
**Produces:** `diagnose(box) -> dict`, written to `profiles/<brand>-<model>/diag.md`

- [ ] Collect boot reason, `dumpsys dropbox`, pstore, thermal zones, power supply, uptime, memory.
- [ ] Every source is optional: a missing one is reported as unavailable, never an exception.
- [ ] The rendered report **concludes** at the strength of its evidence: "signs of power loss", never "it is the power supply".
- [ ] Writes nothing to the device. Refuses to run if any write flag is passed.

### Task 5: `tools/profile.py` — capture state and fixtures

**Files:** Create `tools/profile.py`

- [ ] Writes `profiles/<brand>-<model>/probe.json`, `packages.txt`, `settings.json`.
- [ ] Writes raw dumps under `profiles/<brand>-<model>/raw/` (gitignored) for later fixture use.
- [ ] Anonymises everything that lands in a committed file.

### Task 6: disable / restore / check

**Files:** Create `tools/disable.sh`, `tools/restore.sh`, `tools/check.py`, `tools/classify.py`

- [ ] `classify.py` turns a package list into NEVER / RISKY / SAFE using `references/classify.md` rules; unknown ⇒ RISKY.
- [ ] `disable.sh` refuses any NEVER package outright — no override flag exists — syncs and waits before suggesting a reboot, and records every change.
- [ ] `restore.sh` replays the recorded state, packages and settings both.
- [ ] `check.py` compares the device to the recorded profile and reports drift.
- [ ] Survival check after each batch: accessibility service still bound, Wi-Fi up, ADB answering, screencap obtained.

### Task 7: The agent interface

**Files:** Create `PROMPT.md`, `PROMPT.fr.md`, `AGENTS.md`, `CLAUDE.md`

- [ ] `PROMPT.md` is what the user pastes into Claude Code: preparation, connection, M0 diagnosis, the four checklist questions, batches, two-tier verification, closing ADB.
- [ ] `AGENTS.md` holds the non-negotiable rules for the agent, including the refusal list and the honesty rules ("an injected tap is not proof of touch").
- [ ] `CLAUDE.md` imports `AGENTS.md`.
- [ ] `PROMPT.fr.md` mirrors `PROMPT.md`.

### Task 8: Recovery template

**Files:** Create `recovery/TEMPLATE.md`

- [ ] Three levels: `restore.sh`, factory reset by the device's own means, EDL last resort marked **Qualcomm only**.
- [ ] States that a page is written only after a probe identifies the SoC.

### Task 9 (deferred by owner): fixture-based tests

**Files:** Create `tests/fixtures/README.md`

- [ ] Explain that fixtures are captured at M0 on real hardware and that the classification tests are written against them. No test code until hardware exists.
