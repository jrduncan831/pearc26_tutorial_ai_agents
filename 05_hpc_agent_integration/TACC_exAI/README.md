# TACC Explainable AI Agent

The **Agent** class provides an interactive or experiment-driven AI assistant environment with session persistence, personality reloading, and a modular action pipeline. It supports **chat**, **development**, and **experiment** modes, along with full conversation history embedding into a vector store.

***

## Features

### Modes of Operation
- **Chat Mode** (`--mode chat`):  
  Standard conversational interaction between the user and the assistant.
- **Dev Mode** (`--mode dev`):  
  Like chat mode but displays more **verbose outputs**, including prompt details and response cycle timing information.
- **Experiment Mode** (`--experiment`):  
  Runs the agent non-interactively for a single evaluation turn:  
  - Uses `--prompt` if provided.  
  - Otherwise replays the most recent user input from available session history (or from a chosen session via `--session`).  
  - Returns exactly one assistant reply (also accessible programmatically since `Agent.run()` returns the last reply).  
  - No persistent state is saved—any temporary history added is discarded immediately.  

### Session Management
- Sessions are stored in `sessions/` as JSON files:
  - Contains a unique `session_id`, conversation `history`, and `last_summary`.  
- On startup:
  - New session IDs are formatted as `YYYYMMDD_HHMMSS`.
  - Past summaries are loaded across all sessions for high-level context.
  - If `--session <id>` is provided, the session history is restored, accepting raw IDs or filenames.
  - Missing or corrupt files are skipped safely.
- Sessions auto-save after every message cycle in interactive modes.
- All sessions in the `sessions/` subfolder are automatically indexed into the **conversation vectorstore** at startup.

### Personality System
- Personality source: `agent_core_personality.txt`.  
- Reloads every turn, allowing live edits while running:  
  - If file contents change, the system notifies the user and adapts.  
- Falls back to `"You are a helpful AI Assistant"` if no file exists.

### Action Pipeline
User input is processed by a series of runtime actions:
- **PickAction** – main action runner for assistant replies.
- **SwitchModeAction** – allows switching between chat and dev mid-session.
- **SummarizeAndReplyAction** – generates summaries and replies.
- **SummarizeFileAction** – produces summaries of files.
- **GenerateCodeAction** – code and programming assistance.
- **SaveSessionAction** – persists session data (invoked every cycle in interactive modes).
- **CurateKnowledgeBaseAction** – manages a wiki-style knowledge base, supporting creation, editing, and searching of wiki pages.

#### Curate Knowledge Base Action
The **CurateKnowledgeBaseAction** enables the agent to manage a wiki-style knowledge base stored in the `knowledge_base/` directory. It supports the following operations:
- **Create**: Creates a new wiki page based on the user's request, including title, description, and content.
- **Edit**: Edits an existing wiki page by applying changes specified by the user.
- **Search**: Searches the knowledge base for relevant wiki pages based on the user's query and provides a concise answer.

The knowledge base is automatically indexed into a vector store (`wiki_pages.pkl` in `vectorstores/`), allowing for efficient searching. When a wiki page is created or edited, an HTML representation is also generated in the `knowledge_base_html/` directory for easy access.

### History Vector Store
- Embedding-based conversation **vector store** is maintained in `vectorstores/full_history.pkl`.
- Full rebuild runs if:
  - The vector store file does not exist,
  - Or the file exists but is empty,
  - Or the saved entries cannot be loaded.
- Rebuild logic:
  - Extracts all messages from all past session files in the `sessions/` subfolder.
  - Appends them to the global indexed store, keyed by session IDs.
- Adds new messages (user, assistant, assistant-action) in real time during interactive use.

### Input and Display System
- Input handled by `get_user_input()` from `user_input_handler.py`.
  - Supports pasting clipboard contents into the input by typing `#paste#`.
- All messages displayed with `utils.display_in_panel()`:
  - User → “You” panel (left-padded).
  - Assistant → “Assistant” panel (right-padded).
  - System/other roles → panels with role-named headers.
- System indicators include:
  - Personality updates (`System Message`).
  - Cycle timing in dev mode (`System Timer`).

### Greeting and Exit Behavior
- On launch, displays a greeting code-block:  
  ```
  Agent Initialized
  ```
- Exit triggers: typing `quit`, `exit`, or `bye`.
  - Displays a formatted farewell code-block:  
    ```
    Goodbye 👋
    ```
  - Saves session before shutdown.

### Structured Generation Backend Configuration
The agent uses a structured generation backend to handle requests for LLM-based structured output. The backend communication is configured as follows:
- The agent supports two backends: an OpenAI-compatible backend and a local Ollama backend.
- To use the OpenAI-compatible backend, set the following environment variables:
  - `EXAI_API_BASE`: The base URL of the OpenAI-compatible API.
  - `EXAI_API_KEY`: The API key for the OpenAI-compatible API.
- The default model for the OpenAI-compatible backend is set to `Llama-4-Maverick-17B-128E-Instruct` at the top of the `structured_generation.py` script.
- The default model for the Ollama backend is set to `qwen3:4b` at the top of the `structured_generation.py` script.
- By default, the agent will attempt to use the OpenAI-compatible backend and model. If the request fails, it will fall back to the local Ollama backend.
- Generation requests can specify a specific model to use with the Ollama backend by passing the `model_name` parameter to the `generate_with_schema` function.

***

## Command Line Usage

```bash
python agent.py [OPTIONS]
```

### Options
- `--mode {chat,dev}`  
  Select interaction mode (default: `dev`).
