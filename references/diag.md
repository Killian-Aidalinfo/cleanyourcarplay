# Diagnosis: the evidence, and what each piece actually proves

The point of this file is restraint. Each source below supports a narrow claim.
The report must not make a wider one.

Android keeps most of this **across a reboot**, which is why no daemon has to be
left running on the box. A crash that happened on the motorway can be read at
the desk the next day.

## Boot reason

```
getprop sys.boot.reason
getprop ro.boot.bootreason
```

The single most useful value in the whole toolkit: it is what separates "the car
cut the power" from "the software fell over".

| Value family | Reading |
|---|---|
| `reboot`, `shutdown,userrequested` | clean, someone or something asked |
| `kernel_panic*`, `watchdog*` | software or driver failure |
| `hard_reset`, `power_key`, `usb` | abrupt |
| `UVLO`, `pon_*`, `cold_boot`, power-related PMIC codes | **undervoltage / power loss — the electrical hypothesis** |

> Property names and value vocabularies vary by SoC and vendor. Treat an
> unrecognised value as unknown and say so; never map it to a cause by guessing.

## Crash mailbox

```
dumpsys dropbox --print
```

Holds app crashes, system server crashes, ANRs, kernel panics and reboot
records, each timestamped. This is where "CarPlay crashed" becomes a named
process and a stack.

Proves: something crashed, when, and what. Does **not** prove the crash caused a
reboot — correlate timestamps with the boot reason.

## Persistent kernel log

```
ls /sys/fs/pstore/
cat /sys/fs/pstore/console-ramoops*
```

Survives a panic. Often absent on consumer firmwares. Absence means nothing — do
not report it as a finding.

## Thermal

```
cat /sys/class/thermal/thermal_zone*/type
cat /sys/class/thermal/thermal_zone*/temp
```

Read at idle and again under mirroring load. A box behind a windscreen in summer
is a plausible thermal-shutdown candidate; a cold box that reboots is not.

Proves: a temperature at a moment. Only a sustained high reading immediately
before a reboot supports a thermal conclusion.

## Power

```
ls /sys/class/power_supply/
cat /sys/class/power_supply/*/voltage_now
cat /sys/class/power_supply/*/current_now
cat /sys/class/power_supply/*/online
```

Supports the electrical hypothesis, and it is the weakest link in the chain: on
a box with no battery these nodes are often missing or meaningless.

**Proves very little on its own.** The honest sentence is "signs consistent with
power loss", never "it is the power supply". To actually prove it, see
[power-test.md](power-test.md).

## Memory and processes

```
cat /proc/meminfo
dumpsys meminfo
ps -A
```

Establishes the before/after of the cleanup, and makes the OOM-killer case when
free memory is chronically low.

## Full bugreport

```
adb bugreport <file>
```

Captured for local reference only. **Never committed.** It contains IP, SSID,
serial number, MAC address, paired phone names, Bluetooth history and often
location.

---

## Writing the report

Conclude, but only to the strength of the evidence.

Good:

> Three reboots in the last 48 h. All three show signs of power loss in the boot
> reason, none shows a crash in dropbox, and the device never exceeded 48 °C.
> Start by changing the power source — debloating will not change this.

Bad:

> Your power supply is faulty.

Bad:

> Here are 40 lines of dropbox output.

If a source is unavailable, drop its line from the report. Never crash on a
missing source, and never present absence as evidence.
