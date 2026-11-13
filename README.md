[![Русский](https://img.shields.io/badge/%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9-181717?style=for-the-badge)](README.ru.md)

# Spore CrossOver Kit

A launcher, graphics settings and small diagnostic tools preserved from a Steam Spore: Galactic Adventures setup on an Apple silicon Mac.

**[Download v0.1.1 source](https://github.com/vkupyansky/spore-crossover-kit/releases/download/v0.1.1/spore-crossover-kit-0.1.1-source.tar.gz)** · [Release and SHA256SUMS](https://github.com/vkupyansky/spore-crossover-kit/releases/tag/v0.1.1)

## Features

| Component | Purpose |
| --- | --- |
| [Launcher](launch-spore.command) | Repairs the creations path, checks that Steam is running and signed in, and passes an explicit game data directory. |
| [Graphics fragment](config/graphics.properties) | Records maximum quality, windowed mode and the separate frame-limit changes. |
| [Package checker](tools/check_packages.py) | Reports identical and different resources shared by DBPF mod packages. |
| [SporeKit patch](patches/sporekit-watchdog/README.md) | Preserves a diagnostic module-name reader fix with its Windows tests. Optional developer material. |

## Setup and launch

Requires macOS, CrossOver, and separately installed Steam copies of **both Spore and Galactic Adventures** in one Windows bottle. The recorded environment was CrossOver 26.3 on Apple silicon with Steam GA 3.1.0.29. Game files, CrossOver, mods and account data are not included.

1. Extract the source archive. Install both games in the bottle's default Steam library, under `C:\Program Files (x86)\Steam\steamapps\common\spore`.
2. Open Steam in that bottle, sign in and wait for its library.
3. Open a terminal in this directory and run:

```sh
./launch-spore.command
```

The bottle name defaults to `Spore`. Use `--bottle NAME` for another name. CrossOver defaults to `/Applications/CrossOver.app`; `--crossover /path/to/CrossOver.app` selects another application location. Bottles must use CrossOver's default location under `~/Library/Application Support/CrossOver/Bottles` and the default Documents mapping.

To repair the creations path without launching Spore:

```sh
./launch-spore.command --prepare-only
```

This sets the 32-bit Spore registry value `PlayerDir` to `My Spore Creations` and creates that folder in Documents. It preserves the game language. The normal launch checks the live Steam process inside the selected bottle and passes `SteamAppId=24720`, `-dataDir:...\Data`, `-w` and `-r:1920x1080`. It does not start Steam or enable verbose Wine logging.

## Graphics and optional mods

With the game closed, follow the [graphics recipe](docs/graphics.md). It merges ten preference keys and changes the frame interval to 16 ms in both game configuration directories, giving a theoretical cap of 62.5 FPS.

The [recorded mod selection](docs/mods.md) and [pinned URLs and SHA-256 values](metadata/mods.json) are optional reference material. They are not automatically installed.

## Package checks

Requires Python 3.10 or later, with no additional packages:

```sh
python3 tools/check_packages.py /path/to/DataEP1
```

Pass package files or directories; directories are read one level deep. Exit codes: `0` means no different overlaps, `1` means different stored resources overlap, and `2` means invalid input or an unsupported format. Spore DBPF 3.0 with index 0.3 is supported. RefPack data is compared as stored, without decompression. Intentional overlaps are common; this is not a mod compatibility verdict.

## Checks

On macOS with Python 3.10+ and the command line `make` tool:

```sh
make check
```

This checks zsh syntax and runs isolated launcher and package-reader tests. The launcher tests use a fake CrossOver and never start a game. The archived patch has a [separate Windows test procedure](patches/sporekit-watchdog/README.md#test).

## Limitations

- The final explicit-data-directory change passed argument and failure-path tests, but a subsequent real game start was not verified. Error 1004 and later mod initialization failures must not be considered universally fixed.
- The launcher bypasses the Steam Play button because the Russian install script can restore an invalid creations folder name. Signed Steam install scripts are not patched. A related report is documented [upstream](https://github.com/WoodyWizard/SporeCoop/issues/190).
- Full HD is a requested window size. SporeBorderless can resize it to the monitor, and Retina rendering resolution was not measured. FPS was not measured either.
- An earlier 1600 x 1000 windowed session resumed after minimizing; exclusive fullscreen hung. The later Full HD and Borderless combination was not fully verified.
- Static checks and unit tests do not establish stability of the whole mod selection. The watchdog patch is retained separately and is not needed by the standalone launcher.

## License

The independent launcher, package checker, configuration fragment and documentation use [MIT](LICENSE). The SporeKit patch preserves its [upstream MIT notice](patches/sporekit-watchdog/LICENSE). External software and distribution boundaries are listed in [THIRD_PARTY.md](THIRD_PARTY.md).
