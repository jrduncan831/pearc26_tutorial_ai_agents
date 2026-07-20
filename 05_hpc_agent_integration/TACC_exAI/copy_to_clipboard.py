#!/usr/bin/env python3
import sys
import os
import pyperclip

# Allowed file extensions (easy to extend)
ALLOWED_EXTENSIONS = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".log"}


def has_allowed_extension(filename):
    """Check if the file has a valid extension."""
    return any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS)


def build_filtered_tree(root, file_set, prefix=""):
    """Build a folder tree including only the paths leading to copied files."""
    tree_lines = []
    entries = sorted(os.listdir(root))
    visible_entries = []

    for entry in entries:
        path = os.path.join(root, entry)
        if os.path.isfile(path) and os.path.abspath(path) in file_set:
            visible_entries.append(entry)
        elif os.path.isdir(path):
            # Include directory if it leads to any copied file
            for fs in file_set:
                if fs.startswith(os.path.abspath(path) + os.sep):
                    visible_entries.append(entry)
                    break

    for i, entry in enumerate(visible_entries):
        path = os.path.join(root, entry)
        connector = "└── " if i == len(visible_entries) - 1 else "├── "
        tree_lines.append(prefix + connector + entry)
        if os.path.isdir(path):
            extension = "    " if i == len(visible_entries) - 1 else "│   "
            tree_lines.extend(build_filtered_tree(path, file_set, prefix + extension))
    return tree_lines


def collect_files(args):
    """Collect all files with allowed extensions from given files or directories."""
    file_paths = set()
    for path in args:
        abs_path = os.path.abspath(path)
        if os.path.isfile(abs_path) and has_allowed_extension(abs_path):
            file_paths.add(abs_path)
        elif os.path.isdir(abs_path):
            for root, _, files in os.walk(abs_path):
                for file in files:
                    if has_allowed_extension(file):
                        file_paths.add(os.path.abspath(os.path.join(root, file)))
        else:
            print(f"Skipping invalid path: {path}")
    return file_paths


def find_common_root(paths):
    """Find the lowest common directory among all copied files."""
    if not paths:
        return None
    return os.path.commonpath(paths)


def main():
    if len(sys.argv) < 2:
        print("Usage: python copy_to_clipboard.py <file_or_folder1> <file_or_folder2> ...")
        sys.exit(1)

    file_paths = collect_files(sys.argv[1:])
    if not file_paths:
        print(f"No valid files found with extensions: {', '.join(ALLOWED_EXTENSIONS)}")
        sys.exit(1)

    # Build folder tree from common root of all collected files
    common_root = find_common_root(list(file_paths))
    if common_root and not os.path.isdir(common_root):
        common_root = os.path.dirname(common_root)
    tree_lines = build_filtered_tree(common_root, file_paths)
    
    file_contents = []
    if tree_lines:
        file_contents.append(f"# Folder tree (common root: {common_root})\n")
        file_contents.append("\n".join(tree_lines) + "\n\n")

    # File contents
    for filename in sorted(file_paths):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                relative_path = os.path.relpath(filename, common_root)
                file_contents.append(f"# **{relative_path}**\n")
                file_contents.append(f.read())
                file_contents.append("\n\n")
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    combined_text = "".join(file_contents)

    if combined_text.strip():
        pyperclip.copy(combined_text)
        print("Copied file contents to clipboard. Total files:", len(file_paths))
    else:
        print("No content copied.")


if __name__ == "__main__":
    main()