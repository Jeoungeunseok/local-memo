# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['sticky_calendar.py'],
    pathex=['C:/Users/smhrd/old/anaconda3/Library/bin'],
    binaries=[('C:/Users/smhrd/old/anaconda3/Library/bin/sqlite3.dll', '.'), ('C:/Users/smhrd/old/anaconda3/Library/bin/ffi.dll', '.')],
    datas=[],
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
    a.binaries,
    a.datas,
    [],
    name='StickyCalendar',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['app_icon.ico'],
)
