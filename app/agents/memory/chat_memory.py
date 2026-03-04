import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.db_models import Message

logger = logging.getLogger(__name__)


class ChatMemory:
    """
    Enhanced conversation memory for agents.
    
    Loads messages from database and provides methods to retrieve
    context with more information than the simple history string.
    """

    def __init__(self, chat_id: UUID, db: Session, max_messages: int = 20):
        self.chat_id = chat_id
        self.db = db
        self.max_messages = max_messages
        self._messages: Optional[List[Message]] = None

    def _load_messages(self) -> List[Message]:
        """Load messages from database."""
        if self._messages is None:
            self._messages = (
                self.db.query(Message)
                .filter(Message.chat_id == self.chat_id)
                .order_by(Message.created_at.asc())
                .limit(self.max_messages)
                .all()
            )
        return self._messages

    def get_messages(self) -> List[Message]:
        """Get raw message objects."""
        return self._load_messages()

    def get_context(
        self,
        include_code: bool = True,
        include_steps: bool = True,
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
        
        if not messages:
            return "No previous conversation."
        
        context_parts = []
        
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
                        code_str = json.dumps(related_code) if isinstance(related_code, (dict, list)) else str(related_code)
                        context_parts.append(f"  [Code: {code_str}]")
                
                if include_steps:
                    steps = msg.steps
                    if steps is not None:
                        step_summary = f"  [Steps executed: {len(steps) if isinstance(steps, list) else 'N/A'}]"
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
