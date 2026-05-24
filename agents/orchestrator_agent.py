from autogen_agentchat.agents import AssistantAgent


def create_orchestrator(model_client):

    orchestrator = AssistantAgent(
        name="orchestrator",
        model_client=model_client,
        system_message=(
            "You are a research orchestrator managing a plant disease "
            "analysis workflow.\n\n"
            "Your responsibilities:\n"
            "1. Decide when to use tools\n"
            "2. Coordinate planner and critic\n"
            "3. Ensure outputs include prediction + explanation\n"
        )
    )

    return orchestrator