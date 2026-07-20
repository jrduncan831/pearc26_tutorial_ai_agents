# actions/switch_mode.py
from .base import Action
from ..utils import display_in_panel, describe_classes
from pydantic import BaseModel, Field
from enum import Enum

class ModeEnum(str, Enum):
    CHAT = "chat"
    DEV = "dev"


class ModeSwitchResponse(BaseModel):
    thoughts: str = Field(
        ...,
        min_length=20,
        max_length=1000,
        description="Reasoning behind deciding which mode the user wants to switch to."
    )
    picked_mode: ModeEnum = Field(
        ..., description="The mode the agent should switch into."
    )


class SwitchModeAction(Action):
    description = "Switch console output between chat mode prompts and verbose logging hidden and dev mode (verbose debug). Only switch this if explicitly asked."
    default_openinference_span_kind: str = "chain" # sets the default span kind for tracing the run method

    def _run_impl(self, user_input: str, mode: str):

        # Build structured generation prompt
        prompt = (
            "Decide which mode the user wants to switch to based off their message:\n\n"
            f"**User message:**\n{user_input}\n\n"
            "**Modes available**\n"
            "- chat: Friendly assistant, conversational responses.\n"
            "- dev: Verbose debug output with structured panels.\n\n"
            "**Response Structure Descriptions:**\n"
            + describe_classes([ModeSwitchResponse])
        )

        # Perform structured generation
        response: ModeSwitchResponse = self.generate_with_schema_action(
            schema=ModeSwitchResponse,
            prompt=prompt,
            mode=mode
        )

        if self.agent.mode == "dev":
            display_in_panel(response, title="Mode Decision", padding_left=5, padding_right=5)
            
        # Apply the mode switch
        self.agent.mode = response.picked_mode.value

        display_in_panel(
            f"Switched mode to {self.agent.mode}",
            title="System Message",
            padding_left=5,
            padding_right=5
        )

        # add action to agent message history
        self.agent.history.append({"role": "assistant-action", "content": f"Switched mode to {self.agent.mode}"})
        return True
