#!/usr/bin/env python3
"""Build The Legend of Zelda: Echoes of Wisdom (1.1.0) into a native Mac app/runner."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

EOW = Path(__file__).resolve().parents[1]
REPO = EOW.parent.parent

APP_NAME = 'Echoes of Wisdom'
MODULES = ('sdk', 'subsdk0', 'subsdk1', 'main')
VERSION = 'v110'

def say(message):
    print(f'[{time.strftime("%H:%M:%S")}] {message}', flush=True)

def elapsed(seconds):
    m, s = divmod(int(seconds), 60)
    return f'{m}m {s:02d}s' if m else f'{s}s'

def run(cmd, cwd=EOW, env=None, check=True):
    res = subprocess.run(cmd, cwd=cwd, env=env)
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed (exit {res.returncode}): {' '.join(str(c) for c in cmd)}")
    return res

def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            digest.update(block)
    return digest.hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game', type=Path, required=True, help='Base game (.xci or .nsp)')
    p.add_argument('--update', type=Path, required=True, help='Update 1.1.0 .nsp')
    p.add_argument('-k', '--keys', type=Path, required=True, help='Path to prod.keys')
    p.add_argument('--work', type=Path, default=Path('/Volumes/lyr-data/carlosarauz/GameBuilds/EoW_build'))
    p.add_argument('--shared-fonts', type=Path, default=Path('/Volumes/lyr-data/carlosarauz/GameBuilds/TOTK_build/totk/extracted/firmware/shared-fonts'))
    p.add_argument('--out', type=Path, default=Path('/Applications'))
    args = p.parse_args()

    game = args.game.expanduser().resolve()
    update = args.update.expanduser().resolve()
    keys = args.keys.expanduser().resolve()
    work = args.work.expanduser().resolve()
    shared_fonts = args.shared_fonts.expanduser().resolve()
    out = args.out.expanduser().resolve()

    for f in (game, update, keys):
        if not f.is_file():
            sys.exit(f"Error: File not found: {f}")

    work.mkdir(parents=True, exist_ok=True)
    logs = work / 'logs'
    logs.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    say(f"Starting build for {APP_NAME} in {work}")

    # 1. Python Environment
    venv = work / 'venv'
    py = venv / 'bin/python'
    if not py.exists():
        say("1/6 python: creating virtual environment in work directory")
        run([sys.executable, '-m', 'venv', str(venv)])
        run([str(venv / 'bin/pip'), 'install', '--quiet', '-r', str(EOW / 'requirements.txt'), 'unicorn'])
    else:
        say("1/6 python: using existing virtual environment in work directory")

    # 2. Extract code from update
    exefs_dir = work / f'extracted/{VERSION}/exefs'
    expected = json.loads((EOW / 'assets/expected-v1.1.0.json').read_text())
    code_valid = False
    if (exefs_dir / 'main').exists():
        current_hashes = {m: sha256(exefs_dir / m) for m in MODULES if (exefs_dir / m).exists()}
        code_valid = all(current_hashes.get(m) == expected['exefs_sha256'][m] for m in MODULES)

    if code_valid:
        say("2/6 code: verified 1.1.0 ExeFS already extracted")
    else:
        say("2/6 code: extracting ExeFS from 1.1.0 update")
        shutil.rmtree(exefs_dir, ignore_errors=True)
        exefs_dir.parent.mkdir(parents=True, exist_ok=True)
        run([str(py), str(EOW / 'scripts/extract_code.py'), str(update), '--keys', str(keys), '--output', str(exefs_dir)])

    # 3. Merge RomFS
    romfs_dir = work / f'extracted/{VERSION}/romfs'
    romfs_valid = False
    if (romfs_dir / 'romfs.bin').exists() and (romfs_dir / 'index.json').exists():
        say("3/6 data: verified merged RomFS already exists")
        romfs_valid = True

    if not romfs_valid:
        say("3/6 data: merging base + 1.1.0 RomFS (this may take a few minutes)")
        shutil.rmtree(romfs_dir, ignore_errors=True)
        romfs_dir.parent.mkdir(parents=True, exist_ok=True)
        run([str(py), str(EOW / 'scripts/merge_romfs.py'), str(game), str(update), '--keys', str(keys), '--output', str(romfs_dir)])

    # 4. Shared fonts
    fonts_dir = work / 'extracted/firmware/shared-fonts'
    if not (fonts_dir / 'manifest.json').exists():
        say(f"4/6 fonts: copying shared fonts from {shared_fonts}")
        fonts_dir.mkdir(parents=True, exist_ok=True)
        for font_file in shared_fonts.glob('*'):
            shutil.copy2(font_file, fonts_dir / font_file.name)
    else:
        say("4/6 fonts: shared fonts already present")

    # 5. Rewrite ARM64 modules
    rewritten_dir = work / f'rewritten/{VERSION}'
    rewritten_dir.mkdir(parents=True, exist_ok=True)
    say("5/6 rewrite: rewriting ARM64 modules for Apple Silicon")
    for m in MODULES:
        patched_bin = rewritten_dir / f'{m}.patched.bin'
        if not patched_bin.exists() or sha256(patched_bin) != expected['rewritten_sha256'].get(f'{m}.patched.bin'):
            say(f"   rewriting {m}...")
            env = dict(os.environ, DM_RULESET='native', DM_PRIVATE_GATES='0')
            run([str(py), str(EOW / 'third_party/d2r/patch_nso.py'), str(exefs_dir / m), str(rewritten_dir), m], env=env)

    # 6. Build runtime and shader tools via make
    say("6/6 runtime: building native runtime and shader tools")
    make_env = dict(os.environ, WORK=str(work), PY=str(py))
    run(['make', '-C', str(EOW), 'prepare', 'runtime', 'shader-tools', f'WORK={work}', f'PY={py}'])

    # Assemble wrapper .app bundle in out directory
    app_target = out / f'{APP_NAME}.app' if out.suffix != '.app' else out
    macos_dir = app_target / 'Contents/MacOS'
    resources_dir = app_target / 'Contents/Resources'
    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    launcher_script = macos_dir / 'EchoesOfWisdom'
    launcher_script.write_text(f"""#!/bin/bash
cd "{work}" || exit 1
export TOTK_GPU_ALLOW_SUBMIT=1
export TOTK_GPU_BLOCKRT=1
export TOTK_GPU_MIDCLEAR=1
export TOTK_GPU_WIDEN=1
export TOTK_GPU_BUDGET_MB=5000
export DM_PRESENT_LINK_FALLBACK=1
exec ./build/eow-native rewritten/{VERSION} boot
""")
    launcher_script.chmod(0o755)

    info_plist = app_target / 'Contents/Info.plist'
    info_plist.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>EchoesOfWisdom</string>
    <key>CFBundleIdentifier</key>
    <string>org.macnativegames.eow</string>
    <key>CFBundleName</key>
    <string>{APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>{APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.1.0</string>
    <key>CFBundleVersion</key>
    <string>1.1.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>26.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
""")

    say(f"done in {elapsed(time.time() - t0)}: {app_target} (1.1.0)")
    say(f"To run: open \"{app_target}\" or cd \"{work}\" && ./build/eow-native rewritten/{VERSION} boot")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
