import asyncio, threading, logging
import curses
from core import screenshot, record, pipeline

_log = logging.getLogger("tutor ai")

class DummyScreen:
    def addstr(self, s):
        _log.info(s.rstrip("\n"))
    
    def refresh(self):
        pass

class BackgroundWorker:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self._t = threading.Thread(target=self.loop.run_forever, daemon=True)

    def start(self):
        self._t.start()

    def stop(self):
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._t.join()

    def ask(self):
        asyncio.run_coroutine_threadsafe(self._job(), self.loop)
    
    async def _job(self):
        png = screenshot()
        wav = await self.loop.run_in_executor(None, record)
        await pipeline(png, wav, DummyScreen())