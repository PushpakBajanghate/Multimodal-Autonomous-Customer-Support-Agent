"""
Integration tests for the LangGraph Autonomous Agent State Machine.
Verifies state transitions, planning, ambiguity branching, and validation routing.
"""

import pytest
from app.agent.graph import agent_graph, build_agent_graph, AgentState
from app.agent.schemas import IntentType


def test_order_tracking_full_graph_trajectory():
    """
    Runs a complete ORDER_TRACKING request through the LangGraph agent state machine
    and asserts that each node transition occurs in the strict canonical order.
    """
    initial_state: AgentState = {
        "customer_id": 1,
        "channel": "chat",
        "raw_input": "Where is my order #1042? Please track it.",
        "conversation_history": [],
        "trajectory": []
    }

    # Execute graph
    final_state = agent_graph.invoke(initial_state)

    # 1. Assert state populated correctly
    assert final_state["normalized_input"] == "Where is my order #1042? Please track it."
    assert final_state["intent"] == IntentType.ORDER_TRACKING
    assert final_state["entities"]["order_id"] == 1042
    assert final_state["is_ambiguous"] is False

    # 2. Assert explicit ordered action plan was generated
    assert len(final_state["plan"]) >= 3
    assert final_state["plan"][0]["step"] == 1
    assert "tracking" in final_state["plan"][1]["action"]

    # 3. Assert tool execution and validation
    assert final_state["selected_tool"] == "get_order_tracking_tool"
    assert final_state["tool_results"]["status"] == "success"
    assert final_state["needs_escalation"] is False

    # 4. Assert final synthesized response
    assert "1042" in final_state["final_response"]
    assert "Carrier" in final_state["final_response"] or "FedEx" in final_state["final_response"]

    # 5. Assert Exact Ordered State Trajectory
    expected_trajectory = [
        "normalize_input",
        "load_memory",
        "classify_intent_entities",
        "check_ambiguity",
        "plan_actions",
        "select_tool",
        "execute_tool",
        "validate_result",
        "generate_response",
        "log_interaction"
    ]
    assert final_state["trajectory"] == expected_trajectory, (
        f"State transition trajectory mismatch.\nGot: {final_state['trajectory']}\nExpected: {expected_trajectory}"
    )


def test_ambiguous_inquiry_branches_to_clarification():
    """
    Tests that an incomplete request (e.g. missing order_id) correctly branches
    to clarification_question instead of executing tools.
    """
    initial_state: AgentState = {
        "customer_id": 1,
        "channel": "chat",
        "raw_input": "mera order cancel karna hai",  # Ambiguous: no order_id
        "conversation_history": [],
        "trajectory": []
    }

    final_state = agent_graph.invoke(initial_state)

    assert final_state["intent"] == IntentType.ORDER_CANCELLATION
    assert final_state["is_ambiguous"] is True
    assert "order_id" in final_state["missing_entities"]
    assert final_state.get("selected_tool") is None or "execute_tool" not in final_state["trajectory"]

    # Trajectory must branch to clarification_question
    expected_trajectory = [
        "normalize_input",
        "load_memory",
        "classify_intent_entities",
        "check_ambiguity",
        "clarification_question",
        "log_interaction"
    ]
    assert final_state["trajectory"] == expected_trajectory


def test_tool_failure_branches_to_escalation():
    """
    Tests that a tool validation error or policy violation routes to human escalation.
    """
    # Build customized graph instance with failing tool for test
    from langgraph.graph import StateGraph, START, END
    from app.agent.graph import (
        normalize_input, load_memory, classify_intent_entities,
        check_ambiguity, clarification_question, plan_actions,
        select_tool, validate_result, escalate, generate_response,
        log_interaction, route_after_ambiguity_check, route_after_validation
    )

    def failing_tool_node(state: AgentState):
        trajectory = list(state.get("trajectory", []))
        trajectory.append("execute_tool")
        return {
            "tool_results": {"status": "error", "error": "Order #9999 is blocked due to security alert."},
            "trajectory": trajectory
        }

    graph = StateGraph(AgentState)
    graph.add_node("normalize_input", normalize_input)
    graph.add_node("load_memory", load_memory)
    graph.add_node("classify_intent_entities", classify_intent_entities)
    graph.add_node("check_ambiguity", check_ambiguity)
    graph.add_node("clarification_question", clarification_question)
    graph.add_node("plan_actions", plan_actions)
    graph.add_node("select_tool", select_tool)
    graph.add_node("execute_tool", failing_tool_node)
    graph.add_node("validate_result", validate_result)
    graph.add_node("escalate", escalate)
    graph.add_node("generate_response", generate_response)
    graph.add_node("log_interaction", log_interaction)

    graph.add_edge(START, "normalize_input")
    graph.add_edge("normalize_input", "load_memory")
    graph.add_edge("load_memory", "classify_intent_entities")
    graph.add_edge("classify_intent_entities", "check_ambiguity")
    graph.add_conditional_edges("check_ambiguity", route_after_ambiguity_check, {
        "clarification_question": "clarification_question",
        "plan_actions": "plan_actions"
    })
    graph.add_edge("clarification_question", "log_interaction")
    graph.add_edge("plan_actions", "select_tool")
    graph.add_edge("select_tool", "execute_tool")
    graph.add_edge("execute_tool", "validate_result")
    graph.add_conditional_edges("validate_result", route_after_validation, {
        "escalate": "escalate",
        "generate_response": "generate_response"
    })
    graph.add_edge("escalate", "log_interaction")
    graph.add_edge("generate_response", "log_interaction")
    graph.add_edge("log_interaction", END)

    compiled = graph.compile()

    initial_state: AgentState = {
        "customer_id": 1,
        "channel": "chat",
        "raw_input": "Track order #9999",
        "conversation_history": [],
        "trajectory": []
    }

    final_state = compiled.invoke(initial_state)

    assert final_state["needs_escalation"] is True
    assert "escalating" in final_state["final_response"].lower()

    expected_trajectory = [
        "normalize_input",
        "load_memory",
        "classify_intent_entities",
        "check_ambiguity",
        "plan_actions",
        "select_tool",
        "execute_tool",
        "validate_result",
        "escalate",
        "log_interaction"
    ]
    assert final_state["trajectory"] == expected_trajectory
