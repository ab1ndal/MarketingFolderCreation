# -*- mode: python ; coding: utf-8 -*- 
a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('templates/A250.docx', 'templates')],
    hiddenimports=[
        'win32com.shell',
        'win32com.shell.shell',
        'win32timezone',
    ],
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
    name='ClickFolder_v2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='FolderCreatorTool.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ClickFolder_v2',
)