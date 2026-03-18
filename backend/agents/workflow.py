from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

try:
    from .agents import invoke_llm
except ImportError:
    from agents import invoke_llm

# LangGraph state (all graph types live here)
class State(TypedDict):
    messages: Annotated[list, add_messages]

def call_model(state: State):
    """Node: run agent on current messages and return state update."""
    return {"messages": [invoke_llm(state["messages"])]}

workflow = StateGraph(State)
workflow.add_node("agent", call_model)


workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)

app = workflow.compile()

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    result = app.invoke({"messages": [HumanMessage(content="Say hello in one sentence.")]})
    for msg in result["messages"]:
        print(f"{msg.type}: {msg.content}")
