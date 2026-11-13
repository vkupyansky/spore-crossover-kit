# SporeKit watchdog export-name patch

A source patch for [SporeCoop v0.7.10.1](https://github.com/WoodyWizard/SporeCoop/tree/87f8314d02c4d92e85def41484d70602e0123179)
(commit `87f8314d02c4d92e85def41484d70602e0123179`).
It makes the watchdog's diagnostic module-name lookup handle both PE32 and PE64
images, unreadable memory and invalid export-name ranges without dereferencing an
unbounded string.

This patch is retained for development and reproduction. SporeKit was removed
from the final standalone Spore setup, so this patch is not part of that setup
and does not need to be installed to use its launcher. It does not repair the
game's fullscreen graphics recovery after minimizing.

## Apply

Start with the upstream source archive for tag `v0.7.10.1`, then run from its root:

```sh
patch --dry-run -p1 < /path/to/fix-export-name.patch
patch -p1 < /path/to/fix-export-name.patch
```

The patch changes `sporekit/watchdog.cpp` and the test target in `Makefile`, and
adds `sporekit/module_name.h` and `tests/module_name_tests.cpp`. It leaves the
upstream version unchanged. No game files or compiled DLLs are included.

## Test

Use llvm-mingw and Wine to build and execute the Windows test. On CrossOver,
choose an existing test bottle rather than a bottle that runs a game:

```sh
make test-module-name \
  LLVM_MINGW=/path/to/llvm-mingw \
  WINE='/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin/wine --bottle TestBottle --debugmsg -all'
```

The test covers valid PE32 and PE64 names, invalid and truncated export data,
unterminated strings, inaccessible memory and an unmapped image. It also runs
the former PE32-only reader in a child process against a PE64 guard-page
fixture. The expected access violation exits that child with code 87. A passing
run ends with `0 failures`; it never starts Spore.

The patch was reapplied to clean `v0.7.10.1` source files and its Windows test was
rebuilt with `-Wextra -Werror` using llvm-mingw `20261104`, then run in CrossOver
26.3: 11 passing cases, `0 failures`. Test results establish the reader's
behavior on those fixtures, not full
SporeCoop compatibility or a general fix for minimize/restore problems.

## License

The upstream code and this patch are distributed under the MIT license. The
original WoodyWizard notice is preserved in [LICENSE](LICENSE).
