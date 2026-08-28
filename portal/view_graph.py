"""LangGraph state machine for the /view fixed interview prototype."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from portal.view_state import (
    confirm_conflict,
    initial_view_state,
    reject_conflict,
    submit_answer,
)


class ViewGraphState(TypedDict, total=False):
    stage: str
    question_index: int
    current_field: str | None
    current_question: str | None
    history: list[dict[str, Any]]
    conflict: dict[str, Any] | None
    complete: bool
    event: Literal["answer", "confirm", "reject", "reset"]
    answer: str
    codes: list[str]


def route_event(state: ViewGraphState) -> str:
    event = state.get("event")
    if event not in {"answer", "confirm", "reject", "reset"}:
        raise ValueError("Unknown /view event.")
    return event


def answer_node(state: ViewGraphState) -> ViewGraphState:
    working = _persistent_state(state)
    return submit_answer(working, state.get("answer", ""))


def confirm_node(state: ViewGraphState) -> ViewGraphState:
    working = _persistent_state(state)
    return confirm_conflict(working, state.get("codes", []))


def reject_node(state: ViewGraphState) -> ViewGraphState:
    working = _persistent_state(state)
    return reject_conflict(working)


def reset_node(_state: ViewGraphState) -> ViewGraphState:
    return initial_view_state()


def _persistent_state(state: ViewGraphState) -> ViewGraphState:
    """Strip transient event payload before persisting the workflow state."""
    return {
        "stage": state["stage"],
        "question_index": state["question_index"],
        "current_field": state.get("current_field"),
        "current_question": state.get("current_question"),
        "history": list(state.get("history", [])),
        "conflict": state.get("conflict"),
        "complete": bool(state.get("complete", False)),
    }


def create_view_graph():
    workflow = StateGraph(ViewGraphState)
    workflow.add_node("route_event", lambda state: {})
    workflow.add_node("answer", answer_node)
    workflow.add_node("confirm", confirm_node)
    workflow.add_node("reject", reject_node)
    workflow.add_node("reset", reset_node)

    workflow.set_entry_point("route_event")
    workflow.add_conditional_edges(
        "route_event",
        route_event,
        {
            "answer": "answer",
            "confirm": "confirm",
            "reject": "reject",
            "reset": "reset",
        },
    )
    workflow.add_edge("answer", END)
    workflow.add_edge("confirm", END)
    workflow.add_edge("reject", END)
    workflow.add_edge("reset", END)
    return workflow.compile()


VIEW_GRAPH = create_view_graph()


def run_view_event(state: dict[str, Any], event: str, **payload: Any) -> dict[str, Any]:
    graph_input: ViewGraphState = {**state, "event": event, **payload}
    result = VIEW_GRAPH.invoke(graph_input)
    return _persistent_state(result)
