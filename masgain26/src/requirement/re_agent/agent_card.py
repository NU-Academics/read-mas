"""Agent card for the Requirements A2A agent."""

from a2a.types import AgentCard

re_agent_card = AgentCard(
    name="re_agent",
    url="http://localhost:8002",
    description=(
        "An expert software requirements architect agent that creates a Software Requirement"
        " Specification (SRS) from the user input using the agent tools available."
    ),
    version="1.0.0",
    capabilities={},
    skills=[
        {
            "id": "collector_agent_tool",
            "name": "Requirements Collector agent tool",
            "description": "List functional and non-functional requirements as Json arrays",
            "tags": ["requirements", "collection", "readmas"],
        },
        {
            "id": "analyzer_agent_tool",
            "name": "Requirements Analyzer agent tool",
            "description": (
                "Lists use cases, domain classes, business rules, data model, traceability, and"
                " validation"
            ),
            "tags": ["requirements", "analysis", "readmas"],
        },
        {
            "id": "specifier_agent_tool",
            "name": "Requirements Specifier agent tool",
            "description": "Returns the Software Requirements Specification (SRS)",
            "tags": ["requirements", "specification", "readmas"],
        },
    ],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    supports_authenticated_extended_card=False,
)
