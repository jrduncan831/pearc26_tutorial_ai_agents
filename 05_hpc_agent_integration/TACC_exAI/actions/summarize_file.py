# actions/summarize_file.py
import os
from .base import Action
from pydantic import BaseModel, Field
from ..utils import display_in_panel, build_default_prompt, describe_classes
from pathlib import Path

class FileExtractResponse(BaseModel):
    thoughts: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Reasoning through how to interpret the user's request and figure out the file name to summarize."
    )
    filename: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description=(
            "The precise file path extracted from the user's input. If the user only gave a file name, just extract the file name."
            "Do not make up paths. Do not put ./ in front of the file name."
            )
    )

class FileSummaryResponse(BaseModel):
    thoughts: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Your thoughts and reasoning on what this file is about. Pick out specific details if needed."
    )
    summary: str = Field(
        ...,
        min_length=20,
        max_length=1500,
        description="A concise but informative summary of the file contents."
    )

class SummarizeFileAction(Action):
    description = "Extract a file path from user input, read the file, and summarize its contents."
    default_openinference_span_kind: str = "chain" # sets the default span kind for tracing the run method

    def _run_impl(self, user_input: str, mode: str, context: str = None):
        # Step 1: Extract file name from user input
        extract_prompt = build_default_prompt(
            self.agent,
            task_description="Identify the file path or file name in the user's input. If multiple are mentioned, choose the most relevant one.",
            response_classes=[FileExtractResponse]
        )

        file_extract_response: FileExtractResponse = self.generate_with_schema_action(
            schema=FileExtractResponse,
            prompt=extract_prompt,
            mode=mode
        )

        if mode == "dev":
            display_in_panel(
            file_extract_response,
            title="Parsing File Name from User Input",
            padding_left=10,
            padding_right=10
            ) 
            
        filename = file_extract_response.filename.strip()
        # Always resolve as relative to current working directory
        script_dir = Path(__file__).resolve().parent.parent
        abs_path = script_dir / filename
        
        if not os.path.isfile(abs_path):
            display_in_panel(
                f"⚠️ File not found: {filename}\nLooked for: {abs_path}",
                title="System Message",
                padding_left=10,
                padding_right=10
            )
            return None

        # Step 2: Read the file contents
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                contents = f.read()
        except Exception as e:
            display_in_panel(
                f"⚠️ Could not read file {filename}: {e}\nLooked for: {abs_path}",
                title="System Message",
                padding_left=10,
                padding_right=10
            )
            return None

        # Step 3: Summarize file contents using custom prompt (not default)
        summarization_prompt = (
            f"Summarize the following file contents.\n\n"
            f"**Optional Context (may guide summarization):**\n{context or 'No additional context provided.'}\n\n"
            f"**Response Structure:**  \n"
            f"{describe_classes([FileSummaryResponse])}"
            f"**File path (relative):** {filename}\n\n"
            f"**File Contents:**\n{contents[:5000]} \n\n"
            f"**Task:** Provide a clear, concise summary of this file's contents."
        )

        summary_response: FileSummaryResponse = self.generate_with_schema_action(
            schema=FileSummaryResponse,
            prompt=summarization_prompt,
            mode=mode
        )

        if mode == "dev":
            display_in_panel(
            f"Thoughts on {filename}:\n\n{summary_response.thoughts}",
            title="System Message",
            padding_left=10,
            padding_right=10
            ) 
            
        # Step 4: Display final summary in a system message panel
        summary = f"📄 Summary of {filename}:\n\n{summary_response.summary}"
        display_in_panel(
            summary,
            title="System Message",
            padding_left=10,
            padding_right=10
        )
        
        # add action to agent message history
        self.agent.history.append({"role": "assistant-action", "content": summary})

        return summary_response
