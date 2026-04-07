from typing import Optional, List, Dict, Any
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _get_slack_client() -> AsyncWebClient:
    return AsyncWebClient(token=settings.slack_bot_token)


async def send_slack_message(
    message: str,
    channel: Optional[str] = None,
    blocks: Optional[List[Dict[str, Any]]] = None,
    thread_ts: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        client = _get_slack_client()
        target_channel = channel or settings.slack_default_channel

        kwargs = {
            "channel": target_channel,
            "text": message,
        }
        if blocks:
            kwargs["blocks"] = blocks
        if thread_ts:
            kwargs["thread_ts"] = thread_ts

        response = await client.chat_postMessage(**kwargs)

        logger.info("slack_message_sent", channel=target_channel, ts=response["ts"])
        return {
            "success": True,
            "ts": response["ts"],
            "channel": response["channel"],
            "message_preview": message[:200],
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
    summary_text: str,
    channel: Optional[str] = None,
) -> Dict[str, Any]:
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
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": summary_text,
            },
        },
    ]

    return await send_slack_message(
        message=f"Nexus AI workflow completed: {user_request}",
        channel=channel,
        blocks=blocks,
    )
