# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification file for OSD (Operating System Diagnostics).
Supports cross-platform building on Windows, Linux, and macOS.
"""
import sys
import os

block_cipher = None

from PyInstaller.utils.hooks import collect_submodules

# Bundle required web, screenshot, and preview assets
added_files = []
for folder in ['assets', 'app_previews', 'web']:
    if os.path.exists(folder):
        added_files.append((folder, folder))

platform_hidden = ['ctypes.wintypes'] if sys.platform == 'win32' else []

hidden_imports = sorted(list(set([
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'psutil',
    'matplotlib',
    'matplotlib.backends.backend_qtagg',
    'sqlite3',
    'ctypes',
] + platform_hidden + collect_submodules('app') + collect_submodules('osd_core'))))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

version_file = 'file_version_info.txt' if sys.platform == 'win32' and os.path.exists('file_version_info.txt') else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OSD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='OSD',
)
