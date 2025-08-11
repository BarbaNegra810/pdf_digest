"""
Testes para o serviço de conversão de PDF.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import pytest

from src.services.pdf_service import PDFService
from src.utils.exceptions import ValidationError, ConversionError


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
        with self.assertRaises(ValidationError):
            self.pdf_service.validate_pdf(self.invalid_file_path)
    
    def test_validate_pdf_with_nonexistent_file(self):
        """
        Testa a validação de um arquivo que não existe.
        """
        with self.assertRaises(ValidationError):
            self.pdf_service.validate_pdf('arquivo_inexistente.pdf')
    
    @patch('src.services.pdf_service.DocumentConverter.convert')
    def test_convert_pdf_to_markdown(self, mock_convert):
        """
        Testa a conversão de PDF para Markdown.
        """
        # Configura o mock para retornar um objeto com document.export_to_markdown
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = 'NOTA DE NEGOCIAÇÃO\n# Título\n\nConteúdo convertido'
        mock_convert.return_value = mock_result
        
        result = self.pdf_service.convert_pdf_to_markdown(self.valid_pdf_path)
        
        # Verifica se retorna um dicionário com as páginas
        self.assertIsInstance(result, dict)
        self.assertIn('1', result)
        self.assertIn('NOTA DE NEGOCIAÇÃO', result['1'])
        mock_convert.assert_called_once_with(self.valid_pdf_path)
    
    def test_convert_pdf_with_invalid_file(self):
        """
        Testa a conversão com um arquivo inválido.
        """
        with self.assertRaises(ValidationError):
            self.pdf_service.convert_pdf_to_markdown(self.invalid_file_path)
    
    def test_convert_pdf_with_nonexistent_file(self):
        """
        Testa a conversão com um arquivo que não existe.
        """
        with self.assertRaises(ValidationError):
            self.pdf_service.convert_pdf_to_markdown('arquivo_inexistente.pdf')
    
    def test_get_device_info(self):
        """
        Testa a obtenção de informações do dispositivo.
        """
        device_info = self.pdf_service.get_device_info()
        
        self.assertIsInstance(device_info, dict)
        self.assertIn('device', device_info)
        self.assertIn('gpu_available', device_info)
        self.assertIn('gpu_enabled', device_info)
    
    def test_clear_cache(self):
        """
        Testa a limpeza do cache.
        """
        result = self.pdf_service.clear_cache()
        self.assertIsInstance(result, bool)
    
    @patch('src.services.pdf_service.DocumentConverter.convert')
    def test_convert_pdf_with_cache_disabled(self, mock_convert):
        """
        Testa a conversão com cache desabilitado.
        """
        mock_result = MagicMock()
        mock_result.document.export_to_markdown.return_value = 'NOTA DE NEGOCIAÇÃO\nConteúdo'
        mock_convert.return_value = mock_result
        
        result = self.pdf_service.convert_pdf_to_markdown(self.valid_pdf_path, use_cache=False)
        
        self.assertIsInstance(result, dict)
        mock_convert.assert_called_once_with(self.valid_pdf_path)
    
    def test_split_by_nota_negociacao(self):
        """
        Testa a divisão do markdown por notas de negociação.
        """
        markdown_content = """
        NOTA DE NEGOCIAÇÃO
        Primeira nota de negociação com conteúdo.
        
        NOTA DE NEGOCIAÇÃO
        Segunda nota de negociação com mais conteúdo.
        """
        
        pages = self.pdf_service._split_by_nota_negociacao(markdown_content)
        
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0][0], 1)
        self.assertEqual(pages[1][0], 2)
        self.assertIn('Primeira nota', pages[0][1])
        self.assertIn('Segunda nota', pages[1][1])

    @patch('src.services.pdf_service.DocumentConverter.convert')
    def test_extract_tables_advanced(self, mock_convert):
        """
        Testa a extração avançada de tabelas.
        """
        # Configura o mock para simular documento com tabelas
        mock_document = MagicMock()
        mock_element = MagicMock()
        mock_element.label = "table"
        mock_element.text = "Header1|Header2\nData1|Data2"
        mock_element.page = 1
        mock_element.bbox = [100, 100, 200, 200]
        mock_element.confidence = 0.95
        
        mock_document.iterate_elements.return_value = [mock_element]
        
        mock_result = MagicMock()
        mock_result.document = mock_document
        mock_convert.return_value = mock_result
        
        result = self.pdf_service.extract_tables_advanced(self.valid_pdf_path, "json")
        
        # Verifica estrutura da resposta
        self.assertIsInstance(result, dict)
        self.assertIn('tables', result)
        self.assertIn('metadata', result)
        self.assertEqual(result['metadata']['export_format'], 'json')
        self.assertEqual(result['metadata']['total_tables'], 1)
        
        # Verifica tabela extraída
        self.assertEqual(len(result['tables']), 1)
        table = result['tables'][0]
        self.assertEqual(table['id'], 1)
        self.assertEqual(table['page'], 1)
        self.assertEqual(table['format'], 'json')
        
        mock_convert.assert_called_once_with(self.valid_pdf_path)

    def test_parse_table_from_text(self):
        """
        Testa a extração de tabela a partir de texto.
        """
        text_content = """Header1    Header2    Header3
        Data1      Data2      Data3
        Value1     Value2     Value3"""
        
        result = self.pdf_service._parse_table_from_text(text_content)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)  # 3 linhas
        self.assertEqual(len(result[0]), 3)  # 3 colunas
        self.assertEqual(result[0][0], 'Header1')
        self.assertEqual(result[1][0], 'Data1')

    def test_parse_table_from_text_with_pipes(self):
        """
        Testa a extração de tabela com separador pipe.
        """
        text_content = """Header1|Header2|Header3
        Data1|Data2|Data3
        Value1|Value2|Value3"""
        
        result = self.pdf_service._parse_table_from_text(text_content)
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], ['Header1', 'Header2', 'Header3'])
        self.assertEqual(result[1], ['Data1', 'Data2', 'Data3'])

    def test_convert_table_to_csv(self):
        """
        Testa a conversão de tabela para CSV.
        """
        table_data = [
            ['Header1', 'Header2', 'Header3'],
            ['Data1', 'Data2', 'Data3'],
            ['Value1', 'Value2', 'Value3']
        ]
        
        csv_result = self.pdf_service._convert_table_to_csv(table_data)
        
        self.assertIsInstance(csv_result, str)
        self.assertIn('Header1,Header2,Header3', csv_result)
        self.assertIn('Data1,Data2,Data3', csv_result)

    def test_convert_table_to_excel_format(self):
        """
        Testa a conversão de tabela para formato Excel.
        """
        table_data = [
            ['Header1', 'Header2', 'Header3'],
            ['Data1', 'Data2', 'Data3'],
            ['Value1', 'Value2', 'Value3']
        ]
        
        excel_result = self.pdf_service._convert_table_to_excel_format(table_data)
        
        self.assertIsInstance(excel_result, dict)
        self.assertIn('headers', excel_result)
        self.assertIn('rows', excel_result)
        self.assertEqual(excel_result['headers'], ['Header1', 'Header2', 'Header3'])
        self.assertEqual(len(excel_result['rows']), 2)

    def test_convert_table_to_html(self):
        """
        Testa a conversão de tabela para HTML.
        """
        table_data = [
            ['Header1', 'Header2'],
            ['Data1', 'Data2']
        ]
        
        html_result = self.pdf_service._convert_table_to_html(table_data)
        
        self.assertIsInstance(html_result, str)
        self.assertIn('<table', html_result)
        self.assertIn('<thead>', html_result)
        self.assertIn('<tbody>', html_result)
        self.assertIn('Header1', html_result)
        self.assertIn('Data1', html_result)

    def test_escape_html(self):
        """
        Testa o escape de caracteres HTML.
        """
        text_with_html = '<script>alert("test")</script>'
        escaped = self.pdf_service._escape_html(text_with_html)
        
        self.assertNotIn('<script>', escaped)
        self.assertIn('&lt;script&gt;', escaped)

    @patch('src.services.pdf_service.DocumentConverter.convert')
    def test_extract_tables_different_formats(self, mock_convert):
        """
        Testa a extração de tabelas em diferentes formatos.
        """
        # Mock básico
        mock_document = MagicMock()
        mock_element = MagicMock()
        mock_element.label = "table"
        mock_element.text = "Col1|Col2\nVal1|Val2"
        mock_document.iterate_elements.return_value = [mock_element]
        
        mock_result = MagicMock()
        mock_result.document = mock_document
        mock_convert.return_value = mock_result
        
        # Testa diferentes formatos
        formats = ['json', 'csv', 'excel', 'html']
        
        for fmt in formats:
            with self.subTest(format=fmt):
                result = self.pdf_service.extract_tables_advanced(self.valid_pdf_path, fmt)
                self.assertEqual(result['metadata']['export_format'], fmt)
                if result['tables']:
                    self.assertEqual(result['tables'][0]['format'], fmt)

    def test_extract_tables_with_invalid_file(self):
        """
        Testa a extração de tabelas com arquivo inválido.
        """
        with self.assertRaises(ValidationError):
            self.pdf_service.extract_tables_advanced(self.invalid_file_path, "json")

    def test_save_tables_to_files_json(self):
        """
        Testa o salvamento de tabelas em arquivos JSON.
        """
        tables_result = {
            'tables': [{
                'id': 1,
                'data': [['Header1', 'Header2'], ['Data1', 'Data2']],
                'format': 'json'
            }],
            'metadata': {'total_tables': 1}
        }
        
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            saved_files = self.pdf_service.save_tables_to_files(tables_result, temp_dir)
            
            self.assertIn('json', saved_files)
            self.assertEqual(len(saved_files['json']), 1)
            self.assertTrue(saved_files['json'][0].endswith('table_1.json'))

    def test_process_tables_for_export_empty_data(self):
        """
        Testa o processamento de tabelas com dados vazios.
        """
        tables_data = [{
            'id': 1,
            'data': None,
            'page': 1,
            'bbox': None,
            'confidence': None
        }]
        
        result = self.pdf_service._process_tables_for_export(tables_data, 'json')
        
        # Deve filtrar tabelas sem dados
        self.assertEqual(len(result), 0)


if __name__ == '__main__':
    unittest.main() 