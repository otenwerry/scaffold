binaries = []
datas = [
        ('logos/icon.png', 'logos'),
        ('logos/gray.png', 'logos'),
        ('logos/blue1.png', 'logos'),
        ('logos/blue2.png', 'logos'),
        ('logos/blue3.png', 'logos'),
        ('styles/base.qss', 'styles'),
    ]

if os.path.exists("/usr/local/bin/tesseract"):
    datas += [("/usr/local/bin/tesseract", "tesseract")]
elif os.path.exists("/opt/homebrew/bin/tesseract"):
    datas += [("/opt/homebrew/bin/tesseract", "tesseract")]

if os.path.isdir("/usr/local/share/tessdata"):
    datas += [("/usr/local/share/tessdata", "tessdata")]
elif os.path.isdir("/opt/homebrew/share/tessdata"):
    datas += [("/opt/homebrew/share/tessdata", "tessdata")]

a = Analysis(
    ['tutor.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'PySide6',
        'sounddevice',
        'numpy',
        'mss',
        'openai',
        'pynput.keyboard',
        'pytesseract',
        'Vision',
        'Cocoa'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name='Tutor4',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False = no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logos/icon2.icns', 
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Tutor4'
)

app = BUNDLE(
    coll,
    name='Tutor4.app',
    icon='logos/icon2.icns',
    bundle_identifier='com.scaffold.tutor4',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'CFBundleIconFile': 'icon2.icns',
        'CFBundleIconName': 'icon',
        "CFBundleVersion": "2",
        'NSMicrophoneUsageDescription': 'Tutor4 needs microphone access to record your questions.',
        'NSScreenCaptureUsageDescription': 'Tutor4 needs screen access to see what you are asking about.',
    },
)