# Third-party software

The repository contains independent setup material and one source patch. It does
not contain game files, Steam, CrossOver/Wine binaries, mod archives, save files,
creations, account credentials or copies of the referenced projects.

| Component | Source and distribution |
| --- | --- |
| Spore and Galactic Adventures | EA/Maxis games, installed separately through Steam. No game code or assets are redistributed. |
| CrossOver | [CodeWeavers](https://www.codeweavers.com/crossover). Required separately; no runtime is included. |
| SporeKit watchdog patch | Based on [WoodyWizard/SporeCoop v0.7.10.1](https://github.com/WoodyWizard/SporeCoop/tree/87f8314d02c4d92e85def41484d70602e0123179), MIT. The patch includes contextual upstream lines and retains the original [license](patches/sporekit-watchdog/LICENSE). |
| SporeModLoader | [Rosalie241/SporeModLoader](https://github.com/Rosalie241/SporeModLoader), GPL-3.0. Downloaded separately; a pinned archive URL and checksum are recorded. |
| Optional mods | Their authors, exact archive URLs and hashes are recorded in [metadata/mods.json](metadata/mods.json). They retain their respective terms and are not bundled. |

The root MIT license covers the independent project files. It does not grant
rights to the separately installed games or external tools.
