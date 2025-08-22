binaries = []
datas = [
        ('logos/icon.png', 'logos'),
        ('logos/gray.png', 'logos'),
        ('logos/blue1.png', 'logos'),
        ('logos/blue2.png', 'logos'),
        ('logos/blue3.png', 'logos'),
        ('system_prompt.txt', '.'),
    ]

if os.path.exists("/usr/local/bin/tesseract"):
    binaries += [("/usr/local/bin/tesseract", "tesseract")]

if os.path.isdir("/usr/local/share/tessdata"):
    datas += [("/usr/local/share/tessdata", "tessdata")]

a = Analysis(
    ['tray.py'],
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
    a.binaries,
    a.datas,
    [],
    name='Tutor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False = no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    #icon='icon.icns',  # convert PNG to ICNS for macOS
)

app = BUNDLE(
    exe,
    name='Tutor.app',
    #icon='icon.icns',
    bundle_identifier='com.yourcompany.tutor',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'NSMicrophoneUsageDescription': 'Tutor needs microphone access to record your questions.',
        'NSScreenCaptureUsageDescription': 'Tutor needs screen access to see what you are asking about.',
    },
)