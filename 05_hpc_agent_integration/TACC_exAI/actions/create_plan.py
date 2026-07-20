# actions/create_plan.py
from .base import Action
from ..utils import display_in_panel, build_enum, describe_classes
from outlines import Template
from pydantic import create_model, Field, BaseModel
import os

from .tracing_helper import trace_method

create_plan_template = Template.from_file(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "create_plan_template.txt",
    )
)


class CreatePlanAction(Action):
    description = (
        "Create a plan to solve the user's request using the available actions."
    )
    default_openinference_span_kind: str = "chain"  # sets the default span kind for tracing the run method

    def _build_dynamic_models(self):
        """
        Build the dynamic enum and plan models that the LLM will populate.
        This is factored out so it can be reused for initial plan and replans.
        """
        available_actions = self.agent.available_actions

        # Build the dynamic enum from available actions (same as PickAction)
        DynamicActionEnum = build_enum(available_actions)

        # Create dynamic PlanStep with action_name using DynamicActionEnum
        DynamicPlanStep = create_model(
            "DynamicPlanStep",
            step_index=(
                int,
                Field(..., description="Index of the step in the plan"),
            ),
            step_name=(
                str,
                Field(..., description="Name of the step"),
            ),
            step_description=(
                str,
                Field(..., description="Description of the step"),
            ),
            action_name=(
                DynamicActionEnum,
                Field(
                    ...,
                    description=(
                        "Name of the action to be executed in this step"
                    ),
                ),
            ),
            custom_user_input=(
                str,
                Field(
                    ...,
                    description=(
                        "A detailed prompt for this step's action. "
                        "It should include all necessary information so the action can complete successfully."
                    ),
                ),
            ),
            __base__=BaseModel,
        )

        # Create dynamic Plan WITHOUT user_request field for LLM generation
        DynamicPlanForLLM = create_model(
            "DynamicPlanForLLM",
            thoughts=(
                str,
                Field(
                    ...,
                    description="Agent's thoughts on how to solve the request",
                ),
            ),
            overall_plan_goal=(
                str,
                Field(..., description="Overall goal of the plan"),
            ),
            plan_description=(
                str,
                Field(..., description="Description of the plan"),
            ),
            plan_steps=(
                list[DynamicPlanStep],
                Field(..., description="List of steps in the plan"),
            ),
            __base__=BaseModel,
        )

        # Full plan model that includes the original user request
        DynamicPlan = create_model(
            "DynamicPlan",
            user_request=(
                str,
                Field(..., description="Original user request"),
            ),
            thoughts=(
                str,
                Field(
                    ...,
                    description="Agent's thoughts on how to solve the request",
                ),
            ),
            overall_plan_goal=(
                str,
                Field(..., description="Overall goal of the plan"),
            ),
            plan_description=(
                str,
                Field(..., description="Description of the plan"),
            ),
            plan_steps=(
                list[DynamicPlanStep],
                Field(..., description="List of steps in the plan"),
            ),
            __base__=BaseModel,
        )

        return DynamicActionEnum, DynamicPlanStep, DynamicPlanForLLM, DynamicPlan

    def _build_prompt(
        self,
        user_request: str,
        DynamicActionEnum,
        DynamicPlanForLLM,
        DynamicPlanStep,
        extra_replan_context: str | None = None,
    ) -> str:
        """
        Build the prompt for initial planning or replanning.
        `extra_replan_context` can contain information about the failed plan,
        history, and failure message.
        """
        # Describe available actions and schema (exclude user_request since it's filled later)
        actions_desc = describe_classes([DynamicActionEnum])
        response_structure_desc = describe_classes(
            [DynamicPlanForLLM, DynamicPlanStep, DynamicActionEnum]
        )

        base_user_request = user_request

        if extra_replan_context:
            # For replanning, provide the old plan, history, etc.
            # The template can condition on this additional context.
            prompt = create_plan_template(
                user_request=base_user_request,
                available_actions=actions_desc,
                response_structure=response_structure_desc,
                replan_context=extra_replan_context,
            )
        else:
            prompt = create_plan_template(
                user_request=base_user_request,
                available_actions=actions_desc,
                response_structure=response_structure_desc,
            )
        return prompt

    def _run_impl(self, user_input: str, mode: str):
        """
        `user_input` here is used as the logical "user_request" for the plan,
        but for replans the caller can pass in an augmented prompt that
        includes the original request plus context about previous failures.
        """
        (
            DynamicActionEnum,
            DynamicPlanStep,
            DynamicPlanForLLM,
            DynamicPlan,
        ) = self._build_dynamic_models()

        # If the agent stored an original_user_request, prefer that as the
        # actual user_request field in the resulting plan. Otherwise fall
        # back to this call's user_input.
        if self.agent is not None and getattr(
            self.agent, "original_user_request", None
        ):
            logical_user_request = self.agent.original_user_request
        else:
            logical_user_request = user_input

        # For replans, the caller may have stored a richer context string
        # in agent.replan_context; otherwise None.
        extra_replan_context = None
        if self.agent is not None:
            extra_replan_context = getattr(self.agent, "replan_context", None)

        # Render prompt from template with dynamic descriptions
        prompt = self._build_prompt(
            user_request=logical_user_request,
            DynamicActionEnum=DynamicActionEnum,
            DynamicPlanForLLM=DynamicPlanForLLM,
            DynamicPlanStep=DynamicPlanStep,
            extra_replan_context=extra_replan_context,
        )

        # Generate the plan using the schema without user_request
        generated_response: BaseModel = self.generate_with_schema_action(
            schema=DynamicPlanForLLM,
            prompt=prompt,
            mode=mode,
        )

        # Instantiate the final plan with the original user request included
        response = DynamicPlan(
            user_request=logical_user_request,
            thoughts=generated_response.thoughts,
            overall_plan_goal=generated_response.overall_plan_goal,
            plan_description=generated_response.plan_description,
            plan_steps=generated_response.plan_steps,
        )

        # Store the plan in agent.current_plan
        if self.agent is not None:
            self.agent.current_plan = response

        if mode == "dev":
            display_in_panel(
                response, title="Created Plan", padding_right=10
            )

        # Add to agent history
        if self.agent is not None:
            self.agent.history.append(
                {"role": "assistant", "content": f"Created plan: {response}"}
            )

        return response
