# Profiles

One directory per device that was **actually probed**. If a model is not listed
here, this toolkit has never seen it.

That is the point. Most repos in this space claim hundreds of supported devices
on the strength of one. This one would rather cover three honestly.

```
profiles/<brand>-<model>/
  probe.json      brand, model, SoC, Android version, build, RAM, storage
  packages.txt    packages and their state, as found
  settings.json   the settings keys this toolkit may change
  diag.md         the rendered diagnosis
  changes.jsonl   every change made, journalled before it was made
  mesures.md      before/after numbers
  raw/            local dumps — gitignored, never committed
```

To add yours, see [CONTRIBUTING.md](../CONTRIBUTING.md). The read-only pass is
enough: a profile and a diagnosis are a real contribution even if you never
disable anything.
