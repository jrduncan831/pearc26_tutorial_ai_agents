# actions/pick_action.py
from .base import Action
from ..utils import display_in_panel, build_enum, build_default_prompt
from pydantic import create_model, Field, BaseModel

class PickAction(Action):
    description = "Evaluate context and pick the most appropriate next action for the agent."
    default_openinference_span_kind: str = "chain" # sets the default span kind for tracing the run method

    def _run_impl(self, user_input: str, mode: str):
        # Available actions (other than PickAction itself)
        available_actions = self.agent.available_actions

        # Dynamically build enum for actions
        PickedActionEnum = build_enum(available_actions)

        # Dynamically build schema for structured response
        PickActionResponse = create_model(
            "PickActionResponse",
            thoughts=(str, Field(
                ..., 
                min_length=20, 
                max_length=1000,
                description="Reasoning behind selecting the action."
            )),
            picked_action=(PickedActionEnum, Field(
                ..., 
                description="The chosen action to execute."
            )),
            __base__=BaseModel
        )

        # Build structured generation prompt
        prompt = build_default_prompt(
            self.agent,
            task_description="Select the most suitable action given the most recent user input.",
            response_classes=[PickActionResponse, PickedActionEnum]
        )

        # Generation
        pick_response: PickActionResponse = self.generate_with_schema_action(  # type: ignore
            schema=PickActionResponse,
            prompt=prompt,
            mode=mode
        )

        if mode == "dev":
            display_in_panel(pick_response)

        # Execute picked action
        for a in available_actions:
            if a.__class__.__name__ == pick_response.picked_action.value:
                return a.run(self.agent, user_input, mode)

        return None
