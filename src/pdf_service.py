"""
Serviço para validação e conversão de arquivos PDF para Markdown.
"""
import os
import logging
from pathlib import Path

from docling.document_converter import DocumentConverter


# Configuração de logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class PDFService:
    """
    Serviço para validar e converter PDFs para Markdown.
    """

    def __init__(self):
        """
        Inicializa o conversor de documentos docling.
        """
        logger.info("Inicializando PDFService")
        self.converter = DocumentConverter()

    def validate_pdf(self, file_path: str) -> bool:
        """
        Verifica se o arquivo existe e é um PDF válido.

        Args:
            file_path (str): Caminho do arquivo a ser validado.

        Returns:
            bool: True se o arquivo existir e for um PDF válido, False caso contrário.
        """
        logger.info(f"Validando arquivo PDF: {file_path}")
        
        # Verifica se o arquivo existe
        if not os.path.isfile(file_path):
            logger.error(f"O arquivo não existe: {file_path}")
            return False
        
        # Verifica se o arquivo tem extensão .pdf
        if not file_path.lower().endswith('.pdf'):
            logger.error(f"O arquivo não tem extensão .pdf: {file_path}")
            return False
        
        # Tenta abrir o arquivo para verificar se é um PDF válido
        try:
            with open(file_path, 'rb') as f:
                header = f.read(5)
                # Verifica se o cabeçalho começa com '%PDF-'
                if header == b'%PDF-':
                    logger.info(f"Arquivo validado com sucesso: {file_path}")
                    return True
                else:
                    logger.error(f"O arquivo não tem o cabeçalho de PDF válido. Cabeçalho encontrado: {header}")
                    return False
        except Exception as e:
            logger.error(f"Erro ao abrir o arquivo: {str(e)}")
            return False

    def convert_pdf_to_markdown(self, file_path: str) -> str:
        """
        Converte um arquivo PDF para Markdown.

        Args:
            file_path (str): Caminho do arquivo PDF a ser convertido.

        Returns:
            str: Conteúdo do arquivo em formato Markdown.

        Raises:
            ValueError: Se o arquivo não existir, não for um PDF válido ou 
                       se ocorrer um erro durante a conversão.
        """
        logger.info(f"Iniciando conversão do PDF para Markdown: {file_path}")
        
        # Valida o arquivo
        if not self.validate_pdf(file_path):
            logger.error(f"Falha na validação do arquivo: {file_path}")
            raise ValueError(f"Arquivo inválido ou não encontrado: {file_path}")
        
        try:
            # Converte o PDF para Markdown usando o docling
            logger.info(f"Executando conversão com docling: {file_path}")
            result = self.converter.convert(file_path)
            markdown = result.document.export_to_markdown()
            logger.info(f"Conversão concluída com sucesso para: {file_path}")
            return markdown
        except Exception as e:
            logger.error(f"Erro durante a conversão do PDF para Markdown: {str(e)}")
            raise ValueError(f"Erro ao converter o PDF para Markdown: {str(e)}") 