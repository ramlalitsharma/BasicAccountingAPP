# -*- mode: python ; coding: utf-8 -*-

import os, sys

block_cipher = None

datas = [('config.py', '.'), ('database', 'database'), ('ui', 'ui'), ('utils', 'utils'), ('icon', 'icon')]

binaries = []
hiddenimports = [
    'openpyxl', 'openpyxl.cell._writer', 'openpyxl.styles',
    'openpyxl.writer.excel', 'openpyxl.reader.excel',
    'matplotlib', 'matplotlib.backends.backend_tkagg',
    'matplotlib.figure', 'matplotlib.backends.backend_agg',
    'matplotlib.backends.backend_pdf',
    'kiwisolver', 'numpy', 'PIL', 'PIL.ImageTk',
    'hashlib', 'hmac', 'base64',
]

excludes = [
    'torch', 'torchvision', 'torchaudio',
    'scipy', 'tensorflow', 'keras', 'sklearn',
    'lxml', 'pytest', 'pip',
    'IPython', 'jedi', 'parso', 'nbformat', 'jsonschema',
    'zmq', 'pygments', 'wcwidth', 'prompt_toolkit',
    'numba', 'llvmlite', 'fsspec', 'lz4',
    'cryptography', 'urllib3',
    'babel', 'sphinx', 'docutils',
    'tests',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
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
    name='AccountingPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon\\accounting_pro.ico'],
)