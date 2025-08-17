"""
Serviço para validação e conversão de arquivos PDF usando exclusivamente o Agno.
"""
import os
import logging
from typing import Dict, List, Optional, Any

from src.config.settings import settings
from src.services.cache_service import cache_service
from src.utils.exceptions import ConversionError, ValidationError
from src.utils.helpers import calculate_file_hash

logger = logging.getLogger(__name__)


class PDFService:
    """
    Serviço para validar e converter PDFs usando exclusivamente o Agno.
    """

    def __init__(self):
        """
        Inicializa o PDFService que opera apenas com Agno.
        """
        logger.info("Inicializando PDFService - operação exclusiva com Agno")
        
        # Verifica disponibilidade do Agno
        try:
            from src.services.agno_service import agno_service
            if agno_service is None:
                raise ConversionError("Serviço Agno não disponível - necessário para operação")
            self.agno_service = agno_service
            logger.info("Serviço Agno disponível e configurado")
        except ImportError as e:
            logger.error(f"Falha ao importar Agno: {e}")
            raise ConversionError("Serviço Agno não disponível - sistema não pode operar")

    def validate_pdf(self, file_path: str) -> bool:
        """
        Verifica se o arquivo existe e é um PDF válido.

        Args:
            file_path (str): Caminho do arquivo a ser validado.

        Returns:
            bool: True se o arquivo existir e for um PDF válido, False caso contrário.
            
        Raises:
            ValidationError: Se a validação falhar
        """
        logger.debug(f"Validando arquivo PDF: {file_path}")
        
        try:
            # Verifica se o arquivo existe
            if not os.path.isfile(file_path):
                raise ValidationError(f"O arquivo não existe: {file_path}")
            
            # Verifica se o arquivo tem extensão .pdf
            if not file_path.lower().endswith('.pdf'):
                raise ValidationError(f"O arquivo não tem extensão .pdf: {file_path}")
            
            # Verifica tamanho do arquivo
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise ValidationError("O arquivo está vazio")
            
            if file_size > settings.max_content_length:
                raise ValidationError(
                    f"Arquivo muito grande: {file_size} bytes. "
                    f"Máximo permitido: {settings.max_content_length} bytes"
                )
            
            # Verifica cabeçalho PDF
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    raise ValidationError(
                        f"O arquivo não tem o cabeçalho de PDF válido. "
                        f"Cabeçalho encontrado: {header}"
                    )
            
            logger.debug(f"Arquivo validado com sucesso: {file_path}")
            return True
            
        except ValidationError:
            logger.error(f"Validação falhou para: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado durante validação: {e}")
            raise ValidationError(f"Erro durante validação: {e}")

    def convert_pdf_adaptive(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Converte PDF usando exclusivamente o Agno.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            use_cache (bool): Se deve usar cache
            
        Returns:
            Dict com resultado da conversão do Agno
            
        Raises:
            ValidationError: Se o arquivo não for válido
            ConversionError: Se houver erro na conversão
        """
        logger.info(f"Conversão com Agno iniciada para: {file_path}")
        
        try:
            # Valida o arquivo primeiro
            self.validate_pdf(file_path)
            
            # Usa o Agno para extração
            return self._convert_with_agno(file_path, use_cache)
                
        except Exception as e:
            logger.error(f"Erro na conversão: {e}")
            raise ConversionError(f"Falha na conversão: {e}")

    def _convert_with_agno(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Converte PDF usando o serviço Agno para extrair trades e fees.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            use_cache (bool): Se deve usar cache
            
        Returns:
            Dict com trades e fees extraídos
        """
        logger.info(f"Convertendo com Agno: {file_path}")
        
        # Extrai trades e fees usando Agno
        agno_result = self.agno_service.extract_trades_and_fees(file_path, use_cache)
        
        # Formata resultado para compatibilidade com a API
        result = {
            'processor': 'agno',
            'format': 'json',
            'data': agno_result,
            'summary': {
                'total_trades': len(agno_result.get('trades', [])),
                'total_fees': len(agno_result.get('fees', [])),
                'processing_info': self.agno_service.get_processing_info()
            }
        }
        
        logger.info(f"Conversão Agno concluída: {result['summary']['total_trades']} trades")
        return result

    def extract_b3_trades(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Extrai trades e fees de notas B3 usando Agno.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            use_cache (bool): Se deve usar cache
            
        Returns:
            Dict com trades e fees extraídos
        """
        logger.info(f"Extração B3 com Agno: {file_path}")
        return self._convert_with_agno(file_path, use_cache)

    def get_device_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o processamento (Agno).
        
        Returns:
            Dict com informações do processamento
        """
        return {
            'processor': 'agno',
            'service_available': self.agno_service is not None,
            'processing_info': self.agno_service.get_processing_info() if self.agno_service else None
        }
    
    def clear_cache(self) -> bool:
        """
        Limpa o cache de conversões.
        
        Returns:
            True se limpeza foi bem-sucedida
        """
        try:
            if cache_service.enabled:
                # Remove chaves relacionadas ao Agno
                return cache_service.clear_all()
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return False

    def debug_pdf_content(self, file_path: str) -> Dict[str, Any]:
        """
        Debug do conteúdo PDF usando Agno.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            
        Returns:
            Dict com informações de debug
        """
        logger.info(f"Debug PDF com Agno: {file_path}")
        
        if not self.agno_service:
            raise ConversionError("Serviço Agno não disponível para debug")
            
        return self.agno_service.debug_extraction_with_raw_content(file_path)


# Instância global do serviço PDF
pdf_service = PDFService()

# Import do serviço Agno (agora obrigatório)
try:
    from src.services.agno_service import agno_service
    AGNO_SERVICE_AVAILABLE = True
    logger.info("Serviço Agno carregado com sucesso")
except ImportError as e:
    logger.error(f"ERRO CRÍTICO: Serviço Agno não disponível: {e}")
    agno_service = None
    AGNO_SERVICE_AVAILABLE = False
    # Como agora só operamos com Agno, isso é um erro crítico
    raise ConversionError("Sistema não pode operar sem o serviço Agno")