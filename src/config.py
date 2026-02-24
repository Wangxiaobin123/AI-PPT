from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"

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
