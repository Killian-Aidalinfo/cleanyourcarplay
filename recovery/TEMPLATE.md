# Recovery — <Brand> <Model>

> Copy this file to `recovery/<brand>-<model>.md` and fill it in **after a probe
> has identified the SoC on the real device.** Never from a datasheet, never by
> analogy with another box.
>
> An EDL procedure written for the wrong SoC family is worse than no page at
> all, because it reads as authoritative to someone who is already panicking.

## Device

| | |
|---|---|
| Brand / model | |
| SoC | |
| Android version / build | |
| Storage | |
| Buttons | (is there a mode button? a pinhole?) |
| Verified by | (who, on which device, when) |

## Level 1 — undo this toolkit's work

```bash
export BOX_HOST=<address>
tools/restore.sh
```

Re-enables every package this toolkit disabled on this device and replays the
saved settings. A package you disabled by hand stays disabled.

Then reboot and check: does ADB come back, does Wi-Fi come up, does the car
screen respond to your finger?

## Level 2 — the device's own reset

Fill in the real procedure for this model: button combination, timing, what the
LED does, how long the first boot takes afterwards.

> On the reference device (Carlinkit TBox Ultra 2) the first boot after erasing
> user data takes about ten minutes. Do not assume it is bricked at minute
> three.

What you lose: pairings, settings, anything stored on the box.

## Level 3 — EDL (**Qualcomm only**)

Delete this whole section if the SoC is not Qualcomm. Amlogic, Allwinner and
MediaTek have entirely different procedures, and a wrong one here will cost
somebody their device.

If it is Qualcomm, document:

- how to enter EDL mode (on the reference device: hold the mode button while
  plugging in USB-C, keep holding ~10 s);
- which firehose loader matches this SoC, and its checksum;
- the exact commands, **limited to reading the partition table and erasing
  userdata/metadata**.

**What this repo will never do:** redistribute a firmware image or a loader,
write a firmware image, or touch `xbl`, `persist`, the bootloader or the modem.
That is how people permanently kill these devices. Get the stock firmware from
the vendor yourself.

## What bricked it, if you know

If you got here because something went wrong, write down what. That is the most
valuable paragraph on this page for the next person — more valuable than the
recovery steps, because it stops them needing it.
