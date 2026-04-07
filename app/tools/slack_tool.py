from typing import Optional, List, Dict, Any, List
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _get_slack_client() -> AsyncWebClient:
    return AsyncWebClient(token=settings.slack_bot_token)


async def send_slack_message(
    async def send_slack_message(
    message: str,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a message to a Slack channel.

    Args:
        message: Plain text fallback message
        channel: Slack channel name or ID (e.g. '#general' or 'C12345')
        blocks: Optional Slack Block Kit blocks for rich formatting
        thread_ts: Optional thread timestamp to reply in a thread

    Returns:
        dict with ts (message timestamp), channel, and status
    """
    try:
        client = _get_slack_client()
        target_channel = channel or settings.slack_default_channel

       response = await client.chat_postMessage(
            channel=target_channel,
            text=message,
        )

        logger.info("slack_message_sent", channel=target_channel, ts=response["ts"])
        return {
            "success": True,
            "ts": response["ts"],
            "channel": response["channel"],
        }
    except SlackApiError as e:
        logger.error("slack_message_failed", error=str(e.response["error"]))
        return {"success": False, "error": e.response["error"]}
    except Exception as e:
        logger.error("slack_message_failed", error=str(e))
        return {"success": False, "error": str(e)}


async def send_workflow_summary_to_slack(
    workflow_id: str,
    user_request: str,
    results: Dict[str, Any],
    channel: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a rich Slack summary of a completed workflow using Block Kit.

    Args:
        workflow_id: The workflow trace ID
        user_request: Original user request
        results: Aggregated results from all agents
        channel: Target channel

    Returns:
        Slack send result
    """
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Nexus AI — Workflow Complete"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Request:* {user_request}\n*Workflow ID:* `{workflow_id}`",
            },
        },
        {"type": "divider"},
    ]

    # Add per-agent result sections
    agent_icons = {
        "calendar_agent": "📅",
        "task_agent": "✅",
        "notes_agent": "📝",
        "notification_agent": "🔔",
        "memory_agent": "🧠",
    }

    for agent_name, agent_result in results.get("agent_results", {}).items():
        icon = agent_icons.get(agent_name, "🤖")
        status = "Success" if agent_result.get("success") else "Failed"
        summary = agent_result.get("summary", "No summary")
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} *{agent_name.replace('_', ' ').title()}* — {status}\n{summary}",
                },
            }
        )

    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Completed in {results.get('duration_ms', 0)}ms • {len(results.get('agent_results', {}))} agents",
                }
            ],
        }
    )

    return await send_slack_message(
        message=f"Nexus AI workflow completed: {user_request}",
        channel=channel,
        blocks=blocks,
    )