- `--session SESSION_ID`  
  Resume from a saved session ID or JSON file (usable in both interactive and experiment modes).
- `--experiment`  
  Run in one-shot experiment mode (no state persisted).
- `--prompt PROMPT`  
  Supply a custom prompt for experiment runs (takes precedence over past history).
- `--force-ollama`  
  Force the use of the local Ollama backend for structured generation tasks.
- `--data-dir`
  Option to pass path (str) to directory containting data to be mounted in docker container

***

## Example Workflows

### 1. Start development mode with verbose prompts and timing
```bash
python agent.py --mode dev
```

### 2. Continue a prior conversation
```bash
python agent.py --mode chat --session 20250929_174200
```

### 3. Run a single-shot experiment with a custom prompt
```bash
python agent.py --experiment --prompt "Summarize this research paper abstract on plasma turbulence."
```

### 4. Replay the last user prompt from history in experiment mode
```bash
python agent.py --experiment
```

### 5. Replay with context from a specific session in experiment mode
```bash
python agent.py --experiment --session 20250929_174200
```

### 6. Update assistant’s core behavior during runtime
Edit `agent_core_personality.txt`. The agent will detect the change and emit:
```
⚡ AI: My core personality file has been updated, and I’ll adapt my responses accordingly.
```

### 7. Create or edit a wiki page in the knowledge base
```
You: Create a new wiki page about the TACC Explainable AI Agent.
```
or
```
You: Edit the wiki page about the TACC Explainable AI Agent to include more details about its features.
```

### 8. Search the knowledge base
```
You: Search for information about the TACC Explainable AI Agent in the knowledge base.
```

***

## File Structure

| Path                            | Description                                                                                      |
|----------------------------------|--------------------------------------------------------------------------------------------------|
| `agent.py`                      | Main entry point and full Agent class.                                                           |
| `sessions/`                     | Saved JSON conversation logs; all sessions are indexed into the vectorstore.                     |
| `vectorstores/`                 | Embedding-based history indexes.                                                                 |
| `agent_core_personality.txt`     | Defines adaptable base assistant text.                                                           |
| `actions/`                      | Extensible runtime action modules for agent (`pick_action.py`, `summarize_and_reply.py`, etc.).            |
| `models/`                       | Pydantic data structures for `Message` and `Summary`.                                                     |
| `utils.py`                      | Utility functions for display formatting and prompt building.                                                         |
| `user_input_handler.py`         | Custom user input processing.                                                                          |
| `history_vector_store.py`       | Builds embedding storage for text data text.                                                         |
| `structured_generation.py`      | Handles all requests for LLM-based structured output, schema validation, and backend selection.  |
| `templates/`                    | Contains dynamic prompt templates (Jinja2 format) loaded and filled at runtime for generation tasks.|
| `docker_code_executor.py` | Code for launching and executing code in a docker container. |
| `knowledge_base/`               | Directory storing wiki pages as JSON files.                                                      |
| `knowledge_base_html/`          | Directory containing HTML representations of wiki pages.                                         |


## Tracing 

You can optionally trace your interactive sessions with this agent.  Tracing is done with [Arize Phoenix](https://github.com/Arize-ai/phoenix).  

### Start the phoenix server 

You can run Phoenix locally by starting the server in your terminal:

```bash
python -m phoenix.server.main serve
```

or 

```bash 
phoenix serve
```

Alternatively you can start a phoenix session in a jupyter notebook with the following Python code.  Note the session will end when you stop the jupyter session:

```python
import phoenix as px
session = px.launch_app()
```

By default, Phoenix will start at http://localhost:6006.

### Set environment variables 

You will need to set a few enviroment varibles for tracing.  The enviroment variables you set will depend on where you host tracing data.  
Add the following environment variables to your .env file or set them in your shell before running the agent:

#### When Using Arize Pheonix Cloud

```bash
export PHOENIX_API_KEY=<your_phoenix_api_key>
export PHOENIX_COLLECTOR_ENDPOINT=<phoenix_collector_endpoint>
```

PHOENIX_API_KEY: Obtain this from your space/settings page in the Phoenix UI.
PHOENIX_COLLECTOR_ENDPOINT: Use your Phoenix instance endpoint (local: http://localhost:6006, cloud: https://app.phoenix.arize.com/s/<your-space-name>).

#### When Running Locally 

If running locally, you do not need to set the above environment variables; By default, you will use the local endpoint: http://localhost:6006.
However, you will need to specify the location of the phoenix working directory.  

The environment variable PHOENIX_WORKING_DIR specifies the directory where Arize Phoenix saves, loads, and exports its data. This directory must be accessible both by the Phoenix server and any notebook environment you use. By default, if not set, it points to ~/.phoenix/.

This is particularly useful if you want to persist data between sessions or use SQLite as the backend database in a persistent volume instead of a temporary directory. To set this environment variable do the following:

```bash
export PHOENIX_WORKING_DIR=/path/to/your/phoenix/data
```

Alternatively, you can set this in a jupyter notebook with:

```python
import os

os.environ["PHOENIX_WORKING_DIR"] = "/path/to/your/phoenix/data"

import phoenix as px
session = px.launch_app(use_temp_dir=False)  # use_temp_dir=False forces use of PHOENIX_WORKING_DIR
```

#### Tracing via command line 

Enable tracing for your agent by using the following CLI arguments when running agent.py:

```bash 
python agent.py --trace --project-name <ProjectName>
```

- `--trace` 
   Enables tracing of your application. (default: False)
- `--project-name: PROJECT_NAME` 
   Name for your tracing project (shows up in Phoenix UI).


