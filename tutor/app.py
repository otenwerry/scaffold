import pystray, pathlib, sys, logging
from PIL import Image
from worker import BackgroundWorker
#import keyboard
from pynput import keyboard as pk

logging.basicConfig(filename="tutor.log", level=logging.INFO)

icon_img = Image.open(pathlib.Path(__file__).with_name("icon.png"))

worker = BackgroundWorker(); worker.start()

def on_ask(icon, item): 
    worker.ask()

def on_quit(icon, item):
    worker.stop()
    icon.stop()
    sys.exit(0)

def on_press(key):
    if key == pk.Key.f9:
        worker.ask()

listener = pk.Listener(on_press=on_press)
listener.daemon = True
listener.start()

#keyboard.add_hotkey("f9", worker.ask)

icon = pystray.Icon("tutor", icon_img, "Tutor AI", menu=pystray.Menu(
    pystray.MenuItem("Ask (F9)", on_ask, default=True),
    pystray.MenuItem("Quit", on_quit),
))

def run_tray():
    icon.visible = True
    icon.run_detached()

def main():
    run_tray()
    with pk.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == "__main__":
    main()