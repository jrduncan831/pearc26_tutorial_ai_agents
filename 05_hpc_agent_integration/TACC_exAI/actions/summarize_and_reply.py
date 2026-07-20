# actions/summarize_and_reply.py
from ..models.summary import Summary
from ..models.message import Message
from ..utils import display_in_panel, build_default_prompt
from .base import Action

class SummarizeAndReplyAction(Action):
    description = (
        "Compose a new message to the user. "
        "Summarizes conversation and code outputs so far, then replies helpfully."
    )

    def _run_impl(self, user_input: str, mode: str):
        # Step 1: Summarize conversation
        summary_prompt = build_default_prompt(
            self.agent,
            task_description="Summarize the current conversation so far.",
            response_classes=[Summary],
            custom_history=self.agent.history,
            hide_current_summary = True
        )

        summary_response: Summary = self.generate_with_schema_action(
            schema=Summary,
            prompt=summary_prompt,
            mode=mode
        )
        self.agent.last_summary = summary_response

        if mode == "dev":
            display_in_panel(summary_response, padding_left=5, padding_right=5)

        # Step 2: Reply to user based on summary + context
        reply_prompt = build_default_prompt(
            self.agent,
            task_description="Respond helpfully to the most recent user message. If they ask for N words, respond with that many words.",
            response_classes=[Message]
        )

        response: Message = self.generate_with_schema_action(
            schema=Message,
            prompt=reply_prompt,
            mode=mode
        )

        # Update history + display
        self.agent.history.append({"role": "assistant", "content": response.contents})

        if mode == "chat":
            display_in_panel(response.contents, title="Assistant", padding_right=20)
        else:
            display_in_panel(response, padding_right=20)

        return "success"
