"""
Sistema de configuração centralizada para o PDF Digest.
"""
import os
from pathlib import Path
from typing import Optional
from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configurações centralizadas da aplicação."""
    
    # Configurações do servidor
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    
    # Configurações do Flask (para compatibilidade com deploy)
    flask_env: str = "production"
    flask_debug: bool = False
    
    # Configurações de upload
    upload_folder: str = "uploads"
    max_content_length: int = 16 * 1024 * 1024  # 16MB
    allowed_extensions: list = ['.pdf']
    
    # Configurações de logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configurações de hardware
    gpu_enabled: bool = True
    device: Optional[str] = None
    
    # Configurações de processamento PDF
    pdf_processor: str = "agno"  # Sistema opera exclusivamente com Agno
    
    # Configurações do Agno
    openai_api_key: Optional[str] = None
    
    # Configurações de cache
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hora
    redis_url: str = "redis://localhost:6379"
    
    # Configurações de segurança
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_secret_key: str = "jwt-secret-key-change-in-production"
    jwt_access_token_expires: int = 3600  # 1 hora
    
    # Rate limiting
    rate_limit_per_minute: int = 5
    rate_limit_per_hour: int = 50
    rate_limit_per_day: int = 200
    
    # Configurações de monitoramento
    metrics_enabled: bool = True
    health_check_interval: int = 30
    
    @field_validator('upload_folder')
    @classmethod
    def create_upload_folder(cls, v):
        """Cria o diretório de upload se não existir."""
        upload_path = Path(v)
        upload_path.mkdir(parents=True, exist_ok=True)
        return str(upload_path.absolute())
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Valida o nível de log."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level deve ser um de: {valid_levels}')
        return v.upper()
    
    @field_validator('pdf_processor')
    @classmethod
    def validate_pdf_processor(cls, v):
        """Valida o processador de PDF."""
        if v.lower() != 'agno':
            raise ValueError('PDF processor deve ser "agno" - sistema opera exclusivamente com Agno')
        return v.lower()
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra="allow"  # Permite campos extras para compatibilidade
    )


# Instância global de configurações
settings = Settings() 