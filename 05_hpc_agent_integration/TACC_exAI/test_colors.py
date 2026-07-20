#!/usr/bin/env python3
from rich.console import Console
from rich.panel import Panel
from rich.box import ROUNDED
from rich.text import Text

# === COPY YOUR COLOR LISTS FROM utils.py HERE ===
BRIGHT_COLORS_DARK = [
    "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
    "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "deep_sky_blue3", "spring_green4", "gold3", "orchid",
    "turquoise4", "chartreuse2", "medium_purple1", "light_salmon1",
    "dodger_blue1", "sandy_brown", "light_pink1", "plum1",
    "hot_pink3", "medium_orchid", "orange3", "light_steel_blue1",
]

BRIGHT_COLORS_LIGHT = [
    "red", "green", "blue", "magenta", "black",
    "dark_red", "dark_green", "dark_blue", "dark_magenta", "dark_cyan",
    "dark_orange3", "dark_orchid", "dark_sea_green", "dark_slate_gray1",
    "dark_turquoise", "dark_violet", "dark_goldenrod",
]

# === TEST FUNCTION ===
def test_colors(colors, mode_name: str):
    console = Console()
    errors = []
    ok_count = 0

    console.rule(f"[bold]Testing {mode_name} colors ({len(colors)} colors)[/bold]")

    for i, color in enumerate(colors, 1):
        try:
            text = Text(
                f"Color {i:2d}: {color}",
                style=color,
            )
            panel = Panel(
                text,
                title=f"[bold {color}]{mode_name}[/bold {color}]",
                box=ROUNDED,
                border_style=color,
                expand=False,
                title_align="left",
            )
            console.print(panel)
            ok_count += 1
        except Exception as e:
            errors.append((color, str(e)))

    console.rule("[bold]Summary[/bold]")
    console.print(
        f"✅ {ok_count} / {len(colors)} colors rendered successfully in {mode_name}."
    )
    if errors:
        console.print(f"❌ {len(errors)} colors failed in {mode_name}:", style="bold red")
        for color, err in errors:
            console.print(f"  {color}: {err}", style="red")
    else:
        console.print("All colors rendered without error.", style="bold green")

    return errors


if __name__ == "__main__":
    all_errors = []

    print("Testing dark‑mode colors…")
    dark_errors = test_colors(BRIGHT_COLORS_DARK, "Dark Mode")
    all_errors.extend(dark_errors)

    print("\nTesting light‑mode colors…")
    light_errors = test_colors(BRIGHT_COLORS_LIGHT, "Light Mode")
    all_errors.extend(light_errors)

    print("\n" + "=" * 60)
    if all_errors:
        print("Some colors failed; check above output for details.")
        exit(1)
    else:
        print("All colors passed! ✅")
        exit(0)
