#!/bin/zsh
set -euo pipefail

bottle='Spore'
crossover='/Applications/CrossOver.app'
prepare_only=0

usage() {
    print -r -- 'Usage: ./launch-spore.command [--bottle NAME] [--crossover PATH] [--prepare-only]'
    print -r -- 'Default bottle: Spore.'
    print -r -- 'Open and sign in to Steam in that bottle before launching the game.'
    print -r -- '--prepare-only repairs the creations path without starting the game.'
}

while (( $# )); do
    case "$1" in
        --bottle|--crossover)
            if (( $# < 2 )) || [[ -z $2 || $2 == --* ]]; then
                print -u2 "Missing value for $1."
                exit 2
            fi
            if [[ $1 == --bottle ]]; then
                bottle=$2
            else
                crossover=$2
            fi
            shift 2
            ;;
        --prepare-only) prepare_only=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) print -u2 "Unknown argument: $1"; usage >&2; exit 2 ;;
    esac
done

if [[ $bottle == */* || $bottle == *\\* || $bottle == '.' || $bottle == '..' ]]; then
    print -u2 'Bottle name must be a single directory name.'
    exit 2
fi

spore_wine="$crossover/Contents/SharedSupport/CrossOver/bin/wine"
spore_bottle="$HOME/Library/Application Support/CrossOver/Bottles/$bottle"
spore_game="$spore_bottle/drive_c/Program Files (x86)/Steam/steamapps/common/spore"
spore_windows_game='C:\Program Files (x86)\Steam\steamapps\common\spore'
spore_steam_key='HKCU\Software\Valve\Steam\ActiveProcess'
spore_registry_key='HKLM\Software\WOW6432Node\Electronic Arts\SPORE'

if [[ ! -x $spore_wine || ! -d $spore_bottle ||
      ! -f "$spore_game/SporebinEP1/SporeApp.exe" ||
      ! -f "$spore_game/Data/Spore_Game.package" ]]; then
    print -u2 'CrossOver, the bottle, or the Steam Spore + Galactic Adventures files are missing.'
    exit 1
fi

if pgrep -u "$(id -u)" -f '(^|[/\\])SporeApp[.]exe([[:space:]]|$)' >/dev/null; then
    print 'Spore is already running.'
    exit 0
fi

# The Russian Steam install script can restore an invalid PlayerDir.
"$spore_wine" --bottle "$bottle" --debugmsg '-all' reg.exe add \
    "$spore_registry_key" /v PlayerDir /t REG_SZ /d 'My Spore Creations' /f >/dev/null
spore_player_dir=$("$spore_wine" --bottle "$bottle" --debugmsg '-all' \
    reg.exe query "$spore_registry_key" /v PlayerDir)
if ! print -r -- "$spore_player_dir" | tr -d '\r' | \
    awk '$1 == "PlayerDir" && $2 == "REG_SZ" { $1=""; $2=""; sub(/^ +/, ""); if ($0 == "My Spore Creations") found=1 } END { exit !found }'; then
    print -u2 'Could not repair the creations path. The game was not started.'
    exit 1
fi
mkdir -p "$HOME/Documents/My Spore Creations"

if (( prepare_only )); then
    print 'Creations path repaired. The game was not started.'
    exit 0
fi

# A registry PID can outlive Steam; confirm the process in this same bottle.
spore_steam_pid=$("$spore_wine" --bottle "$bottle" --debugmsg '-all' reg.exe query \
    "$spore_steam_key" /v pid 2>/dev/null | tr -d '\r' | awk '$1 == "pid" && $2 == "REG_DWORD" { print $3 }') || spore_steam_pid=''
spore_steam_user=$("$spore_wine" --bottle "$bottle" --debugmsg '-all' reg.exe query \
    "$spore_steam_key" /v ActiveUser 2>/dev/null | tr -d '\r' | awk '$1 == "ActiveUser" && $2 == "REG_DWORD" { print $3 }') || spore_steam_user=''
spore_steam_live=''
spore_steam_decimal=''
if [[ $spore_steam_pid =~ '^0x[0-9a-fA-F]+$' && $spore_steam_user =~ '^0x[0-9a-fA-F]+$' ]] && \
    (( spore_steam_pid != 0 && spore_steam_user != 0 )); then
    spore_steam_decimal=$(( spore_steam_pid ))
    spore_steam_live=$("$spore_wine" --bottle "$bottle" --debugmsg '-all' tasklist.exe /FO CSV /NH \
        /FI "PID eq $spore_steam_decimal" /FI 'IMAGENAME eq steam.exe' 2>/dev/null) || spore_steam_live=''
fi
if ! print -r -- "$spore_steam_live" | tr -d '\r' | \
    awk -F '"' -v expected="$spore_steam_decimal" 'tolower($2) == "steam.exe" && $4 == expected { found=1 } END { exit !found }'; then
    print -u2 "Open and sign in to Steam in CrossOver bottle '$bottle', then run this launcher again."
    exit 1
fi

exec "$spore_wine" \
    --bottle "$bottle" --env SteamAppId=24720 \
    --debugmsg '-all' \
    --workdir "$spore_windows_game\\SporebinEP1" \
    "$spore_game/SporebinEP1/SporeApp.exe" \
    "-dataDir:$spore_windows_game\\Data" \
    -w -r:1920x1080
