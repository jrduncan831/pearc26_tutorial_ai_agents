import argparse
import os
import sys

# Fix for direct execution
if __name__ == '__main__':
    # Tell Python this is part of TACC_exAI package
    __package__ = 'TACC_exAI'
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)

import datetime
import json
import time
from typing import List, Union, Optional
from .models.message import Message
from .models.summary import Summary
from .utils import display_in_panel, set_mode
from .actions.pick_action import PickAction
from .actions.summarize_and_reply import SummarizeAndReplyAction
from .actions.save_session import SaveSessionAction
from .actions.switch_mode import SwitchModeAction
from .actions.summarize_file import SummarizeFileAction
from .actions.generate_code import GenerateCodeAction
from .actions.curate_knowledge_base import CurateKnowledgeBaseAction
from .actions.create_plan import CreatePlanAction
from .actions.run_plan import RunPlanAction
from .actions.base import ActionFailureException
from .actions.generate_slurm_script import GenerateSlurmScriptAction
from .docker_code_executor import set_use_apptainer

from .user_input_handler import get_user_input
from .history_vector_store import HistoryVectorStore
from . import structured_generation
import shutil
from pathlib import Path
import pickle

class Agent:
    def __init__(
        self,
        mode: str = "chat",
        session: str = None,
        experiment: bool = False,
        experiment_prompt: Optional[str] = None,
        isolated_session: bool = False,
        no_save: bool = False,
        batch_prompts: Optional[List[str]] = None,
        data_dir: str = None,
        tracer=None,
        default_action_model_name: str = "Qwen3-32B",
        action_model_names: Optional[dict] = None,
        max_plan_retries: int = 1,
        trace_data_file=None, num_traces=3, use_vector_search=False,
        force_ollama: bool = False,
        display_mode: str = "dark",
        use_apptainer: bool = False,
    ):
        self.mode = mode
        self.experiment = experiment
        self.experiment_prompt = experiment_prompt
        self.agent_personality = None
        self.last_personality = None
        self.session_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.sessions_dir = "sessions"
        os.makedirs(self.sessions_dir, exist_ok=True)
        self.last_summary = None
        self.history = []
        self.isolated_session = isolated_session
        self.plan = None  # deprecated in favor of current_plan but kept for compatibility
        self.current_plan = None  # Current action plan being executed, if any
        self.original_user_request: Optional[str] = None
        self.replan_context: Optional[str] = None
        self.no_save = no_save  # Whether to save session and update vectorstore
        self.batch_prompts = batch_prompts  # store batch prompts for batch mode
        self.tracer = tracer
        self.max_plan_retries = max(0, int(max_plan_retries))

        
        self.trace_data_file = trace_data_file
        self.num_traces = num_traces if num_traces != -1 else float('inf')
        self.use_vector_search = use_vector_search
        self.trace_subset_seed = None
        
        # Switch display mode via global state
        if display_mode == "light":
            set_mode("light")
        else:
            set_mode("dark")  # any other value defaults to dark

        # Configure Ollama backend if requested
        if force_ollama:
            display_in_panel("⚠️ Forcing local Ollama backend", title="System Message")
        else:
            display_in_panel("Using OpenAI-compatible backend", title="System Message")
        structured_generation.set_force_local(force_ollama, default_model_name=default_action_model_name)

        # Load trace data if file provided
        if self.trace_data_file and os.path.exists(self.trace_data_file):
            try:
                with open(self.trace_data_file, "rb") as f:
                    self.trace_data = pickle.load(f)
                
                # Count UNIQUE problem_ids = actual traces
                if isinstance(self.trace_data, list) and len(self.trace_data) > 0:
                    problem_ids = {entry.get('problem_id') for entry in self.trace_data 
                                if isinstance(entry, dict) and 'problem_id' in entry}
                    num_traces = len(problem_ids)
                else:
                    num_traces = 0
                
                display_in_panel(
                    f"✅ Loaded {num_traces} traces from {self.trace_data_file}",
                    title="Trace Data Loaded",
                )
                
            except Exception as e:
                display_in_panel(
                    f"⚠️ Failed to load trace data: {e}",
                    title="Trace Data Error",
                )
                self.trace_data = None
        else:
            self.trace_data = None



        if data_dir is not None:
            path = Path(data_dir)
            if not path.is_dir():
                raise ValueError(f"{path} is not a valid directory")
            self.data_dir = path

        else:
            self.data_dir = None

        # initialize the message history embedding vectorstore
        self.vectorstore_name = "full_history"
        vs_dir = "vectorstores"
        os.makedirs(vs_dir, exist_ok=True)
        vs_path = os.path.join(vs_dir, f"{self.vectorstore_name}.pkl")

        # Not saving and no previous session data, don't create convo vectorstore
        if no_save and not session and (
            not os.path.exists(vs_path) or self.isolated_session
        ):
            self.past_summaries = []
            self.full_history_store = None
            display_in_panel(
                "```⚠️ No session specified and no existing vector store found. Running without history vector store.```",
                title="Vector Store Status",
            )

        elif self.isolated_session:
            # don't use old session summaries
            self.past_summaries = []

            # Only build vectorstore from current/selected session for querying
            self.full_history_store = HistoryVectorStore("isolated_temp_history")
            display_in_panel(
                "```Running Isolated Session Mode: building vector store only from current session.```",
                title="Vector Store Status",
            )
            if session:
                if not session.endswith(".json"):
                    session_filename = f"session_{session}.json"
                else:
                    session_filename = session
                session_path = os.path.join(self.sessions_dir, session_filename)
                if os.path.exists(session_path):
                    try:
                        with open(session_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        session_id = data.get("session_id", session_filename)
                        history = data.get("history", [])
                        self.full_history_store.build_from_history(
                            history, session_id=session_id
                        )
                    except Exception as e:
                        display_in_panel(
                            f"⚠️ Failed to load {session_filename}: {e}",
                            title="Vector Store Warning",
                        )
                # else: leave empty
            # else: new session, leave empty
            display_in_panel(
                "```Isolated session vector store ready.```",
                title="Vector Store Status",
            )
            # Load rest of session as normal
            if session:
                self.load_session(session)
        else:
            # load past session summaries for context
            self.past_summaries = self.load_past_summaries()

            # Standard: build/load main vectorstore from all session histories
            build_full_history = False
            if not os.path.exists(vs_path) or os.path.getsize(vs_path) == 0:
                build_full_history = True

            self.full_history_store = HistoryVectorStore(self.vectorstore_name)

            if build_full_history or not self.full_history_store.entries:
                display_in_panel(
                    "```Building vector store from all session histories.```",
                    title="Vector Store Status",
                )
                for fname in os.listdir(self.sessions_dir):
                    if fname.endswith(".json"):
                        try:
                            with open(
                                os.path.join(self.sessions_dir, fname),
                                "r",
                                encoding="utf-8",
                            ) as f:
                                data = json.load(f)
                            session_id = data.get("session_id", fname)
                            history = data.get("history", [])
                            self.full_history_store.build_from_history(
                                history, session_id=session_id
                            )
                        except Exception as e:
                            display_in_panel(
                                f"⚠️ Failed to load {fname}: {e}",
                                title="Vector Store Warning",
                            )
                display_in_panel(
                    "```Vector store build complete.```",
                    title="Vector Store Status",
                )
            else:
                display_in_panel(
                    "```Vector store is up-to-date.```",
                    title="Vector Store Status",
                )
            if session:
                self.load_session(session)

        # Note: actions here are the "pipeline" actions the agent runs for each prompt.
        self.actions = [
            CreatePlanAction(agent=self, tracer=self.tracer),
            RunPlanAction(agent=self, tracer=self.tracer),
        ]

        # available_actions are the concrete tool-like actions available for planning.
        self.available_actions = [
            SwitchModeAction(),
            SummarizeAndReplyAction(),
            #    SummarizeFileAction(),
            GenerateCodeAction(),
            CurateKnowledgeBaseAction(),
            # CreatePlanAction(),
            GenerateSlurmScriptAction(),
        ]
        self.save_session_action = SaveSessionAction()

        # Initialize action model names dictionary
        # Collect unique action class names from both lists
        unique_action_class_names = {
            action.__class__.__name__ for action in self.actions
        }
        unique_action_class_names.update(
            {action.__class__.__name__ for action in self.available_actions}
        )

        self.action_model_names = {
            name: default_action_model_name
            for name in unique_action_class_names
        }

        # Override with provided dictionary if any
        if action_model_names:
            for key, val in action_model_names.items():
                if key in self.action_model_names:
                    self.action_model_names[key] = val

        # Configure Apptainer vs Docker for code execution
        set_use_apptainer(use_apptainer)
        if use_apptainer:
            display_in_panel(
                "Using Apptainer for code execution",
                title="Container Backend",
            )
        else:
            display_in_panel(
                "Using Docker for code execution",
                title="Container Backend",
            )


    def run_batch(self):
        results = []
        if not self.batch_prompts:
            return results

        # Store session history and summary to reset after each prompt
        if self.history:
            initial_history = self.history.copy()
        else:
            initial_history = None
        if self.last_summary:
            initial_last_summary = self.last_summary.model_copy()
        else:
            initial_last_summary = None

        for prompt in self.batch_prompts:
            # Reset history and summary to initial state
            if initial_history:
                self.history = initial_history.copy()
            else:
                self.history = []
            if initial_last_summary:
                self.last_summary = initial_last_summary.model_copy()
            else:
                self.last_summary = None

            self.original_user_request = prompt
            self.current_plan = None
            self.replan_context = None

            # Add user prompt message
            self.history.append({"role": "user", "content": prompt})

            # Run experiment actions on prompt
            for action in self.actions:
                try:
                    action.run(prompt, self.mode)
                except ActionFailureException:
                    display_in_panel(
                        "Execution aborted due to action failure",
                        title="Action Execution Aborted",
                    )
                    break

            # Extract last assistant reply
            last_reply = None
            for msg in reversed(self.history):
                if msg.get("role") == "assistant":
                    last_reply = msg["content"]
                    break

            results.append((prompt, last_reply))

        return results

    def load_past_summaries(self) -> List[str]:
        summaries = []
        for fname in os.listdir(self.sessions_dir):
            if fname.endswith(".json"):
                try:
                    with open(
                        os.path.join(self.sessions_dir, fname),
                        "r",
                        encoding="utf-8",
                    ) as f:
                        data = json.load(f)
                        if "last_summary" in data:
                            summaries.append(data["last_summary"])
                except Exception:
                    continue
        return summaries

    def load_session(self, session: str):
        if not session.endswith(".json"):
            session_filename = f"session_{session}.json"
        else:
            session_filename = session

        path = os.path.join(self.sessions_dir, session_filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.session_id = data.get("session_id", self.session_id)
            self.history = data.get("history", [])
            last_summary = data.get("last_summary", "")
            if last_summary:
                self.last_summary = Summary(
                    thoughts=" " * 20, summary=last_summary
                )

            display_in_panel(
                f"```✅ Loaded session {self.session_id} with {len(self.history)} history items.```",
                title="Session Load Status",
            )

            # --- NEW DISPLAY LOGIC ---
            skip_last_pair = self.experiment and not self.experiment_prompt
            cutoff = len(self.history)
            if skip_last_pair and cutoff >= 2:
                cutoff -= 2

            for msg in self.history[:cutoff]:
                role = msg.get("role", "")
                content = msg.get("content", "")
                if role == "user":
                    display_in_panel(
                        content, title="You", padding_left=20
                    )
                elif role == "assistant":
                    display_in_panel(
                        content, title="Assistant", padding_right=20
                    )
                else:
                    display_in_panel(
                        content,
                        title=role.capitalize(),
                        padding_left=10,
                    )
        else:
            print(
                f"⚠️ Session file {path} not found. Starting a new session."
            )

    def save_session(self):
        if not self.history or self.no_save:
            return
        session_data = {
            "session_id": self.session_id,
            "history": self.history,
            "last_summary": self.last_summary.summary
            if self.last_summary
            else "",
        }
        outpath = os.path.join(
            self.sessions_dir, f"session_{self.session_id}.json"
        )
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    def display_user_input(self, user_input: str):
        title = "You" if self.mode == "chat" else "You (Dev Mode)"
        display_in_panel(user_input, title=title, padding_left=20)

    def display_response(self, response: Union[Message, str]):
        if isinstance(response, Message):
            display_in_panel(
                response.contents, title="Assistant", padding_right=20
            )
        else:
            display_in_panel(
                str(response), title="Assistant", padding_right=20
            )

    def cleanup_isolated_temp_history(self):
        if self.isolated_session:
            temp_vs_dir = os.path.join(
                "vectorstores", "isolated_temp_history.pkl"
            )
            # Delete the isolated_temp_history file if it exists
            if os.path.exists(temp_vs_dir):
                try:
                    os.remove(temp_vs_dir)
                    display_in_panel(
                        f"```✅ Deleted isolated temp vector store: {temp_vs_dir}```",
                        title="Temporary Session Vectorstore Cleanup",
                    )
                except Exception as e:
                    display_in_panel(
                        f"```⚠️ Failed to delete isolated temp vector store: {e}```",
                        title="Temporary Session Vectorstore Cleanup",
                    )

    def run(self):
        greeting = Message(
            thoughts=" " * 20,
            contents="```👋 How can I assist you today?```",
        )
        self.display_response(greeting)

        # Experiment mode: single non-interactive response
        if self.experiment:
            # Decide prompt
            if self.experiment_prompt:
                last_user_msg = self.experiment_prompt
            else:
                last_user_msg = None
                for msg in reversed(self.history):
                    if msg.get("role") == "user":
                        last_user_msg = msg["content"]
                        break
            if not last_user_msg:
                display_in_panel(
                    "⚠️ No user message found in history and no prompt provided.",
                    title="Agent Experiment Configuration Error",
                )
                return None

            self.history.append({"role": "user", "content": last_user_msg})
            self.original_user_request = last_user_msg
            self.current_plan = None
            self.replan_context = None

            for action in self.actions:
                try:
                    action.run(last_user_msg, self.mode)
                except ActionFailureException:
                    display_in_panel(
                        f"{action.__class__.__name__}Execution aborted due to action failure",
                        title="Action Execution Aborted",
                    )
                    break

            last_reply = None
            for msg in reversed(self.history):
                if msg.get("role") == "assistant":
                    last_reply = msg["content"]
                    break

            return last_reply

        # Default interactive loop
        last_history_len = len(self.history)
        while True:
            user_input = get_user_input(self.mode)
            start_time = time.time()
            try:
                with open(
                    "agent_core_personality.txt", "r", encoding="utf-8"
                ) as f:
                    latest_personality = f.read().strip()
            except FileNotFoundError:
                latest_personality = "You are a helpful AI Assistant"
            if (
                self.agent_personality is not None
                and latest_personality != self.agent_personality
            ):
                display_in_panel(
                    "⚡ AI: My core personality file has been updated, and I’ll adapt my responses accordingly.",
                    title="System Message",
                    padding_left=10,
                    padding_right=10,
                )
            self.agent_personality = latest_personality

            if user_input.lower() in {"quit", "exit", "bye"}:
                goodbye = Message(
                    thoughts=" " * 20,
                    contents="```Bye! Have a great day! 👋```",
                )
                self.display_response(goodbye)
                self.save_session()
                break

            self.history.append({"role": "user", "content": user_input})
            self.original_user_request = user_input
            self.current_plan = None
            self.replan_context = None

            for action in self.actions:
                try:
                    action.run(user_input, self.mode)
                except ActionFailureException:
                    display_in_panel(
                        "Execution aborted due to action failure",
                        title="Action Execution Aborted",
                    )
                    break
            self.save_session()

            new_msgs = self.history[last_history_len:]

            # Always append messages to the 'main' persisted vectorstore for future queries
            # (ensuring vectorstore exists first)
            if not self.no_save and not hasattr(
                self, "_main_persisted_vector_store"
            ):
                # Load or create on first usage
                main_vs_path = os.path.join(
                    "vectorstores", f"{self.vectorstore_name}.pkl"
                )
                self._main_persisted_vector_store = HistoryVectorStore(
                    self.vectorstore_name
                )
            if not self.no_save:
                for msg in new_msgs:
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if (
                        role in {"user", "assistant", "assistant-action"}
                        and content.strip()
                    ):
                        self.full_history_store.add_message(
                            self.session_id, role, content
                        )  # in-session vectorstore (may be isolated)
                        # Also always add to persisted vectorstore for future indexing
                    self._main_persisted_vector_store.add_message(
                        self.session_id, role, content
                    )
            last_history_len = len(self.history)

            elapsed = time.time() - start_time
            if self.mode == "dev":
                display_in_panel(
                    f"⏱️ Response cycle time: {elapsed:.2f} seconds",
                    title="System Timer",
                    padding_left=10,
                    padding_right=10,
                )

        self.cleanup_isolated_temp_history()


def main():
    parser = argparse.ArgumentParser(description="Run AI assistant.")
    parser.add_argument("--mode", choices=["chat", "dev"], default="dev")
    parser.add_argument(
        "--session",
        type=str,
        help="Continue from a specific saved session (ID or file)",
    )
    parser.add_argument(
        "--experiment",
        action="store_true",
        help="Run agent in non-interactive experiment mode",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Custom prompt to use in experiment mode (overrides session history)",
    )
    parser.add_argument(
        "--force-ollama",
        action="store_true",
        help="Force the use of the local Ollama backend (passed to Agent constructor)",
    )
    parser.add_argument(
        "--default-model",
        type=str,
        default="Qwen3-32B",
        help="model name to use for all actions (default: qwen3:32b)",
    )
    parser.add_argument(
        "--isolated-session",
        action="store_true",
        help="Only build history vectorstore from the selected/current session",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Disable saving session data and updating history vectorstore.",
    )
    parser.add_argument(
        "--batch-prompts",
        type=str,
        nargs="*",
        help="Batch prompts to run in experiment mode",
    )
    parser.add_argument(
        "--batch-file",
        type=str,
        help="File containing batch prompts (one per line) to run in experiment mode",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Optional directory path for agent data",
    )
    # arguments for tracing
    parser.add_argument(
        "--trace",
        action="store_true",
        default=False,
        help="Enable tracing of the application (default: False)",
    )
    parser.add_argument(
        "--project-name",
        type=str,
        default=None,
        help="Project name for tracing",
    )
    parser.add_argument(
        "--max-plan-retries",
        type=int,
        default=1,
        help="Maximum number of times to re-generate and re-run a plan after failures (default: 1)",
    )
    parser.add_argument(
        "--trace-data",
        type=str,
        default=None,
        help="Path to JSON file containing trace data for benchmarking"
    )
    parser.add_argument(
        "--num-traces",
        type=int,
        default=3,
        help="Number of traces to use from trace data file (-1 for all, default: 3)"
    )
    parser.add_argument(
        "--use-vector-search",
        action="store_true",
        default=False,
        help="Use vector search to select relevant traces (default: random)"
    )
    # Add display mode option
    parser.add_argument(
        "--display-mode",
        choices=["dark", "light"],
        default="dark",
        help="Color scheme: 'dark' (default) or 'light' for light terminals"
    )
    # use apptainer instead of docker for code execution (for HPC environments without docker support)
    parser.add_argument(
        "--use-apptainer",
        action="store_true",
        help="Use Apptainer instead of Docker in the docker_code_executor",
    )


    args = parser.parse_args()

    batch_prompts = None
    if args.batch_file:
        if os.path.exists(args.batch_file):
            with open(args.batch_file, "r", encoding="utf-8") as f:
                batch_prompts = [line.strip() for line in f if line.strip()]
        else:
            print(f"⚠️ Batch file {args.batch_file} not found.")
    elif args.batch_prompts:
        batch_prompts = args.batch_prompts

    if args.trace:
        from phoenix.otel import register
        from openinference.instrumentation.openai import OpenAIInstrumentor

        # os.environ['PHOENIX_WORKING_DIR'] = '/Users/jrduncan/Desktop/exAI_agent/repo/TACC_exAI/benchmarks/phoenix_data'
        tracer_provider = register(project_name=args.project_name)
        tracer = tracer_provider.get_tracer(__name__)
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
    else:
        tracer = None

    agent = Agent(
        mode=args.mode,
        session=args.session,
        experiment=args.experiment,
        experiment_prompt=args.prompt,
        isolated_session=args.isolated_session,
        no_save=args.no_save,
        batch_prompts=batch_prompts,
        data_dir=args.data_dir,
        tracer=tracer,
        max_plan_retries=args.max_plan_retries,
        trace_data_file=args.trace_data,
        num_traces=args.num_traces,
        use_vector_search=args.use_vector_search,
        force_ollama=args.force_ollama, 
        default_action_model_name=args.default_model, 
        display_mode=args.display_mode,
        use_apptainer=args.use_apptainer,
    )


    # If batch mode, run batch and print results:
    if batch_prompts:
        results = agent.run_batch()
        for i, (prompt, response) in enumerate(results):
            print(f"\n=== Batch Prompt {i + 1} ===")
            print(f"Prompt: {prompt}")
            print(f"Response: {response}")
        return

    # Otherwise continue normal run:
    if args.trace:
        with tracer.start_as_current_span(
            "AgentRun", openinference_span_kind="agent"
        ) as span:
            result = agent.run()
            span.set_attribute(result, "result from agent.run")
    else:
        result = agent.run()
    if args.experiment and result:
        print("\n=== Experiment Result ===")
        print(result)


if __name__ == "__main__":
    main()
