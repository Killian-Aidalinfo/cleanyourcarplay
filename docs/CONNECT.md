# Reaching a box that has no screen

On your desk this device is blind. It has no display of its own — it renders
into your car's CarPlay window — so you cannot read an IP address off it, and
you cannot tap "allow" on a prompt. Plan the connection before you need it.

Three routes, best first.

## 1. USB — if this model exposes ADB over its USB-C port

The best one, and the probe reports whether it is available.

```bash
adb devices          # a serial with no ':' is a USB device
```

A cable survives a Wi-Fi that no longer comes up, which is this project's worst
failure mode. **If USB works on your box, run batches over the cable** and keep
Wi-Fi as the way back rather than the only way in.

## 2. The box on your home Wi-Fi — the default

Most of these boxes join a Wi-Fi network once and remember it. Get it onto your
home network once, from the car or over USB, and it is reachable from your desk
forever after.

```bash
export BOX_HOST=192.168.1.50
python3 tools/box.py --probe
```

Finding it:

```bash
arp -a | grep -i -E 'carlink|ottocast|autokit'   # may or may not help
nmap -p 5555 --open 192.168.1.0/24               # if you have nmap
```

Many of these boxes leave port 5555 open at every boot regardless of what the
settings say — see the security note in the README.

## 3. The box's own access point — fallback only

The box creates a Wi-Fi access point to pair with your phone, usually named
something like `AutoKit-xxxx`. You can join it from your computer and talk ADB
to the gateway.

**Read this before you do:** that access point exists to pair a phone. It very
probably has **no internet uplink**. If your computer has one network interface
and you join it, you lose your connection to everything else — including, if
you are driving this from Claude Code, the agent itself.

So use this route only with a second interface: a USB Wi-Fi dongle, or your
phone's hotspot on the built-in adapter while the dongle joins the box.

```bash
# after joining the box's AP on a second interface
ip route | grep default        # the gateway is usually the box
export BOX_HOST=192.168.50.1   # varies by vendor
```

## If ADB asks for authentication

The pure-Python client in `tools/box.py` does not implement the RSA handshake.
If the box demands it, install Android platform-tools and let the toolkit use
the real `adb` binary — it picks it up automatically when it is on PATH.

```bash
adb connect 192.168.1.50:5555
```

The confirmation prompt appears on the box's display, which means **in the
car**. Accept it there once, tick "always allow from this computer", and you
will not be asked again.

## When you are done

Let the toolkit close debugging, and let it verify. The toggle looking right is
not the same as the port being shut.
