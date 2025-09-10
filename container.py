import os
import subprocess
from pathlib import Path
from rich.progress import (
    Progress, BarColumn, TextColumn, TimeRemainingColumn,
    TimeElapsedColumn, SpinnerColumn, MofNCompleteColumn
)
from rich.panel import Panel
from rich.box import ROUNDED
import time
import traceback
from config import IMAGES, BIN, DESKTOP_DIR, console
from logger import main_logger, subprocess_logger, log_subprocess_output
from utils import choose_yes_no

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
                ("Pobieranie obrazu bazowego", 10, "purple"),
                ("Tworzenie kontenera bazowego", 10, "blue"),
                ("Instalowanie pakietu", 40, "cyan"),
                ("Zapisywanie obrazu", 20, "green"),
                ("Usuwanie tymczasowego kontenera", 10, "yellow"),
                ("Tworzenie skryptu i pliku .desktop", 10, "magenta")
            ]
            current_advance = 0
            # Download base image
            subtask = progress.add_task(stages[0][0], total=None, style=stages[0][2])
            console.print(f"[bold {stages[0][2]}]>> {stages[0][0]}...[/bold {stages[0][2]}]")
            main_logger.info(f"Starting base image pull for {pkg}")
            proc = subprocess.run(["podman", "pull", "archlinux"], capture_output=True, check=True)
            log_subprocess_output(subprocess_logger, proc, f"Pull archlinux for {pkg}")
            progress.update(main_task, advance=stages[0][1])
            current_advance += stages[0][1]
            progress.remove_task(subtask)
            time.sleep(0.2)
            # Create base container
            subtask = progress.add_task(stages[1][0], total=None, style=stages[1][2])
            console.print(f"[bold {stages[1][2]}]>> {stages[1][0]} dla {pkg}...[/bold {stages[1][2]}]")
            main_logger.info(f"Creating base container for {pkg}")
            output = subprocess.check_output(["podman", "create", "-it", "archlinux", "/bin/bash"], stderr=subprocess.STDOUT)
            cid = output.decode().strip()
            subprocess_logger.info(f"Create container for {pkg} stdout: {output.decode()}")
            progress.update(main_task, advance=stages[1][1])
            current_advance += stages[1][1]
            progress.remove_task(subtask)
            time.sleep(0.2)
            # Install package
            subtask = progress.add_task(stages[2][0], total=None, style=stages[2][2])
            console.print(f"[bold {stages[2][2]}]>> {stages[2][0]} {pkg}...[/bold {stages[2][2]}]")
            main_logger.info(f"Installing package {pkg}")
            proc = subprocess.run(["podman", "start", "-ai", cid, "-c", "pacman -Syu --noconfirm"], capture_output=True, check=True)
            log_subprocess_output(subprocess_logger, proc, f"Update system for {pkg}")
            proc = subprocess.run(["podman", "start", "-ai", cid, "-c", f"pacman -S --noconfirm {pkg}"], capture_output=True, check=False)
            log_subprocess_output(subprocess_logger, proc, f"Install pacman for {pkg}")
            if proc.returncode != 0:
                error_output = proc.stderr.decode()
                if "target not found" in error_output.lower():
                    if choose_yes_no():
                        main_logger.info(f"Installing AUR dependencies for {pkg}")
                        proc = subprocess.run(["podman", "start", "-ai", cid, "-c", "pacman -S --needed --noconfirm git base-devel sudo"], capture_output=True, check=True)
                        log_subprocess_output(subprocess_logger, proc, f"Install AUR deps for {pkg}")
                        main_logger.info(f"Creating builder user for AUR installation of {pkg}")
                        proc = subprocess.run(["podman", "start", "-ai", cid, "-c", "useradd -m builder && echo 'builder ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers"], capture_output=True, check=True)
                        log_subprocess_output(subprocess_logger, proc, f"Create builder user for {pkg}")
                        main_logger.info(f"Installing yay-bin for {pkg}")
                        proc = subprocess.run(["podman", "start", "-ai", cid, "-c", 'su builder -c "git clone https://aur.archlinux.org/yay-bin.git ~/yay-bin && cd ~/yay-bin && makepkg -si --noconfirm"'], capture_output=True, check=True)
                        log_subprocess_output(subprocess_logger, proc, f"Install yay for {pkg}")
                        main_logger.info(f"Installing {pkg} with yay")
                        proc = subprocess.run(["podman", "start", "-ai", cid, "-c", f'su builder -c "yay -S --noconfirm {pkg}"'], capture_output=True, check=True)
                        log_subprocess_output(subprocess_logger, proc, f"Install with yay for {pkg}")
                    else:
                        raise subprocess.CalledProcessError(proc.returncode, proc.args, proc.stdout, proc.stderr)
                else:
                    raise subprocess.CalledProcessError(proc.returncode, proc.args, proc.stdout, proc.stderr)
            progress.update(main_task, advance=stages[2][1])
            current_advance += stages[2][1]
            progress.remove_task(subtask)
            time.sleep(0.2)
            # Commit image
            subtask = progress.add_task(stages[3][0], total=None, style=stages[3][2])
            console.print(f"[bold {stages[3][2]}]>> {stages[3][0]}...[/bold {stages[3][2]}]")
            main_logger.info(f"Committing image for {pkg}")
            proc = subprocess.run(["podman", "commit", cid, str(image_name)], capture_output=True, check=True)
            log_subprocess_output(subprocess_logger, proc, f"Commit image for {pkg}")
            progress.update(main_task, advance=stages[3][1])
            current_advance += stages[3][1]
            progress.remove_task(subtask)
            time.sleep(0.2)
            # Remove temporary container
            subtask = progress.add_task(stages[4][0], total=None, style=stages[4][2])
            console.print(f"[bold {stages[4][2]}]>> {stages[4][0]}...[/bold {stages[4][2]}]")
            main_logger.info(f"Removing temporary container for {pkg}")
            proc = subprocess.run(["podman", "rm", cid], capture_output=True, check=True)
            log_subprocess_output(subprocess_logger, proc, f"Remove container for {pkg}")
            progress.update(main_task, advance=stages[4][1])
            current_advance += stages[4][1]
            progress.remove_task(subtask)
            time.sleep(0.2)
            # Create run script and .desktop file
            subtask = progress.add_task(stages[5][0], total=None, style=stages[5][2])
            console.print(f"[bold {stages[5][2]}]>> {stages[5][0]}...[/bold {stages[5][2]}]")
            main_logger.info(f"Creating run script and .desktop file for {pkg}")
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
            progress.update(main_task, advance=stages[5][1])
            current_advance += stages[5][1]
            progress.remove_task(subtask)
            if current_advance < 100:
                progress.update(main_task, advance=100 - current_advance)
        console.print(Panel(
            f"[bold green]Sukces: Pakiet {pkg} został zainstalowany i skonfigurowany![/bold green]",
            border_style="green",
            padding=(1, 2),
            style="on #1a2525",
            box=ROUNDED
        ))
        console.print("\n")
        main_logger.info(f"Successfully installed and configured {pkg}")
    except subprocess.CalledProcessError as e:
        main_logger.error(f"CalledProcessError during {pkg} installation: {str(e)}")
        log_subprocess_output(subprocess_logger, e, f"Error installing {pkg}")
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
        main_logger.error(f"Attempted to run non-existent package {pkg}")
        sys.exit(1)
    console.print(f"[bold cyan]Uruchamianie {pkg}...[/bold cyan]")
    main_logger.info(f"Starting container for {pkg}")
    try:
        with Progress(
            SpinnerColumn(spinner_name="runner"),
            TextColumn("[progress.description]{task.description}", style="cyan"),
            console=console
        ) as progress:
            task = progress.add_task("Uruchamianie...", total=None)
            proc = subprocess.run([str(run_script)], capture_output=True, check=True)
            log_subprocess_output(subprocess_logger, proc, f"Run container {pkg}")
            progress.remove_task(task)
        console.print(f"[bold green]{pkg} uruchomiony pomyślnie[/bold green]\n")
        main_logger.info(f"Successfully ran {pkg}")
    except subprocess.CalledProcessError as e:
        main_logger.error(f"Run error for {pkg}: {str(e)}")
        log_subprocess_output(subprocess_logger, e, f"Error running {pkg}")
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

