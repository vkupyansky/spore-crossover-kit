# Graphics configuration

This records the settings used with Steam Galactic Adventures 3.1.0.29 and
CrossOver 26.3 on Apple silicon. It is a manual configuration recipe, not a
measured performance result or a guarantee of stable gameplay.

## Quality and window mode

Close Spore before editing `%APPDATA%\Spore\Preferences\Preferences.prop` inside
the CrossOver bottle. Merge the keys from
[`config/graphics.properties`](../config/graphics.properties) into that existing
file: replace each matching value, add absent keys, and keep one entry per key.
Preserve every other preference. Do not replace the whole file or modify
`login.prop`.

The fragment selects the game's maximum quality values, enables high-resolution
textures, and keeps windowed mode for SporeBorderless. `OptionScreenSize` is
deliberately absent because its numeric mode identifier is not a portable
resolution setting.

## Frame limit

Under the installed game directory, apply the following changes in **both**
`Data/Config` and `DataEP1/Config`:

| File | Required line |
| --- | --- |
| `Properties.txt` | `property frameLimitMS 44 int` |
| `ConfigManager.txt` | `intProp frameLimitMS 16` |

Replace an existing `frameLimitMS` declaration/value, or add it if absent. Leave
exactly one relevant line in each file and preserve unrelated settings. A frame
interval of 16 ms gives a theoretical cap of **62.5 FPS**. Actual FPS was not
measured.

## Resolution and minimizing

The launcher requests windowed 1920 x 1080 with `-w -r:1920x1080`.
SporeBorderless fits the window to the active monitor, so this request does not
establish that the actual rendering resolution is Full HD, especially on a
Retina display.

An earlier 1600 x 1000 windowed session resumed after minimizing. Exclusive
fullscreen hung on restore in this setup. The later combination of the Full HD
request and SporeBorderless was not fully verified. Use these settings as a
record of the configuration, with these limitations, rather than a validated
fullscreen preset.
