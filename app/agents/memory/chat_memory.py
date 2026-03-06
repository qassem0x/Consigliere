import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.llm import call_llm_with_usage_async
from app.models.db_models import Message, Chat

logger = logging.getLogger(__name__)

DEFAULT_MAX_MESSAGES = 10


class ChatMemory:
    """
    Enhanced conversation memory for agents.

    Loads messages from database and provides methods to retrieve
    context with more information than the simple history string.
    """

    def __init__(
        self, chat_id: UUID, db: Session, max_messages: int = DEFAULT_MAX_MESSAGES
    ):
        self.chat_id = chat_id
        self.db = db
        self.max_messages = max_messages
        self._messages: Optional[List[Message]] = None
        self._summary: str = ""
        self._load_summary()

    def _load_summary(self) -> None:
        """Load existing summary from database."""
        chat = self.db.query(Chat).filter(Chat.id == self.chat_id).first()
        if chat and chat.summary:
            self._summary = chat.summary

    def get_summary(self) -> str:
        """Get the current conversation summary."""
        return self._summary

    async def update_summary(self, new_message: Message) -> str:
        """
        Update the rolling summary with a new message.
        Uses LLM to incrementally summarize: summarize(previous_summary + new_message).
        """
        new_content = str(new_message.content)
        if new_message.role == "assistant":
            try:
                content_dict = json.loads(new_content)
                new_content = content_dict.get("text", new_content)
            except (json.JSONDecodeError, TypeError):
                pass

        prompt = f"""You are maintaining a concise summary of a conversation. 
Given the previous summary and a new message, produce an updated summary that captures the key points.

Previous summary:
{self._summary if self._summary else "(No previous summary)"}

New message ({new_message.role}):
{new_content}

Respond with only the updated summary, no explanation or formatting."""

        try:
            result = await call_llm_with_usage_async(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout=30,
            )
            new_summary = result.get("content", "")

            chat = self.db.query(Chat).filter(Chat.id == self.chat_id).first()
            if chat:
                chat.summary = new_summary
                self.db.commit()

            self._summary = new_summary
            return new_summary
        except Exception as e:
            logger.error(f"Failed to update summary: {e}")
            return self._summary

    def _load_messages(self) -> List[Message]:
        """Load messages from database."""
        if self._messages is None:
            self._messages = (
                self.db.query(Message)
                .filter(Message.chat_id == self.chat_id)
                .order_by(Message.created_at.desc())
                .limit(self.max_messages)
                .all()
            )

        return self._messages

    def get_messages(self) -> List[Message]:
        """Get raw message objects."""
        return self._load_messages()

    def get_context(
        self,
        include_code: bool = False,
        include_steps: bool = False,
        max_text_length: Optional[int] = None,
    ) -> str:
        """
        Get conversation context as a formatted string.

        Args:
            include_code: Include executed code from related_code
            include_steps: Include execution steps info
            max_text_length: Truncate individual messages (None = no limit)
        """
        messages = self._load_messages()

        if not messages and not self._summary:
            return "No previous conversation."

        context_parts = []

        if self._summary:
            context_parts.append(f"[Summary: {self._summary}]")
            context_parts.append("")

        for msg in messages:
            role = str(msg.role).capitalize()

            if str(msg.role) == "user":
                content = str(msg.content)
                if max_text_length and len(content) > max_text_length:
                    content = content[:max_text_length] + "..."
                context_parts.append(f"{role}: {content}")

            elif str(msg.role) == "assistant":
                try:
                    content_dict = json.loads(str(msg.content))
                    text = content_dict.get("text", str(msg.content))
                except (json.JSONDecodeError, TypeError):
                    text = str(msg.content)

                if max_text_length and len(text) > max_text_length:
                    text = text[:max_text_length] + "..."

                context_parts.append(f"{role}: {text}")

                if include_code:
                    related_code = msg.related_code
                    if related_code is not None:
                        code_str = (
                            json.dumps(related_code)
                            if isinstance(related_code, (dict, list))
                            else str(related_code)
                        )
                        context_parts.append(f"  [Code: {code_str}]")

                if include_steps:
                    steps = msg.steps
                    if steps is not None:
                        step_summary = f"  [Steps executed: {json.dumps(steps) if isinstance(steps, list) else 'N/A'}]"
                        context_parts.append(step_summary)

        return "\n".join(context_parts)

    def get_recent_messages(self, count: int = 6) -> List[Message]:
        """Get the N most recent messages."""
        messages = self._load_messages()
        return messages[-count:] if len(messages) > count else messages

    def get_structured_context(self) -> Dict[str, Any]:
        """
        Get context as structured data instead of string.
        Useful for agents that want more control over formatting.
        """
        messages = self._load_messages()

        structured = []
        for msg in messages:
            entry = {
                "role": msg.role,
                "content": str(msg.content),
            }

            if msg.related_code is not None:
                entry["code"] = msg.related_code

            if msg.steps is not None:
                entry["steps"] = msg.steps

            if msg.artifacts is not None:
                entry["artifacts"] = msg.artifacts

            structured.append(entry)

        return {"messages": structured, "count": len(structured)}

    def invalidate(self):
        """Clear cached messages (call after new message is added)."""
        self._messages = None
        self._load_summary()
