# actions/save_session.py
from .base import Action

class SaveSessionAction(Action):
    description = "Save the current session's history and summary to disk."

    def _run_impl(self, agent):
        agent.save_session()
        return "success"
