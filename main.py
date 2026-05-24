import asyncio
import time

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.tools import FunctionTool

from agents.planner_agent import create_planner
from agents.critic_agent import create_critic
from agents.orchestrator_agent import create_orchestrator

from workflows.research_workflow import run_research_workflow

from tools.rice_blast_model import rice_blast_risk


# -----------------------------
# Tool
# -----------------------------
rice_blast_tool = FunctionTool(
    rice_blast_risk,
    description="Estimate rice blast infection risk"
)


# -----------------------------
# Model
# -----------------------------
model_client = OpenAIChatCompletionClient(
    model="qwen2.5:7b",
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    model_info={
        "family": "openai",
        "context_window": 4096,
        "max_output_tokens": 512,
        "vision": False,
        "function_calling": False,
        "json_output": False,
        "structured_output": False
    }
)


# -----------------------------
# Create_translator
# -----------------------------
def create_translator(model_client):

    from autogen_agentchat.agents import AssistantAgent

    return AssistantAgent(
        name="translator",
        model_client=model_client,
        system_message=(
            "Translate the given text into Thai.\n"
            "Keep scientific accuracy.\n"
            "Do not add extra explanation."
        )
    )


# -----------------------------
# TransThai Function
# -----------------------------
async def translate_to_thai(text, translator):

    from autogen_agentchat.messages import TextMessage
    from autogen_core import CancellationToken

    response = await translator.on_messages(
        [TextMessage(content=text, source="user")],
        cancellation_token=CancellationToken()
    )

    return response.chat_message.content

def save_report(filename, content):

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


# -----------------------------
# Agents
# -----------------------------
planner = create_planner(model_client)
critic = create_critic(model_client)
orchestrator = create_orchestrator(model_client)
translator = create_translator(model_client)


# ------------------------------
# Main
# ------------------------------
async def main():

    start = time.time()

    # Tool execution (temporary)
    tool_result = rice_blast_risk(
        temp=27,
        humidity=92,
        rainfall=15
    )

    question = "Explain rice blast infection risk in tropical climate."

    planner_v1, critic_feedback, planner_v2 = await run_research_workflow(
        question,
        planner,
        critic,
        tool_result=tool_result
    )

    end = time.time()

    print("\n===== Planner v1 =====\n", planner_v1)
    print("\n===== Critic =====\n", critic_feedback)
    print("\n===== Planner v2 =====\n", planner_v2)
    print(f"\n⏱ Runtime: {end - start:.2f}s")

    # # -------------------------
    # # Translate to Thai
    # # -------------------------
    # planner_v1_th, critic_th, planner_v2_th = await asyncio.gather(
    #     translate_to_thai(planner_v1, translator),
    #     translate_to_thai(critic_feedback, translator),
    #     translate_to_thai(planner_v2, translator)
    # )

    # -------------------------
    # Combine report
    # -------------------------
    report = f"""===== Planner v1 =====
    {planner_v1}

    ===== Critic =====
    {critic_feedback}

    ===== Planner v2 =====
    {planner_v2}
    """

    # -------------------------
    # Save file
    # -------------------------
    import datetime

    filename = f"report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    save_report(filename, report)

    print(f"\n📄 Report saved: {filename}")

    # end_2 = time.time()
    # print(f"\n⏱ Runtime: {end_2 - start:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())