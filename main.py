import os
import subprocess
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeRemainingColumn,
    TimeElapsedColumn, SpinnerColumn, MofNCompleteColumn
)
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.box import ROUNDED
import sys
import uuid
import time
import traceback
import termios
import fcntl

console = Console()
# Configuration
ISOLATOR_DIR = Path.home() / ".isolator-apps"
IMAGES = ISOLATOR_DIR / "images"
CONTAINERS = ISOLATOR_DIR / "containers"
BIN = ISOLATOR_DIR / "bin"
DESKTOP_DIR = Path.home() / ".local/share/applications"
# Ensure directories exist
for directory in [IMAGES, CONTAINERS, BIN, DESKTOP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

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
                console.print(f"  [white]{opt}[/white]")
        key = get_key()
        if key == '\x1b':  # escape sequence for arrows
            next_key = get_key()  # should be '['
            if next_key == '[':
                direction = get_key()
                if direction == 'A':  # up
                    selected = (selected - 1) % len(options)
                elif direction == 'B':  # down
                    selected = (selected + 1) % len(options)
        elif key in ('\r', '\n'):  # enter
            console.clear()
            return options[selected] == "Tak"

def print_header():
    console.print("\n")
    title = Text("Isolator: Kontenerowy Menedżer Pakietów", style="bold white")
    title.stylize("color(75) bold", 0, 9) # Gradient effect on "Isolator"
    title.stylize("color(117)", 9, len(title)) # Gradient continuation
    console.print(Panel(
        title,
        border_style="bold cyan",
        padding=(1, 3),
        expand=False,
        style="on #1a2525",
        box=ROUNDED
    ))
    console.print("\n")

def show_help():
    table = Table(
        title="Dostępne Komendy",
        title_style="bold color(201) on #1a2525",
        show_lines=True,
        border_style="bright_cyan",
        header_style="bold white on #2d3b3b",
        padding=(0, 1),
        box=ROUNDED
    )
    table.add_column("Komenda", style="cyan", no_wrap=True, width=25)
    table.add_column("Opis", style="green", width=45)
    table.add_column("Przykład", style="yellow")
    commands = [
        ("install <pakiet>", "Instaluje pakiet w nowym kontenerze", "isolator install {pakiet}"),
        ("run <pakiet>", "Uruchamia zainstalowany pakiet", "isolator run {pakiet}"),
        ("update-all", "Aktualizuje wszystkie kontenery", "isolator update-all"),
        ("list", "Wyświetla listę zainstalowanych pakietów", "isolator list"),
        ("help", "Wyświetla to menu pomocy", "isolator help"),
        ("?", "Synonim dla help", "isolator ?")
    ]
    for cmd, desc, example in commands:
        table.add_row(cmd, desc, example)
    console.print(Panel(
        table,
        border_style="cyan",
        padding=(1, 2),
        style="on #1a2525",
        box=ROUNDED
    ))
    console.print("\n")

def create_container_image(pkg):
    image_name = IMAGES / f"{pkg}.img"
    run_script = BIN / f"run-{pkg}.sh"
    try:
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}", style="bold cyan"),
            BarColumn(bar_width=None, style="blue", complete_style="green"),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.1f}%", style="white"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            main_task = progress.add_task(f"Instalacja {pkg}", total=100)
            stages = [
                ("Tworzenie kontenera bazowego", 20, "blue"),
                ("Instalowanie pakietu", 40, "cyan"),
                ("Zapisywanie obrazu", 20, "green"),
                ("Usuwanie tymczasowego kontenera", 10, "yellow"),
                ("Tworzenie skryptu i pliku .desktop", 10, "magenta")
            ]
            # Create base container
            subtask = progress.add_task(stages[0][0], total=None, style=stages[0][2])
            console.print(f"[bold {stages[0][2]}]>> {stages[0][0]} dla {pkg}...[/bold {stages[0][2]}]")
            cid = subprocess.check_output(["podman", "create", "-it", "archlinux", "/bin/bash"]).decode().strip()
            progress.update(main_task, advance=stages[0][1])
            progress.remove_task(subtask)
            time.sleep(0.2) # Smooth transition
            # Install package
            subtask = progress.add_task(stages[1][0], total=None, style=stages[1][2])
            console.print(f"[bold {stages[1][2]}]>> {stages[1][0]} {pkg}...[/bold {stages[1][2]}]")
            # First update system
            subprocess.run(["podman", "start", "-ai", cid, "-c", "pacman -Syu --noconfirm"], check=True)
            # Try to install with pacman
            proc = subprocess.run(["podman", "start", "-ai", cid, "-c", f"pacman -S --noconfirm {pkg}"], capture_output=True, check=False)
            if proc.returncode != 0:
                error_output = proc.stderr.decode()
                if "target not found" in error_output.lower():
                    if choose_yes_no():
                        # Install dependencies for AUR
                        subprocess.run(["podman", "start", "-ai", cid, "-c", "pacman -S --needed --noconfirm git base-devel sudo"], check=True)
                        # Create builder user
                        subprocess.run(["podman", "start", "-ai", cid, "-c", "useradd -m builder && echo 'builder ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers"], check=True)
                        # Install yay-bin
                        subprocess.run(["podman", "start", "-ai", cid, "-c", 'su builder -c "git clone https://aur.archlinux.org/yay-bin.git ~/yay-bin && cd ~/yay-bin && makepkg -si --noconfirm"'], check=True)
                        # Install package with yay
                        subprocess.run(["podman", "start", "-ai", cid, "-c", f'su builder -c "yay -S --noconfirm {pkg}"'], check=True)
                    else:
                        raise subprocess.CalledProcessError(proc.returncode, proc.args, proc.stdout, proc.stderr)
                else:
                    raise subprocess.CalledProcessError(proc.returncode, proc.args, proc.stdout, proc.stderr)
            progress.update(main_task, advance=stages[1][1])
            progress.remove_task(subtask)
            time.sleep(0.2)
            # Commit image
            subtask = progress.add_task(stages[2][0], total=None, style=stages[2][2])
            console.print(f"[bold {stages[2][2]}]>> {stages[2][0]}...[/bold {stages[2][2]}]")
            subprocess.run(["podman", "commit", cid, str(image_name)], check=True)
            progress.update(main_task, advance=stages[2][1])
            progress.remove_task(subtask)
            time.sleep(0.2)
            # Remove temporary container
            subtask = progress.add_task(stages[3][0], total=None, style=stages[3][2])
            console.print(f"[bold {stages[3][2]}]>> {stages[3][0]}...[/bold {stages[3][2]}]")
            subprocess.run(["podman", "rm", cid], check=True)
            progress.update(main_task, advance=stages[3][1])
            progress.remove_task(subtask)
            time.sleep(0.2)
            # Create run script and .desktop file
            subtask = progress.add_task(stages[4][0], total=None, style=stages[4][2])
            console.print(f"[bold {stages[4][2]}]>> {stages[4][0]}...[/bold {stages[4][2]}]")
            with open(run_script, "w") as f:
                f.write(f"""#!/bin/bash
xhost +SI:localuser:$USER
podman run --rm -it \\
    -e DISPLAY=$DISPLAY \\
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw \\
    -v $HOME:/home/user:rw \\
    --device /dev/dri \\
    {image_name} {pkg}
""")
            run_script.chmod(0o755)
            with open(DESKTOP_DIR / f"{pkg}.desktop", "w") as f:
                f.write(f"""[Desktop Entry]
Name={pkg}
Exec={run_script}
Icon={pkg}
Type=Application
Terminal=false
""")
            progress.update(main_task, advance=stages[4][1])
            progress.remove_task(subtask)
        console.print(Panel(
            f"[bold green]Sukces: Pakiet {pkg} został zainstalowany i skonfigurowany![/bold green]",
            border_style="green",
            padding=(1, 2),
            style="on #1a2525",
            box=ROUNDED
        ))
        console.print("\n")
    except subprocess.CalledProcessError as e:
        error_msg = f"[bold red]Błąd podczas instalacji {pkg}: {str(e)}[/bold red]\n"
        error_msg += "[red]Sprawdź, czy pakiet istnieje i czy podman jest prawidłowo skonfigurowany.[/red]"
        console.print(Panel(error_msg, border_style="red", padding=(1, 2), style="on #2d1a1a", box=ROUNDED))
        if os.environ.get("DEBUG"):
            console.print("[red]Szczegóły błędu:[/red]")
            console.print(traceback.format_exc())
        sys.exit(1)

