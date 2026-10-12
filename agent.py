import os
from composio import Composio
from agents import Agent, HostedMCPTool
from dotenv import load_dotenv

load_dotenv()

composio = Composio(
    api_key=os.getenv("COMPOSIO_API_KEY")
)

SYSTEM_PROMPT = """
You are a helpful AI assistant.

Use the available Composio MCP tools whenever they are required
to complete the user's request.

Before using a tool, carefully understand the user's request
and select the appropriate tool.

Do not use tools unnecessarily.

Do not claim that an action was completed unless the tool
confirms that it was completed.

If a required Composio integration is not connected and
Composio provides a connection URL, you MUST return the
connection information in this exact JSON structure:

{
    "required_connection": true,
    "button_link": "<connection_url>",
    "service": "<service_name>",
    "message": "<short message for the user>"
}

If no connection is required, return:

{
    "required_connection": false,
    "button_link": null,
    "service": null,
    "message": "<normal assistant response>"
}

Never put Markdown around this JSON.
Never invent a connection URL.
Only use a connection URL returned by Composio.
"""



def create_agent(user_id:str) -> Agent:
    session=composio.sessions.create( 
            user_id=user_id,
            mcp=True
        )
    
 
    mcp_tool = HostedMCPTool(
        tool_config={
            "type": "mcp",
            "server_label": "composio",
            "server_url": session.mcp.url,
            "headers": session.mcp.headers,
            "require_approval": "never",
        }
    )

    agent=Agent(
        name="BestAssistant",
        instructions=SYSTEM_PROMPT,
        model= os.getenv("MODEL"),
        tools=[mcp_tool]
    )
    
    return agent







