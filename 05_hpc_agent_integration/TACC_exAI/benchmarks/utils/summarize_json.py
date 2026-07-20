#!/usr/bin/env python3
import argparse
import json
import os
from collections import Counter
from statistics import mean

import pyperclip


def type_name(v):
    if isinstance(v, dict):
        return "object"
    if isinstance(v, list):
        return "array"
    if isinstance(v, str):
        return "string"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if v is None:
        return "null"
    return type(v).__name__


def summarize_value(value, path="root", depth=0, max_depth=4, max_array_samples=3):
    """
    Summarize a value; stop recursion when max_depth is reached.
    Arrays: sample up to max_array_samples elements.
    """
    summary = {
        "path": path,
        "type": type_name(value),
    }

    if depth >= max_depth:
        summary["kind"] = "truncated"
        return summary

    if isinstance(value, dict):
        summary["kind"] = "object"
        summary["num_keys"] = len(value)
        summary["keys"] = sorted(value.keys())
        children = []
        for k, v in value.items():
            child_path = f"{path}.{k}"
            children.append(
                summarize_value(
                    v,
                    path=child_path,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_array_samples=max_array_samples,
                )
            )
        summary["children"] = children

    elif isinstance(value, list):
        summary["kind"] = "array"
        length = len(value)
        summary["length"] = length
        elem_types = [type_name(v) for v in value]
        summary["element_type_counts"] = dict(Counter(elem_types))

        obj_elements = [v for v in value if isinstance(v, dict)]
        if obj_elements:
            key_counter = Counter()
            for obj in obj_elements:
                key_counter.update(obj.keys())
            summary["object_element_keys"] = {
                "keys": sorted(key_counter.keys()),
                "num_object_elements": len(obj_elements),
            }

        lens = []
        for v in value:
            if isinstance(v, (str, list, dict)):
                lens.append(len(v))
        if lens:
            summary["element_length_stats"] = {
                "avg_length": mean(lens),
                "min_length": min(lens),
                "max_length": max(lens),
            }

        sample_children = []
        for idx, v in enumerate(value[:max_array_samples]):
            child_path = f"{path}[{idx}]"
            sample_children.append(
                summarize_value(
                    v,
                    path=child_path,
                    depth=depth + 1,
                    max_depth=max_depth,
                    max_array_samples=max_array_samples,
                )
            )
        if sample_children:
            summary["sample_element_summaries"] = sample_children

    else:
        summary["kind"] = "primitive"
        if isinstance(value, str):
            summary["length"] = len(value)
        summary["repr"] = repr(value)[:80]

    return summary


def collect_global_stats(value):
    type_counter = Counter()
    key_counter = Counter()
    string_lengths = []
    array_lengths = []

    def walk(v):
        tname = type_name(v)
        type_counter[tname] += 1
        if isinstance(v, dict):
            for k, val in v.items():
                key_counter[k] += 1
                walk(val)
        elif isinstance(v, list):
            array_lengths.append(len(v))
            for elem in v:
                walk(elem)
        elif isinstance(v, str):
            string_lengths.append(len(v))

    walk(value)

    stats = {
        "type_counts": dict(type_counter),
        "key_counts": dict(key_counter),
    }

    if string_lengths:
        stats["string_length_stats"] = {
            "avg_length": mean(string_lengths),
            "min_length": min(string_lengths),
            "max_length": max(string_lengths),
        }

    if array_lengths:
        stats["array_length_stats"] = {
            "avg_length": mean(array_lengths),
            "min_length": min(array_lengths),
            "max_length": max(array_lengths),
        }

    return stats


