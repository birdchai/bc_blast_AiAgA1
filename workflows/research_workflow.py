from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken


async def run_research_workflow(
    question,
    planner,
    critic,
    tool_result=None
):

    # -------------------------
    # Inject tool result
    # -------------------------
    if tool_result:
        question = (
            f"{question}\n\n"
            f"Tool output:\n{tool_result}"
        )

    # -------------------------
    # Planner v1
    # -------------------------
    planner_response = await planner.on_messages(
        [TextMessage(content=question, source="user")],
        cancellation_token=CancellationToken()
    )

    planner_v1 = planner_response.chat_message.content

    # -------------------------
    # Critic
    # -------------------------
    critic_prompt = (
        "Review this explanation and identify scientific weaknesses:\n\n"
        + planner_v1
    )

    critic_response = await critic.on_messages(
        [TextMessage(content=critic_prompt, source="user")],
        cancellation_token=CancellationToken()
    )

    critic_feedback = critic_response.chat_message.content

    # -------------------------
    # Refinement
    # -------------------------
    refine_prompt = (
        "Improve the explanation using this feedback.\n\n"
        "Original:\n"
        + planner_v1
        + "\n\nFeedback:\n"
        + critic_feedback
    )

    refined_response = await planner.on_messages(
        [TextMessage(content=refine_prompt, source="user")],
        cancellation_token=CancellationToken()
    )

    planner_v2 = refined_response.chat_message.content

    return planner_v1, critic_feedback, planner_v2