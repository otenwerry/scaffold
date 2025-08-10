from re import L
import rumps
import sounddevice as sd
import numpy as np
import wave, tempfile, threading, time, math
import mss

SR = 16000

class HelloTray(rumps.App):
    def __init__(self):
        super().__init__("Tutor") # text in menu bar
        self.quit_button.title = "Exit" # rename default quit button
        # state for recording
        self.recording = False
        self._buf = [] # audio buffer
        self._lock = threading.Lock() # lock for buffer
        self._stream = None # audio stream

        # debug state
        self._frames = 0
        self._last_rms = 0.0
        self._last_cb_log = 0.0

        #menu
        self.say_hello = rumps.MenuItem("Say Hello", callback=self.on_hello)
        self.record_button = rumps.MenuItem("Start Recording", callback=self.on_record)
        self.screenshot_button = rumps.MenuItem("Take Screenshot", callback=self.on_screenshot)
        self.menu = [self.say_hello, self.record_button, self.screenshot_button]

    # say hello
    def on_hello(self, _):
        rumps.alert("hello world") # alert

    def _audio_cb(self, indata, frames, t, status):
        if status:
            print("Audio status:", status)
        # compute simple RMS for debug
        rms = float(np.sqrt(np.mean(indata.astype(np.float32)**2))) if frames else 0.0
        self._last_rms = rms
        self._frames += frames

        with self._lock:
            self._buf.append(indata.copy())
        
        # throttle terminal logs to ~1/sec
        now = time.time()
        if now - self._last_cb_log > 1.0:
            self._last_cb_log = now
            print(f"[cb] frames+={frames}, total={self._frames}, rms={rms:.5f}")

    def on_record(self, _):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def _tick_meter(self, _):
        # show RMS in dBFS and total frames
        rms = self._last_rms
        db = 20 * math.log10(rms + 1e-12)  # avoid -inf
        self.level_item.title = f"Mic: {db:5.1f} dBFS • {self._frames} fr"
    
    def start_recording(self):
        if self.recording:
            return
        self._buf.clear()
        # float32 is fine; we'll convert to int16 on save
        self._stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32", callback=self._audio_cb)
        self._stream.start()
        self.recording = True
        self.record_button.title = "Stop Recording"
        rumps.notification("Tutor", "", "Recording…")

    def stop_recording(self):
        if not self.recording:
            return
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None
            self.recording = False
            self.record_button.title = "Start Recording"
        # collapse buffer --> wav
        with self._lock:
            audio = np.concatenate(self._buf, axis=0) if self._buf else np.zeros((0, 1), dtype="float32")

        if audio.size == 0:
            rumps.notification("Tutor", "", "No audio captured.")
            return
        
        # debug summary before write
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        secs = audio.shape[0] / SR
        print(f"[stop] samples={audio.shape[0]}, secs={secs:.2f}, peak={peak:.4f}")


        audio_int16 = (audio.flatten() * 32767).astype(np.int16)
        tmp = tempfile.NamedTemporaryFile(prefix="tutor-", suffix=".wav", delete=False)
        with wave.open(tmp, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(audio_int16.tobytes())
        rumps.notification("Tutor", "", f"Saved WAV: {tmp.name}")

    def on_screenshot(self, _):
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])  # full display
            png_bytes = mss.tools.to_png(img.rgb, img.size)

        tmp = tempfile.NamedTemporaryFile(prefix="tutor-", suffix=".png", delete=False)
        with open(tmp.name, "wb") as f:
            f.write(png_bytes)
        rumps.notification("Tutor", "", f"Saved PNG: {tmp.name}")

if __name__ == "__main__":
    HelloTray().run()