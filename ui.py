from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from config import console

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
        ("remove <pakiet>", "Usuwa pakiet i powiązane pliki", "isolator remove {pakiet}"),
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
