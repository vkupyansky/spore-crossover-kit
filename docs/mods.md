# Recorded mod selection

These are the optional components used in the standalone configuration, not an
automatically installed bundle or a claim of complete compatibility.
[metadata/mods.json](../metadata/mods.json) records the exact downloaded archives.

| Component | Recorded version | Selection |
| --- | --- | --- |
| SporeModLoader | macOS arm64 build `6d7419b`, CoreAPI `2.5.586.10` | Native manager and `dinput8` loader |
| SporeCrashFix | 0.7 | Default |
| Enhanced Color Picker | 1.2 | Default |
| Advanced CE | 3.0.2 | Base and Suppress Snapping; Evo-Outfitter disabled |
| Valla's Editor Camera Fixes | 1.2 | Default Camera |
| SporeBorderless | 1.2 | Windowed game |
| Universal Property Enhancer | 1.2.0 | Dependency; not the 2.0 prerelease |

Use the [official Linux/macOS loader instructions](https://launcherkit.sporecommunity.com/support/linux-mac)
and the native SporeModManager supplied with that loader. In the selected
CrossOver bottle, set the per-application `SporeApp.exe` DLL override for
`dinput8` to native. Do not install a second Launcher Kit alongside it. The
manifest records a rolling-release asset by its build and checksum, not as an
unpinned promise of the latest version.

AutoSave 2.3 and UI Fixer Framework 2.1 were removed during diagnosis. AutoSave
appeared in four initialization crash stacks; UI Fixer was a diagnostic
candidate, not a proven cause. They are excluded from the manifest. There is no
automatic saving in the recorded selection: save manually using Ctrl+S or the
game menu. Sneky Graphics was not installed because the required author's
download was unavailable.

Installed archives matched their recorded SHA-256 values. Static DLL dependency
and resource checks were completed, but full gameplay compatibility on CrossOver
was not established. Camera Fix and Borderless can also fail after the base game
fails to initialize; those secondary dialogs alone do not identify the original
cause. Start with the base game when investigating startup failures.
