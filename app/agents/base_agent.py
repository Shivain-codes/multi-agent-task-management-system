import uuid
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

APP_NAME = "nexus_ai"


class BaseAgent(ABC):
    """
    Base class for all Nexus sub-agents.
    Each sub-agent manages its own session service (avoids the async create_session conflict).
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self._agent: Optional[LlmAgent] = None

    @abstractmethod
    def _build_agent(self) -> LlmAgent:
        """Subclasses implement this to define their tools and instructions."""
        pass

    def _get_agent(self) -> LlmAgent:
        if self._agent is None:
            self._agent = self._build_agent()
        return self._agent

    async def run(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the agent on a user message.

        Args:
            user_message: The task/instruction for this agent
            session_id: Optional shared session ID for multi-turn context
            context: Optional extra context passed to the agent as preamble

        Returns:
            dict with success, response, and agent_name
        """
        sid = session_id or uuid.uuid4().hex

        # Fresh InMemorySessionService per request avoids the async create_session issue
        session_service = InMemorySessionService()
        await session_service.create_session(
            app_name=APP_NAME, user_id="nexus_user", session_id=sid
        )

        runner = Runner(
            agent=self._get_agent(),
            app_name=APP_NAME,
            session_service=session_service,
        )

        # Prepend context if provided
        full_message = user_message
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            full_message = f"Context:\n{context_str}\n\nTask:\n{user_message}"

        try:
            from google.genai.types import Content, Part

            result_text = ""
            async for event in runner.run_async(
                user_id="nexus_user",
                session_id=sid,
                new_message=Content(parts=[Part(text=full_message)]),
            ):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            result_text += part.text

            logger.info("agent_run_complete", agent=self.name, session_id=sid)
            return {
                "success": True,
                "response": result_text,
                "agent_name": self.name,
                "session_id": sid,
            }

        except Exception as e:
            logger.error("agent_run_failed", agent=self.name, error=str(e))
            return {
                "success": False,
                "response": f"Agent {self.name} encountered an error: {str(e)}",
                "agent_name": self.name,
                "session_id": sid,
                "error": str(e),
            }
