import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from get_token_count import count_qwen_tokens


def extract_errors_to_file(
    input_file: str,
) -> str:
    """
    Load the given JSON file (experiment_runs_rag1.json or traces_rag1.json),
    find ALL LLM spans (ERROR + non-error generations), count tokens for each llm_input,
    and save them to a new JSON file.
    
    Output file: <input_file_basename>_errors.json
    
    Each entry includes:
    - "is_error": true/false to delineate error vs successful generations
    - "llm_input": prompt text
    - "token_count": token count of llm_input
    - context metadata
    
    Returns:
        Path to the created output file.
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = []

    def visit(obj: Any, path: List[Any]) -> None:
        if (
            isinstance(obj, dict)
            and "status_code" in obj
            and "attributes" in obj
        ):
            # Check for LLM input presence (either input_messages or input.value)
            llm_input = None
            if isinstance(obj["attributes"], dict):
                # Try llm.input_messages.0.message.content
                if "llm.input_messages" in obj["attributes"]:
                    llm_msgs = obj["attributes"]["llm.input_messages"]
                    if isinstance(llm_msgs, list) and len(llm_msgs) > 0:
                        if isinstance(llm_msgs[0], dict) and "message" in llm_msgs[0]:
                            msg = llm_msgs[0]["message"]
                            if isinstance(msg, dict) and "content" in msg:
                                llm_input = msg["content"]
                # Fall back to attributes.input.value (raw prompt)
                if llm_input is None and "input.value" in obj["attributes"]:
                    llm_input = obj["attributes"]["input.value"]

            # Skip if no llm_input found
            if llm_input is None:
                return

            # Determine if this is an error generation
            is_error = obj["status_code"] == "ERROR"
            
            # Count tokens
            token_count = count_qwen_tokens(llm_input)
            
            # Create entry
            entry = {
                "is_error": is_error,
                "status_code": obj["status_code"],
                "status_message": obj.get("status_message", ""),
                "llm_input": llm_input,
                "token_count": token_count,
                "context": {},
                "raw_path": path.copy(),
            }

            # Capture basic span/trace IDs
            if "trace_id" in obj:
                entry["context"]["trace_id"] = obj["trace_id"]
            if "id" in obj:
                entry["context"]["span_id"] = obj["id"]
            if "span_id" in obj:
                entry["context"]["span_id"] = obj["span_id"]
            if "name" in obj:
                entry["context"]["name"] = obj["name"]
            
            entries.append(entry)

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                visit(item, path + [i])
        elif isinstance(obj, dict):
            for k, v in obj.items():
                visit(v, path + [k])

    # Traverse the data
    visit(data, [])

    # Build output file path
    input_path = Path(input_file)
    output_path = input_path.parent / f"{input_path.stem}_errors.json"

    # Save to JSON file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    return str(output_path)


# Example usage
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_error_prompts.py <path/to/input.json>")
        sys.exit(1)

    output_file = extract_errors_to_file(sys.argv[1])
    
    # Count total entries and breakdown
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        total_entries = len(data)
        error_count = sum(1 for entry in data if entry["is_error"])
        success_count = total_entries - error_count
    
    print(f"All LLM generations extracted and saved to: {output_file}")
    print(f"Total entries: {total_entries}")
    print(f"Error generations: {error_count}")
    print(f"Success generations: {success_count}")
