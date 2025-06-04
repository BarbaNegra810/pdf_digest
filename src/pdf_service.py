"""
Serviço para validação e conversão de arquivos PDF para Markdown.
"""
import os
import logging
import torch
import re
from pathlib import Path
from typing import Any, List, Tuple

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
        
        # Configura o dispositivo (GPU se disponível, CPU caso contrário)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Usando dispositivo: {self.device}")
        
        # Inicializa o conversor
        self.converter = DocumentConverter()
        
        # Move o modelo para o dispositivo apropriado se possível
        if hasattr(self.converter, 'model') and hasattr(self.converter.model, 'to'):
            self.converter.model.to(self.device)
            logger.info(f"Modelo movido para {self.device}")

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

    def _split_by_nota_negociacao(self, markdown: str) -> List[Tuple[int, str]]:
        """
        Divide o markdown em seções baseado no marcador "NOTA DE NEGOCIAÇÃO".
        
        Args:
            markdown (str): Conteúdo completo em markdown
            
        Returns:
            List[Tuple[int, str]]: Lista de tuplas (número da página, conteúdo)
        """
        # Encontra todas as ocorrências de "NOTA DE NEGOCIAÇÃO"
        matches = list(re.finditer(r'NOTA DE NEGOCIAÇÃO', markdown, re.IGNORECASE))
        
        if not matches:
            logger.warning("Nenhuma ocorrência de 'NOTA DE NEGOCIAÇÃO' encontrada")
            return [(1, markdown)]
            
        pages = []
        for i, match in enumerate(matches):
            start_pos = match.start()
            
            # Se for a última ocorrência, vai até o final do texto
            if i == len(matches) - 1:
                content = markdown[start_pos:]
            else:
                # Caso contrário, vai até o início da próxima ocorrência
                end_pos = matches[i + 1].start()
                content = markdown[start_pos:end_pos]
            
            pages.append((i + 1, content.strip()))
            
        return pages

    def convert_pdf_to_markdown(self, file_path: str) -> dict:
        """
        Converte um arquivo PDF para Markdown, separando por ocorrências de "NOTA DE NEGOCIAÇÃO".

        Args:
            file_path (str): Caminho do arquivo PDF a ser convertido.

        Returns:
            dict: Dicionário com o conteúdo de cada nota em formato Markdown.
                 Chaves são números (1-indexed) e valores são strings markdown.

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
            
            # Verifica se o resultado da conversão é válido
            if not result or not hasattr(result, 'document'):
                logger.error("Resultado da conversão inválido ou vazio")
                raise ValueError("Falha ao converter o documento: resultado inválido")
            
            # Converte o documento inteiro para markdown
            markdown = result.document.export_to_markdown()
            
            # Divide o markdown em páginas baseado no marcador
            pages = self._split_by_nota_negociacao(markdown)
            logger.info(f"Documento dividido em {len(pages)} notas de negociação")
            
            # Converte a lista de tuplas em um dicionário
            pages_markdown = {page_num: content for page_num, content in pages}
            
            logger.info(f"Conversão concluída com sucesso para: {file_path}")
            return pages_markdown
            
        except Exception as e:
            logger.error(f"Erro durante a conversão do PDF para Markdown: {str(e)}")
            raise ValueError(f"Erro ao converter o PDF para Markdown: {str(e)}") 