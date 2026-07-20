#!/usr/bin/env python3
import argparse
import json
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import GroupKFold

from history_vector_store import recursive_chunk


# ---------- Helpers copied / adapted from process_arize_exports.py ----------


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_action_type(steps: List[Dict[str, Any]], start_index: int) -> str:
    """
    Walk backwards from start_index-1 until a step with name != 'ChatCompletion'
    is found. Return that name, or '' if none is found.
    """
    idx = start_index - 1
    while idx >= 0:
        name = steps[idx].get("name")
        if name and name != "ChatCompletion":
            return name
        idx -= 1
    return ""


def extract_step_data(steps_dict: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Given a dict of steps keyed by numeric strings ("0","1",...), extract the
    desired data from ChatCompletion and run_python_in_docker steps, preserving
    order by step index.
    """
    ordered_step_keys = sorted(
        steps_dict.keys(),
        key=lambda k: int(k) if isinstance(k, str) and k.isdigit() else k,
    )
    steps: List[Dict[str, Any]] = [steps_dict[k] for k in ordered_step_keys]

    extracted: List[Dict[str, Any]] = []

    for i, step in enumerate(steps):
        name = step.get("name")
        attrs = step.get("attributes", {}) or {}

        if name == "ChatCompletion":
            args_value = attrs.get(
                "llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments"
            )

            if args_value is not None:
                action_type = find_action_type(steps, i)
                extracted.append(
                    {
                        "name": name,
                        "action_type": action_type,
                        "arguments": args_value,
                    }
                )

        elif name == "run_python_in_docker":
            result_value = attrs.get("output.result")

            if result_value is not None:
                extracted.append(
                    {
                        "name": name,
                        "result": result_value,
                    }
                )

    return extracted


def build_problem_records(
    experiment_runs: Dict[str, Any],
    traces: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Build a dict keyed by problem_id with:
      - problem_id
      - trace_id
      - steps
      - output
      - task_prompt
      - success (bool)
    This is essentially the union of successes/failures from process_arize_exports.py
    but kept together.
    """
    trace_ids = experiment_runs.get("trace_id", {})
    results = experiment_runs.get("result", {})
    outputs = experiment_runs.get("output", {})
    inputs = experiment_runs.get("input", {})

    traces_by_id = traces

    records: Dict[str, Dict[str, Any]] = {}

    for problem_key, result_info in results.items():
        label_str = str(result_info.get("label"))
        is_success = label_str == "True"

        trace_id = trace_ids.get(problem_key)
        trace_steps = traces_by_id.get(trace_id) if trace_id is not None else None

        problem_output = outputs.get(problem_key)

        problem_input = inputs.get(problem_key, {}) or {}
        if isinstance(problem_input, dict):
            task_prompt = problem_input.get("prompt")
        else:
            task_prompt = None

        if not isinstance(trace_steps, dict):
            record = {
                "problem_id": problem_key,
                "trace_id": trace_id,
                "steps": [],
                "output": problem_output,
                "task_prompt": task_prompt,
                "success": is_success,
            }
        else:
            extracted_steps = extract_step_data(trace_steps)
            record = {
                "problem_id": problem_key,
                "trace_id": trace_id,
                "steps": extracted_steps,
                "output": problem_output,
                "task_prompt": task_prompt,
                "success": is_success,
            }

        records[problem_key] = record

    return records


# ---------- Helpers copied / adapted from kfold_vector_embeddings.py ----------


def expand_dict_column(df: pd.DataFrame, col_name: str, prefix: str | None = None) -> pd.DataFrame:
    """
    df: pandas DataFrame
    col_name: name of the column containing dictionaries
    prefix: optional prefix for new column names
    """
    expanded = df[col_name].apply(pd.Series)
    if prefix:
        expanded = expanded.add_prefix(prefix)
    return pd.concat([df.drop(columns=[col_name]), expanded], axis=1)


def create_folds(n_splits: int, path_to_experiments: Path) -> Tuple[Dict[int, List[int]], pd.DataFrame]:
    """
    Create GroupKFold splits using file_name as the grouping variable.
    """
    merged_df = pd.read_json(path_to_experiments)
    df_new = expand_dict_column(merged_df, "metadata")
    gkf = GroupKFold(n_splits=n_splits)
    groups = df_new["file_name"].values
    folds = {
        fold: val_idx.tolist()
        for fold, (_, val_idx) in enumerate(gkf.split(df_new, groups=groups))
    }
    return folds, df_new


# ---------- New: combine folds/embeddings with trace info ----------


def create_and_write_folds_with_traces(
    folds: Dict[int, List[int]],
    embedding_model: str,
    df_new: pd.DataFrame,
    path_to_write: Path,
    max_chunk_size: int,
    problem_records: Dict[str, Dict[str, Any]],
) -> None:
    """
    For each fold, create chunked embeddings and enrich each entry with
    the trace/metadata built from experiment_runs + traces, including a
    'success' boolean instead of splitting successes/failures.
    """
    model = SentenceTransformer(embedding_model)

    for fold, indices in folds.items():
        entries: List[Dict[str, Any]] = []

        for index in indices:
            # problem_id in experiment_runs.json is keyed by string
            problem_id_str = str(index)

            # df_new.input[index] comes from experiment_runs["input"][problem_id]
            content = df_new.input[index]["prompt"]

            # find the corresponding trace/metadata record
            record = problem_records.get(problem_id_str, {})
            trace_id = record.get("trace_id")
            steps = record.get("steps")
            output = record.get("output")
            task_prompt = record.get("task_prompt")
            success = record.get("success")

            chunks = recursive_chunk(content, max_size=max_chunk_size)

            for idx, chunk in enumerate(chunks):
                embedding = model.encode(chunk, normalize_embeddings=True)

                entry = {
                    "problem_id": index,            # numeric index
                    "trace_id": trace_id,
                    "orig_content": content,
                    "result": df_new.result[index],
                    "chunk_index": idx,
                    "chunk_text": chunk,
                    "embedding": embedding,
                    "steps": steps,
                    "output": output,
                    "task_prompt": task_prompt,
                    "success": success,
                }
                entries.append(entry)

        file_name = path_to_write / f"question_fold_{fold}.pkl"
        with file_name.open("wb") as f:
            pickle.dump(entries, f, protocol=pickle.HIGHEST_PROTOCOL)

    # also keep folds mapping for downstream use (unchanged behavior)
    with (path_to_write / "folds.json").open("w", encoding="utf-8") as f:
        json.dump(folds, f)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create question folds, compute embeddings, and attach "
            "trace/Arize export metadata (including success flag) into per-fold pickle files."
        )
    )
    parser.add_argument(
        "--n_splits",
        type=int,
        default=3,
        help="Number of folds for cross-validation.",
    )
    parser.add_argument(
        "--path_to_experiments",
        type=Path,
        default=Path("experiment_runs.json"),
        help="Path to experiment_runs.json file.",
    )
    parser.add_argument(
        "--traces_path",
        type=Path,
        default=Path("traces.json"),
        help="Path to traces.json file.",
    )
    parser.add_argument(
        "--max_chunk_size",
        type=int,
        default=250,
        help="Maximum size of text chunks.",
    )
    parser.add_argument(
        "--path_to_write",
        type=Path,
        default=Path("."),
        help="Directory to save output pickle files.",
    )
    parser.add_argument(
        "--embedding_model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="SentenceTransformer model name.",
    )

    args = parser.parse_args()

    # Load experiment_runs + traces and build per-problem records
    experiment_runs = load_json(args.path_to_experiments)
    traces = load_json(args.traces_path)
    problem_records = build_problem_records(experiment_runs, traces)

    # Build folds and dataframe (same as original)
    folds, df_new = create_folds(args.n_splits, args.path_to_experiments)

    # Create embeddings + attach trace info
    create_and_write_folds_with_traces(
        folds=folds,
        embedding_model=args.embedding_model,
        df_new=df_new,
        path_to_write=args.path_to_write,
        max_chunk_size=args.max_chunk_size,
        problem_records=problem_records,
    )


if __name__ == "__main__":
    main()
