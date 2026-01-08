"""LangGraph configuration for Harbor framework integration."""
from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
import os
import json

# Try to import SqliteSaver if available (requires langgraph-checkpoint-sqlite package)
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    SqliteSaver = None


class AgentState(TypedDict):
    """State shared across the graph"""
    task_id: str
    task_path: str
    instruction: str
    environment_ready: bool
    current_episode: int
    max_episodes: int
    trajectory: list[dict]
    files_modified: list[str]
    test_results: dict | None
    oracle_solution: str | None
    error: str | None
    should_continue: bool
    container_name: str | None
    task_config: dict | None
    current_run: str | None


class HarborGraph:
    """LangGraph workflow for Harbor task execution."""
    
    def __init__(self, model: str = None, checkpointer=None):
        """Initialize the Harbor graph.
        
        Args:
            model: Model name to use. Defaults to environment variable or claude-sonnet-4-20250514
            checkpointer: Optional checkpointer. Defaults to in-memory SqliteSaver
        """
        # Get model from environment or use default
        model = model or os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
        
        # Configure LLM with Portkey support if available
        portkey_api_key = os.getenv("PORTKEY_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        portkey_base_url = os.getenv("ANTHROPIC_BASE_URL") or os.getenv("LLM_BASE_URL")
        
        # Parse Portkey headers if available
        portkey_headers = None
        portkey_headers_str = os.getenv("ANTHROPIC_HEADERS")
        if portkey_headers_str:
            try:
                portkey_headers = json.loads(portkey_headers_str)
            except json.JSONDecodeError:
                pass
        
        # Use OpenAI interface for Portkey, Anthropic interface otherwise
        if portkey_base_url and "portkey" in portkey_base_url.lower():
            if os.getenv("DEBUG_HARBOR_LG"):
                print(f"DEBUG: Using Portkey with OpenAI interface")
            self.llm = ChatOpenAI(
                model=model,
                api_key=portkey_api_key,
                base_url=portkey_base_url,
                default_headers=portkey_headers,
                temperature=0,
                max_tokens=4096
            )
        else:
            if os.getenv("DEBUG_HARBOR_LG"):
                print(f"DEBUG: Using direct Anthropic")
            llm_kwargs = {
                "model": model,
                "api_key": portkey_api_key,
                "temperature": 0,
            }
            if portkey_base_url:
                llm_kwargs["anthropic_api_url"] = portkey_base_url
            if portkey_headers:
                llm_kwargs["default_headers"] = portkey_headers
            
            # Debug output to see what's being passed
            if os.getenv("DEBUG_HARBOR_LG"):
                print(f"DEBUG: Initializing ChatAnthropic with kwargs: {llm_kwargs}")
            
            self.llm = ChatAnthropic(**llm_kwargs)
        # Use provided checkpointer, or default to MemorySaver
        # SqliteSaver requires langgraph-checkpoint-sqlite package which has version conflicts
        if checkpointer is None:
            self.checkpointer = MemorySaver()
        else:
            self.checkpointer = checkpointer
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        try:
            from nodes import HarborNodes
        except ImportError:
            from .nodes import HarborNodes
        
        nodes = HarborNodes(self.llm)
        
        workflow = StateGraph(AgentState)
        
        # Define nodes
        workflow.add_node("parse_task", nodes.parse_task_node)
        workflow.add_node("setup_environment", nodes.setup_environment_node)
        workflow.add_node("agent_episode", nodes.agent_episode_node)
        workflow.add_node("execute_commands", nodes.execute_commands_node)
        workflow.add_node("verify_solution", nodes.verify_solution_node)
        workflow.add_node("oracle_check", nodes.oracle_check_node)
        workflow.add_node("record_trajectory", nodes.record_trajectory_node)
        
        # Define edges
        workflow.set_entry_point("parse_task")
        workflow.add_edge("parse_task", "setup_environment")
        workflow.add_edge("setup_environment", "agent_episode")
        workflow.add_edge("agent_episode", "execute_commands")
        workflow.add_edge("execute_commands", "verify_solution")
        
        # Conditional routing after verification
        workflow.add_conditional_edges(
            "verify_solution",
            nodes.should_continue_or_end,
            {
                "continue": "record_trajectory",
                "oracle": "oracle_check",
                "end": END
            }
        )
        
        workflow.add_edge("record_trajectory", "agent_episode")
        workflow.add_edge("oracle_check", END)
        
        return workflow.compile(checkpointer=self.checkpointer)