def run_container(pkg):
    run_script = BIN / f"run-{pkg}.sh"
    if not run_script.exists():
        console.print(Panel(
            f"[bold red]Błąd: Pakiet {pkg} nie jest zainstalowany![/bold red]\n"
            f"[red]Użyj 'isolator install {pkg}' aby zainstalować pakiet.[/red]",
            border_style="red",
            padding=(1, 2),
            style="on #2d1a1a",
            box=ROUNDED
        ))
        sys.exit(1)
    console.print(f"[bold cyan]Uruchamianie {pkg}...[/bold cyan]")
    try:
        with Progress(
            SpinnerColumn(spinner_name="runner"),
            TextColumn("[progress.description]{task.description}", style="cyan"),
            console=console
        ) as progress:
            task = progress.add_task("Uruchamianie...", total=None)
            subprocess.run([str(run_script)], check=True)
            progress.remove_task(task)
        console.print(f"[bold green]{pkg} uruchomiony pomyślnie[/bold green]\n")
    except subprocess.CalledProcessError as e:
        console.print(Panel(
            f"[bold red]Błąd podczas uruchamiania {pkg}: {str(e)}[/bold red]\n"
            f"[red]Sprawdź konfigurację podman i uprawnienia.[/red]",
            border_style="red",
            padding=(1, 2),
            style="on #2d1a1a",
            box=ROUNDED
        ))
        if os.environ.get("DEBUG"):
            console.print("[red]Szczegóły błędu:[/red]")
            console.print(traceback.format_exc())
        sys.exit(1)

