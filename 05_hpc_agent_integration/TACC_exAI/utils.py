from pprint import pformat
from matplotlib import lines
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter
from pydantic import BaseModel
from rich.console import Console, Group
from rich.panel import Panel
from rich.box import ROUNDED
from rich.text import Text
from rich.markdown import Markdown
from typing import Union
import hashlib
import random
import json
from sentence_transformers import SentenceTransformer
import numpy as np


# Global mode: dark or light
DARK_MODE = True  # Default to dark mode

def set_mode(mode: str):
    """Set display mode: 'dark' or 'light'."""
    global DARK_MODE
    if mode.lower() == "dark":
        DARK_MODE = True
    elif mode.lower() == "light":
        DARK_MODE = False
    else:
        raise ValueError("Mode must be 'dark' or 'light'")

# Color sets for dark mode (light colors on dark background)
BRIGHT_COLORS_DARK = [
    "bright_red", "bright_green", "bright_yellow",
    "bright_blue", "bright_magenta", "bright_cyan", "bright_white",
    "red", "green", "yellow", "blue", "magenta", "cyan", "white",
    "deep_sky_blue3", "spring_green4", "gold3", "orchid",
    "turquoise4", "chartreuse2", "medium_purple1", "light_salmon1",
    "dodger_blue1", "sandy_brown", "light_pink1", "plum1",
    "hot_pink3", "medium_orchid", "orange3", "light_steel_blue1"
]

# Color set for light mode (dark, high-contrast colors on light background)
BRIGHT_COLORS_LIGHT = [
    "red", "green", "blue", "magenta", "black",
    "dark_red", "dark_green", "dark_blue", "dark_magenta", "dark_cyan",
    "dark_orange3", "dark_sea_green", 
    "dark_violet", "dark_goldenrod"
]



def get_bright_color(name: str) -> str:
    """Pick a color from the current mode’s palette."""
    colors = BRIGHT_COLORS_LIGHT if not DARK_MODE else BRIGHT_COLORS_DARK
    i = int(hashlib.md5(name.encode()).hexdigest(), 16) % len(colors)
    return colors[i]



from rich.syntax import Syntax
import re


def _render_model(obj: BaseModel, title: str = None, parent_color: str = None) -> Panel:
    """Recursively render a Pydantic model as nested Panels, handling lists of BaseModel objects."""
    class_name = obj.__class__.__name__
    border_color = parent_color or get_bright_color(class_name)
    subpanels = []
    codeblock_pattern = re.compile(r"``````")

    for field_name, value in obj.model_dump().items():
        field_value = getattr(obj, field_name)
        if isinstance(field_value, BaseModel):
            # Recurse for submodels
            sub_panel = _render_model(field_value, title=field_name, parent_color=border_color)
            subpanels.append(sub_panel)
        elif isinstance(field_value, list):
            # Handle list fields
            list_items = []
            for idx, item in enumerate(field_value):
                if isinstance(item, BaseModel):
                    # Each item gets its own panel, titled with index
                    list_panel = _render_model(item, title=f"{field_name}[{idx}]", parent_color=border_color)
                else:
                    # Primitives or strings: render normally
                    if isinstance(item, str):
                        match = codeblock_pattern.search(item)
                        if match:
                            lexer = match.group(1) or "python"
                            code = match.group(2).strip()
                            rendered_item = Syntax(code, lexer, theme="monokai", line_numbers=False)
                        elif any(c in item for c in ["#", "*", "-", "`", "\n"]):
                            rendered_item = Markdown(item, style=border_color)
                        else:
                            rendered_item = Text(repr(item), style=border_color)
                    else:
                        rendered_item = Text(repr(item), style=border_color)
                    list_panel = Panel(
                        rendered_item,
                        title=f"[bold {border_color}]{field_name}[{idx}][/bold {border_color}]",
                        box=ROUNDED,
                        border_style=border_color,
                        expand=False,
                        title_align="left",
                    )
                list_items.append(list_panel)
            group = Group(*list_items)
            sub_panel = Panel(
                group,
                title=f"[bold {border_color}]{field_name}[/bold {border_color}]",
                box=ROUNDED,
                border_style=border_color,
                expand=False,
                title_align="left",
            )
            subpanels.append(sub_panel)
        else:
            # Original handling for non-list fields
            rendered_content = None
            if isinstance(value, str):
                match = codeblock_pattern.search(value)
                if match:
                    lexer = match.group(1) or "python"
                    code = match.group(2).strip()
                    rendered_content = Syntax(code, lexer, theme="monokai", line_numbers=False)
                elif any(c in value for c in ["#", "*", "-", "`", "\n"]):
                    rendered_content = Markdown(value, style=border_color)
                else:
                    rendered_content = Text(repr(value), style=border_color)
            else:
                rendered_content = Text(repr(value), style=border_color)
            sub_panel = Panel(
                rendered_content,
                title=f"[bold {border_color}]{field_name}[/bold {border_color}]",
                box=ROUNDED,
                border_style=border_color,
                expand=False,
                title_align="left",
            )
            subpanels.append(sub_panel)

    group = Group(*subpanels)
    return Panel(
        group,
        title=f"[bold {border_color}]{title or class_name}[/bold {border_color}]",
        box=ROUNDED,
        border_style=border_color,
        expand=False,
    )


