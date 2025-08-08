import curses, asyncio, time
from core import screenshot, record, pipeline
import platform

IS_WINDOWS = platform.system() == "Windows"

if IS_WINDOWS:
    curses.KEY_F9 = ord('a')

def loop(stdscr):
    #enter cbreak mode to make characters immediately available instead of waiting for enter
    curses.cbreak()
    #allow special keys like f9 to be detected
    stdscr.keypad(True)
    #return -1 if no key is pressed immediately
    stdscr.nodelay(True)
    trigger = "A" if IS_WINDOWS else "F9"
    stdscr.addstr(f"Press {trigger} to ask.  Esc to quit.\n")
    while True:
        #wait for a key to be pressed
        key = stdscr.getch()
        if key == 27: #esc
            break
        elif key == curses.KEY_F9:
            stdscr.addstr(f"Recording... Press {trigger} to stop.\n")
            wav = record(stdscr)
            #take a screenshot
            png = screenshot()
            #run the pipeline using the wav file and the screenshot
            asyncio.run(pipeline(png, wav, stdscr))
            #restart the loop
            stdscr.addstr(f"Press {trigger} to ask.  Esc to quit. S to skip.\n")
            stdscr.refresh() #update the screen
        else: #other key pressed or no key pressed
            time.sleep(.02)

if __name__ == '__main__':
    #sets up the terminal for curses use, allocates a standard screen object (stdscr),
    #calls loop(stdscr), and cleans up the terminal when the program exits
    curses.wrapper(loop)