# MacNativeGames Workspace Rules

## Legal & Security Guardrails
- **Only the player's own files:** Never search the internet for, download, or ask anyone for game files (`.xci`, `.nsp`, `.nsz`), `prod.keys`, title keys, or firmware.
- **Never expose keys:** Never read, print, `cat`, copy, or paste the contents of `prod.keys` or ticket files. Pass the path to `build_app.py` via `-k "<path>"`.
- **Never commit game content:** Never commit game binaries, ExeFS/RomFS files, art, audio, translated shaders, keys, or `.app`/`.ipa` bundles.
- **Never weaken integrity checks:** Never edit `expected-*.json`, `sha256.txt`, `game_version.h`, `build_app.py`, or Makefiles to bypass a SHA-256 or signature check.

## Architecture & Repository Isolation
- **No CPU emulation:** Game ARM64 code runs natively after ahead-of-time rewriting (`patch_nso.py`). Fix platform bugs in the runtime/NVN-on-Metal layer, not by hiding symptoms in game code.
- **Per-game folder isolation:** `games/totk` is shared by Tears of the Kingdom, Breath of the Wild, Donkey Kong Bananza, and Pokémon Pokopia. Every other port in `games/<name>/` is strictly self-contained and must never reference `../totk` or another game's folder in scripts, Makefiles, or imports.

## Build & Verification Workflows
- Use the `build-game` skill as the universal entry point to inspect, verify, and compile any game in the repository with default paths (`/Volumes/lyr-data/carlosarauz/GameBuilds/<game_id>_build` and `/Applications/<Name>.app`).
- Use dedicated skills `install-zelda`, `install-oot`, or `install-ra2` when working directly on those specific titles.
- Run offline unit and C UBSan tests with `make check` (uses `python3.14 -m unittest discover -s tests`).
