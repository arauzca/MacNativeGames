---
name: build-game
description: Universal builder for compiling and verifying any supported game in MacNativeGames (Switch 1, Switch 2, and Windows games) into a native Mac app. Verifies feasibility, checks title IDs and versions, and routes to the correct builder with customizable work and output directories.
---

# Universal Game Builder (`build-game`)

This skill inspects, verifies, and compiles **any supported game** in the `MacNativeGames` repository into a native macOS application. It verifies feasibility before building, determines the appropriate build pipeline, enforces repository guardrails, and manages background compilation.

---

## 1. Input Parameters

When invoking this skill, collect or identify these parameters:

| Parameter | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| **Game File** | `--game` | Path to the base game dump (`.xci`, `.nsp`, `.nup`, or dump folder). Required. | *(None)* |
| **Update File** | `--update` | Path to the cumulative update (`.nsp` / `.nsz`), if required by the game. | *(Optional / game-specific)* |
| **Keys** | `-k` / `--keys` | Path to `prod.keys`. Required for Switch 1 games; **not** required for Switch 2 dumps. | `/Users/carlosarauz/Downloads/docs/ProdKeys.NET-v22.5.0/prod.keys` |
| **Work Directory** | `--work` | Location for intermediate extraction, code rewriting, and build caches. | `/Volumes/lyr-data/carlosarauz/GameBuilds/<game_id>_build` |
| **Output App** | `--out` | Final destination of the generated `.app` bundle. | `/Applications/<Game Name>.app` |

---

## 2. Core Guardrails

1. **Only the player's own files:** Never search the web for, download, or solicit game dumps, keys, or firmware.
2. **Never expose or print keys:** Pass `-k "<path>"` directly; do not `cat`, print, or echo key contents.
3. **Never weaken hash or integrity checks:** Never edit `expected-*.json`, `game_version.h`, or build scripts to bypass an error. If a hash mismatches, halt and explain that the version or dump is unsupported or corrupted.
4. **Volume consistency:** Keep `--work` on an APFS volume (such as `/Volumes/lyr-data/` or internal storage) so large 17–26 GB game data uses instantaneous APFS copy-on-write cloning instead of duplicating storage.
5. **Metal Toolchain Prerequisite:** Offline shader compilation (`compile-shader-libraries`) requires the offline Xcode Metal toolchain component. If missing (`[RED] no Metal compiler`), install it via:
   ```bash
   xcodebuild -downloadComponent MetalToolchain
   ```

---

## 3. Step 1: Pre-Flight Feasibility & Routing Matrix

Before launching any build command, inspect the input file to identify its **Title ID**, **Type** (Base vs. Update), and **Version**:

```sh
# Inspect file existence and size:
ls -lh "<game_path>"
```

### Title ID Role Detection:
* Ends in **`...000`**: **Base Game** (required to build).
* Ends in **`...800`**: **Cumulative Update** (an update alone cannot be compiled without the matching base game).

Match the input against the supported game engines and builders:

### Tier 1: Mainline Games (`build_app.py`)
These are fully integrated and package directly into `/Applications/<Name>.app`:

| Game | Title ID | Supported Base | Supported Updates | Keys Needed? | Special Flags |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Zelda: Tears of the Kingdom** | `0100F2C0115B6000` | 1.0.0 (XCI / NSP) | 1.2.1, 1.4.3 (preferred) | Yes (`-k`) | `--update` |
| **Zelda: Breath of the Wild** | `01007EF00011E000` | 1.6.0 card or base NSP | 1.6.0, 1.9.0 | Yes (`-k`) | `--shared-fonts <fonts>`, `--dlc` |
| **Zelda: Ocarina of Time (Switch 2)** | `0400486024DEC000` | Update 131072 (`.nup` or dump folder) | Bundled in package | **No** | `--shared-fonts <fonts>` |
| **Pokémon Pokopia (Switch 2)** | `0400A3A01EE4C000` | Update 655360 / 2.0.1 (dump folder) | Bundled in package | **No** | `--shared-fonts <fonts>` |
| **Donkey Kong Bananza (Switch 2)** | `040074A01BF12000` | Update 458752 (dump folder) | Bundled in package | **No** | `--shared-fonts <fonts>` |