from rich.padding import Padding


def display_in_panel(
    obj: Union[str, BaseModel],
    title: str = None,
    padding_left: int = 0,
    padding_right: int = 0,
):
    console = Console()
    if isinstance(obj, BaseModel):
        panel = _render_model(obj, title=title)
    else:
        border_color = get_bright_color(title)
        markdown_obj = Markdown(obj, style=border_color)
        panel = Panel(
            markdown_obj,
            title=title,
            box=ROUNDED,
            border_style=border_color,
            expand=False,
        )

    # Apply padding around the outermost panel
    padded_panel = Padding(panel, (0, padding_right, 0, padding_left))
    console.print(padded_panel)


def pretty_print_response(response: BaseModel, title: str = "Structured Response") -> None:
    print(f"\n{'=' * len(title)}")
    print(title)
    print(f"{'=' * len(title)}")
    data = response.model_dump()
    formatted = pformat(data, sort_dicts=False, width=150)
    highlighted = highlight(formatted, PythonLexer(), TerminalFormatter())
    print(highlighted)


def get_class_field_descriptions(model_class) -> str:
    descriptions = []
    for field_name, field_info in model_class.model_fields.items():
        desc = getattr(field_info, "description", None) or "No description provided"
        descriptions.append(f"{field_name}: {desc}")
    return "\n".join(descriptions)


from enum import Enum
from pydantic import BaseModel


def describe_classes(classes) -> str:
    all_descriptions = []
    for cls in classes:
        if issubclass(cls, BaseModel):
            # Handle Pydantic models
            descriptions = []
            for field_name, field_info in cls.model_fields.items():
                desc = getattr(field_info, "description", None) or "No description provided"
                descriptions.append(f"{field_name}: {desc}")
            all_descriptions.append(
                f"Class {cls.__name__} properties:\n" + "\n".join(descriptions) + "\n"
            )
        elif issubclass(cls, Enum):
            # Handle Enums with descriptions
            enum_items = []
            for member in cls:
                desc = getattr(member, "description", None) or "No description provided"
                enum_items.append(f"{member.name}: {member.value} — {desc}")
            all_descriptions.append(
                f"Enum {cls.__name__} members:\n" + "\n".join(enum_items) + "\n"
            )
        else:
            all_descriptions.append(f"{cls.__name__}: Unsupported type\n")
    return "\n".join(all_descriptions)


import base64
from io import BytesIO
from PIL import Image
import matplotlib.pyplot as plt


def display_base64_image(img_base64):
    # Decode base64 image
    img_bytes = base64.b64decode(img_base64)

    # Load image from bytes
    img = Image.open(BytesIO(img_bytes))

    # Display image using matplotlib
    plt.imshow(img)
    plt.show()


from enum import Enum


def build_enum(classes):
    """Build a dynamic enum of available choices using their class names and descriptions."""
    if all(isinstance(x, tuple) and len(x) == 2 for x in classes):
        members = {x[0]: x for x in classes}
    else:
        members = {
            a.__class__.__name__: (a.__class__.__name__, a.description)
            for a in classes
        }
    # Custom Enum subclass that exposes the description
    class DynamicEnum(str, Enum):
        def __new__(cls, value, description):
            obj = str.__new__(cls, value)
            obj._value_ = value
            obj.description = description  # attach description dynamically
            return obj

    return DynamicEnum("DynamicEnum", members)


