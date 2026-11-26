# Proving the electrical hypothesis (manual, optional)

The toolkit can only ever say "signs consistent with power loss". It reads what
the device reports about itself, and a box that browns out mid-write may not
report anything at all. If you want certainty, you have to measure from outside.

None of this is automated, and none of it is required.

## What you are testing for

Two different faults, often confused:

1. **Not enough current.** Car USB ports and cheap cigarette-lighter adapters
   frequently deliver well under 1 A. The box boots fine, then resets the moment
   mirroring and Wi-Fi draw at the same time.
2. **Voltage sag at crank.** The vehicle's 12 V rail collapses while the starter
   turns. A box powered from an unfiltered accessory socket reboots every time
   you start the engine — and only then.

They need different fixes, so it is worth knowing which you have.

## Test 1 — how much does it actually draw?

A USB power meter, inline between the supply and the box, costs very little.

1. Plug the meter between the box and its usual car supply.
2. Watch the current at idle, then while CarPlay is mirroring with navigation
   running — that is the real peak.
3. Compare against what the supply claims.

If peak draw approaches or exceeds the port's rating, you have fault 1. Move to
a known-good supply rated well above the peak and see whether the reboots stop.

## Test 2 — does it survive the crank?

Easiest honest version, no bench equipment:

1. Power the box from a **separate, known-good source** — a USB power bank is
   ideal, because it does not care what the car's rail is doing.
2. Drive normally for as long as it usually takes to see a reboot, engine stops
   and starts included.
3. If the reboots stop, the fault is the car's supply.

With a bench supply you can do it properly: set 5 V, dip briefly toward 4.0–4.2 V
to imitate the crank, and watch whether the box survives. Do this only if you
are comfortable with the equipment.

## What to do with the result

| Result | Fix |
|---|---|
| High peak draw, weak port | A proper 12 V → USB adapter rated well above peak, wired to a switched accessory circuit |
| Fine at idle, reboots only at engine start | A supply with hold-up, or one on a circuit that is not dropped during cranking |
| Reboots on a power bank too | It is not electrical. Go back to [diag.md](diag.md) |

Record the outcome in the device's profile under `mesures.md`. A confirmed
electrical fault is worth far more to the next person than another package list.
