import os
from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from tools import extract_invoice_data, convert_currency, search_local_ledger
import asyncio

# 1. Load Shoots API Key securely
load_dotenv()
MORPHEUS_API_KEY = os.getenv("MORPHEUS_API_KEY")

# 2. Define the Agent's Memory State
# This dictionary gets passed between nodes. It is how your UI will read the final output.
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda a, b: a + b]
    invoice_amount: float
    invoice_currency: str
    converted_rm_amount: float
    reconciliation_status: str

# 3. Initialize the Shoots AI Brain
# We use the OpenAI wrapper but hijack the base URL to point to the decentralized Shoots network
llm = ChatOpenAI(
    model="glm-4.7-flash",
    openai_api_key=MORPHEUS_API_KEY,
    openai_api_base="https://api.mor.org/api/v1",
    temperature=0.1 
)

# 4. Define Tool Interfaces (To be built by your Data Engineer in tools.py)
# The LLM reads these docstrings to understand what tools it has available.
# def extract_invoice_data(file_path: str) -> dict:
#     """Extracts the total amount and currency from a payment proof PDF/Image."""
#     pass

# def convert_currency(amount: float, from_currency: str, to_currency: str) -> float:
#     """Converts a foreign currency amount to MYR (RM) using historical exchange rates."""
#     pass

# def search_local_ledger(converted_amount: float) -> dict:
#     """Searches the local bank ledger CSV for a matching RM deposit."""
#     pass

# Bind the tools to the LLM
tools = [extract_invoice_data, convert_currency, search_local_ledger]
llm_with_tools = llm.bind_tools(tools)

# 5. Core Logic Node (The "Close Match" Discrepancy Override)
def run_agent(state: AgentState):
    """The brain of the agent. Evaluates state and decides next action."""
    messages = state.get('messages', [])
    
    # Inject the persona and the hackathon-winning discrepancy logic
    system_prompt = SystemMessage(content="""
            You are a Global Treasury Reconciliation Agent. Your job is to match foreign invoices to local RM bank statements.
            
            CRITICAL RULE 1: Always respect the tolerance threshold provided by the user. If the variance is within that threshold, 
            do not fail the match. Mark it as 'Matched with Fee Variance' and log the exact fee percentage.
            
            CRITICAL RULE 2: When calling the search_local_ledger tool, you MUST explicitly pass the extracted invoice_id. Never leave it null.
            """)
    
    # Ensure the system prompt is always guiding the agent
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [system_prompt] + messages
        
    # The agent thinks and decides whether to use a tool or return a final answer
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 6. Build and Compile the LangGraph Workflow
workflow = StateGraph(AgentState)

# Define the Tool Executor Node
tool_node = ToolNode(tools)

# Define conditional edge logic
def should_continue(state: AgentState):
    """Return the next node to execute."""
    messages = state.get("messages", [])
    last_message = messages[-1]
    
    # If the LLM decided to invoke a tool, route to "tools"
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    # Otherwise, finish the loop
    return END

# Add nodes
workflow.add_node("agent", run_agent)
workflow.add_node("tools", tool_node)

# Set the entry point and routing
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)
workflow.add_edge("tools", "agent") # Autonomous loop back to agent

# Compile the graph into an executable application
app = workflow.compile()

# 7. Streaming Test Wrapper
async def run_reconciliation_test(user_prompt: str):
    """Streams the agent's thought trace step-by-step."""
    print(f"\n--- Starting Reconciliation Test ---")
    print(f"User Prompt: {user_prompt}\n")
    
    initial_state = {
        "messages": [HumanMessage(content=user_prompt)],
        "invoice_amount": 0.0,
        "invoice_currency": "",
        "converted_rm_amount": 0.0,
        "reconciliation_status": "unprocessed"
    }

    async for event in app.astream(initial_state):
        for node_name, state_update in event.items():
            print(f"--- Node: {node_name} ---")
            messages = state_update.get("messages", [])
            for msg in messages:
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    print(f"Agent called tools: {msg.tool_calls}")
                elif hasattr(msg, "content") and msg.content:
                    print(f"Agent thought/Content: {msg.content}")

if __name__ == "__main__":
    # Test the agent's autonomous looping with a specific file path
    test_prompt = "I have an invoice located at './data/invoice_001.csv'. Please extract, convert, and search the ./data/local_ledger.csv for a match."
    asyncio.run(run_reconciliation_test(test_prompt))