"""
Funções auxiliares para o PDF Digest.
"""
import hashlib
import logging
import os
import psutil
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def sanitize_log_data(data: dict) -> dict:
    """
    Remove informações sensíveis dos dados de log.
    
    Args:
        data: Dicionário com dados para log
        
    Returns:
        Dicionário sanitizado
    """
    sensitive_keys = ['password', 'token', 'api_key', 'secret', 'auth', 'key']
    
    if not isinstance(data, dict):
        return data
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            sanitized[key] = '***'
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        else:
            sanitized[key] = value
    
    return sanitized


def calculate_file_hash(file_path: str) -> str:
    """
    Calcula o hash SHA-256 de um arquivo.
    
    Args:
        file_path: Caminho do arquivo
        
    Returns:
        Hash hexadecimal do arquivo
    """
    hash_sha256 = hashlib.sha256()
    
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        logger.error(f"Erro ao calcular hash do arquivo {file_path}: {e}")
        raise


def get_disk_usage(path: str = ".") -> float:
    """
    Retorna o percentual de uso do disco.
    
    Args:
        path: Caminho para verificar o uso do disco
        
    Returns:
        Percentual de uso do disco (0-100)
    """
    try:
        disk_usage = psutil.disk_usage(path)
        return (disk_usage.used / disk_usage.total) * 100
    except Exception as e:
        logger.error(f"Erro ao obter uso do disco: {e}")
        return 0.0


def get_memory_usage() -> float:
    """
    Retorna o percentual de uso da memória.
    
    Returns:
        Percentual de uso da memória (0-100)
    """
    try:
        memory = psutil.virtual_memory()
        return memory.percent
    except Exception as e:
        logger.error(f"Erro ao obter uso da memória: {e}")
        return 0.0


def ensure_directory_exists(directory: str) -> None:
    """
    Garante que um diretório existe, criando-o se necessário.
    
    Args:
        directory: Caminho do diretório
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def clean_filename(filename: str) -> str:
    """
    Limpa um nome de arquivo removendo caracteres perigosos.
    
    Args:
        filename: Nome do arquivo original
        
    Returns:
        Nome do arquivo limpo
    """
    # Remove caracteres perigosos
    dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
    clean_name = filename
    
    for char in dangerous_chars:
        clean_name = clean_name.replace(char, '_')
    
    # Limita o tamanho do nome
    if len(clean_name) > 255:
        name, ext = os.path.splitext(clean_name)
        clean_name = name[:255-len(ext)] + ext
    
    return clean_name


def format_file_size(size_bytes: int) -> str:
    """
    Formata o tamanho do arquivo em formato legível.
    
    Args:
        size_bytes: Tamanho em bytes
        
    Returns:
        Tamanho formatado (ex: "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def create_response(success: bool, data: Any = None, error: str = None, 
                   code: str = None, details: Dict = None) -> Dict[str, Any]:
    """
    Cria uma resposta padronizada para a API.
    
    Args:
        success: Se a operação foi bem-sucedida
        data: Dados da resposta
        error: Mensagem de erro
        code: Código de erro
        details: Detalhes adicionais
        
    Returns:
        Dicionário com resposta padronizada
    """
    response = {
        'success': success,
        'timestamp': int(__import__('time').time())
    }
    
    if success:
        response['data'] = data
    else:
        response['error'] = {
            'message': error,
            'code': code,
            'details': details or {}
        }
    
    return response 