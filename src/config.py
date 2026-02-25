from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    deepseek_api_key: str = ""
    llm_api_key: str = ""  # Generic key — used when provider-specific key is empty
    llm_model: str = "claude-sonnet-4-20250514"
    llm_base_url: str = ""  # Custom base URL for openai_compatible provider

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Output
    output_dir: str = "./output"
    max_file_size_mb: int = 50

    # Skills
    skills_public_dir: str = "./src/skills/public"
    skills_user_dir: str = "./src/skills/user"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
