# Rules for coding agents in this repo

## First: which job are you doing?

| You are... | Read |
|---|---|
| cleaning someone's box | `PROMPT.md`, then this file's **Cleaning a box** section |
| changing this repo | this whole file |

---

## Cleaning a box: the rules that are not negotiable

This device has **no screen of its own, no remote, and no reachable settings
menu.** It renders into a car's CarPlay window. ADB over the network is the only
way back from any mistake. Everything below follows from that.

### Refuse, without exception

- **Never disable a NEVER package.** `tools/apply.py` enforces this and there is
  no override flag. Do not add one, do not shell out around it, and do not ask
  the user to authorise an exception. If a user insists, explain the
  consequence and decline.
- **Never `pm uninstall`.** Disable only, `pm disable-user --user 0`.
- **No root, no flashing, no `/system`.** Nothing in this repo writes a
  firmware image, touches a bootloader or a modem, or redistributes a loader.
- **Never launch a factory or engineering menu app**, even to look. Disabling
  one is fine; opening one can write to partitions. `dumpsys package <name>`
  tells you what you need.
- **Never treat an unknown package as safe.** Unknown is RISKY. Read
  `dumpsys package <name>` first, then ask the user.

### Sequence

1. **Probe before anything.** If it is not an Android AI Box, stop and say so.
2. **Diagnose and capture a profile before any change.** The read-only pass has
   value on its own, and it is the backup.
3. **Prove restore works before the first real batch**: disable one obviously
   harmless package, reboot, restore it, reboot. Only then continue.
4. **Write the model's recovery page before the first batch**, not after. If
   EDL is the only way back on this SoC, you want it read and understood before
   you need it.
5. **Small batches.** Until it is proven on hardware that the mirroring
   accessibility service binds outside a car, one package family per in-car
   cycle.
6. **`sync` and wait before every reboot.** An entire batch was lost on the
   reference device by rebooting too soon.
7. **Survival check after every batch**, four greens or stop: ADB answers,
   accessibility service still bound, Wi-Fi up, screencap obtained.

### Honesty

- **An injected tap is not proof of touch.** `input tap` takes a different path
  than a finger on the car's screen. Say so every time you report a desk check.
- **Only the tool saying the port is closed counts**, not how a toggle looks.
- **Say what you could not establish.** A named gap is worth more than a
  confident guess, and this whole project exists because other repos did the
  opposite.
- **Do not claim support for hardware you have not seen.** `profiles/` lists
  devices that were actually probed. Nothing else.

### Ask before

- anything in the RISKY group — Android Auto above all, because it depends on
  which phones are in the household and you cannot know that;
- anything the user's family or passengers rely on;
- disabling Play Services, with the Bluetooth-pairing and text-to-speech
  consequence stated first.

### Never put in a public file

IP addresses, Wi-Fi names, email addresses, serial numbers, Android IDs, MAC
addresses, paired phone names. `tools/box.py:redact()` handles the obvious
cases; read what you are about to commit anyway. Raw dumps live under
`profiles/*/raw/` and are gitignored — keep it that way.

---

## Repo map

| Path | Responsibility |
|---|---|
| `PROMPT.md` / `PROMPT.fr.md` | the user-facing interface |
| `AGENTS.md` / `CLAUDE.md` | these rules |
| `tools/box.py` | ADB transport, probe, redaction, device family |
| `tools/diag.py` | read-only diagnosis and its conclusions |
| `tools/profile.py` | state capture: backup, contribution, fixtures |
| `tools/classify.py` | NEVER / RISKY / SAFE, the heart of the project |
| `tools/apply.py` | disable, restore, survival check |
| `tools/check.py` | drift against the recorded profile |
| `references/` | the human-readable rules and what evidence proves |
| `profiles/<brand>-<model>/` | what a real device reported |
| `recovery/<brand>-<model>.md` | how to get that model back |

## Where a change goes

- A package's classification changes in **`tools/classify.py` and
  `references/classify.md` together.** They must agree; the Markdown is the
  explanation, not a separate source of truth.
- A new device gets a `profiles/<brand>-<model>/` directory and, once its SoC
  is known, a `recovery/` page.
- A new evidence source goes in `tools/diag.py` **and** gets a paragraph in
  `references/diag.md` saying what it proves and what it does not.

## Hard rules for repo changes

- Python 3.9+, standard library only. No new dependencies.
- English is canonical. Changing `PROMPT.md` or `README.md` means changing
  `PROMPT.fr.md` or `README.fr.md` in the same PR.
- Do not weaken a guardrail to make a workflow smoother. If a rule is wrong,
  argue it in an issue with the device that proves it.
- A package moves to SAFE only with a reason and a device it was verified on.
  A package moves to NEVER on a single report.

## Commit and PR style

Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`). Say which device,
if any, a change was verified on. Be kind in reviews.