def select_trace_subset(agent, top_k: int = 3) -> list:
    """
    Select subset of traces based on CLI configuration.
    Prioritizes vector search using agent.original_user_request when available.
    """
    if not agent.trace_data:
        return []

    # Handle both dict (old format) and list (new pickle format)
    if isinstance(agent.trace_data, dict):
        available_traces = list(agent.trace_data.values())
    else:
        available_traces = agent.trace_data

    effective_k = min(top_k, len(available_traces), getattr(agent, "num_traces", top_k))
    if effective_k == 0:
        return []

    if getattr(agent, "use_vector_search", False) and hasattr(agent, "original_user_request") and agent.original_user_request:
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np

            model = SentenceTransformer("all-MiniLM-L6-v2")
            query_embedding = model.encode(agent.original_user_request, normalize_embeddings=True)

            valid_traces = []
            embeddings = []

            for trace in available_traces:
                # Get values FIRST, then check them safely
                emb1 = trace.get("embedding")
                emb2 = trace.get("chunk_embedding")

                # Check each individually without 'or' short‑circuiting
                embedding_data = None
                if emb1 is not None:
                    embedding_data = emb1
                elif emb2 is not None:
                    embedding_data = emb2

                if embedding_data is None:
                    continue

                try:
                    # Handle NumPy array directly (most likely case)
                    if isinstance(embedding_data, np.ndarray):
                        embedding_array = embedding_data.copy()  # Avoid modifying original
                    # Handle string representation
                    elif isinstance(embedding_data, str):
                        import re

                        clean_str = re.sub(r"[\[\]\n]", " ", embedding_data.strip())
                        embedding_array = np.fromstring(clean_str, sep=" ")
                    # Handle lists or other array‑like
                    else:
                        embedding_array = np.asarray(embedding_data)

                    if len(embedding_array) == 0:
                        continue

                    norm = np.linalg.norm(embedding_array)
                    if norm == 0:
                        continue

                    embedding_array = embedding_array / norm
                    embeddings.append(embedding_array)
                    valid_traces.append(trace)

                except Exception:
                    continue

            if embeddings:
                embeddings_array = np.vstack(embeddings)
                similarities = np.dot(embeddings_array, query_embedding)
                top_indices = np.argsort(-similarities)[:effective_k]
                selected_traces = [valid_traces[i] for i in top_indices]

                display_in_panel(
                    f"✅ Vector search: {len(selected_traces)} traces (top sim: {similarities[top_indices[0]]:.3f})",
                    title="Trace Selection",
                )
                return selected_traces
            else:
                display_in_panel(
                    "⚠️ No valid embeddings found, using random",
                    title="Trace Selection",
                )

        except Exception as e:
            display_in_panel(
                f"⚠️ Vector search failed: {str(e)[:50]}...",
                title="Trace Selection",
            )

    # Fallback random selection
    import random

    # Ensure seed is an int; initialize if missing or None
    seed = getattr(agent, "trace_subset_seed", None)
    if seed is None:
        seed = random.randint(0, 1000000)
    agent.trace_subset_seed = seed + 1  # safe int arithmetic

    random.seed(agent.trace_subset_seed - 1)  # use the “old” seed for sampling
    selected_traces = random.sample(available_traces, effective_k)

    display_in_panel(
        f"🎲 Random: {effective_k} traces (seed: {agent.trace_subset_seed - 1})",
        title="Trace Selection",
    )
    return selected_traces


# --- Truncation settings for step results ---
STEP_RESULT_TRUNCATE_MAX = 1200  # Max total length of step result string
STEP_RESULT_TRUNCATE_HEAD = 500  # Keep first N chars
STEP_RESULT_TRUNCATE_TAIL = 500  # Keep last N chars
STEP_RESULT_TRUNCATE_MARKER = "... (truncated for clarity) ..."


# --- Helper function ---
def truncate_step_result(
    s,
    max_total=STEP_RESULT_TRUNCATE_MAX,
    head=STEP_RESULT_TRUNCATE_HEAD,
    tail=STEP_RESULT_TRUNCATE_TAIL,
    marker=STEP_RESULT_TRUNCATE_MARKER,
):
    """Truncate a step result string for display."""
    s = str(s)
    n = len(s)
    if n <= max_total:
        return s
    if head + len(marker) + tail >= max_total:
        available = max_total - len(marker)
        return s[:available] + marker
    return s[:head] + marker + s[-tail:]


def stringify_trace(trace_data: dict) -> str:
    """Convert trace data to readable string format."""
    # Problem ID
    lines = [f"**Problem ID: {trace_data.get('problem_id', 'N/A')}**\n"]
    lines.append(f"**Task Prompt:** {trace_data.get('task_prompt', 'N/A')}\n")

    # Steps
    if "steps" in trace_data:
        lines.append("**Steps:**")
        for i, step in enumerate(trace_data["steps"], 1):
            lines.append(f"  Step {i}:")
            lines.append(f"    Name: {step.get('name', 'N/A')}")
            lines.append(f"    Action Type: {step.get('action_type', 'N/A')}")
            if "arguments" in step:
                lines.append(f"    Arguments: {json.dumps(step['arguments'])}...")
            if "result" in step:
                truncated_result = truncate_step_result(step["result"])
                lines.append(f"    Result: {truncated_result}")

    # Output
    if "output" in trace_data:
        lines.append("**Output:**")
        for key, value in trace_data["output"].items():
            lines.append(f"  {key}: {value}")

    lines.append(f"Was answer correct?: {trace_data.get('success', 'N/A')}\n")

    return "\n".join(lines)