def remove_package(pkg):
    image_name = IMAGES / f"{pkg}.img"
    run_script = BIN / f"run-{pkg}.sh"
    desktop_file = DESKTOP_DIR / f"{pkg}.desktop"

    if not image_name.exists() and not run_script.exists() and not desktop_file.exists():
        console.print(Panel(
            f"[bold red]Błąd: Pakiet {pkg} nie jest zainstalowany![/bold red]\n"
            f"[red]Użyj 'isolator list' aby zobaczyć zainstalowane pakiety.[/red]",
            border_style="red",
            padding=(1, 2),
            style="on #2d1a1a",
            box=ROUNDED
        ))
        main_logger.error(f"Attempted to remove non-existent package {pkg}")
        sys.exit(1)

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
            main_task = progress.add_task(f"Usuwanie {pkg}", total=100)
            stages = [
                ("Usuwanie obrazu kontenera", 40, "red"),
                ("Usuwanie skryptu uruchamiającego", 30, "yellow"),
                ("Usuwanie pliku .desktop", 30, "magenta")
            ]
            current_advance = 0

            if image_name.exists():
                subtask = progress.add_task(stages[0][0], total=None, style=stages[0][2])
                console.print(f"[bold {stages[0][2]}]>> {stages[0][0]}...[/bold {stages[0][2]}]")
                main_logger.info(f"Removing container image for {pkg}")
                proc = subprocess.run(["podman", "rmi", str(image_name)], capture_output=True, check=True)
                log_subprocess_output(subprocess_logger, proc, f"Remove image for {pkg}")
                progress.update(main_task, advance=stages[0][1])
                current_advance += stages[0][1]
                progress.remove_task(subtask)
                time.sleep(0.2)

            if run_script.exists():
                subtask = progress.add_task(stages[1][0], total=None, style=stages[1][2])
                console.print(f"[bold {stages[1][2]}]>> {stages[1][0]}...[/bold {stages[1][2]}]")
                main_logger.info(f"Removing run script for {pkg}")
                run_script.unlink()
                progress.update(main_task, advance=stages[1][1])
                current_advance += stages[1][1]
                progress.remove_task(subtask)
                time.sleep(0.2)

            if desktop_file.exists():
                subtask = progress.add_task(stages[2][0], total=None, style=stages[2][2])
                console.print(f"[bold {stages[2][2]}]>> {stages[2][0]}...[/bold {stages[2][2]}]")
                main_logger.info(f"Removing .desktop file for {pkg}")
                desktop_file.unlink()
                progress.update(main_task, advance=stages[2][1])
                current_advance += stages[2][1]
                progress.remove_task(subtask)
                time.sleep(0.2)

            if current_advance < 100:
                progress.update(main_task, advance=100 - current_advance)

        console.print(Panel(
            f"[bold green]Sukces: Pakiet {pkg} został usunięty![/bold green]",
            border_style="green",
            padding=(1, 2),
            style="on #1a2525",
            box=ROUNDED
        ))
        console.print("\n")
        main_logger.info(f"Successfully removed package {pkg}")

    except (subprocess.CalledProcessError, OSError) as e:
        main_logger.error(f"Error removing package {pkg}: {str(e)}")
        if isinstance(e, subprocess.CalledProcessError):
            log_subprocess_output(subprocess_logger, e, f"Error removing image for {pkg}")
        console.print(Panel(
            f"[bold red]Błąd podczas usuwania {pkg}: {str(e)}[/bold red]\n"
            f"[red]Sprawdź uprawnienia lub czy wszystkie pliki zostały poprawnie usunięte.[/red]",
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
        main_logger.info("No packages found for update")
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
                main_logger.info(f"Starting update for {name}")
                output = subprocess.check_output(["podman", "create", "-it", str(image), "/bin/bash"], stderr=subprocess.STDOUT)
                cid = output.decode().strip()
                subprocess_logger.info(f"Create container for update {name}: {output.decode()}")
                proc = subprocess.run(["podman", "start", "-ai", cid, "-c", "pacman -Syu --noconfirm"], capture_output=True, check=True)
                log_subprocess_output(subprocess_logger, proc, f"Update system for {name}")
                proc = subprocess.run(["podman", "commit", cid, str(image)], capture_output=True, check=True)
                log_subprocess_output(subprocess_logger, proc, f"Commit update for {name}")
                proc = subprocess.run(["podman", "rm", cid], capture_output=True, check=True)
                log_subprocess_output(subprocess_logger, proc, f"Remove update container for {name}")
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
        main_logger.info("All containers updated successfully")
    except subprocess.CalledProcessError as e:
        main_logger.error(f"Update error: {str(e)}")
        log_subprocess_output(subprocess_logger, e, "Update error")
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
        main_logger.info("No installed packages found")
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
    main_logger.info("Listed installed packages")
