from autogen_agentchat.agents import AssistantAgent


def create_planner(model_client):

    return AssistantAgent(
        name="planner",
        model_client=model_client,
        system_message=(
            "You are a plant disease researcher.\n"
            "Use provided epidemiological model outputs when available.\n"
            "Provide prediction and mechanistic explanation."
        )
    )