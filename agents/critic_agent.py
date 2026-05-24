from autogen_agentchat.agents import AssistantAgent


def create_critic(model_client):

    return AssistantAgent(
        name="critic",
        model_client=model_client,
        system_message=(
            "You are a scientific reviewer.\n"
            "Identify missing mechanisms, assumptions, and weaknesses."
        )
    )