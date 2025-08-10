import rumps

class HelloTray(rumps.App):
    def __init__(self):
        super().__init__("Tutor") # text in menu bar
        self.quit_button.title = "Exit" # rename default quit button
        self.menu = ["Say Hello"]

    @rumps.clicked("Say Hello")
    def on_click(self, sender):
        rumps.alert("hello world") # alert

if __name__ == "__main__":
    HelloTray().run()