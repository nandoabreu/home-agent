from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    telegram_bot_token: str
    opencode_server_url: str = "http://127.0.0.1:4096"
    telegram_admin_user_ids: str = ""
    restart_command: str = "bash ./scripts/restart-home-agent.sh"
    debug_mode: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