*Shared Fonts Source on this Mac:*
`/Volumes/lyr-data/carlosarauz/GameBuilds/TOTK_build/totk/extracted/firmware/shared-fonts`

### Tier 2: Community Ports with Standalone App Builders
* **Zelda: Echoes of Wisdom (`games/eow`)**:
  * Base: `01008CF01BAAC000` (1.0.0 / v0, XCI or NSP)
  * Update: `01008CF01BAAC800` (1.1.0 / v196608 NSP required)
  * Keys: Required (`-k`)
  * Builder: `python3.14 games/eow/scripts/build_eow.py --game <base> --update <update> -k <keys> --work <work> --out <out>`
* **Octopath Traveler 0 (`games/ot0`)**:
  * Base: `01005270232F2000` (XCI)
  * Updates: Must be **1.0.3** (v196608), **1.0.4** (v262144), or **1.0.5** (v327680)
  * Keys: Required (`-k`)
  * Builder: `python3.14 games/ot0/scripts/build_ot0.py --game <base> --update <update> -k <keys> --work <work> --out <out>`

### Tier 3: Statically Recompiled Windows Games
* **Red Alert 2 & Yuri's Revenge (`windows_games/ra2`)**:
  * Input: Steam PC installation folder holding `GAME.EXE` / `gamemd.exe`.
  * Keys: None.
  * Builder: `cd windows_games/ra2 && scripts/build.sh <install_folder>`

### Tier 4: Community Diagnostic Ports (`games/<name>`)
For other ports like *Luigi's Mansion 3* (`games/lm3`), *Xenoblade 3* (`games/xc3`), *Super Mario Wonder* (`games/wonder`), etc., consult their respective `games/<name>/README.md`.

---

## 4. Step 2: Formulating the Build Command

Once the game is verified, assemble the exact command applying the default directory structure:

### Example A: Tears of the Kingdom
```bash
python3.14 -u build_app.py "<base.xci>" \
  -k "<prod.keys>" \
  --update "<update.nsp>" \
  --work "/Volumes/lyr-data/carlosarauz/GameBuilds/TOTK_build" \
  -o "/Applications/Tears of the Kingdom.app" 2>&1 | tee ~/Library/Logs/MacNativeGames-build.log
```

### Example B: Ocarina of Time (Switch 2)
```bash
python3.14 -u build_app.py "<oot.nup>" \
  --shared-fonts "/Volumes/lyr-data/carlosarauz/GameBuilds/TOTK_build/totk/extracted/firmware/shared-fonts" \
  --work "/Volumes/lyr-data/carlosarauz/GameBuilds/OcarinaOfTime_build" \
  -o "/Applications/Ocarina of Time.app" 2>&1 | tee ~/Library/Logs/OcarinaOfTime-build.log
```

### Example C: Octopath Traveler 0
```bash
python3.14 -u games/ot0/scripts/build_ot0.py \
  --game "<base.xci>" \
  --update "<update.nsp>" \
  -k "<prod.keys>" \
  --work "/Volumes/lyr-data/carlosarauz/GameBuilds/OT0_build" \
  --out "/Applications" 2>&1 | tee ~/Library/Logs/Octopath0-build.log
```

### Example D: Echoes of Wisdom
```bash
python3.14 -u games/eow/scripts/build_eow.py \
  --game "<base.xci_or_nsp>" \
  --update "<update_1.1.0.nsp>" \
  -k "<prod.keys>" \
  --work "/Volumes/lyr-data/carlosarauz/GameBuilds/EoW_build" \
  --out "/Applications" 2>&1 | tee ~/Library/Logs/EchoesOfWisdom-build.log
```

---

## 5. Step 3: Execution and Monitoring

1. **Launch with Background Tasking:** Full builds take **20 to 40 minutes**. Execute via `run_command` with a wait timeout (e.g., `WaitMsBeforeAsync: 10000`).
2. **Monitor without Interruption:** Check progress periodically if requested, but do not kill or cancel the build during quiet phases (e.g. shader translation or GPU pipeline archive generation).
3. **Verify App Bundle:** Once the task finishes with code 0:
   ```sh
   ls -ld "<output_path>" && plutil -p "<output_path>/Contents/Info.plist" | head -n 20
   ```
4. **Notify the User:** Inform the user of completion, provide launch instructions (`open "<output_path>"`), and explain in-game controls (e.g. Key `1` settings panel).
