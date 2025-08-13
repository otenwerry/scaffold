a = Analysis(
    ['tray.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.png', '.'),
    ],
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
    icon='icon.icns',  # convert PNG to ICNS for macOS
)

app = BUNDLE(
    exe,
    name='Tutor.app',
    icon='icon.icns',
    bundle_identifier='com.yourcompany.tutor',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSUIElement': '1',  # This makes it a menu bar only app (no dock icon)
        'NSMicrophoneUsageDescription': 'Tutor needs microphone access to record your questions.',
        'NSScreenCaptureUsageDescription': 'Tutor needs screen access to see what you are asking about.',
    },
)