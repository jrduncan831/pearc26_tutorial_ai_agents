#!/usr/bin/env python3
import argparse
import json
import pickle
from pathlib import Path
from typing import Any, List, Dict

import numpy as np


def truncate_embedding(value: Any, max_len: int) -> str:
    """
    Turn the embedding (list or numpy array) into a string and truncate it.
    Only the string form of the embedding is truncated; other fields remain intact.
    """
    # Convert common embedding types to a compact string
    if isinstance(value, np.ndarray):
        text = np.array2string(value, max_line_width=80, threshold=10)
    else:
        # list, tuple, etc.
        text = str(value)

    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def convert_entry(entry: Dict[str, Any], max_len: int) -> Dict[str, Any]:
    """
    Return a JSON-serializable copy of entry, truncating only the embedding string.
    """
    out = dict(entry)

    # Handle embedding specially
    emb = out.get("embedding")
    if emb is not None:
        out["embedding"] = truncate_embedding(emb, max_len)

    # Make sure any numpy scalars/arrays in other fields are JSON-safe
    def make_json_safe(obj: Any) -> Any:
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (list, tuple)):
            return [make_json_safe(x) for x in obj]
        if isinstance(obj, dict):
            return {k: make_json_safe(v) for k, v in obj.items()}
        return obj

    return make_json_safe(out)


def pickle_to_json(pickle_path: Path, max_embedding_len: int) -> Path:
    """
    Load a pickle file containing a list of entries and write a JSON file
    with truncated embedding strings.
    """
    with pickle_path.open("rb") as f:
        data = pickle.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected pickle to contain a list of entries")

    converted: List[Dict[str, Any]] = [
        convert_entry(entry, max_embedding_len) for entry in data
    ]

    json_path = pickle_path.with_suffix(".json")
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(converted, f, indent=2, ensure_ascii=False)

    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert a fold pickle file to JSON, truncating only the embedding field."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the .pkl file (e.g., question_fold_0.pkl)",
    )
    parser.add_argument(
        "--max_embedding_len",
        type=int,
        default=200,
        help="Maximum length of the embedding string representation.",
    )

    args = parser.parse_args()
    pickle_path: Path = args.path

    json_path = pickle_to_json(pickle_path, args.max_embedding_len)
    print(f"Wrote JSON to {json_path}")


if __name__ == "__main__":
    main()