def build_default_prompt(
    agent,
    task_description: str = "",
    response_classes: list = [],
    custom_history=None,
    hide_current_summary: bool = False,
    top_k_vector_matches: int = 3,
    trace_data_only: bool = False,
) -> str:
    """
    Build a standardized LLM prompt for structured generation.

    Args:
        agent: The agent instance (provides personality, history, summaries).
        task_description: A clear description of what the LLM should do.
        response_classes: List of Pydantic models or Enums to describe the expected response.
        custom_history: Optional override for conversation history.
        hide_current_summary: If True, omits the current conversation summary.
        top_k_vector_matches: Number of top relevant matches to retrieve from vector store and include in prompt.

    Returns:
        str: The assembled prompt string including agent personality, past summaries,
        relevant vector store context, current conversation summary, recent exchanges,
        and most recent user message.
    """

    # Add trace data context
    trace_context_text = ""
    if agent.trace_data:
        selected_traces = select_trace_subset(agent, agent.num_traces)
        if selected_traces:
            trace_context_text = "**Benchmark Trace Examples (for reference):**\n"
            for trace in selected_traces:
                trace_context_text += stringify_trace(trace) + "\n\n"
        else:
            trace_context_text = "**No trace examples available.**\n"

    if trace_data_only:
        # Include only trace data context
        prompt = trace_context_text
    else:
        # Past summaries
        past_summaries_text = "\n".join(
            [f"- {s}" for s in agent.past_summaries[-3:]]
        ) or "No past sessions."

        # Use either the custom history or recent history (last 5 messages excluding current)
        if custom_history:
            recent_history = custom_history
        else:
            recent_history = agent.history[-6:-1]

        # Find the most recent user message scanning backward
        most_recent_user_message = None
        for msg in reversed(agent.history[-6:]):
            if msg["role"] == "user":
                most_recent_user_message = msg["content"]
                break

        # Retrieve top matches from vector store based on most recent user message
        vector_matches_text = ""
        if most_recent_user_message and agent.full_history_store:
            hits = agent.full_history_store.search(
                most_recent_user_message, top_k=top_k_vector_matches
            )
            if hits:
                vector_matches_text = "\n".join(
                    f"- {hit[1].get('role', 'unknown')}: {hit[1].get('chunk_text', '')}"
                    for hit in hits
                    if hit[1].get("chunk_text")
                )
            else:
                vector_matches_text = "No relevant context from past history found."
        else:
            vector_matches_text = "No user message found to query vector store."

        # Assemble the prompt string
        prompt = (
            "**Core Agent Personality**\n"
            + (agent.agent_personality or "No defined personality.")
            + "\n\n"
            + trace_context_text
            + "\n\n"
            f"**Your task: {task_description}**\n\n"
            "**Response Structure Descriptions:**\n"
            + describe_classes(response_classes)
            + "\n\n"
            "**Summaries of past conversations with user (for context only):**\n"
            + past_summaries_text
            + "\n\n"
            "**Relevant context retrieved from past conversation history:**\n"
            + vector_matches_text
            + "\n\n"
        )

        # Add current conversation summary unless hidden
        if not hide_current_summary and agent.last_summary:
            prompt += (
                "**Summary of current conversation with user:**\n"
                + (agent.last_summary.summary or "No current summary.")
                + "\n\n"
            )

        # Add recent exchanges with user in this conversation
        conversation_context = ""
        for msg in recent_history:
            role = msg["role"]
            conversation_context += f"{role}: {msg['content']}  \n"
        prompt += (
            "**Recent exchanges with user in this conversation:**\n"
            + (conversation_context or "No recent context.")
            + "\n\n"
        )

        # Add the most recent user message
        prompt += (
            "**Most recent user message:**\n"
            + f"user: {most_recent_user_message}\n\n"
        )

    return prompt


import argparse
import os
import shutil
import sys


def delete_agent_outputs():
    """
    Delete contents of specific subdirectories: knowledge_base, knowledge_base_html,
    generated_code, sessions, and vectorstores, under the script's root.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    target_dirs = [
        "knowledge_base",
        "knowledge_base_html",
        "generated_code",
        "sessions",
        "vectorstores",
    ]

    for dirname in target_dirs:
        full_path = os.path.join(base_dir, dirname)
        if os.path.exists(full_path):
            # Remove contents, but not the folder itself
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    print(f"Error deleting {item_path}: {e}")
            print(f"Cleared contents of {full_path}")
        else:
            print(f"Directory {full_path} does not exist, skipping.")


def main():
    parser = argparse.ArgumentParser(
        description="utils.py CLI: perform utility functions via flags. No action unless a flag is explicitly set."
    )
    parser.add_argument(
        "--delete-agent-outputs",
        action="store_true",
        help="Delete contents of agent-related output directories.",
    )
    args = parser.parse_args()

    if not any(vars(args).values()):
        parser.print_help()
        sys.exit(1)

    if args.delete_agent_outputs:
        delete_agent_outputs()


if __name__ == "__main__":
    main()
