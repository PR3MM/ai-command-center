import os

from dotenv import load_dotenv

try:
    from .models import ModelsCorpClaude
except ImportError:
    from models import ModelsCorpClaude

load_dotenv()

def _ssl_verify() -> bool:
    v = os.getenv("MODELS_CORP_SSL_VERIFY", "true").lower()
    return v not in ("0", "false", "no")

# Private model instance (AI only, no graph types)
my_private_llm = ModelsCorpClaude(
    user_key=os.getenv("MODELS_CORP_KEY", ""),
    api_url=os.getenv("MODELS_CORP_API_URL", ""),
    verify_ssl=_ssl_verify(),
)

def invoke_llm(messages):
    """Invoke the LLM with a list of messages. Returns the AI response message."""
    return my_private_llm.invoke(messages)
