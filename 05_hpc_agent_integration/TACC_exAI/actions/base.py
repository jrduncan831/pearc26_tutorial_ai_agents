from typing import TYPE_CHECKING, Optional, Type, Any
if TYPE_CHECKING:
    from ..agent import Agent

from pydantic import BaseModel
from ..structured_generation import generate_with_schema
from .tracing_helper import trace_method
from ..utils import display_in_panel


class ActionFailureException(Exception):
    pass


class Action:
    default_openinference_span_kind: str = "tool"
    description: str = "Base Action Class"

    def __init__(
        self,
        parent: Optional["Action"] = None,
        child: Optional["Action"] = None,
        tracer=None,
        agent: "Agent" = None,
    ):
        self.parent = parent
        self.child = child
        self.tracer = tracer
        self.agent = agent
        if parent:
            parent.child = self

        if self.tracer:
            span_name = f"{self.__class__.__name__} Action"
            # Wrap the *public* run entrypoint, not the hook
            self.run = trace_method(
                self.tracer,
                self.run,  # this will be the wrapper below
                span_name,
                openinference_span_kind=self.default_openinference_span_kind,
            )

    def run(self, user_input: str, mode: str) -> Any:
        """
        Public entrypoint for all actions.

        - Calls subclass hook `_run_impl`.
        - Treats `None` return as failure and dispatches to `onFailure`.
        - Lets non-None values be considered success and returned as-is.
        """
        try:
            result = self._run_impl(user_input=user_input, mode=mode)

            # Central None-as-failure policy
            if result is None:
                error_message = (
                    f"{self.__class__.__name__} returned None from _run_impl; "
                    f"treating this as an action failure."
                )
                self.onFailure(error_message)
                # onFailure raises; this return is only to satisfy type-checkers
                return None

            return result

        except ActionFailureException:
            # Already handled & logged by onFailure / onChildFailure
            raise
        except Exception as exc:
            error_message = (
                f"Unhandled exception in {self.__class__.__name__}.run: {exc}"
            )
            self.onFailure(error_message)
            # onFailure raises; this return is only to satisfy type-checkers
            return None

    def _run_impl(self, user_input: str, mode: str) -> Any:
        """
        Subclasses override this instead of `run`.

        Must return a non-None value on success.
        Returning None signals failure and will trigger onFailure.
        """
        raise NotImplementedError

    def onFailure(self, error_message: str):
        message = (
            f"Action Failure in {self.__class__.__name__}:\n{error_message}"
        )
        display_in_panel(
            message,
            title="System Message",
            padding_left=10,
            padding_right=10,
        )
        if self.agent is not None:
            self.agent.history.append(
                {"role": "assistant-action", "content": message}
            )
        raise ActionFailureException(message)

    def onChildFailure(self, child_action: "Action", error_message: str):
        message = (
            f"Child Action Failure from {child_action.__class__.__name__} "
            f"to {self.__class__.__name__}:\n{error_message}"
        )
        display_in_panel(
            message,
            title="System Message",
            padding_left=10,
            padding_right=10,
        )
        if self.agent is not None:
            self.agent.history.append(
                {"role": "assistant-action", "content": message}
            )
        raise ActionFailureException(message)

    def generate_with_schema_action(
        self,
        prompt: str,
        schema: Type[BaseModel],
        max_retries: int = 2,
        mode: str = "chat",
        model_name: Optional[str] = None,
    ):
        try:
            if model_name is None and self.agent is not None:
                model_name = self.agent.action_model_names.get(
                    self.__class__.__name__, None
                )

            result = generate_with_schema(
                prompt=prompt,
                schema=schema,
                max_retries=max_retries,
                mode=mode,
                model_name=model_name,
            )
            return result
        except Exception as exc:
            error_message = f"Error in generate_with_schema_action: {exc}"
            self.onFailure(error_message)
            return None
