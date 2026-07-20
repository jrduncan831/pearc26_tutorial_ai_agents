# run_agent_example.py

from .agent import Agent

session_id = "20250929_173041"

def run_from_session():
    print("\n=== Starting Agent from session, rerunning last query ===")
    # Use an existing session ID, e.g., "20250929_183055"
    # Replace this with the ID of one of your saved sessions in /sessions/

    agent = Agent(
        session=session_id,
        experiment=True,
        experiment_prompt=None
    )
    result = agent.run()
    if result:
        print("\nExperiment Output (no custom prompt):")
        print(result)


def run_with_custom_prompt():
    print("\n=== Running Agent from specific session with a custom prompt ===")

    # Provide your own direct prompt
    custom_prompt = "Generate python code to compute the Fibonacci sequence up to 100."
    
    agent = Agent(
        session=session_id,
        experiment=True,
        experiment_prompt=custom_prompt
    )
    result = agent.run()
    if result:
        print("\nExperiment Output (with custom prompt):")
        print(result)


def run_with_global_model_override():
    print("\n=== Running Agent with global default model override ===")
    # Set the default model globally for all actions
    agent = Agent(
        experiment=True,
        experiment_prompt="Explain the theory of relativity in simple terms.",
        default_action_model_name="Llama-4-Maverick-17B-128E-Instruct"
    )
    result = agent.run()
    if result:
        print("\nExperiment Output (global model override):")
        print(result)


def run_with_action_specific_model_override():
    print("\n=== Running Agent with model override for SummarizeAndReplyAction only ===")
    # Override only SummarizeAndReplyAction model, keep global default as usual
    action_model_names = {
        "SummarizeAndReplyAction": "Llama-4-Maverick-17B-128E-Instruct"
    }
    agent = Agent(
        experiment=True,
        experiment_prompt="Provide a summary of climate change impacts.",
        default_action_model_name="Qwen3-32B",  # this is the default normally used
        action_model_names=action_model_names
    )
    result = agent.run()
    if result:
        print("\nExperiment Output (action-specific model override):")
        print(result)


if __name__ == "__main__":
    # Example 1: Session only
    run_from_session()

    # Example 2: Session + Custom Prompt
    run_with_custom_prompt()

    # Example 3: Global Default Model Override
    run_with_global_model_override()

    # Example 4: Model Override for SummarizeAndReplyAction Only
    run_with_action_specific_model_override()
