"""
Testes para o serviço de conversão de PDF.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import pytest

from src.pdf_service import PDFService


class TestPDFService(unittest.TestCase):
    """
    Testes unitários para o serviço de PDF.
    """
    
    def setUp(self):
        """
        Configuração para os testes.
        """
        self.pdf_service = PDFService()
        
        # Cria um PDF falso para testes
        self.temp_dir = tempfile.mkdtemp()
        self.valid_pdf_path = os.path.join(self.temp_dir, 'valid.pdf')
        with open(self.valid_pdf_path, 'wb') as f:
            f.write(b'%PDF-1.5\nconteudo do pdf')
        
        self.invalid_file_path = os.path.join(self.temp_dir, 'invalid.txt')
        with open(self.invalid_file_path, 'w') as f:
            f.write('Este não é um PDF')
    
    def tearDown(self):
        """
        Limpeza após os testes.
        """
        # Remove os arquivos temporários
        if os.path.exists(self.valid_pdf_path):
            os.remove(self.valid_pdf_path)
        if os.path.exists(self.invalid_file_path):
            os.remove(self.invalid_file_path)
        os.rmdir(self.temp_dir)
    
    def test_validate_pdf_with_valid_file(self):
        """
        Testa a validação de um arquivo PDF válido.
        """
        result = self.pdf_service.validate_pdf(self.valid_pdf_path)
        self.assertTrue(result)
    
    def test_validate_pdf_with_invalid_file(self):
        """
        Testa a validação de um arquivo que não é PDF.
        """
        result = self.pdf_service.validate_pdf(self.invalid_file_path)
        self.assertFalse(result)
    
    def test_validate_pdf_with_nonexistent_file(self):
        """
        Testa a validação de um arquivo que não existe.
        """
        result = self.pdf_service.validate_pdf('arquivo_inexistente.pdf')
        self.assertFalse(result)
    
    @patch('docling.document_converter.DocumentConverter.convert')
    def test_convert_pdf_to_markdown(self, mock_convert):
        """
        Testa a conversão de PDF para Markdown.
        """
        # Configura o mock para retornar um objeto com document.export_to_markdown
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = '# Título\n\nConteúdo convertido'
        mock_convert.return_value = mock_result
        
        result = self.pdf_service.convert_pdf_to_markdown(self.valid_pdf_path)
        
        self.assertEqual(result, '# Título\n\nConteúdo convertido')
        mock_convert.assert_called_once_with(self.valid_pdf_path)
    
    def test_convert_pdf_with_invalid_file(self):
        """
        Testa a conversão com um arquivo inválido.
        """
        with self.assertRaises(ValueError):
            self.pdf_service.convert_pdf_to_markdown(self.invalid_file_path)
    
    def test_convert_pdf_with_nonexistent_file(self):
        """
        Testa a conversão com um arquivo que não existe.
        """
        with self.assertRaises(ValueError):
            self.pdf_service.convert_pdf_to_markdown('arquivo_inexistente.pdf') 