import sys
import os
from datetime import datetime

SR = 24000
FRAME_MS = 20 
BLOCKSIZE = int(SR * FRAME_MS / 1000) 
RING_SECONDS = 60 #60 seconds of audio to buffer
#APPLE_OCR = True
EDGE_FUNCTION_URL = "wss://giohlugbdruxxlgzdtlj.supabase.co/functions/v1/realtime-proxy"

def asset_path(name: str) -> str:
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            base = sys._MEIPASS
        elif sys.platform == 'darwin':
            base = os.path.normpath(os.path.join(os.path.dirname(sys.executable), "..", "Resources"))
        else:
            base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)

def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]
