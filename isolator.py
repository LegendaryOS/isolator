import sys
from config import console
from ui import print_header, show_help
from container import create_container_image, run_container, remove_package, update_all, list_packages
from logger import main_logger

def main():
    print_header()
    main_logger.info("Starting isolator script")
    if len(sys.argv) < 2 or sys.argv[1] in ["help", "?"]:
        show_help()
        main_logger.info("Displayed help menu")
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
                main_logger.error("Invalid install command usage")
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
                main_logger.error("Invalid run command usage")
                return
            run_container(sys.argv[2])
        elif command == "remove":
            if len(sys.argv) != 3:
                console.print(Panel(
                    "[bold red]Błąd: Użycie: isolator remove <pakiet>[/bold red]\n"
                    "[red]Przykład: isolator remove pakiet[/red]",
                    border_style="red",
                    padding=(1, 2),
                    style="on #2d1a1a",
                    box=ROUNDED
                ))
                main_logger.error("Invalid remove command usage")
                return
            remove_package(sys.argv[2])
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
            main_logger.error(f"Unknown command: {command}")
            console.print("\n")
    except Exception as e:
        main_logger.error(f"Unexpected error: {str(e)}")
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
    main_logger.info("Ending isolator script")

if __name__ == "__main__":
    main()
