# actions/generate_slurm_script.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..agent import Agent

from pathlib import Path

from .base import Action
from ..models.slurm import GenerateSlurmScript
from ..utils import display_in_panel, describe_classes, build_default_prompt
from outlines import Template


generate_slurm_template = Template.from_file(
    Path(__file__).parent.parent / "templates" / "generate_slurm_template.txt"
)

fill_in_slurm_template = Template.from_file(
    Path(__file__).parent.parent / "templates" / "slurm_template.txt"
)

class GenerateSlurmScriptAction(Action):
    description = (
        "Generate a Slurm submit script for the user's task and save it "
        "to the local directory."
    )

    def _run_impl(self, user_input: str, mode: str):
        """
        Use structured generation to create a Slurm script that:
        - Uses partition gg, gh, or gh-dev only.
        - Uses time in HH:MM:SS with a maximum of 48:00:00.
        - Contains the commands/code the user requested to run.
        """
        # Build trace context (if you want to include it, similar to GenerateCode)
        trace_context = build_default_prompt(self.agent, trace_data_only=True)

        # Build prompt using template
        prompt = generate_slurm_template(
            user_task=user_input,
            response_structure=describe_classes([GenerateSlurmScript]),
            trace_context=trace_context,
        )

        response: GenerateSlurmScript = self.generate_with_schema_action(
            prompt=prompt,
            schema=GenerateSlurmScript,
            mode=mode,
        )

        # Decide where to save the script
        # Here: project_root/generated_slurm/<filename>
        scripts_dir = Path(__file__).parent.parent / "generated_slurm"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        script_path = scripts_dir / response.script_filename

        # Write the script by building Slurm script from structured response class components
        script_text = fill_in_slurm_template(slurm=response)

        if not script_text.endswith("\n"):
            script_text += "\n"

        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_text)

        # Optionally make it executable
        try:
            script_path.chmod(script_path.stat().st_mode | 0o111)
        except Exception:
            # Non-fatal; ignore permission errors on some platforms
            pass

        # Panel output in dev mode
        if mode == "dev":
            panel_text = ""
            if getattr(response, "thoughts", None):
                panel_text += f"### Thoughts\n{response.thoughts.strip()}\n\n"
            panel_text += "### Slurm Script\n"
            panel_text += f"Saved to: {script_path}\n\n"
            panel_text += "```bash\n" + script_text + "```"
            display_in_panel(
                panel_text,
                title="Generated Slurm Script",
                padding_right=10,
            )

        # Add to conversation history
        convo_msg = (
            "Here is the generated Slurm script for the user's task:\n\n"
            f"File: {script_path}\n\n"
            "```bash\n"
            f"{script_text}"
            "```"
        )
        self.agent.history.append({"role": "assistant", "content": convo_msg})

        # return something so that the action is registered as having successfully completed
        return str(script_path)
