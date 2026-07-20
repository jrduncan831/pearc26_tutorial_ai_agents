import shutil
import sys
import pyperclip  # pip install pyperclip
from .utils import display_in_panel


def get_user_input(mode: str) -> str:
    """
    Prompt for user input, then clear the raw input line(s) (including multiline pastes
    and wrapped lines) from the console before re-displaying it in a styled panel.
    Any occurrence of '#paste#' will be replaced with the current clipboard contents.
    """
    prompt_text = "You: "
    user_typed_input = input(prompt_text)

    # Replace #paste# with clipboard contents
    if "#paste#" in user_typed_input:
        try:
            clipboard_text = pyperclip.paste()
        except pyperclip.PyperclipException:
            clipboard_text = ""
        user_input = user_typed_input.replace("#paste#", clipboard_text)
    else:
        user_input = user_typed_input  

    # Determine terminal width
    term_width = shutil.get_terminal_size((80, 20)).columns

    # Split into actual lines (in case of pasted newlines)
    raw_lines = user_typed_input.splitlines() or [""]

    # Count console rows used = sum of wrapped lines for each actual line
    total_console_rows = 0
    for i, line in enumerate(raw_lines):
        # Add prompt length only to the first line
        extra = len(prompt_text) if i == 0 else 0
        total_console_rows += ((len(line) + extra) // term_width) + 1

    # Move cursor up and clear each console row
    for _ in range(total_console_rows):
        sys.stdout.write("\x1b[1A")  # Move up
        sys.stdout.write("\x1b[2K")  # Clear line
    sys.stdout.flush()

    # Display input in styled panel
    title = "You" if mode == "chat" else "You (Dev Mode)"
    display_in_panel(user_input.strip(), title=title, padding_left=20)

    return user_input.strip()

