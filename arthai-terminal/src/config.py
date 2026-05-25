# src/config.py - Updated with extra="ignore"
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

class Settings(BaseSettings):
    # 🔐 Telegram Configuration
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    
    # 📊 Data Source Selection
    data_source: str = "yfinance"
    
    # 🤖 Ollama Local AI
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    
    # ⚠️ Angel One Smart API Credentials
    angel_api_key: str | None = None
    angel_api_secret: str | None = None  # Stores your 4-digit MPIN
    angel_client_code: str | None = None
    angel_totp_secret: str | None = None
    
    # 📈 Finnhub API (optional)
    finnhub_api_key: str | None = None
    
    # 🪵 Logging
    log_level: str = "INFO"

    # ✅ Allow extra fields in .env (for future expansion)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # ← This line fixes the error!
    )

# Create singleton instance
settings = Settings()