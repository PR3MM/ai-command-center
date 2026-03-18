import requests
from typing import List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

class ModelsCorpClaude(BaseChatModel):
    # These are defaults, you can override them when you create the object
    model_id: str = "claude-sonnet-4@20250514"
    api_url: str = ""  # Set via MODELS_CORP_API_URL in env or when instantiating
    user_key: str = ""
    verify_ssl: bool = True  # Set False for internal APIs with self-signed certs

    def _generate(self, messages: List[BaseMessage], **kwargs) -> ChatResult:
        payload = {
            "anthropic_version": "vertex-2023-10-16",
            "messages": [{"role": m.type if m.type != "human" else "user", "content": m.content} for m in messages],
            "max_tokens": 1024,
            "temperature": 0
        }
        headers = {
            "Authorization": f"Bearer {self.user_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(self.api_url, json=payload, headers=headers, verify=self.verify_ssl)
        response.raise_for_status()
        data = response.json()
        
        message = AIMessage(content=data["content"][0]["text"])
        return ChatResult(generations=[ChatGeneration(message=message)])

    @property
    def _llm_type(self) -> str:
        return "models-corp-claude"