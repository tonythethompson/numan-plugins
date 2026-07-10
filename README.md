# numan-plugins

CI build+sign pipeline feeder for the [Numan](https://github.com/tonythethompson/numan)
official registry — implements the binary-delivery half of
[numan #30](https://github.com/tonythethompson/numan/issues/30).

## Why this repo exists

Numan installs plugins from **signed, hash-pinned binary artifacts** (a plugin
install bails if `sha256` is missing). But almost every popular Nushell plugin
ships source-only — no prebuilt release binaries — so users would need a full
Rust toolchain to install them. A survey of the curated
[`awesome-nu`](https://github.com/nushell/awesome-nu) plugin list found that
**every** plugin with a compliant release asset is already in the registry; the
~50 most-wanted plugins (highlight, dns, regex, dbus, plot, compress, units, …)
are all source-only and cannot be hand-intaken.

This repo closes that gap: it cross-compiles those plugins from their upstream
tags, packages one archive per target, and publishes them as GitHub release
assets. [`numan-registry`](https://github.com/tonythethompson/numan-registry)
then pins those URLs and signs the index with the official trust root.

## Trust boundary

- This repo **builds and hosts binaries only**. It never holds signing keys.
- Signing stays in `numan-registry` (`production.yml` + the Ed25519 trust root).
- Every hash is computed at intake by `numan-registry`'s `add-package.py` from
  the uploaded asset — never hand-typed here.
- Provenance (upstream repo + tag) is pinned in `manifest.json` and each release.

## Layout

| Path | Purpose |
|------|---------|
| `manifest.json` | `active[]` = plugins built now; build matrix + target→runner map |
| `docs/backlog.json` | demand-ranked source-only plugins awaiting promotion |
| `.github/workflows/build.yml` | matrix build → package → release → emit spec |
| `scripts/package_plugin.py` | normalize a built binary into a `.tar.gz`/`.zip` |
| `scripts/gen_spec.py` | emit a `numan-registry` `kind:binary` spec (no sha256) |

## Build matrix

`x86_64`/`aarch64` Linux (gnu), `x86_64`/`aarch64` macOS, `x86_64` Windows.
Linux aarch64 cross-compiles via `taiki-e/setup-cross-toolchain-action`; the
rest build on native runners.

## Flow (per plugin)

1. Add the plugin to `manifest.json` `active[]` (repo, upstream tag, bin, Nu
   version compat).
2. Run the **build-plugins** workflow (`workflow_dispatch`, optional `only=`
   filter). It builds all targets, publishes a release `<name>-<version>` with
   the archives, and uploads a `spec-<name>.json` artifact.
3. Drop `spec-<name>.json` into `numan-registry/specs/`, run
   `python scripts/add-package.py --spec … --write` there (computes every
   sha256, merges + schema-validates the index).
4. Lifecycle-prove on a clean `NUMAN_ROOT`
   (`search → info → install → activate → doctor → list → remove → gc`) on each
   target OS against a real Nu binary.
5. Open the registry PR; staging signs ephemerally, production signs with the
   trust root and publishes.

## Currently active

- `cptpiepmatz/nu-plugin-highlight` @ `v1.4.15+0.113.1` → `nu_plugin_highlight` 1.4.15
- `fdncred/nu_plugin_regex` @ `v0.22.0` → `nu_plugin_regex` 0.22.0
- `dead10ck/nu_plugin_dns` @ `v4.0.10` → `nu_plugin_dns` 4.0.10

## Registry-side follow-up

`numan-registry`'s `add-package.py` `build_version_entry()` carries only
`verified_with` / `activation` / `dependencies` / `artifact`. To land build
provenance (`git`/`rev`/`cargo_name`) in the **signed** index — the auditability
payoff for #30 — teach it to pass through the schema's existing `source` block.
Until then, provenance lives in this repo's `manifest.json` and release tags.
