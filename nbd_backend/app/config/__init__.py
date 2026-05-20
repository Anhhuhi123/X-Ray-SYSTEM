import os
import shutil
from pathlib import Path
from typing import Final

import yaml
from chonkie import AutoEmbeddings, CodeChunker, RecursiveChunker
from dotenv import load_dotenv
from rerankers import Reranker

# Get the base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env_file = BASE_DIR / ".env"
load_dotenv(env_file)

_LANGSMITH_DEFAULT_ENDPOINT: Final[str] = "https://api.smith.langchain.com"


def initialize_langsmith() -> bool:
    """Normalize LangSmith-related environment variables when tracing is enabled.

    Returns True when tracing is enabled and the environment is ready for LangSmith,
    otherwise returns False and leaves runtime behavior unchanged.
    """
    tracing_enabled = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    api_key = os.getenv("LANGSMITH_API_KEY", "").strip()

    if not tracing_enabled or not api_key:
        return False

    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGSMITH_ENDPOINT", _LANGSMITH_DEFAULT_ENDPOINT)
    os.environ.setdefault("LANGSMITH_PROJECT", "nfd")
    return True


def is_ffmpeg_installed():
    """
    Check if ffmpeg is installed on the current system.

    Returns:
        bool: True if ffmpeg is installed, False otherwise.
    """
    return shutil.which("ffmpeg") is not None


