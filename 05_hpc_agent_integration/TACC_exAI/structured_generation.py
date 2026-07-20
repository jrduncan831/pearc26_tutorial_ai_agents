from typing import Type, Optional, Tuple
from pydantic import BaseModel, ValidationError
import os
import traceback
from openai import OpenAI
from outlines import from_openai
from instructor import from_openai as instructor_from_openai
from .utils import display_in_panel
import traceback

# variable to hold model name
global llm_model_name

# Primary (remote) backend settings
api_key = os.getenv("EXAI_API_KEY")
base_url = os.getenv("EXAI_BASE_URL")

# Fallback (local Ollama) settings
ollama_base_url = "http://localhost:11434/v1"

_force_local = None
_last_backend = None

def _is_backend_available(base_url: str, api_key: str, model_name: str) -> Tuple[bool, Optional[str]]:
    """Check if the backend is usable by making a tiny test call."""
    try:
        test_client = OpenAI(api_key=api_key or "dummy", base_url=base_url)
        resp = test_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            temperature=0,
        )
        if resp.choices and resp.choices[0].message.content:
            return True, None
        return False, "No choices returned from response"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)}"

def _get_clients():
    """Get or reuse cached clients and configuration for structured generation."""
    global _force_local, _last_backend
    global _cached_openai_client, _cached_structured_client, _cached_chosen_backend
    global _cached_api_key, _cached_base_url, _cached_force_local_env

    # Initialize cache globals if not already present
    if "_cached_openai_client" not in globals():
        _cached_openai_client = None
        _cached_structured_client = None
        _cached_chosen_backend = None
        _cached_api_key = None
        _cached_base_url = None
        _cached_force_local_env = None

    # Read current environment configuration
    current_api_key = os.getenv("EXAI_API_KEY")
    current_base_url = os.getenv("EXAI_BASE_URL")
    current_force_local_env = os.getenv("FORCE_LOCAL_OLLAMA", "false").lower() == "true"

    # Update _force_local flag based on current environment state
    _force_local = current_force_local_env if _force_local is None else _force_local

    # Determine whether we need to rebuild based on environment changes
    rebuild_needed = False
    env_changed = (
        current_api_key != _cached_api_key
        or current_base_url != _cached_base_url
        or current_force_local_env != _cached_force_local_env
    )

    if env_changed:
        display_in_panel("[Info] Environment configuration changed, rebuilding clients.", title="Environment Config Change", padding_left=5, padding_right=5)
        rebuild_needed = True

    if rebuild_needed:
        display_in_panel("[Info] Building OpenAI and structured clients based on current configuration.", title="Building Inferencing Client", padding_left=5, padding_right=5)
        # Detect whether we can use the remote backend
        if not _force_local:
            ok, err = _is_backend_available(current_base_url, current_api_key, llm_model_name)
            if ok:
                chosen_backend = "Remote OpenAI-Compatible"
                if (
                    _last_backend != chosen_backend
                ):
                    openai_client = OpenAI(api_key=current_api_key, base_url=current_base_url)
                    structured_client = instructor_from_openai(openai_client)
            else:
                display_in_panel(
                    f"[Backend Failure] Remote model `{llm_model_name}` at `{current_base_url}` unavailable: {err}",
                    title="Backend Failure",
                    padding_left=5,
                    padding_right=5,
                )
                _force_local = True
                chosen_backend = "Local Ollama"
                openai_client = OpenAI(api_key="ollama", base_url=ollama_base_url)
                structured_client = None
                rebuild_needed = True
        else:
            chosen_backend = "Local Ollama"
            if (
                _last_backend != chosen_backend
            ):
                openai_client = OpenAI(api_key="ollama", base_url=ollama_base_url)
                structured_client = None

        # Refresh the cache
        _cached_openai_client = openai_client
        _cached_structured_client = structured_client
        _cached_chosen_backend = chosen_backend
        _cached_api_key = current_api_key
        _cached_base_url = current_base_url
        _cached_force_local_env = current_force_local_env

        display_in_panel(
            f"Using **{chosen_backend}** backend.\n\nDefault Model: `{llm_model_name}`\nBase URL: {_cached_openai_client.base_url}",
            title="Backend Selection",
            padding_left=5,
            padding_right=5,
        )
        _last_backend = chosen_backend
    else:
        # Use cached objects if available
        openai_client = _cached_openai_client
        structured_client = _cached_structured_client
        chosen_backend = _cached_chosen_backend

    return openai_client, structured_client, chosen_backend

