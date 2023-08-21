
import curses


def startscreen(stdscr, title, info, messages=[]):
    "Displays title, info string and list of messages on a start screen"
    stdscr.clear()
    stdscr.addstr(0, 0, title, curses.A_REVERSE)
    stdscr.addstr(2, 0, info)
    for count, m in enumerate(messages):
        if count:
            stdscr.addstr(4+count, 4, m)
        else:
            # highlight first message
            stdscr.addstr(4+count, 4, m, curses.A_REVERSE)
    stdscr.refresh()
