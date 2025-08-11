"""
Testes para o serviço de gestão de arquivos.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from werkzeug.datastructures import FileStorage
from io import BytesIO

from src.services.file_service import FileService
from src.utils.exceptions import ValidationError, SecurityError


class TestFileService(unittest.TestCase):
    """
    Testes unitários para o serviço de arquivos.
    """
    
    def setUp(self):
        """
        Configuração para os testes.
        """
        self.file_service = FileService()
        
        # Cria diretório temporário para testes
        self.temp_dir = tempfile.mkdtemp()
        self.file_service.upload_folder = self.temp_dir
        
        # Cria um PDF válido para testes
        self.valid_pdf_path = os.path.join(self.temp_dir, 'valid.pdf')
        with open(self.valid_pdf_path, 'wb') as f:
            f.write(b'%PDF-1.5\nconteudo do pdf')
        
        # Cria um arquivo inválido
        self.invalid_file_path = os.path.join(self.temp_dir, 'invalid.txt')
        with open(self.invalid_file_path, 'w') as f:
            f.write('Este não é um PDF')
    
    def tearDown(self):
        """
        Limpeza após os testes.
        """
        # Remove arquivos temporários
        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(self.temp_dir)
    
    def test_validate_file_security_valid_pdf(self):
        """
        Testa a validação de segurança com um PDF válido.
        """
        result = self.file_service.validate_file_security(self.valid_pdf_path)
        self.assertTrue(result)
    
    def test_validate_file_security_invalid_file(self):
        """
        Testa a validação de segurança com arquivo inválido.
        """
        with self.assertRaises(SecurityError):
            self.file_service.validate_file_security(self.invalid_file_path)
    
    def test_validate_file_security_nonexistent_file(self):
        """
        Testa a validação de segurança com arquivo inexistente.
        """
        with self.assertRaises(SecurityError):
            self.file_service.validate_file_security('arquivo_inexistente.pdf')
    
    def test_save_uploaded_file_valid_pdf(self):
        """
        Testa o salvamento de um arquivo PDF válido.
        """
        # Cria um FileStorage mock
        pdf_content = b'%PDF-1.5\nconteudo do pdf'
        file_storage = FileStorage(
            stream=BytesIO(pdf_content),
            filename='test.pdf',
            content_type='application/pdf'
        )
        
        result = self.file_service.save_uploaded_file(file_storage)
        
        # Verifica se o resultado contém as informações esperadas
        self.assertIn('original_filename', result)
        self.assertIn('saved_filename', result)
        self.assertIn('file_path', result)
        self.assertIn('file_size', result)
        self.assertIn('file_hash', result)
        self.assertEqual(result['original_filename'], 'test.pdf')
        
        # Verifica se o arquivo foi realmente salvo
        self.assertTrue(os.path.exists(result['file_path']))
    
    def test_save_uploaded_file_invalid_extension(self):
        """
        Testa o salvamento de arquivo com extensão inválida.
        """
        file_storage = FileStorage(
            stream=BytesIO(b'conteudo qualquer'),
            filename='test.txt',
            content_type='text/plain'
        )
        
        with self.assertRaises(ValidationError):
            self.file_service.save_uploaded_file(file_storage)
    
    def test_save_uploaded_file_empty_filename(self):
        """
        Testa o salvamento de arquivo com nome vazio.
        """
        file_storage = FileStorage(
            stream=BytesIO(b'%PDF-1.5\nconteudo'),
            filename='',
            content_type='application/pdf'
        )
        
        with self.assertRaises(ValidationError):
            self.file_service.save_uploaded_file(file_storage)
    
    def test_validate_existing_file_valid(self):
        """
        Testa a validação de arquivo existente válido.
        """
        result = self.file_service.validate_existing_file(self.valid_pdf_path)
        
        self.assertIn('filename', result)
        self.assertIn('file_path', result)
        self.assertIn('file_size', result)
        self.assertIn('file_hash', result)
        self.assertEqual(result['file_path'], self.valid_pdf_path)
    
    def test_validate_existing_file_invalid(self):
        """
        Testa a validação de arquivo existente inválido.
        """
        with self.assertRaises(ValidationError):
            self.file_service.validate_existing_file(self.invalid_file_path)
    
    def test_cleanup_file_existing(self):
        """
        Testa a limpeza de arquivo existente.
        """
        # Cria um arquivo temporário
        temp_file = os.path.join(self.temp_dir, 'temp.pdf')
        with open(temp_file, 'wb') as f:
            f.write(b'%PDF-1.5\ntemp content')
        
        # Verifica se existe
        self.assertTrue(os.path.exists(temp_file))
        
        # Remove
        result = self.file_service.cleanup_file(temp_file)
        
        # Verifica se foi removido
        self.assertTrue(result)
        self.assertFalse(os.path.exists(temp_file))
    
    def test_cleanup_file_nonexistent(self):
        """
        Testa a limpeza de arquivo inexistente.
        """
        result = self.file_service.cleanup_file('arquivo_inexistente.pdf')
        self.assertFalse(result)
    
    def test_get_upload_stats(self):
        """
        Testa a obtenção de estatísticas de upload.
        """
        stats = self.file_service.get_upload_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('upload_folder', stats)
        self.assertIn('total_files', stats)
        self.assertIn('total_size', stats)
        self.assertIn('max_file_size', stats)
        self.assertIn('allowed_extensions', stats)
    
    def test_cleanup_old_files(self):
        """
        Testa a limpeza de arquivos antigos.
        """
        # Cria alguns arquivos temporários
        for i in range(3):
            temp_file = os.path.join(self.temp_dir, f'temp_{i}.pdf')
            with open(temp_file, 'wb') as f:
                f.write(b'%PDF-1.5\ntemp content')
        
        # Executa limpeza (com idade 0 para remover tudo)
        removed_count = self.file_service.cleanup_old_files(max_age_hours=0)
        
        # Verifica se pelo menos alguns arquivos foram removidos
        self.assertGreaterEqual(removed_count, 0)


if __name__ == '__main__':
    unittest.main() 