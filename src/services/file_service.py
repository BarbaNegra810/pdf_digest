"""
Serviço de gestão de arquivos para o PDF Digest.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from src.config.settings import settings
from src.utils.exceptions import ValidationError, SecurityError, FileProcessingError
from src.utils.helpers import clean_filename, calculate_file_hash, format_file_size

logger = logging.getLogger(__name__)


class FileService:
    """Serviço para gestão segura de arquivos."""
    
    def __init__(self):
        """Inicializa o serviço de arquivos."""
        self.upload_folder = settings.upload_folder
        self.max_size = settings.max_content_length
        self.allowed_extensions = settings.allowed_extensions
        
        # Garante que o diretório de upload existe
        Path(self.upload_folder).mkdir(parents=True, exist_ok=True)
    
    def validate_file_security(self, file_path: str) -> bool:
        """
        Realiza validação robusta de segurança do arquivo.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            True se o arquivo é seguro, False caso contrário
            
        Raises:                             
            SecurityError: Se detectada uma ameaça de segurança
        """
        try:
            # Verifica se o arquivo existe
            if not os.path.exists(file_path):
                raise SecurityError(f"Arquivo não encontrado: {file_path}")
            
            # Verifica tamanho do arquivo
            file_size = os.path.getsize(file_path)
            if file_size > self.max_size:
                raise SecurityError(
                    f"Arquivo muito grande: {format_file_size(file_size)}. "
                    f"Máximo permitido: {format_file_size(self.max_size)}"
                )
            
            if file_size == 0:
                raise SecurityError("Arquivo está vazio")
            
            # Verifica header PDF manualmente
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    raise SecurityError("Arquivo não é um PDF válido (header inválido)")
            
            # Verifica se não há path traversal no nome do arquivo
            normalized_path = os.path.normpath(file_path)
            if '..' in normalized_path or normalized_path.startswith('/'):
                raise SecurityError("Path traversal detectado no nome do arquivo")
            
            logger.info(f"Arquivo validado com sucesso: {file_path}")
            return True
            
        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"Erro durante validação de segurança: {e}")
            raise SecurityError(f"Erro durante validação: {e}")
    
    def save_uploaded_file(self, file: FileStorage) -> Dict[str, Any]:
        """
        Salva um arquivo enviado com validações de segurança.
        
        Args:
            file: Arquivo enviado
            
        Returns:
            Dicionário com informações do arquivo salvo
            
        Raises:
            ValidationError: Se a validação falhar
            SecurityError: Se detectada ameaça de segurança
        """
        file_path = None
        try:
            # Validações básicas
            if not file or not file.filename:
                raise ValidationError("Nenhum arquivo fornecido")
            
            if file.filename == '':
                raise ValidationError("Nome do arquivo está vazio")
            
            # Verifica extensão
            file_ext = Path(file.filename).suffix.lower()
            if file_ext not in self.allowed_extensions:
                raise ValidationError(
                    f"Extensão não permitida: {file_ext}. "
                    f"Permitidas: {', '.join(self.allowed_extensions)}"
                )
            
            # Limpa e protege o nome do arquivo
            clean_name = clean_filename(file.filename)
            secure_name = secure_filename(clean_name)
            
            # Gera nome único para evitar conflitos
            timestamp = int(__import__('time').time())
            unique_name = f"{timestamp}_{secure_name}"
            
            # Caminho completo do arquivo
            file_path = os.path.join(self.upload_folder, unique_name)
            
            # Salva o arquivo
            file.save(file_path)
            logger.info(f"Arquivo salvo: {file_path}")
            
            # Valida segurança do arquivo salvo
            self.validate_file_security(file_path)
            
            # Calcula informações do arquivo
            file_size = os.path.getsize(file_path)
            file_hash = calculate_file_hash(file_path)
            
            return {
                'original_filename': file.filename,
                'saved_filename': unique_name,
                'file_path': file_path,
                'file_size': file_size,
                'file_size_formatted': format_file_size(file_size),
                'file_hash': file_hash,
                'content_type': file.content_type
            }
            
        except (ValidationError, SecurityError):
            # Remove arquivo se foi salvo mas falhou na validação
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Arquivo removido após falha na validação: {file_path}")
                except Exception as cleanup_error:
                    logger.error(f"Erro ao remover arquivo após falha: {cleanup_error}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao salvar arquivo: {e}")
            raise FileProcessingError(f"Erro ao salvar arquivo: {e}")
    
    def validate_existing_file(self, file_path: str) -> Dict[str, Any]:
        """
        Valida um arquivo já existente no sistema.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            Dicionário com informações do arquivo
            
        Raises:
            ValidationError: Se a validação falhar
        """
        try:
            # Normaliza o caminho
            normalized_path = os.path.normpath(file_path)
            
            # Verifica se o arquivo existe
            if not os.path.exists(normalized_path):
                raise ValidationError(f"Arquivo não encontrado: {normalized_path}")
            
            # Verifica se é um arquivo (não diretório)
            if not os.path.isfile(normalized_path):
                raise ValidationError(f"Caminho não é um arquivo: {normalized_path}")
            
            # Valida segurança
            self.validate_file_security(normalized_path)
            
            # Coleta informações do arquivo
            file_size = os.path.getsize(normalized_path)
            file_hash = calculate_file_hash(normalized_path)
            filename = os.path.basename(normalized_path)
            
            return {
                'filename': filename,
                'file_path': normalized_path,
                'file_size': file_size,
                'file_size_formatted': format_file_size(file_size),
                'file_hash': file_hash
            }
            
        except (ValidationError, SecurityError):
            raise
        except Exception as e:
            logger.error(f"Erro ao validar arquivo existente: {e}")
            raise ValidationError(f"Erro na validação: {e}")
    
    def cleanup_file(self, file_path: str) -> bool:
        """
        Remove um arquivo de forma segura.
        
        Args:
            file_path: Caminho do arquivo
            
        Returns:
            True se removido com sucesso, False caso contrário
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Arquivo removido: {file_path}")
                return True
            else:
                logger.warning(f"Tentativa de remover arquivo inexistente: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Erro ao remover arquivo {file_path}: {e}")
            return False
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Remove arquivos antigos do diretório de upload.
        
        Args:
            max_age_hours: Idade máxima dos arquivos em horas
            
        Returns:
            Número de arquivos removidos
        """
        removed_count = 0
        max_age_seconds = max_age_hours * 3600
        current_time = __import__('time').time()
        
        try:
            for filename in os.listdir(self.upload_folder):
                file_path = os.path.join(self.upload_folder, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        if self.cleanup_file(file_path):
                            removed_count += 1
            
            logger.info(f"Limpeza concluída: {removed_count} arquivos removidos")
            return removed_count
            
        except Exception as e:
            logger.error(f"Erro durante limpeza de arquivos antigos: {e}")
            return removed_count
    
    def get_upload_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do diretório de upload.
        
        Returns:
            Dicionário com estatísticas
        """
        try:
            total_files = 0
            total_size = 0
            
            for filename in os.listdir(self.upload_folder):
                file_path = os.path.join(self.upload_folder, filename)
                if os.path.isfile(file_path):
                    total_files += 1
                    total_size += os.path.getsize(file_path)
            
            return {
                'upload_folder': self.upload_folder,
                'total_files': total_files,
                'total_size': total_size,
                'total_size_formatted': format_file_size(total_size),
                'max_file_size': self.max_size,
                'max_file_size_formatted': format_file_size(self.max_size),
                'allowed_extensions': self.allowed_extensions
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas de upload: {e}")
            return {'error': str(e)}


# Instância global do serviço de arquivos
file_service = FileService() 