def get_model_handler():
    """
    Return a handle to a function that can generate structured output
    using the appropriate backend based on availability.
    generate_fn(prompt, schema) returns BaseModel or str, and also raw text for validation fixes.
    """
    global llm_model_name
    openai_client, structured_client, chosen_backend = _get_clients()

    if chosen_backend.startswith("Remote OpenAI-Compatible"):
        def instructor_generate(prompt: str, schema: Type[BaseModel]) -> Tuple[BaseModel, str]:
            result = structured_client.chat.completions.create(
                model=llm_model_name,
                messages=[{"role": "user", "content": prompt}],
                response_model=schema,
            )
            # Instructor returns already validated object, get original string from its attribute if needed
            raw = result.model_dump_json() if hasattr(result, "model_dump_json") else str(result)
            return result, raw, None
        return instructor_generate

    # Local Ollama path: Outlines. Always try to return raw output (string) as well.
    def outlines_generate(prompt: str, schema: Type[BaseModel]) -> Tuple[Optional[BaseModel], str, Optional[str]]:
        """
        Takes a prompt and schema.
        Returns (parsed_result, raw_output, error_trace).
        If validation fails, parsed_result is None and error_trace contains the details.
        """

        global llm_model_name

        candidate = from_openai(openai_client, model_name=llm_model_name)
        resp = candidate(prompt, schema)
        raw = resp if isinstance(resp, str) else str(resp)
        try:
            parsed = schema.model_validate_json(raw)
            return parsed, raw, None
        except (ValidationError, ValueError) as exc:
            trace = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            return None, raw, trace

    return outlines_generate

def generate_with_schema(
    prompt: str,
    schema: Type[BaseModel],
    max_retries: int = 2,
    mode: str = "chat",
    model_name: Optional[str] = None,
) -> BaseModel:
    """
    Generate structured output using unified retry logic.
    Remote: Instructor with model_name.
    Local: Outlines with requested_model (fallback if needed).
    """
    
    # set the selected model name globally
    global llm_model_name
    llm_model_name = model_name

    schema_name = schema.__name__

    # initialize the generation function
    generate_fn = get_model_handler()
    model_info = f"Using model `{llm_model_name}` on backend `{_get_clients()[2]}`."

    if mode == "dev":
        display_in_panel(
            f"{model_info}\n\nPrompt:\n{prompt}",
            title=f"Prompt to LLM for {schema_name}",
            padding_left=5,
            padding_right=5,
        )

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            result, raw_response, error_trace = generate_fn(prompt, schema)
            if result is not None:
                return result
            last_error = error_trace or "Unknown validation error."
        except Exception as exc:
            last_error = "".join(traceback.format_exception_only(type(exc), exc)).strip()

        if mode == "dev":
            display_in_panel(
                f"Attempt {attempt} failed for {schema.__name__}. Error: {last_error}",
                title=f"Generation Error {attempt}",
                padding_left=5,
                padding_right=5,
            )

    raise ValueError(
        f"Failed to generate a valid response for {schema.__name__} "
        f"after {max_retries} attempts (using model {llm_model_name} "
        f"on backend {_get_clients()[2]}). Last error: {last_error}"
    )

def set_force_local(force_local: bool, default_model_name: str = "qwen3:30b"):
    global _force_local, llm_model_name
    llm_model_name = default_model_name
    _force_local = force_local
    _get_clients()
