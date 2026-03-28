"""Agent card for the Requirements A2A agent."""

from a2a.types import AgentCard

design_agent_card = AgentCard(
    name="desogm_agent",
    url="http://localhost:8003",
    description=(
        "An expert software architect agent with experience in software architecture and design."
        " Creates and documents a software design from the provided Software Requirements"
        " Specification (SRS) using the agent tools available."
    ),
    version="1.0.0",
    capabilities={},
    skills=[
        {
            "id": "designer_agent_tool",
            "name": "Software Designer agent tool",
            "description": "List system architecture, file structure, and component design",
            "tags": ["design", "software-design", "readmas"],
        },
        {
            "id": "documenter_agent_tool",
            "name": "Software Design Documenter agent tool",
            "description": (
                "Documents requirements summary, system architecture, file structure, class and"
                " sequence diagrams"
            ),
            "tags": ["design", "documentation", "readmas"],
        },
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    supports_authenticated_extended_card=False,
)
