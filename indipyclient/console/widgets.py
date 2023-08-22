
import asyncio, curses


def startscreen(stdscr, title, info, messages=[]):
    "Displays title, info string and list of messages on a start screen"
    stdscr.clear()
    stdscr.addstr(0, 0, title, curses.A_BOLD)
    stdscr.addstr(2, 0, info)
    lastmessagenumber = len(messages) - 1
    for count, m in enumerate(messages):
        if count == lastmessagenumber:
            # high light the last, current message
            stdscr.addstr(4+count, 4, m, curses.A_BOLD)
        else:
            stdscr.addstr(4+count, 4, m)
    # put [Devices] [Quit] buttons on screen
    stdscr.addstr( curses.LINES - 1, curses.COLS//2 - 10, "[Devices]", curses.A_REVERSE)
    stdscr.addstr( curses.LINES - 1, curses.COLS//2 + 2, "[Quit]")
    stdscr.refresh()


async def startinputs(stdscr):
    "Gets inputs from the screen"
    try:
        stdscr.nodelay(True)
        while True:
            await asyncio.sleep(0)
            try:
                key = stdscr.getkey()
            except curses.error:
                continue
            if key == "q" or key == "Q":
                return "Quit"
    except Exception:
        return "Quit"