def load_global_llm_configs():
    """
    Load global LLM configurations from YAML file.
    Falls back to example file if main file doesn't exist.

    Returns:
        list: List of global LLM config dictionaries, or empty list if file doesn't exist
    """
    # Try main config file first
    global_config_file = BASE_DIR / "app" / "config" / "global_llm_config.yaml"

    if not global_config_file.exists():
        # No global configs available
        return []

    try:
        with open(global_config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("global_llm_configs", [])
    except Exception as e:
        print(f"Warning: Failed to load global LLM configs: {e}")
        return []


def load_router_settings():
    """
    Load router settings for Auto mode from YAML file.
    Falls back to default settings if not found.

    Returns:
        dict: Router settings dictionary
    """
    # Default router settings
    default_settings = {
        "routing_strategy": "usage-based-routing",
        "num_retries": 3,
        "allowed_fails": 3,
        "cooldown_time": 60,
    }

    # Try main config file first
    global_config_file = BASE_DIR / "app" / "config" / "global_llm_config.yaml"

    if not global_config_file.exists():
        return default_settings

    try:
        with open(global_config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            settings = data.get("router_settings", {})
            # Merge with defaults
            return {**default_settings, **settings}
    except Exception as e:
        print(f"Warning: Failed to load router settings: {e}")
        return default_settings


def initialize_llm_router():
    """
    Initialize the LLM Router service for Auto mode.
    This should be called during application startup.
    """
    global_configs = load_global_llm_configs()
    router_settings = load_router_settings()

    if not global_configs:
        print("Info: No global LLM configs found, Auto mode will not be available")
        return

    try:
        from app.services.llm_router_service import LLMRouterService

        LLMRouterService.initialize(global_configs, router_settings)
        print(
            f"Info: LLM Router initialized with {len(global_configs)} models "
            f"(strategy: {router_settings.get('routing_strategy', 'usage-based-routing')})"
        )
    except Exception as e:
        print(f"Warning: Failed to initialize LLM Router: {e}")


class Config:
    # Check if ffmpeg is installed
    if not is_ffmpeg_installed():
        import static_ffmpeg

        # ffmpeg installed on first call to add_paths(), threadsafe.
        static_ffmpeg.add_paths()
        # check if ffmpeg is installed again
        if not is_ffmpeg_installed():
            raise ValueError(
                "FFmpeg is not installed on the system. Please install it to use media generation features."
            )

    # Deployment Mode (self-hosted or cloud)
    # self-hosted: Full access to local file system connectors (Obsidian, etc.)
    # cloud: Only cloud-based connectors available
    DEPLOYMENT_MODE = os.getenv("NFD_DEPLOYMENT_MODE", "self-hosted")

    @classmethod
    def is_self_hosted(cls) -> bool:
        """Check if running in self-hosted mode."""
        return cls.DEPLOYMENT_MODE == "self-hosted"

    @classmethod
    def is_cloud(cls) -> bool:
        """Check if running in cloud mode."""
        return cls.DEPLOYMENT_MODE == "cloud"

    # GEMINI_API_KEY
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Celery / Redis
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    )
    CELERY_TASK_DEFAULT_QUEUE = os.getenv("CELERY_TASK_DEFAULT_QUEUE", "nfd")
    REDIS_APP_URL = os.getenv("REDIS_APP_URL", CELERY_BROKER_URL)
    CONNECTOR_INDEXING_LOCK_TTL_SECONDS = int(
        os.getenv("CONNECTOR_INDEXING_LOCK_TTL_SECONDS", str(8 * 60 * 60))
    )

    NEXT_FRONTEND_URL = os.getenv("NEXT_FRONTEND_URL")
    # Backend URL to override the http to https in the OAuth redirect URI
    BACKEND_URL = os.getenv("BACKEND_URL")

    # Auth
    AUTH_TYPE = os.getenv("AUTH_TYPE")
    REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "TRUE").upper() == "TRUE"

    # Google OAuth
    GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    GOOGLE_PICKER_API_KEY = os.getenv("GOOGLE_PICKER_API_KEY")

    # LangSmith observability (opt-in)
    LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    LANGSMITH_ENDPOINT = os.getenv("LANGSMITH_ENDPOINT", _LANGSMITH_DEFAULT_ENDPOINT)
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "nfd")

    # Google Drive redirect URI
    GOOGLE_DRIVE_REDIRECT_URI = os.getenv("GOOGLE_DRIVE_REDIRECT_URI")

    # Discord OAuth
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

    # Composio Configuration (for managed OAuth integrations)
    # Get your API key from https://app.composio.dev
    COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
    # Respect the environment variable: set to "TRUE" to enable Composio, "FALSE" to disable
    COMPOSIO_ENABLED = os.getenv("COMPOSIO_ENABLED", "FALSE").upper() == "TRUE"
    COMPOSIO_REDIRECT_URI = os.getenv("COMPOSIO_REDIRECT_URI")

    # LLM instances are now managed per-user through the LLMConfig system
    # Legacy environment variables removed in favor of user-specific configurations

    # Global LLM Configurations (optional)
    # Load from global_llm_config.yaml if available
    # These can be used as default options for users
    GLOBAL_LLM_CONFIGS = load_global_llm_configs()

    # Router settings for Auto mode (LiteLLM Router load balancing)
    ROUTER_SETTINGS = load_router_settings()

    # Chonkie Configuration | Edit this to your needs
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
    # Azure OpenAI credentials from environment variables
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

    # Pass Azure credentials to embeddings when using Azure OpenAI
    embedding_kwargs = {}
    if AZURE_OPENAI_ENDPOINT:
        embedding_kwargs["azure_endpoint"] = AZURE_OPENAI_ENDPOINT
    if AZURE_OPENAI_API_KEY:
        embedding_kwargs["azure_api_key"] = AZURE_OPENAI_API_KEY

    embedding_model_instance = AutoEmbeddings.get_embeddings(
        EMBEDDING_MODEL,
        **embedding_kwargs,
    )
    is_local_embedding_model = "://" not in (EMBEDDING_MODEL or "")
    chunker_instance = RecursiveChunker(
        chunk_size=getattr(embedding_model_instance, "max_seq_length", 512)
    )
    code_chunker_instance = CodeChunker(
        chunk_size=getattr(embedding_model_instance, "max_seq_length", 512)
    )

    # Reranker's Configuration | Pinecone, Cohere etc. Read more at https://github.com/AnswerDotAI/rerankers?tab=readme-ov-file#usage
    RERANKERS_ENABLED = os.getenv("RERANKERS_ENABLED", "FALSE").upper() == "TRUE"
    if RERANKERS_ENABLED:
        RERANKERS_MODEL_NAME = os.getenv("RERANKERS_MODEL_NAME")
        RERANKERS_MODEL_TYPE = os.getenv("RERANKERS_MODEL_TYPE")
        reranker_instance = Reranker(
            model_name=RERANKERS_MODEL_NAME,
            model_type=RERANKERS_MODEL_TYPE,
        )
    else:
        reranker_instance = None

    # OAuth JWT
    SECRET_KEY = os.getenv("SECRET_KEY")

    # JWT Token Lifetimes
    ACCESS_TOKEN_LIFETIME_SECONDS = int(
        os.getenv("ACCESS_TOKEN_LIFETIME_SECONDS", str(24 * 60 * 60))  # 1 day
    )
    REFRESH_TOKEN_LIFETIME_SECONDS = int(
        os.getenv("REFRESH_TOKEN_LIFETIME_SECONDS", str(14 * 24 * 60 * 60))  # 2 weeks
    )

    # ETL Service
    ETL_SERVICE = os.getenv("ETL_SERVICE")

    # Pages limit for ETL services (default to very high number for OSS unlimited usage)
    PAGES_LIMIT = int(os.getenv("PAGES_LIMIT", "999999999"))

    if ETL_SERVICE == "UNSTRUCTURED":
        # Unstructured API Key
        UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY")

    elif ETL_SERVICE == "LLAMACLOUD":
        # LlamaCloud API Key
        LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

    # Residential Proxy Configuration (anonymous-proxies.net)
    # Used for web crawling and YouTube transcript fetching to avoid IP bans.
    RESIDENTIAL_PROXY_USERNAME = os.getenv("RESIDENTIAL_PROXY_USERNAME")
    RESIDENTIAL_PROXY_PASSWORD = os.getenv("RESIDENTIAL_PROXY_PASSWORD")
    RESIDENTIAL_PROXY_HOSTNAME = os.getenv("RESIDENTIAL_PROXY_HOSTNAME")
    RESIDENTIAL_PROXY_LOCATION = os.getenv("RESIDENTIAL_PROXY_LOCATION", "")
    RESIDENTIAL_PROXY_TYPE = int(os.getenv("RESIDENTIAL_PROXY_TYPE", "1"))

    # Validation Checks
    # Check embedding dimension
    if (
        hasattr(embedding_model_instance, "dimension")
        and embedding_model_instance.dimension > 2000
    ):
        raise ValueError(
            f"Embedding dimension for Model: {EMBEDDING_MODEL} "
            f"has {embedding_model_instance.dimension} dimensions, which "
            f"exceeds the maximum of 2000 allowed by PGVector."
        )

    @classmethod
    def get_settings(cls):
        """Get all settings as a dictionary."""
        return {
            key: value
            for key, value in cls.__dict__.items()
            if not key.startswith("_") and not callable(value)
        }


# Create a config instance
config = Config()
