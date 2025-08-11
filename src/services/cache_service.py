"""
Serviço de cache para o PDF Digest.
"""
import json
import logging
import redis
from typing import Optional, Dict, Any
from src.config.settings import settings
from src.utils.exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheService:
    """Serviço de cache usando Redis."""
    
    def __init__(self):
        """Inicializa a conexão com Redis."""
        self.enabled = settings.cache_enabled
        self.ttl = settings.cache_ttl
        self.client = None
        
        if self.enabled:
            try:
                self.client = redis.from_url(settings.redis_url, decode_responses=True)
                # Testa a conexão
                self.client.ping()
                logger.info("Cache Redis conectado com sucesso")
            except redis.ConnectionError as e:
                logger.warning(f"Não foi possível conectar ao Redis: {e}")
                logger.warning("Cache será desabilitado")
                self.enabled = False
            except Exception as e:
                logger.error(f"Erro inesperado ao configurar cache: {e}")
                self.enabled = False
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Recupera um valor do cache.
        
        Args:
            key: Chave do cache
            
        Returns:
            Valor do cache ou None se não encontrado
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            cached_data = self.client.get(key)
            if cached_data:
                logger.debug(f"Cache hit para chave: {key}")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache miss para chave: {key}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar dados do cache para chave {key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao recuperar do cache: {e}")
            return None
    
    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Armazena um valor no cache.
        
        Args:
            key: Chave do cache
            value: Valor a ser armazenado
            ttl: Tempo de vida em segundos (usa default se None)
            
        Returns:
            True se armazenado com sucesso, False caso contrário
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            cache_ttl = ttl or self.ttl
            serialized_value = json.dumps(value, ensure_ascii=False)
            
            result = self.client.setex(key, cache_ttl, serialized_value)
            
            if result:
                logger.debug(f"Valor armazenado no cache com chave: {key}, TTL: {cache_ttl}s")
            else:
                logger.warning(f"Falha ao armazenar no cache com chave: {key}")
            
            return result
            
        except json.JSONEncodeError as e:
            logger.error(f"Erro ao serializar dados para cache: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao armazenar no cache: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Remove um valor do cache.
        
        Args:
            key: Chave do cache
            
        Returns:
            True se removido com sucesso, False caso contrário
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            result = self.client.delete(key)
            logger.debug(f"Chave removida do cache: {key}")
            return bool(result)
        except Exception as e:
            logger.error(f"Erro ao remover do cache: {e}")
            return False
    
    def clear_all(self) -> bool:
        """
        Limpa todos os dados do cache.
        
        Returns:
            True se limpeza foi bem-sucedida, False caso contrário
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.flushdb()
            logger.info("Cache limpo com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do cache.
        
        Returns:
            Dicionário com estatísticas do cache
        """
        if not self.enabled or not self.client:
            return {'enabled': False}
        
        try:
            info = self.client.info()
            return {
                'enabled': True,
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0)
            }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do cache: {e}")
            return {'enabled': True, 'error': str(e)}
    
    def test_connection(self) -> bool:
        """
        Testa a conexão com o Redis.
        
        Returns:
            True se conexão está funcionando, False caso contrário
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Teste de conexão do cache falhou: {e}")
            return False


# Instância global do serviço de cache
cache_service = CacheService() 