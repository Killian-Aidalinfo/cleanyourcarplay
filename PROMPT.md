# The prompt

Copy everything below the line into Claude Code (or any coding agent with shell
access) and fill in the one blank. The agent does the rest, and asks you four
questions along the way.

## Before you start

1. **Your box must be an Android AI Box**, not a Linux dongle. If yours is a
   small adapter with a web config page and no Android, stop here — see
   [references/families.md](references/families.md). The toolkit will tell you
   too, but you may as well know now.
2. **Enable ADB.** On most of these boxes it is already on: the firmware opens
   port 5555 at every boot regardless of the setting. If not, find Settings →
   About and tap the build number seven times, then enable USB debugging and
   network/ADB debugging.
3. **Get the box onto your home Wi-Fi**, once, from the car. Everything after
   that happens at your desk. If your box exposes ADB over USB, use the cable
   instead — see [docs/CONNECT.md](docs/CONNECT.md).
4. **Know that the first run changes nothing.** It reads, it tells you what it
   found, and it stops. You decide whether to go further.

---

I want to diagnose and debloat my Android CarPlay AI Box with the
cleanyourcarplay toolkit.

My box is: `<BRAND AND MODEL HERE, or "I don't know">`

Work on the real device, step by step, and show me what you find as you go. Ask
me before anything that depends on what I use. Never guess at a package's role.

**Get the toolkit**

Clone https://github.com/Killian-Aidalinfo/cleanyourcarplay and read
`AGENTS.md` before you touch my device. The rules in it are not negotiable, and
they exist because this device has no screen, no remote and no reset button: if
you break its boot or its Wi-Fi, neither of us can get back in.

**Connect**

Find my box on the network — ARP, mDNS, a port scan for 5555, or ask me for the
address. Prefer USB if `adb devices` shows it there; a cable survives a Wi-Fi
that stops coming up.

If ADB wants authorisation, tell me, because the prompt appears on the box's
screen, which means in the car.

Set `BOX_HOST` and confirm you are talking to it:

```bash
export BOX_HOST=<address>
python3 tools/box.py --probe
```

If the probe says this is a Linux dongle, stop and tell me. There is nothing
here for it.

**Diagnose first — this changes nothing**

```bash
python3 tools/diag.py --write
python3 tools/profile.py
```

Then tell me, in plain words:

- why the box last rebooted, and whether it looks electrical or like software;
- what has been crashing;
- how much memory is actually free;
- how hot it has been running.

If the evidence points at power loss, **say so before we debloat anything**, and
explain that cleaning up will not fix a supply problem. My box runs off a
cigarette-lighter or car USB port, so this is a real possibility, not a formality.
Point me at `references/power-test.md` if it is worth measuring.

Stop here and let me read it. This first pass is worth having on its own.

**Debloat**

Only if I say to continue.

Build the package list from what is actually installed, using
`python3 tools/classify.py` with my device's `probe.json`. Do not reuse a list
from another model.

Before you touch anything in the RISKY group, ask me these four as a checklist
and only disable what I do not tick:

1. Do I use **Android Auto** as well as CarPlay? (Ask it. It depends on the
   phones in my household, and you cannot know that.)
2. Do calls and audio go through the box, or through the car's own Bluetooth?
3. Keep firmware updates?
4. Keep the voice assistant?

Then work in **small batches**:

```bash
tools/disable.sh <list-file>
```

The tool refuses NEVER packages by itself. Do not try to work around it, and do
not ask me to authorise an exception — there is no flag, by design.

After each batch the tool syncs, waits, and runs a survival check. If any of it
comes back red, **stop and restore**. Do not start the next batch.

Tell me honestly after each batch that the desk check does **not** prove the
touchscreen still works. An injected tap is not a finger on the car's screen.

**Verify**

Measure before and after: free memory, process count, and the time from power-on
to CarPlay appearing — that last one is what I actually feel.

Then send me to the car with a list of what to check:

- the screen responds to my finger;
- CarPlay pairs and connects wirelessly;
- audio plays and calls work;
- Android Auto still works, if I said I use it;
- how long it takes from starting the engine to CarPlay appearing.

If anything is wrong, `tools/restore.sh` puts it all back.

**Finish**

- Write `profiles/<brand>-<model>/mesures.md` with the before/after numbers.
- Write `recovery/<brand>-<model>.md` **for the SoC you actually found**, not
  from a template. If it is not Qualcomm, do not write an EDL section.
- Offer to close ADB debugging, and verify the port is really shut rather than
  trusting the toggle.
- Tell me what you could not establish. I would rather have an honest gap than
  a confident guess.

Everything you do is reversible with one command, and nothing is uninstalled.
