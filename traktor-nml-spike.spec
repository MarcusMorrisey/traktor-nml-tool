# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['spike/packaging/spike_app.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/codex/traktor-nml-tool/.venv/Lib/site-packages/nicegui', 'nicegui'), ('C:/Users/marcu/AppData/Local/Microsoft/WinGet/Packages/AcoustID.Chromaprint_Microsoft.Winget.Source_8wekyb3d8bbwe/chromaprint-fpcalc-1.6.1-windows-x86_64/fpcalc.exe', '.'), ('C:/codex/traktor-nml-tool/traktor_nml/gui/fonts', 'traktor_nml/gui/fonts')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='traktor-nml-spike',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='traktor-nml-spike',
)
