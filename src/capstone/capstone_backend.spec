# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / 'run_server.py'), str(ROOT / 'system' / 'monitor_manager.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / 'tools' / 'system_metrics' / 'LibreHardwareMonitor'), 'capstone/tools/system_metrics/LibreHardwareMonitor')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='capstone_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
