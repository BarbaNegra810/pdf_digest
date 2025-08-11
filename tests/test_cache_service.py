"""
Testes para o serviço de cache.
"""
import unittest
from unittest.mock import patch, MagicMock

from src.services.cache_service import CacheService


class TestCacheService(unittest.TestCase):
    """
    Testes unitários para o serviço de cache.
    """
    
    def setUp(self):
        """
        Configuração para os testes.
        """
        # Cria instância com cache desabilitado para testes
        self.cache_service = CacheService()
        self.cache_service.enabled = False  # Desabilita para testes unitários
    
    def test_cache_disabled_get(self):
        """
        Testa o get quando cache está desabilitado.
        """
        result = self.cache_service.get('test_key')
        self.assertIsNone(result)
    
    def test_cache_disabled_set(self):
        """
        Testa o set quando cache está desabilitado.
        """
        result = self.cache_service.set('test_key', {'data': 'test'})
        self.assertFalse(result)
    
    def test_cache_disabled_delete(self):
        """
        Testa o delete quando cache está desabilitado.
        """
        result = self.cache_service.delete('test_key')
        self.assertFalse(result)
    
    def test_cache_disabled_clear_all(self):
        """
        Testa o clear_all quando cache está desabilitado.
        """
        result = self.cache_service.clear_all()
        self.assertFalse(result)
    
    def test_cache_disabled_get_stats(self):
        """
        Testa get_stats quando cache está desabilitado.
        """
        stats = self.cache_service.get_stats()
        self.assertEqual(stats, {'enabled': False})
    
    def test_cache_disabled_test_connection(self):
        """
        Testa test_connection quando cache está desabilitado.
        """
        result = self.cache_service.test_connection()
        self.assertFalse(result)
    
    @patch('redis.from_url')
    def test_cache_enabled_operations(self, mock_redis_from_url):
        """
        Testa operações quando cache está habilitado.
        """
        # Mock do cliente Redis
        mock_client = MagicMock()
        mock_redis_from_url.return_value = mock_client
        
        # Cria nova instância com cache habilitado
        cache_service = CacheService()
        cache_service.enabled = True
        cache_service.client = mock_client
        
        # Testa get
        mock_client.get.return_value = '{"data": "test"}'
        result = cache_service.get('test_key')
        self.assertEqual(result, {"data": "test"})
        
        # Testa set
        mock_client.setex.return_value = True
        result = cache_service.set('test_key', {'data': 'test'})
        self.assertTrue(result)
        
        # Testa delete
        mock_client.delete.return_value = 1
        result = cache_service.delete('test_key')
        self.assertTrue(result)
        
        # Testa clear_all
        result = cache_service.clear_all()
        mock_client.flushdb.assert_called_once()
        self.assertTrue(result)
        
        # Testa test_connection
        result = cache_service.test_connection()
        mock_client.ping.assert_called()
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main() 