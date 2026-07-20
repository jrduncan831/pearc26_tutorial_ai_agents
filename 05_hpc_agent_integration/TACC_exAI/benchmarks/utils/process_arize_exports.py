#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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

    Expected structure for each trace_id in traces.json:

      traces_json[trace_id][step_index]["name"]
      traces_json[trace_id][step_index]["attributes"]["llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments"]
      traces_json[trace_id][step_index]["attributes"]["output.result"]
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


def process_directory(directory: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load experiment_runs.json and traces.json from directory, and build
    successes and failures dicts keyed by problem id.

    Assumptions:

    - experiment_runs.json contains:
        {
          "trace_id": { "0": "<trace_id0>", ... },
          "result":   { "0": {"label": "True"/"False", ...}, ... },
          "output":   { "0": {...}, "1": {...}, ... },
          "input":    { "0": {"prompt": "..."} , ... }
          ...
        }

    - traces.json contains:
        {
          "<trace_id0>": {
            "0": { "name": "...", "attributes": {...}, ... },
            "1": { ... },
            ...
          },
          "<trace_id1>": { ... },
          ...
        }
    """
    traces_path = directory / "traces.json"
    experiment_runs_path = directory / "experiment_runs.json"

    traces = load_json(traces_path)
    experiment_runs = load_json(experiment_runs_path)

    trace_ids = experiment_runs.get("trace_id", {})
    results = experiment_runs.get("result", {})
    outputs = experiment_runs.get("output", {})  # per-problem outputs
    inputs = experiment_runs.get("input", {})    # per-problem inputs (prompts etc.)

    traces_by_id = traces

    successes: Dict[str, Any] = {}
    failures: Dict[str, Any] = {}

    for problem_key, result_info in results.items():
        label_str = str(result_info.get("label"))
        is_success = label_str == "True"

        trace_id = trace_ids.get(problem_key)
        trace_steps = traces_by_id.get(trace_id) if trace_id is not None else None

        # experiment_runs output for this problem (may be None)
        problem_output = outputs.get(problem_key)

        # initial task prompt for this problem (may be None)
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
            }
        else:
            extracted_steps = extract_step_data(trace_steps)
            record = {
                "problem_id": problem_key,
                "trace_id": trace_id,
                "steps": extracted_steps,
                "output": problem_output,
                "task_prompt": task_prompt,
            }

        if is_success:
            successes[problem_key] = record
        else:
            failures[problem_key] = record

    return successes, failures


def main() -> None:
    """
    Entry point for processing Arize export artifacts.

    Usage:
        python process_arize_exports.py /path/to/export_dir

    Expected inputs in the given directory:
    - experiment_runs.json: Contains per-problem metadata, including:
        * result[label]: Whether each problem was a success or failure
        * trace_id: Mapping from problem index to trace hash
        * output: Final task-level outputs for each problem
        * input: Initial task prompts for each problem
    - traces.json: Contains raw trace spans keyed by trace_id, where each
      trace is a mapping from step index (0..N) to a span with:
        * name: Span type (e.g., "ChatCompletion", "run_python_in_docker")
        * attributes: Flat key-value metadata for that step

    What this script does:
    - Loads experiment_runs.json to determine, for each problem:
        * success/failure label
        * associated trace_id
        * final structured output fields
        * the initial task prompt from input[problem_id]["prompt"]
    - Loads traces.json and, for each trace_id, walks the step indices in
      order to extract:
        * For "ChatCompletion" steps:
            - The tool call arguments from
              attributes["llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments"]
            - An action_type inferred from the closest preceding non-
              "ChatCompletion" span name
        * For "run_python_in_docker" steps:
            - The execution result from attributes["output.result"]
    - Aggregates this information into per-problem records of the form:
        {
            "problem_id": ...,
            "trace_id": ...,
            "steps": [...extracted step summaries...],
            "output": {...values from experiment_runs.json["output"][problem_id]...},
            "task_prompt": experiment_runs.json["input"][problem_id]["prompt"]
        }
    - Writes two files to the same directory:
        * successes.json: Records for problems where label == "True"
        * failures.json: Records for problems where label != "True"

    This provides a compact, analysis-ready view of model traces and
    final outputs, grouped by success vs failure.
    """

    parser = argparse.ArgumentParser(
        description="Split traces into successes.json and failures.json"
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Directory containing experiment_runs.json and traces.json",
    )
    args = parser.parse_args()

    directory: Path = args.path
    successes, failures = process_directory(directory)

    write_json(directory / "successes.json", successes)
    write_json(directory / "failures.json", failures)


if __name__ == "__main__":
    main()
