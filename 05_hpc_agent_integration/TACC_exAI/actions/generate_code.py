from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..agent import Agent

from .base import Action
from ..models.code import GenerateCode
from ..utils import display_in_panel
from ..docker_code_executor import run_python_in_docker, process_docker_response
from pathlib import Path
from outlines import Template
import uuid
from ..utils import describe_classes, build_default_prompt

# --- Truncation settings for long outputs/errors ---
DISPLAY_TRUNCATE_MAX = 1200         # Max total length of displayed string
DISPLAY_TRUNCATE_HEAD = 500        # Keep first N chars
DISPLAY_TRUNCATE_TAIL = 500        # Keep last N chars
DISPLAY_TRUNCATE_MARKER = "... truncated for clarity...\n"

# --- Helper function to truncate long strings ---
def truncate_for_display(s, max_total=DISPLAY_TRUNCATE_MAX, head=DISPLAY_TRUNCATE_HEAD, tail=DISPLAY_TRUNCATE_TAIL, marker=DISPLAY_TRUNCATE_MARKER):
    """Truncate a string, keeping first `head` and last `tail` chars, with a marker in the middle."""
    s = str(s)
    n = len(s)
    if n <= max_total:
        return s
    # If not enough space for both head and tail, just use head + marker
    if head + len(marker) + tail >= max_total:
        available = max_total - len(marker)
        return s[:available] + marker
    return s[:head] + marker + s[-tail:]

# --- Load template ---
generate_code_template = Template.from_file(Path(__file__).parent.parent / 'templates/generate_code_template.txt')


class GenerateCodeAction(Action):
    description = ("Generate Python code for user task and execute it inside a Docker container."
                   " Returns only the standard output or error from execution. "
                   " Always try and write all of the code in one shot that you can."
    )

    def _run_impl(self, user_input: str, mode: str):
        attempt = 0
        max_attempts = 3
        prev_code, prev_error = "", ""

        # import trace data if available
        trace_context = build_default_prompt(self.agent, trace_data_only=True)

        while attempt < max_attempts:
            attempt += 1

            # Use the loaded template to build the prompt
            prompt = generate_code_template(
                user_task=user_input,
                prev_code=prev_code or "None",
                prev_error=prev_error or "None",
                response_structure=describe_classes([GenerateCode]),
                trace_context=trace_context,
            )

            response: GenerateCode = self.generate_with_schema_action(
                prompt=prompt,
                schema=GenerateCode,
                mode=mode,
            )

            # Execute the code in Docker
            if self.tracer:
                with self.tracer.start_as_current_span("run_python_in_docker", openinference_span_kind="chain") as span:
                    span.set_attribute("input.code", response.code)
                    span.set_attribute("input.data_dir", self.agent.data_dir)

                    # Execute the function
                    result = run_python_in_docker(response.code, data_dir=self.agent.data_dir)

                    # Record output
                    span.set_attribute("output.result", str(result))
            else:
                result = run_python_in_docker(response.code, data_dir=self.agent.data_dir)

            # Truncate long output for display and error reuse
            output_for_display = truncate_for_display(result["output"])

            # Show everything in one panel when in dev mode
            if mode == "dev":
                panel_text = ""
                if hasattr(response, "thoughts") and response.thoughts:
                    panel_text += f"### Thoughts\n{response.thoughts.strip()}\n\n"
                panel_text += "### Code\n" + self.format_code_block(response.code) + "\n\n"
                if result["success"]:
                    if result.get("is_image"):
                        panel_text += "### Execution Result\nThe code executed successfully and generated an image (`image.png`)."
                    else:
                        panel_text += f"### Execution Result\n{output_for_display}"
                else:
                    panel_text += f"### Execution Result (Error)\n{output_for_display}"
                display_in_panel(
                    panel_text,
                    title=f"Generating Code Attempt {attempt}",
                    padding_right=10
                )

            if result["success"]:

                filename = Path(__file__).parent.parent / 'generated_code' / f"generated_code_{uuid.uuid4().hex[:8]}.py"
                filename.parent.mkdir(parents=True, exist_ok=True)  # <-- ensure the folder exists
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(response.code)

                # Wrap code in backticks for assistant message
                code_block = self.format_code_block(response.code)

                if result.get("is_image"):
                    convo_msg = (
                        f"Here is the generated code that solved the user's task:\n\n"
                        f"{code_block}\n\n"
                        f"Execution result:\nThe code executed successfully and generated an image which was saved as 'image.png'."
                    )
                else:
                    convo_msg = (
                        f"Here is the generated code that solved the user's task:\n\n"
                        f"{code_block}\n\n"
                        f"Execution result:\n{truncate_for_display(result['output'])}"
                    )
                self.agent.history.append({"role": "assistant", "content": convo_msg})
                return "success"

            prev_code = response.code
            prev_error = truncate_for_display(result["output"])  # Truncated for prompt reuse

        # Truncate final error/output for display
        truncated_final_output = truncate_for_display(prev_error)
        error_msg = (
            "Failed to generate working code after 3 attempts.\n"
            "Final Error message:\n" + truncated_final_output + "\n"
            "Final generated code:\n" + prev_code
        )   

        self.agent.history.append({"role": "assistant", "content": error_msg})
        if mode == "dev":
            display_in_panel(error_msg, title="Error", padding_right=10)

    @staticmethod
    def format_code_block(code: str) -> str:
        """Ensure code is wrapped in fenced backticks with python hint."""
        block = code.strip()
        if not block.startswith("```"):
            block = "```python\n" + block
        if not block.endswith("```"):
            block = block + "\n```"
        return block
