import os
from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from tools import extract_invoice_data, ocr_invoice_data, convert_currency, search_local_ledger
from workspace_tools import save_report_to_sheets, upload_invoice_to_drive
import asyncio

load_dotenv()
SHOOTS_API_KEY = os.getenv("SHOOTS_API_KEY")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda a, b: a + b]
    invoice_amount: float
    invoice_currency: str
    converted_rm_amount: float
    reconciliation_status: str

llm = ChatOpenAI(
    model="Qwen/Qwen3.5-397B-A17B-TEE",
    openai_api_key=SHOOTS_API_KEY,
    openai_api_base="https://llm.chutes.ai/v1",
    temperature=0.1 
)

tools = [
    extract_invoice_data,
    ocr_invoice_data,
    convert_currency,
    search_local_ledger,
    save_report_to_sheets,
    upload_invoice_to_drive,
]
llm_with_tools = llm.bind_tools(tools)

def run_agent(state: AgentState):
    """The brain of the agent. Evaluates state and decides next action."""
    messages = state.get('messages', [])

    system_prompt = SystemMessage(content="""
            You are a Global Treasury Reconciliation Agent. Your job is to match foreign invoices to local RM bank statements.

            OCR RULE: If the invoice is a scanned PDF or image (PNG/JPG), use the ocr_invoice_data tool to extract fields.
            WORKSPACE RULE: Use save_report_to_sheets or upload_invoice_to_drive only when the user explicitly asks.
            
            CRITICAL RULE 1: Always respect the tolerance threshold provided by the user. If the variance is within that threshold, 
            do not fail the match. Mark it as 'Matched with Fee Variance' and log the exact fee percentage.
            
            CRITICAL RULE 2: When calling the search_local_ledger tool, you MUST explicitly pass the extracted invoice_id. Never leave it null.
            
            CRITICAL RULE 3: Once you have successfully called the tools and matched the invoice (and completed any user-requested exports), you MUST STOP. Output a final text summary of the reconciliation result and DO NOT invoke any further tools! If you keep invoking tools infinitely, you will be penalized.
            """)

    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [system_prompt] + messages

    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

workflow = StateGraph(AgentState)

tool_node = ToolNode(tools)

def should_continue(state: AgentState):
    """Return the next node to execute."""
    messages = state.get("messages", [])
    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END

workflow.add_node("agent", run_agent)
workflow.add_node("tools", tool_node)

workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)
workflow.add_edge("tools", "agent")

app = workflow.compile()

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
    test_prompt = "I have an invoice located at './data/invoice_001.csv'. Please extract, convert, and search the ./data/local_ledger.csv for a match."
    asyncio.run(run_reconciliation_test(test_prompt))