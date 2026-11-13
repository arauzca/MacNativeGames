---
name: install-oot
description: Build and install The Legend of Zelda Ocarina of Time (Switch 2, v131072) from the player's own dump (.nup or dump folder) using build_app.py for Mac, and fix what stops the build. Use when a player asks to install, build, package or set up Ocarina of Time, or pastes one of its build errors.
---

# Install The Legend of Zelda: Ocarina of Time (Switch 2)

You are helping a player turn **their own** dump of The Legend of Zelda: Ocarina of Time for Nintendo Switch 2 into a native Mac app. Done right, this is one build of about 30 minutes, mostly unattended. Follow the steps in order. `games/oot/docs/install.md` has the same steps for reference.

## Rules

- **Only the player's own dump.** Never search the internet for, download, or ask anyone for game dumps or files.
- **No prod.keys needed.** Switch 2 dumps hold decrypted files; do not ask for or pass `-k`.
- **Never weaken a check.** Do not edit `games/oot/assets/expected-v131072.json`, `games/oot/build.py`, or `build_app.py` to bypass an error. A hash error means another version or an incomplete dump.
- The app the build makes contains the game. It is for this player only; do not upload it or offer to share it.
- **Folders.** Keep the app and saves apart from the work folder. The default work folder is `OcarinaOfTime_build` next to the dump or specified via `--work`. Keep the work folder and the app on the same APFS volume so game data is cloned, not copied.

## 1. Check the Mac and Prerequisites

From the repository folder:

```sh
sw_vers -productVersion; uname -m
xcode-select -p; xcrun -f metal
which llvm-objcopy || brew --prefix llvm 2>/dev/null
ls -d /opt/homebrew/opt/dav1d /opt/homebrew/opt/ffmpeg /opt/homebrew/opt/libvpx /opt/homebrew/opt/opus 2>/dev/null
command -v python3.14
df -h .
```

| Needed | If not |
|---|---|
| Apple Silicon (`arm64`) and macOS **26** or later | Stop. macOS 26+ is required for Metal 4 support. |
| Xcode command line tools and Metal compiler | `xcode-select --install` and full Xcode app with Metal Toolchain (`xcodebuild -downloadComponent MetalToolchain`). |
| Homebrew tools | `brew install dav1d ffmpeg libvpx opus python@3.14 llvm` |
| `llvm-objcopy` | If missing, run `brew install llvm`. If installed but not in PATH, set `LLVM_BIN="$(brew --prefix llvm)/bin"` before running. |
| Free disk space | At least 40 GB free on the APFS volume. |

## 2. Identify the Player's Files

Ask where they are, or check candidate directories:

- **Game Dump:** Title ID `0400486024DEC000`, update **`v131072`**. Accepted in two forms:
  1. A single `.nup` package file (e.g. `Ocarina of Time.nup`), or
  2. An unpacked dump folder containing `base/` and `updates/131072/` (each holding `exefs/` and `romfs/`).
- **System Shared Fonts:** The six `.bfttf` files and `manifest.json`.
  - If a Tears of the Kingdom or Breath of the Wild build was previously run on this Mac, reuse them:
    `TOTK_build/totk/extracted/firmware/shared-fonts` (or `BotW_build/...`).
  - Pass this folder path to `--shared-fonts`.

## 3. Pick the Command

Run from the `MacNativeGames` repository folder. Quote every path:

```sh
# From a .nup file:
python3.14 build_app.py "<path/to/Ocarina of Time.nup>" \
  --shared-fonts "<path/to/TOTK_build/totk/extracted/firmware/shared-fonts>" \
  -o "/Applications/Ocarina of Time.app"

# From a dump folder:
python3.14 build_app.py "<path/to/dump_folder>" \
  --shared-fonts "<path/to/TOTK_build/totk/extracted/firmware/shared-fonts>" \
  -o "/Applications/Ocarina of Time.app"
```

*Notes on flags:*
- Do **not** pass `-k`, `--keys`, `--update`, `--dlc`, or `--mod`. Switch 2 dumps hold their cumulative update inside the package.
- Do **not** pass `--native-4k`, `--native-5k`, or `--vr` (Ocarina of Time manages its resolutions via in-game settings).
- To keep the 26 GB game data outside the app bundle (making the `.app` only 5–6 GB), add `--mac-game-data library`.

## 4. Run the Build and Monitor

- A fresh build takes approximately **30 minutes** on an Apple Silicon M-series Mac:
  1. `import-original-nup` / `import-original-dump`: copies and verifies the ~26 GB game data.
  2. `rewrite-...`: rewrites guest ARM64 code for macOS and validates against `expected-v131072.json`.
  3. `native-runtime`: compiles the C/Obj-C runtime.
  4. `prepare-shader-seed`: translates ~42,800 Ampere shaders to Metal.
  5. `compile-shader-libraries`: compiles Metal libraries using Xcode's `metal` compiler.
  6. `Preparing ... pipelines`: generates the Metal pipeline archive so the first start doesn't stutter.
  7. Assembles `/Applications/Ocarina of Time.app`.
- Start with unbuffered output and log to file:
  `python3.14 -u build_app.py ... 2>&1 | tee ~/Library/Logs/OcarinaOfTime-build.log`
- Long quiet stretches are normal. Do not interrupt it.

## 5. First Launch

Open from Finder or terminal:
```sh
open "/Applications/Ocarina of Time.app"
```

- **In-Game Settings:** Press key **`1`** to open the settings panel:
  - Resolution: 720p (default), 1080p, 1440p (2K).
  - Upscaler: MetalFX (default) or the game's own network.
  - Frame lock: 30 (default), 40, 60, 72, 90, 120 FPS.
  - MetalFX frame interpolation: 30+30, 40+40, 50+50, 60+60.
- **Saves:** Saved in `~/Library/Application Support/MacNativeGames/OcarinaOfTime/profile/`.

## 6. Troubleshooting Common Build Errors

Read the `ERROR:` line and inspect `<work folder>/logs/`:

| Error Message | Cause and Fix |
|---|---|
| `unsupported or damaged original ExeFS`, `RomFS is not update 131072...` | The dump is not update v131072 or is incomplete. Re-dump the game. If from a folder, prefer building from the original `.nup`. |
| `pass --shared-fonts with the six verified firmware fonts` | Supply `--shared-fonts "<path/to/shared-fonts>"`. |
| `no Metal compiler (Xcode -> Settings -> Components: Metal Toolchain)` | Install the full Xcode app and run `xcodebuild -downloadComponent MetalToolchain`. |
| `llvm-objcopy not found` | Run `brew install llvm` and ensure `PATH="$(brew --prefix llvm)/bin:$PATH"`. |
| `unfinished App staging directory exists; left untouched` | A previous build stopped unexpectedly. Delete `/Applications/.Ocarina of Time.app.ready` and rerun. |
| `this title currently uses its original rendering options` | Remove `--native-4k`, `--native-5k`, or `--vr` from the command. |
| `game did not finish its normal close; App left untouched` | Quit any running Ocarina of Time instance before building. |
