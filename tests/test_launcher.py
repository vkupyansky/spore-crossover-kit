"""Exercise launcher boundaries with a fake CrossOver, never the installed game."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
FAKE_WINE = r'''
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
with Path(os.environ["MOCK_CALLS"]).open("a") as stream:
    stream.write(json.dumps(args) + "\n")
if "reg.exe" in args:
    if os.environ.get("MOCK_REG_FAIL") == "1":
        sys.exit(1)
    value = args[args.index("/v") + 1]
    if "add" in args:
        sys.exit(0)
    if value == "PlayerDir":
        value = os.environ.get("MOCK_PLAYER_DIR", "My Spore Creations")
        print("    PlayerDir    REG_SZ    " + value + "\r")
    elif value == "pid":
        print("    pid    REG_DWORD    " + os.environ.get("MOCK_PID", "0x2a") + "\r")
    elif value == "ActiveUser":
        print("    ActiveUser    REG_DWORD    " + os.environ.get("MOCK_USER", "0x1") + "\r")
elif "tasklist.exe" in args:
    if os.environ.get("MOCK_STEAM_LIVE", "1") == "1":
        print('"steam.exe","' + os.environ.get("MOCK_LIVE_PID", "42") + '","Console","1","0 K"\r')
'''


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.app = self.base / "Fake CrossOver.app"
        self.bottle = "Lab bottle"
        self.game = (
            self.home / "Library/Application Support/CrossOver/Bottles" / self.bottle
            / "drive_c/Program Files (x86)/Steam/steamapps/common/spore"
        )
        for relative in ("SporebinEP1/SporeApp.exe", "Data/Spore_Game.package"):
            path = self.game / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        wine = self.app / "Contents/SharedSupport/CrossOver/bin/wine"
        wine.parent.mkdir(parents=True)
        wine.write_text(f"#!{sys.executable}\n" + FAKE_WINE)
        wine.chmod(0o755)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        pgrep = self.bin / "pgrep"
        pgrep.write_text('#!/bin/sh\nexit "${MOCK_PGREP_STATUS:-1}"\n')
        pgrep.chmod(0o755)
        self.calls_path = self.base / "calls.jsonl"
        self.env = dict(os.environ, HOME=str(self.home), MOCK_CALLS=str(self.calls_path))
        self.env["PATH"] = str(self.bin) + os.pathsep + os.environ["PATH"]

    def run_launcher(self, *extra, **env):
        return subprocess.run(
            ["zsh", str(ROOT / "launch-spore.command"), "--bottle", self.bottle,
             "--crossover", str(self.app), *extra],
            env=dict(self.env, **env), capture_output=True, text=True, check=False,
        )

    def calls(self):
        if not self.calls_path.exists():
            return []
        return [json.loads(line) for line in self.calls_path.read_text().splitlines()]

    def test_prepare_only_does_not_query_steam_or_launch(self):
        result = self.run_launcher("--prepare-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls()), 2)
        self.assertTrue(all("reg.exe" in call and "PlayerDir" in call for call in self.calls()))
        self.assertTrue((self.home / "Documents/My Spore Creations").is_dir())

    def test_help_lists_options_without_starting_crossover(self):
        result = self.run_launcher("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--prepare-only", result.stdout)
        self.assertIn("Default bottle: Spore.", result.stdout)
        self.assertEqual(self.calls(), [])

    def test_default_bottle_is_spore(self):
        bottles = self.home / "Library/Application Support/CrossOver/Bottles"
        (bottles / self.bottle).rename(bottles / "Spore")
        result = subprocess.run(
            ["zsh", str(ROOT / "launch-spore.command"), "--crossover", str(self.app), "--prepare-only"],
            env=self.env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(all(call[call.index("--bottle") + 1] == "Spore" for call in self.calls()))

    def test_launch_quotes_paths_and_passes_explicit_data_directory(self):
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        call = self.calls()[-1]
        self.assertIn(str(self.game / "SporebinEP1/SporeApp.exe"), call)
        self.assertEqual(call.count("-dataDir:C:\\Program Files (x86)\\Steam\\steamapps\\common\\spore\\Data"), 1)
        self.assertEqual(call[call.index("--workdir") + 1], "C:\\Program Files (x86)\\Steam\\steamapps\\common\\spore\\SporebinEP1")
        self.assertIn("SteamAppId=24720", call)
        self.assertEqual(call[-2:], ["-w", "-r:1920x1080"])
        self.assertNotIn("--cx-log", call)
        self.assertNotIn("-applaunch", call)
        self.assertTrue(all(call[call.index("--bottle") + 1] == self.bottle for call in self.calls()))

    def test_stale_missing_or_unsigned_in_steam_never_launches(self):
        cases = [
            {"MOCK_STEAM_LIVE": "0"}, {"MOCK_LIVE_PID": "43"},
            {"MOCK_PID": "0x0"}, {"MOCK_USER": "0x0"}, {"MOCK_PID": "bad"},
        ]
        for values in cases:
            with self.subTest(values=values):
                self.calls_path.unlink(missing_ok=True)
                result = self.run_launcher(**values)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(any(any(arg.endswith("SporeApp.exe") for arg in call) for call in self.calls()))

    def test_registry_failure_or_failed_readback_stops_launch(self):
        for values in ({"MOCK_REG_FAIL": "1"}, {"MOCK_PLAYER_DIR": "??? ????????"}):
            with self.subTest(values=values):
                self.calls_path.unlink(missing_ok=True)
                result = self.run_launcher(**values)
                self.assertEqual(result.returncode, 1)
                self.assertFalse(any("tasklist.exe" in call for call in self.calls()))

    def test_running_game_is_not_launched_again(self):
        result = self.run_launcher(MOCK_PGREP_STATUS="0")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_missing_installation_does_not_create_a_bottle(self):
        (self.game / "SporebinEP1/SporeApp.exe").unlink()
        result = self.run_launcher()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.calls(), [])

    def test_invalid_arguments_cannot_escape_the_bottle_directory(self):
        for arguments in (("--bottle", "../other"), ("--bottle", ".."), ("--bottle", ""),
                          ("--crossover",), ("--unknown",)):
            with self.subTest(arguments=arguments):
                result = self.run_launcher(*arguments)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(self.calls(), [])


if __name__ == "__main__":
    unittest.main()
