# backend/config.py
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

load_dotenv()

class Settings(BaseSettings):
    # Database Configuration
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    
    # LLM Configuration
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "https://17c0cf9d2c00.ngrok-free.app")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "llama3.1:latest")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    
    # Application Configuration
    VERBOSE: bool = os.getenv("VERBOSE", "True").lower() == "true"
    MAX_RETRY_ATTEMPTS: int = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))
    
    # FastAPI Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def get_llm_config(self) -> dict:
        """
        Get LLM configuration for CrewAI agents.
        Returns configuration compatible with different CrewAI versions.
        """
        return {
            "model": f"ollama/{self.MODEL_NAME}",
            "base_url": self.OLLAMA_URL,
            "temperature": self.LLM_TEMPERATURE
        }
    
    @classmethod
    def get_llm(cls):
        """
        Get configured LLM instance.
        This method handles different CrewAI versions.
        """
        instance = cls()
        
        try:
            # Try newer CrewAI version (0.28.0+)
            from langchain_community.llms import Ollama
            
            return Ollama(
                model=instance.MODEL_NAME,
                base_url=instance.OLLAMA_URL,
                temperature=instance.LLM_TEMPERATURE
            )
        except ImportError:
            try:
                # Try alternative import for older versions
                from langchain.llms import Ollama
                
                return Ollama(
                    model=instance.MODEL_NAME,
                    base_url=instance.OLLAMA_URL,
                    temperature=instance.LLM_TEMPERATURE
                )
            except ImportError:
                # Fallback: return configuration dict
                print("Warning: Could not import Ollama LLM. Using configuration dict.")
                return instance.get_llm_config()

settings = Settings()