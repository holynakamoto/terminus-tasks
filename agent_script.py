import os
import json

from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool


# Portkey configuration
# Use Portkey API key (not raw Anthropic key)
portkey_api_key = os.getenv("PORTKEY_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
portkey_base_url = os.getenv("ANTHROPIC_BASE_URL") or os.getenv("LLM_BASE_URL")

# Parse Portkey headers from environment (JSON string)
portkey_headers_str = os.getenv("ANTHROPIC_HEADERS")
portkey_headers = None
if portkey_headers_str:
    try:
        portkey_headers = json.loads(portkey_headers_str)
    except json.JSONDecodeError:
        print(f"Warning: Failed to parse ANTHROPIC_HEADERS as JSON: {portkey_headers_str}")

# Build LLM configuration
llm_kwargs = {
    "model": os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
    "api_key": portkey_api_key,
}

# Set base URL if provided (required for Portkey)
if portkey_base_url:
    llm_kwargs["base_url"] = portkey_base_url

# Add headers if provided (for Portkey provider/virtual key)
# The OpenHands SDK may support headers through various parameter names
# We'll try the most common ones, and if none work, the SDK will ignore them
if portkey_headers:
    import inspect
    sig = inspect.signature(LLM.__init__)
    # Check which header parameter the SDK supports
    for header_param in ['extra_headers', 'headers', 'default_headers', 'api_headers']:
        if header_param in sig.parameters:
            llm_kwargs[header_param] = portkey_headers
            break
    else:
        # If no header parameter found, print a warning but continue
        print(f"Warning: OpenHands SDK doesn't appear to support headers directly.")
        print(f"Portkey headers: {portkey_headers}")
        print(f"You may need to configure headers via ANTHROPIC_HEADERS environment variable.")

llm = LLM(**llm_kwargs)

agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
        Tool(name=TaskTrackerTool.name),
    ],
)

cwd = os.getcwd()
conversation = Conversation(agent=agent, workspace=cwd)

conversation.send_message("Write 3 facts about the current project into FACTS.txt.")
conversation.run()
print("All done!")

