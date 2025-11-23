binaries = [
    ('../frameworks/Sparkle.framework', 'Sparkle.framework')
]
datas = [
        ('../logos/icon.png', 'logos'),
        ('../logos/gray.png', 'logos'),
        ('../logos/blue1.png', 'logos'),
        ('../logos/blue2.png', 'logos'),
        ('../logos/blue3.png', 'logos'),
        ('../styles/base.qss', 'styles'),
    ]

a = Analysis(
    ['../app.py'],
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
    name='Scaffold',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False = no terminal window
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../logos/icon.icns', 
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Scaffold'
)

app = BUNDLE(
    coll,
    name='Scaffold.app',
    icon='../logos/icon.icns',
    bundle_identifier='com.scaffoldvoice.scaffold-beta',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '1.0.8',
        'CFBundleVersion': '108', # need to increment this every time you ship the same bundle id
        'NSMicrophoneUsageDescription': 'Scaffold needs microphone access to record your questions.',
        'NSScreenCaptureUsageDescription': 'Scaffold needs screen access to see what you are asking about.',
        'CFBundleURLTypes': [
            {
                'CFBundleURLName': 'Scaffold Auth Callback',
                'CFBundleURLSchemes': ['scaffold'],
            }
        ],
        'SUPublicEDKey': 'X8Kqb9r+krRf40hRCgRtWoTyUUa6uhD3+Y1u5TdZF4o=',
        'SUFeedURL': 'https://updates.scaffoldvoice.com/appcast.xml',
        'SUEnableAutomaticChecks': True,
    },
)