a = Analysis(['tray.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=['rumps', 'sounddevice', 'openai', 'mss', 'pynput', 'pynput.keyboard'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=None,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='Tutor',
          debug=False,  # Set to True to see error messages
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,  # Disable UPX compression
          console=False,  # Set to True temporarily to see errors
          disable_windowed_traceback=False)

app = BUNDLE(exe,
             name='Tutor.app',
             bundle_identifier='com.tutor.app',
             info_plist={
                'LSUIElement': '1',  # This is crucial for menu bar apps
                'LSBackgroundOnly': '0',
                'NSHighResolutionCapable': 'True',
                'CFBundleShortVersionString': '1.0.0',
             })