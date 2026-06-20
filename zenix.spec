# -*- mode: python ; coding: utf-8 -*-
"""
ZENIX Bot - PyInstaller Build Spec
Build command: pyinstaller zenix.spec
Output: zenix.exe (single file)
"""

import os
import sys
from pathlib import Path

# Get imageio_ffmpeg binary path
try:
    import imageio_ffmpeg
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_bin)
    ffmpeg_name = os.path.basename(ffmpeg_bin)
    ffmpeg_datas = [(ffmpeg_bin, 'imageio_ffmpeg/binaries')]
except ImportError:
    ffmpeg_datas = []

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('bot', 'bot'),
        ('scripts', 'scripts'),
        ('data/.gitkeep', 'data'),
    ] + ffmpeg_datas,
    hiddenimports=[
        'ws3_fca',
        'aiohttp',
        'PIL',
        'aiosqlite',
        'deep_translator',
        'gtts',
        'requests',
        'yt_dlp',
        'imageio_ffmpeg',
        'asyncio',
        'json',
        'pathlib',
        'importlib',
        'importlib.util',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='zenix',
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
