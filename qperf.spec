# -*- mode: python -*-

block_cipher = None


a = Analysis(['qperf.py'],
             pathex=[],
             binaries=[],
             datas=[('qperf.py', '.'), ('qperf.ui', '.'), ('pyIperf.py', '.'),
					('images/*', 'images/'),
                    ('bin/Linux/x86_64/iperf3','bin/Linux/x86_64/'),
                    ('bin/Windows/*','bin/Windows/')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='qperf',
          debug=False,
          strip=False,
          upx=False,
          console=False , icon='images/qperf.ico')