def format_summary(summary, global_stats, file_path, max_lines=80):
    """
    Produce a concise, roughly <=500-word text summary.
    max_lines is a soft cap to keep it small.
    """
    lines = []
    lines.append(f"JSON summary for file: {os.path.basename(file_path)}")
    lines.append("")

    # Global stats short form
    lines.append("Global structure:")
    type_parts = [f"{t}={c}" for t, c in sorted(global_stats["type_counts"].items())]
    lines.append("  Value types: " + ", ".join(type_parts))
    if global_stats["key_counts"]:
        most_common_keys = sorted(
            global_stats["key_counts"].items(), key=lambda kv: kv[1], reverse=True
        )[:10]
        key_str = ", ".join(f"{k}({c})" for k, c in most_common_keys)
        lines.append("  Common keys (top 10): " + key_str)

    s_stats = global_stats.get("string_length_stats")
    if s_stats:
        lines.append(
            f"  String length: avg={s_stats['avg_length']:.1f}, "
            f"min={s_stats['min_length']}, max={s_stats['max_length']}"
        )

    a_stats = global_stats.get("array_length_stats")
    if a_stats:
        lines.append(
            f"  Array length: avg={a_stats['avg_length']:.1f}, "
            f"min={a_stats['min_length']}, max={a_stats['max_length']}"
        )

    lines.append("")
    lines.append("Hierarchy (truncated for brevity):")
    lines.extend(format_summary_node(summary, indent=0, max_lines=max_lines - len(lines)))

    # Enforce max_lines to keep size under control
    if len(lines) > max_lines:
        lines = lines[: max_lines - 1] + ["... (summary truncated)"]

    return "\n".join(lines)


def format_summary_node(node, indent=0, max_lines=60, current_lines=None):
    if current_lines is None:
        current_lines = []

    if len(current_lines) >= max_lines:
        return current_lines

    ind = "  " * indent
    path = node.get("path", "")
    typ = node.get("type")
    kind = node.get("kind")

    header = f"{ind}- {path}: {kind}, {typ}"
    current_lines.append(header)
    if len(current_lines) >= max_lines:
        return current_lines

    if kind == "object":
        current_lines.append(f"{ind}  keys ({node['num_keys']}): {', '.join(node['keys'])}")
        for child in node.get("children", []):
            format_summary_node(child, indent + 1, max_lines, current_lines)

    elif kind == "array":
        current_lines.append(f"{ind}  length={node['length']}")
        etc = node.get("element_type_counts", {})
        if etc:
            type_str = ", ".join(f"{t}={c}" for t, c in sorted(etc.items()))
            current_lines.append(f"{ind}  element types: {type_str}")
        obj_info = node.get("object_element_keys")
        if obj_info:
            current_lines.append(
                f"{ind}  object elements={obj_info['num_object_elements']}, "
                f"keys: {', '.join(obj_info['keys'])}"
            )
        el_stats = node.get("element_length_stats")
        if el_stats:
            current_lines.append(
                f"{ind}  element length avg={el_stats['avg_length']:.1f}, "
                f"min={el_stats['min_length']}, max={el_stats['max_length']}"
            )
        samples = node.get("sample_element_summaries")
        if samples:
            current_lines.append(f"{ind}  sample elements:")
            for child in samples:
                format_summary_node(child, indent + 2, max_lines, current_lines)

    elif kind == "primitive":
        if "length" in node:
            current_lines.append(f"{ind}  length={node['length']}")
        if "repr" in node:
            current_lines.append(f"{ind}  example={node['repr']}")

    elif kind == "truncated":
        current_lines.append(f"{ind}  (structure truncated at this depth)")

    return current_lines


def main():
    parser = argparse.ArgumentParser(
        description="Summarize JSON hierarchy concisely and copy summary to clipboard."
    )
    parser.add_argument("json_path", help="Path to JSON file")
    args = parser.parse_args()

    json_path = args.json_path
    if not os.path.isfile(json_path):
        print(f"Error: file does not exist: {json_path}")
        raise SystemExit(1)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading/parsing JSON file '{json_path}': {e}")
        raise SystemExit(1)

    root_summary = summarize_value(data, path="root")
    global_stats = collect_global_stats(data)
    text_summary = format_summary(root_summary, global_stats, json_path)

    print(text_summary)

    if text_summary.strip():
        try:
            pyperclip.copy(text_summary)
            print("\nCopied concise JSON summary to clipboard.")
        except Exception as e:
            print(f"\nFailed to copy to clipboard: {e}")
    else:
        print("\nSummary was empty; nothing copied.")


if __name__ == "__main__":
    main()