def update_all():
    images = list(IMAGES.glob("*.img"))
    if not images:
        console.print(Panel(
            "[bold yellow]Brak zainstalowanych pakietów do aktualizacji[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
            style="on #2d2a1a",
            box=ROUNDED
        ))
        console.print("\n")
        return
    try:
        with Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}", style="bold cyan"),
            BarColumn(bar_width=None, style="blue", complete_style="green"),
            MofNCompleteColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.1f}%", style="white"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            main_task = progress.add_task("Aktualizacja wszystkich kontenerów", total=len(images) * 100)
            for image in images:
                name = image.stem
                subtask = progress.add_task(f"Aktualizacja {name}", total=None)
                console.print(f"[bold cyan]>> Aktualizowanie {name}...[/bold cyan]")
                cid = subprocess.check_output(["podman", "create", "-it", str(image), "/bin/bash"]).decode().strip()
                subprocess.run(["podman", "start", "-ai", cid, "-c", "pacman -Syu --noconfirm"], check=True)
                subprocess.run(["podman", "commit", cid, str(image)], check=True)
                subprocess.run(["podman", "rm", cid], check=True)
                progress.update(main_task, advance=100)
                progress.remove_task(subtask)
                time.sleep(0.2)
        console.print(Panel(
            "[bold green]Wszystkie kontenery zostały zaktualizowane![/bold green]",
            border_style="green",
            padding=(1, 2),
            style="on #1a2525",
            box=ROUNDED
        ))
        console.print("\n")
    except subprocess.CalledProcessError as e:
        console.print(Panel(
            f"[bold red]Błąd podczas aktualizacji: {str(e)}[/bold red]\n"
            f"[red]Sprawdź połączenie sieciowe i konfigurację podman.[/red]",
            border_style="red",
            padding=(1, 2),
            style="on #2d1a1a",
            box=ROUNDED
        ))
        if os.environ.get("DEBUG"):
            console.print("[red]Szczegóły błędu:[/red]")
            console.print(traceback.format_exc())
        sys.exit(1)

def list_packages():
    images = list(IMAGES.glob("*.img"))
    if not images:
        console.print(Panel(
            "[bold yellow]Brak zainstalowanych pakietów[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
            style="on #2d2a1a",
            box=ROUNDED
        ))
        console.print("\n")
        return
    table = Table(
        title="Zainstalowane Pakiety",
        title_style="bold color(201) on #1a2525",
        show_lines=True,
        border_style="bright_cyan",
        header_style="bold white on #2d3b3b",
        padding=(0, 1),
        box=ROUNDED
    )
    table.add_column("Pakiet", style="cyan", width=25)
    table.add_column("Ścieżka Obrazu", style="green")
    for image in images:
        table.add_row(image.stem, str(image))
    console.print(Panel(
        table,
        border_style="cyan",
        padding=(1, 2),
        style="on #1a2525",
        box=ROUNDED
    ))
    console.print("\n")

def main():
    print_header()
    if len(sys.argv) < 2 or sys.argv[1] in ["help", "?"]:
        show_help()
        return
    command = sys.argv[1]
    try:
        if command == "install":
            if len(sys.argv) != 3:
                console.print(Panel(
                    "[bold red]Błąd: Użycie: isolator install <pakiet>[/bold red]\n"
                    "[red]Przykład: isolator install pakiet[/red]",
                    border_style="red",
                    padding=(1, 2),
                    style="on #2d1a1a",
                    box=ROUNDED
                ))
                return
            create_container_image(sys.argv[2])
        elif command == "run":
            if len(sys.argv) != 3:
                console.print(Panel(
                    "[bold red]Błąd: Użycie: isolator run <pakiet>[/bold red]\n"
                    "[red]Przykład: isolator run pakiet[/red]",
                    border_style="red",
                    padding=(1, 2),
                    style="on #2d1a1a",
                    box=ROUNDED
                ))
                return
            run_container(sys.argv[2])
        elif command == "update-all":
            update_all()
        elif command == "list":
            list_packages()
        else:
            console.print(Panel(
                "[bold red]Nieznana komenda[/bold red]\n"
                "[red]Użyj 'isolator help' lub 'isolator ?' po listę komend.[/red]",
                border_style="red",
                padding=(1, 2),
                style="on #2d1a1a",
                box=ROUNDED
            ))
            console.print("\n")
    except Exception as e:
        console.print(Panel(
            f"[bold red]Nieoczekiwany błąd: {str(e)}[/bold red]\n"
            f"[red]Spróbuj ponownie lub sprawdź konfigurację systemu.[/red]",
            border_style="red",
            padding=(1, 2),
            style="on #2d1a1a",
            box=ROUNDED
        ))
        if os.environ.get("DEBUG"):
            console.print("[red]Szczegóły błędu:[/red]")
            console.print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()
