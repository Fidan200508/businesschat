import operator
from typing import Annotated, Sequence, TypedDict, Dict, Any, List
from langgraph.graph import StateGraph, END

# Define the state object for the graph
class AgentState(TypedDict):
    messages: Annotated[Sequence[Dict[str, str]], operator.add]
    context: Dict[str, Any]
    current_agent: str
    final_reply: str

# --- Agent Nodes ---

def risk_analyzer_node(state: AgentState):
    """Interprets the AI model's results and SHAP explanations."""
    ctx = state["context"]
    msg = state["messages"][-1]["content"].lower()
    
    analysis = "No recent analysis found. Please run a loan risk assessment first!"
    
    if ctx and ctx.get("explanations"):
        reasons = []
        for exp in ctx['explanations']:
            impact_type = "Negative" if "increases" in exp['impact'] else "Positive"
            reasons.append(f"- **{exp['feature']}**: {exp['impact']} ({impact_type} impact)")
        
        analysis = "### Risk Analysis Report\n" + "\n".join(reasons)
        if ctx.get("risk_label") == 1:
            analysis += "\n\nStatus: **High Risk**"
        else:
            analysis += "\n\nStatus: **Approved / Low Risk**"
            
    return {
        "messages": [{"role": "bot", "content": analysis}],
        "current_agent": "Risk Analyzer",
        "final_reply": analysis
    }

def strategic_advisor_node(state: AgentState):
    """Provides strategic financial advice based on the risk analysis."""
    ctx = state["context"]
    advice = "I recommend maintaining a solid liquidity ratio and keeping your credit score above 720."
    
    if ctx and ctx.get("explanations"):
        to_improve = [exp['feature'] for exp in ctx['explanations'] if "increases" in exp['impact']]
        if to_improve:
            advice = "### Strategic Recommendations\n\n"
            for feat in to_improve:
                if feat == "Debt to Equity":
                    advice += "- **Debt Optimization**: Reduce short-term liabilities to bring your D/E ratio under 2.0.\n"
                elif "Income" in feat:
                    advice += "- **Profitability**: Focus on reducing COGS to boost your Net Margin.\n"
                elif feat == "Credit Score":
                    advice += "- **Credit Repair**: Resolve any outstanding disputes to push your score higher.\n"
        else:
            advice = "Your profile is exceptionally strong. Maintain your current capital structure."

    return {
        "messages": [{"role": "bot", "content": advice}],
        "current_agent": "Strategic Advisor",
        "final_reply": advice
    }

def messenger_node(state: AgentState):
    """Handles general conversation and final formatting."""
    msg = state["messages"][-1]["content"].lower()
    
    if "hello" in msg or "hi" in msg:
        reply = "Hello! I am your Multi-Agent Financial Team. How can we assist you with your loan application today?"
    elif "field" in msg or "business" in msg:
        reply = "Currently, sectors like **Renewable Energy** and **HealthTech** are showing the lowest risk profiles in our model."
    else:
        reply = "I'm routing your request to our specialized agents..."

    return {
        "messages": [{"role": "bot", "content": reply}],
        "current_agent": "Messenger",
        "final_reply": reply
    }

# --- Graph Logic ---

def route_request(state: AgentState):
    """Determines which agent should handle the user request."""
    msg = state["messages"][-1]["content"].lower()
    
    if "why" in msg or "reason" in msg or "reject" in msg or "explain" in msg or "means" in msg:
        return "risk_analyzer"
    elif "improve" in msg or "better" in msg or "how" in msg:
        return "strategic_advisor"
    else:
        return "messenger"

# --- Define the Graph ---

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("risk_analyzer", risk_analyzer_node)
workflow.add_node("strategic_advisor", strategic_advisor_node)
workflow.add_node("messenger", messenger_node)

# Set entry point
workflow.set_conditional_entry_point(
    route_request,
    {
        "risk_analyzer": "risk_analyzer",
        "strategic_advisor": "strategic_advisor",
        "messenger": "messenger"
    }
)

# Connect everything to END
workflow.add_edge("risk_analyzer", END)
workflow.add_edge("strategic_advisor", END)
workflow.add_edge("messenger", END)

# Compile the graph
advisor_graph = workflow.compile()
