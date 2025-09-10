import sys
import termios
import fcntl
from config import console

def get_key():
    fd = sys.stdin.fileno()
    oldterm = termios.tcgetattr(fd)
    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
    termios.tcsetattr(fd, termios.TCSANOW, newattr)
    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)
    try:
        while True:
            try:
                c = sys.stdin.read(1)
                if c:
                    termios.tcsetattr(fd, termios.TCDRAIN, oldterm)
                    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
                    return c
            except IOError:
                pass
    finally:
        termios.tcsetattr(fd, termios.TCDRAIN, oldterm)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)

def choose_yes_no():
    options = ["Tak", "Nie"]
    selected = 0
    while True:
        console.clear()
        console.print("[bold cyan]Pakiet nie znaleziony w standardowych repozytoriach. Czy sprawdzić AUR?[/bold cyan]\n")
        for i, opt in enumerate(options):
            if i == selected:
                console.print(f"> [bold green]{opt}[/bold green]")
            else:
                console.print(f" [white]{opt}[/white]")
        key = get_key()
        if key == '\x1b':
            next_key = get_key()
            if next_key == '[':
                direction = get_key()
                if direction == 'A':
                    selected = (selected - 1) % len(options)
                elif direction == 'B':
                    selected = (selected + 1) % len(options)
        elif key in ('\r', '\n'):
            console.clear()
            return options[selected] == "Tak"
