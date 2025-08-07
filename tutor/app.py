import pystray, pathlib, sys, logging
from PIL import Image
from worker import BackgroundWorker

logging.basicConfig(filename="tutor.log", level=logging.INFO)

icon_img = Image.open(pathlib.Path(__file__).with_name("icon.png"))

worker = BackgroundWorker(); worker.start()

def on_ask(icon, item): 
    worker.ask()

def on_quit(icon, item):
    worker.stop()
    icon.stop()
    sys.exit(0)

icon = pystray.Icon("tutor", icon_img, "Tutor AI", menu=pystray.Menu(
    pystray.MenuItem("Ask (F9)", on_ask, default=True),
    pystray.MenuItem("Quit", on_quit),
))

icon.run()