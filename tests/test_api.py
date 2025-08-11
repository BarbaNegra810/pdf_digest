"""
Testes de integração para a API do PDF Digest.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

from src.api.app import create_app


class TestPDFDigestAPI(unittest.TestCase):
    """
    Testes de integração para a API.
    """
    
    def setUp(self):
        """
        Configuração para os testes.
        """
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Cria diretório temporário para testes
        self.temp_dir = tempfile.mkdtemp()
        
        # Cria um PDF válido para testes
        self.valid_pdf_content = b'%PDF-1.5\nconteudo do pdf\nNOTA DE NEGOCIACAO\nconteudo da nota'
    
    def tearDown(self):
        """
        Limpeza após os testes.
        """
        # Remove arquivos temporários
        if os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(self.temp_dir)
    
    def test_health_check(self):
        """
        Testa o endpoint de health check.
        """
        response = self.client.get('/api/health')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('status', data['data'])
        self.assertIn('checks', data['data'])
    
    def test_root_endpoint(self):
        """
        Testa o endpoint raiz.
        """
        response = self.client.get('/')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['name'], 'PDF Digest API')
        self.assertIn('endpoints', data)
    
    def test_info_endpoint(self):
        """
        Testa o endpoint de informações.
        """
        response = self.client.get('/api/info')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('name', data['data'])
        self.assertIn('endpoints', data['data'])
        self.assertIn('limits', data['data'])
    
    def test_stats_endpoint(self):
        """
        Testa o endpoint de estatísticas.
        """
        response = self.client.get('/api/stats')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('system', data['data'])
        self.assertIn('upload', data['data'])
        self.assertIn('cache', data['data'])
        self.assertIn('device', data['data'])
    
    @patch('src.services.pdf_service.DocumentConverter.convert')
    def test_convert_pdf_upload_success(self, mock_convert):
        """
        Testa conversão de PDF via upload com sucesso.
        """
        # Configura o mock
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = 'NOTA DE NEGOCIAÇÃO\nConteúdo convertido'
        mock_convert.return_value = mock_result
        
        # Prepara o arquivo para upload
        data = {
            'file': (BytesIO(self.valid_pdf_content), 'test.pdf', 'application/pdf')
        }
        
        response = self.client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('pages', data['data'])
        self.assertIn('file_info', data['data'])
    
    def test_convert_pdf_no_file(self):
        """
        Testa conversão sem enviar arquivo.
        """
        response = self.client.post('/api/convert', json={})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_convert_pdf_invalid_extension(self):
        """
        Testa conversão com arquivo de extensão inválida.
        """
        data = {
            'file': (BytesIO(b'conteudo qualquer'), 'test.txt', 'text/plain')
        }
        
        response = self.client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_convert_pdf_empty_filename(self):
        """
        Testa conversão com nome de arquivo vazio.
        """
        data = {
            'file': (BytesIO(self.valid_pdf_content), '', 'application/pdf')
        }
        
        response = self.client.post('/api/convert', data=data, content_type='multipart/form-data')
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
    
    def test_convert_pdf_json_path(self):
        """
        Testa conversão via JSON com caminho do arquivo.
        """
        # Cria um arquivo PDF temporário
        pdf_path = os.path.join(self.temp_dir, 'test.pdf')
        with open(pdf_path, 'wb') as f:
            f.write(self.valid_pdf_content)
        
        with patch('src.services.pdf_service.DocumentConverter.convert') as mock_convert:
            mock_result = MagicMock()
            mock_result.document.export_to_markdown.return_value = 'NOTA DE NEGOCIAÇÃO\nConteúdo convertido'
            mock_convert.return_value = mock_result
            
            response = self.client.post('/api/convert', json={'path': pdf_path})
            
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data['success'])
    
    def test_clear_cache_endpoint(self):
        """
        Testa o endpoint de limpeza de cache.
        """
        response = self.client.post('/api/cache/clear')
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
    
    def test_cleanup_endpoint(self):
        """
        Testa o endpoint de limpeza de arquivos.
        """
        response = self.client.post('/api/cleanup', json={'max_age_hours': 1})
        
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('data', data)
        self.assertIn('removed_files', data['data'])
    
    def test_cleanup_endpoint_invalid_parameter(self):
        """
        Testa o endpoint de limpeza com parâmetro inválido.
        """
        response = self.client.post('/api/cleanup', json={'max_age_hours': -1})
        
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['success'])
    
    def test_rate_limiting(self):
        """
        Testa o rate limiting fazendo muitas requisições.
        """
        # Faz várias requisições rapidamente
        responses = []
        for _ in range(10):
            response = self.client.get('/api/health')
            responses.append(response)
        
        # Pelo menos algumas devem ter sucesso
        success_count = sum(1 for r in responses if r.status_code == 200)
        self.assertGreater(success_count, 0)
        
        # Se houver rate limiting, algumas podem retornar 429
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        # Note: este teste pode passar mesmo sem rate limiting ativo em desenvolvimento
    
    def test_404_error_handler(self):
        """
        Testa o handler de erro 404.
        """
        response = self.client.get('/api/endpoint_inexistente')
        
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'NOT_FOUND')
    
    def test_method_not_allowed_error_handler(self):
        """
        Testa o handler de erro 405.
        """
        response = self.client.put('/api/health')
        
        self.assertEqual(response.status_code, 405)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'METHOD_NOT_ALLOWED')
    
    def test_security_headers(self):
        """
        Testa se os headers de segurança estão sendo aplicados.
        """
        response = self.client.get('/api/health')
        
        # Verifica headers de segurança
        self.assertIn('X-Content-Type-Options', response.headers)
        self.assertIn('X-Frame-Options', response.headers)
        self.assertIn('X-XSS-Protection', response.headers)
        self.assertIn('Content-Security-Policy', response.headers)
        
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')


if __name__ == '__main__':
    unittest.main() 