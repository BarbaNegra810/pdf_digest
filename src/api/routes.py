"""
Rotas da API do PDF Digest.
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from flask import Blueprint, request, jsonify

from src.config.settings import settings
from src.services.pdf_service import pdf_service
from src.services.file_service import file_service
from src.services.cache_service import cache_service
from src.api.middlewares import rate_limit_middleware
from src.utils.exceptions import PDFDigestException, ValidationError, SecurityError, ConversionError
from src.utils.helpers import create_response, get_disk_usage, get_memory_usage

logger = logging.getLogger(__name__)

# Blueprint para as rotas da API
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/health', methods=['GET'])
def health_check() -> Dict[str, Any]:
    """
    Endpoint para verificar a saúde da API.
    
    Returns:
        Dict com status detalhado da API
    """
    logger.debug("Verificação de saúde solicitada")
    
    try:
        # Testa componentes críticos
        checks = {
            'api': True,
            'pdf_service': True,
            'cache': cache_service.test_connection(),
            'disk_space': get_disk_usage() < 90,
            'memory_usage': get_memory_usage() < 85,
            'gpu_available': pdf_service.get_device_info()['gpu_available']
        }
        
        # Status geral
        overall_status = 'healthy' if all(checks.values()) else 'degraded'
        
        response_data = {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'checks': checks,
            'system_info': {
                'disk_usage_percent': round(get_disk_usage(), 2),
                'memory_usage_percent': round(get_memory_usage(), 2),
                'upload_folder': settings.upload_folder,
                'max_file_size_mb': settings.max_content_length / (1024 * 1024)
            }
        }
        
        status_code = 200 if overall_status == 'healthy' else 503
        return jsonify(create_response(True, response_data)), status_code
        
    except Exception as e:
        logger.error(f"Erro durante verificação de saúde: {e}")
        return jsonify(create_response(
            False, 
            error="Erro durante verificação de saúde",
            code="HEALTH_CHECK_ERROR",
            details={'error': str(e)}
        )), 500


@api_bp.route('/convert', methods=['POST'])
@rate_limit_middleware()
def convert_pdf() -> Dict[str, Any]:
    """
    Endpoint para converter um arquivo PDF para Markdown.
    
    Aceita dois formatos:
    1. Upload de arquivo via multipart/form-data
    2. JSON com caminho do arquivo no servidor
    
    Returns:
        Dict com resultado da conversão ou erro
    """
    logger.info(f"Nova requisição de conversão: {request.method} {request.path}")
    
    file_info = None
    temp_file_path = None
    
    try:
        # Determina o tipo de requisição e processa o arquivo
        if request.files and 'file' in request.files:
            # Opção 1: Upload de arquivo
            logger.info("Processando upload de arquivo")
            uploaded_file = request.files['file']
            
            file_info = file_service.save_uploaded_file(uploaded_file)
            temp_file_path = file_info['file_path']
            
        elif request.json and 'path' in request.json:
            # Opção 2: Arquivo já existe no servidor
            logger.info("Processando arquivo existente no servidor")
            
            file_path = request.json['path']
            
            # Se path é um diretório e filename está presente
            if 'filename' in request.json:
                file_path = os.path.join(file_path, request.json['filename'])
            
            file_info = file_service.validate_existing_file(file_path)
            temp_file_path = file_info['file_path']
            
        else:
            return jsonify(create_response(
                False,
                error="Nenhum arquivo fornecido",
                code="NO_FILE_PROVIDED",
                details={
                    'instructions': 'Envie um arquivo PDF no campo "file" ou forneça "path" no JSON'
                }
            )), 400
        
        # Executa a conversão usando o método adaptativo
        logger.info(f"Iniciando conversão do arquivo: {temp_file_path}")
        conversion_result = pdf_service.convert_pdf_adaptive(temp_file_path)
        
        # Prepara resposta de sucesso baseada no processador usado
        if conversion_result.get('processor') == 'agno':
            # Resposta para processamento com Agno (JSON estruturado)
            response_data = {
                'processor': 'agno',
                'format': 'json',
                'trades': conversion_result['data']['trades'],
                'fees': conversion_result['data']['fees'],
                'file_info': {
                    'filename': file_info.get('filename', file_info.get('original_filename')),
                    'size_bytes': file_info['file_size'],
                    'size_formatted': file_info['file_size_formatted'],
                    'hash': file_info['file_hash']
                },
                'processing_info': {
                    'total_trades': conversion_result['summary']['total_trades'],
                    'total_fees': conversion_result['summary']['total_fees'],
                    'processor_info': conversion_result['summary']['processing_info']
                }
            }
        else:
            # Resposta para processamento com Docling (Markdown - comportamento original)
            response_data = {
                'processor': 'docling',
                'format': 'markdown',
                'pages': conversion_result['data'],
                'file_info': {
                    'filename': file_info.get('filename', file_info.get('original_filename')),
                    'size_bytes': file_info['file_size'],
                    'size_formatted': file_info['file_size_formatted'],
                    'hash': file_info['file_hash'],
                    'pages_count': len(conversion_result['data'])
                },
                'processing_info': {
                    'device': str(pdf_service.device),
                    'cached': False,  # TODO: Implementar detecção de cache
                    'processor_info': conversion_result['summary']['processing_info']
                }
            }
        
        if conversion_result.get('processor') == 'agno':
            logger.info(f"Conversão concluída com sucesso: {conversion_result['summary']['total_trades']} trades, {conversion_result['summary']['total_fees']} fees")
        else:
            logger.info(f"Conversão concluída com sucesso: {conversion_result['summary']['total_pages']} páginas")
        return jsonify(create_response(True, response_data))
        
    except ValidationError as e:
        logger.warning(f"Erro de validação: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="VALIDATION_ERROR"
        )), 400
        
    except SecurityError as e:
        logger.warning(f"Erro de segurança: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="SECURITY_ERROR"
        )), 400
        
    except ConversionError as e:
        logger.error(f"Erro de conversão: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="CONVERSION_ERROR"
        )), 422
        
    except PDFDigestException as e:
        logger.error(f"Erro do PDF Digest: {e}")
        return jsonify(create_response(
            False,
            error=e.message,
            code=e.code,
            details=e.details
        )), 500
        
    except Exception as e:
        logger.exception(f"Erro inesperado durante conversão: {e}")
        return jsonify(create_response(
            False,
            error="Erro inesperado durante conversão",
            code="UNEXPECTED_ERROR",
            details={'error': str(e)}
        )), 500
        
    finally:
        # Limpa arquivo temporário se foi um upload
        if temp_file_path and 'uploaded_file' in locals():
            file_service.cleanup_file(temp_file_path)


@api_bp.route('/extract-tables', methods=['POST'])
@rate_limit_middleware()
def extract_tables() -> Dict[str, Any]:
    """
    Endpoint para extração avançada de tabelas de PDFs.
    
    Aceita dois formatos:
    1. Upload de arquivo via multipart/form-data
    2. JSON com caminho do arquivo no servidor
    
    Query parameters:
    - format: Formato de export ('json', 'csv', 'excel', 'html') - padrão: 'json'
    - save_files: Se deve salvar arquivos (true/false) - padrão: false
    
    Returns:
        Dict com tabelas extraídas em formato estruturado
    """
    logger.info(f"Nova requisição de extração de tabelas: {request.method} {request.path}")
    
    file_info = None
    temp_file_path = None
    
    try:
        # Obtém parâmetros da query string
        export_format = request.args.get('format', 'json').lower()
        save_files = request.args.get('save_files', 'false').lower() == 'true'
        
        # Valida formato de export
        valid_formats = ['json', 'csv', 'excel', 'html']
        if export_format not in valid_formats:
            return jsonify(create_response(
                False,
                error=f"Formato inválido: {export_format}. Formatos válidos: {', '.join(valid_formats)}",
                code="INVALID_FORMAT"
            )), 400
        
        # Determina o tipo de requisição e processa o arquivo
        if request.files and 'file' in request.files:
            # Opção 1: Upload de arquivo
            logger.info("Processando upload de arquivo para extração de tabelas")
            uploaded_file = request.files['file']
            
            file_info = file_service.save_uploaded_file(uploaded_file)
            temp_file_path = file_info['file_path']
            
        elif request.json and 'path' in request.json:
            # Opção 2: Arquivo já existe no servidor
            logger.info("Processando arquivo existente para extração de tabelas")
            
            file_path = request.json['path']
            
            # Se path é um diretório e filename está presente
            if 'filename' in request.json:
                file_path = os.path.join(file_path, request.json['filename'])
            
            file_info = file_service.validate_existing_file(file_path)
            temp_file_path = file_info['file_path']
            
        else:
            return jsonify(create_response(
                False,
                error="Nenhum arquivo fornecido",
                code="NO_FILE_PROVIDED",
                details={
                    'instructions': 'Envie um arquivo PDF no campo "file" ou forneça "path" no JSON'
                }
            )), 400
        
        # Executa a extração avançada de tabelas
        logger.info(f"Iniciando extração de tabelas: {temp_file_path} (formato: {export_format})")
        tables_result = pdf_service.extract_tables_advanced(temp_file_path, export_format)
        
        # Salva arquivos se solicitado
        saved_files = {}
        if save_files and tables_result['tables']:
            try:
                # Cria diretório baseado no nome do arquivo
                base_name = Path(file_info.get('filename', 'unknown')).stem
                output_dir = f"tables_output/{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                saved_files = pdf_service.save_tables_to_files(tables_result, output_dir)
                logger.info(f"Tabelas salvas em arquivos: {output_dir}")
            except Exception as e:
                logger.warning(f"Erro ao salvar arquivos: {e}")
                saved_files = {'error': str(e)}
        
        # Prepara resposta de sucesso
        response_data = {
            'tables': tables_result['tables'],
            'metadata': tables_result['metadata'],
            'file_info': {
                'filename': file_info.get('filename', file_info.get('original_filename')),
                'size_bytes': file_info['file_size'],
                'size_formatted': file_info['file_size_formatted'],
                'hash': file_info['file_hash']
            },
            'export_info': {
                'format': export_format,
                'files_saved': save_files,
                'saved_files': saved_files if save_files else None
            }
        }
        
        logger.info(f"Extração de tabelas concluída: {len(tables_result['tables'])} tabelas encontradas")
        return jsonify(create_response(True, response_data))
        
    except ValidationError as e:
        logger.warning(f"Erro de validação: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="VALIDATION_ERROR"
        )), 400
        
    except SecurityError as e:
        logger.warning(f"Erro de segurança: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="SECURITY_ERROR"
        )), 400
        
    except ConversionError as e:
        logger.error(f"Erro de extração: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="EXTRACTION_ERROR"
        )), 422
        
    except PDFDigestException as e:
        logger.error(f"Erro do PDF Digest: {e}")
        return jsonify(create_response(
            False,
            error=e.message,
            code=e.code,
            details=e.details
        )), 500
        
    except Exception as e:
        logger.exception(f"Erro inesperado durante extração de tabelas: {e}")
        return jsonify(create_response(
            False,
            error="Erro inesperado durante extração de tabelas",
            code="UNEXPECTED_ERROR",
            details={'error': str(e)}
        )), 500
        
    finally:
        # Limpa arquivo temporário se foi um upload
        if temp_file_path and 'uploaded_file' in locals():
            file_service.cleanup_file(temp_file_path)


@api_bp.route('/extract-b3-trades', methods=['POST'])
@rate_limit_middleware()
def extract_b3_trades() -> Dict[str, Any]:
    """
    Endpoint específico para extrair trades e fees de notas de corretagem da B3.
    
    Sempre usa o processador Agno para extração estruturada de dados.
    
    Aceita dois formatos:
    1. Upload de arquivo via multipart/form-data
    2. JSON com caminho do arquivo no servidor
    
    Returns:
        Dict com trades e fees extraídos em formato JSON estruturado
    """
    logger.info(f"Nova requisição de extração B3: {request.method} {request.path}")
    
    file_info = None
    temp_file_path = None
    
    try:
        # Determina o tipo de requisição e processa o arquivo
        if request.files and 'file' in request.files:
            # Opção 1: Upload de arquivo
            logger.info("Processando upload de arquivo para extração B3")
            uploaded_file = request.files['file']
            
            file_info = file_service.save_uploaded_file(uploaded_file)
            temp_file_path = file_info['file_path']
            
        elif request.json and 'path' in request.json:
            # Opção 2: Arquivo já existe no servidor
            logger.info("Processando arquivo existente para extração B3")
            
            file_path = request.json['path']
            
            # Se path é um diretório e filename está presente
            if 'filename' in request.json:
                file_path = os.path.join(file_path, request.json['filename'])
            
            file_info = file_service.validate_existing_file(file_path)
            temp_file_path = file_info['file_path']
            
        else:
            return jsonify(create_response(
                False,
                error="Nenhum arquivo fornecido",
                code="NO_FILE_PROVIDED",
                details={
                    'instructions': 'Envie um arquivo PDF no campo "file" ou forneça "path" no JSON'
                }
            )), 400
        
        # Força uso do Agno para esta extração
        from src.services.agno_service import agno_service
        if agno_service is None:
            return jsonify(create_response(
                False,
                error="Serviço Agno não disponível",
                code="AGNO_UNAVAILABLE",
                details={'message': 'Framework Agno não está configurado ou disponível'}
            )), 503
        
        # Executa extração com Agno
        logger.info(f"Iniciando extração B3 com Agno: {temp_file_path}")
        extraction_result = agno_service.extract_trades_and_fees(temp_file_path)
        
        # Prepara resposta de sucesso
        response_data = {
            'trades': extraction_result['trades'],
            'fees': extraction_result['fees'],
            'file_info': {
                'filename': file_info.get('filename', file_info.get('original_filename')),
                'size_bytes': file_info['file_size'],
                'size_formatted': file_info['file_size_formatted'],
                'hash': file_info['file_hash']
            },
            'processing_info': {
                'processor': 'agno',
                'total_trades': len(extraction_result['trades']),
                'total_fees': len(extraction_result['fees']),
                'schema_version': '1.0',
                'extraction_method': 'b3_structured'
            }
        }
        
        logger.info(f"Extração B3 concluída: {len(extraction_result['trades'])} trades, {len(extraction_result['fees'])} fees")
        return jsonify(create_response(True, response_data))
        
    except ValidationError as e:
        logger.warning(f"Erro de validação: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="VALIDATION_ERROR"
        )), 400
        
    except SecurityError as e:
        logger.warning(f"Erro de segurança: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="SECURITY_ERROR"
        )), 400
        
    except ConversionError as e:
        logger.error(f"Erro de extração: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="EXTRACTION_ERROR"
        )), 422
        
    except PDFDigestException as e:
        logger.error(f"Erro do PDF Digest: {e}")
        return jsonify(create_response(
            False,
            error=e.message,
            code=e.code,
            details=e.details
        )), 500
        
    except Exception as e:
        logger.exception(f"Erro inesperado durante extração B3: {e}")
        return jsonify(create_response(
            False,
            error="Erro inesperado durante extração B3",
            code="UNEXPECTED_ERROR",
            details={'error': str(e)}
        )), 500
        
    finally:
        # Limpa arquivo temporário se foi um upload
        if temp_file_path and 'uploaded_file' in locals():
            file_service.cleanup_file(temp_file_path)


@api_bp.route('/convert-enhanced', methods=['POST'])
@rate_limit_middleware()
def convert_pdf_enhanced() -> Dict[str, Any]:
    """
    Endpoint para conversão avançada de PDF com extração de tabelas em separado.
    
    Combina a conversão tradicional para Markdown com extração estruturada de tabelas.
    
    Query parameters:
    - include_tables: Se deve incluir extração de tabelas (true/false) - padrão: true
    - table_format: Formato das tabelas ('json', 'csv', 'excel', 'html') - padrão: 'json'
    
    Returns:
        Dict com markdown e tabelas extraídas
    """
    logger.info(f"Nova requisição de conversão avançada: {request.method} {request.path}")
    
    file_info = None
    temp_file_path = None
    
    try:
        # Obtém parâmetros da query string
        include_tables = request.args.get('include_tables', 'true').lower() == 'true'
        table_format = request.args.get('table_format', 'json').lower()
        
        # Valida formato de tabela
        valid_formats = ['json', 'csv', 'excel', 'html']
        if include_tables and table_format not in valid_formats:
            return jsonify(create_response(
                False,
                error=f"Formato de tabela inválido: {table_format}. Formatos válidos: {', '.join(valid_formats)}",
                code="INVALID_TABLE_FORMAT"
            )), 400
        
        # Determina o tipo de requisição e processa o arquivo
        if request.files and 'file' in request.files:
            # Opção 1: Upload de arquivo
            logger.info("Processando upload de arquivo para conversão avançada")
            uploaded_file = request.files['file']
            
            file_info = file_service.save_uploaded_file(uploaded_file)
            temp_file_path = file_info['file_path']
            
        elif request.json and 'path' in request.json:
            # Opção 2: Arquivo já existe no servidor
            logger.info("Processando arquivo existente para conversão avançada")
            
            file_path = request.json['path']
            
            # Se path é um diretório e filename está presente
            if 'filename' in request.json:
                file_path = os.path.join(file_path, request.json['filename'])
            
            file_info = file_service.validate_existing_file(file_path)
            temp_file_path = file_info['file_path']
            
        else:
            return jsonify(create_response(
                False,
                error="Nenhum arquivo fornecido",
                code="NO_FILE_PROVIDED",
                details={
                    'instructions': 'Envie um arquivo PDF no campo "file" ou forneça "path" no JSON'
                }
            )), 400
        
        # Executa conversão tradicional para Markdown
        logger.info(f"Iniciando conversão avançada: {temp_file_path}")
        markdown_result = pdf_service.convert_pdf_to_markdown(temp_file_path)
        
        # Executa extração de tabelas se solicitado
        tables_result = None
        if include_tables:
            try:
                logger.info(f"Extraindo tabelas em formato {table_format}")
                tables_result = pdf_service.extract_tables_advanced(temp_file_path, table_format)
            except Exception as e:
                logger.warning(f"Erro na extração de tabelas: {e}")
                tables_result = {
                    'tables': [],
                    'metadata': {'error': str(e), 'total_tables': 0}
                }
        
        # Prepara resposta de sucesso
        response_data = {
            'markdown': {
                'pages': markdown_result,
                'pages_count': len(markdown_result)
            },
            'tables': tables_result if include_tables else None,
            'file_info': {
                'filename': file_info.get('filename', file_info.get('original_filename')),
                'size_bytes': file_info['file_size'],
                'size_formatted': file_info['file_size_formatted'],
                'hash': file_info['file_hash']
            },
            'processing_info': {
                'device': str(pdf_service.device),
                'markdown_extraction': True,
                'table_extraction': include_tables,
                'table_format': table_format if include_tables else None
            }
        }
        
        total_tables = tables_result['metadata']['total_tables'] if tables_result else 0
        logger.info(f"Conversão avançada concluída: {len(markdown_result)} páginas, {total_tables} tabelas")
        return jsonify(create_response(True, response_data))
        
    except ValidationError as e:
        logger.warning(f"Erro de validação: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="VALIDATION_ERROR"
        )), 400
        
    except SecurityError as e:
        logger.warning(f"Erro de segurança: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="SECURITY_ERROR"
        )), 400
        
    except ConversionError as e:
        logger.error(f"Erro de conversão: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="CONVERSION_ERROR"
        )), 422
        
    except PDFDigestException as e:
        logger.error(f"Erro do PDF Digest: {e}")
        return jsonify(create_response(
            False,
            error=e.message,
            code=e.code,
            details=e.details
        )), 500
        
    except Exception as e:
        logger.exception(f"Erro inesperado durante conversão avançada: {e}")
        return jsonify(create_response(
            False,
            error="Erro inesperado durante conversão avançada",
            code="UNEXPECTED_ERROR",
            details={'error': str(e)}
        )), 500
        
    finally:
        # Limpa arquivo temporário se foi um upload
        if temp_file_path and 'uploaded_file' in locals():
            file_service.cleanup_file(temp_file_path)


@api_bp.route('/stats', methods=['GET'])
def get_stats() -> Dict[str, Any]:
    """
    Endpoint para obter estatísticas do sistema.
    
    Returns:
        Dict com estatísticas detalhadas
    """
    logger.debug("Solicitação de estatísticas")
    
    try:
        stats_data = {
            'system': {
                'disk_usage_percent': round(get_disk_usage(), 2),
                'memory_usage_percent': round(get_memory_usage(), 2),
                'timestamp': datetime.utcnow().isoformat()
            },
            'upload': file_service.get_upload_stats(),
            'cache': cache_service.get_stats(),
            'device': pdf_service.get_device_info(),
            'settings': {
                'max_file_size_mb': settings.max_content_length / (1024 * 1024),
                'allowed_extensions': settings.allowed_extensions,
                'cache_enabled': settings.cache_enabled,
                'gpu_enabled': settings.gpu_enabled
            }
        }
        
        return jsonify(create_response(True, stats_data))
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return jsonify(create_response(
            False,
            error="Erro ao obter estatísticas",
            code="STATS_ERROR",
            details={'error': str(e)}
        )), 500


@api_bp.route('/cache/clear', methods=['POST'])
def clear_cache() -> Dict[str, Any]:
    """
    Endpoint para limpar o cache.
    
    Returns:
        Dict com resultado da operação
    """
    logger.info("Solicitação de limpeza de cache")
    
    try:
        success = pdf_service.clear_cache()
        
        if success:
            logger.info("Cache limpo com sucesso")
            return jsonify(create_response(
                True,
                {'message': 'Cache limpo com sucesso'}
            ))
        else:
            return jsonify(create_response(
                False,
                error="Falha ao limpar cache",
                code="CACHE_CLEAR_FAILED"
            )), 500
            
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {e}")
        return jsonify(create_response(
            False,
            error="Erro ao limpar cache",
            code="CACHE_ERROR",
            details={'error': str(e)}
        )), 500


@api_bp.route('/cleanup', methods=['POST'])
def cleanup_old_files() -> Dict[str, Any]:
    """
    Endpoint para limpar arquivos antigos.
    
    Returns:
        Dict com resultado da limpeza
    """
    logger.info("Solicitação de limpeza de arquivos antigos")
    
    try:
        # Obtém parâmetro de idade máxima (padrão: 24 horas)
        max_age_hours = request.json.get('max_age_hours', 24) if request.json else 24
        
        if not isinstance(max_age_hours, (int, float)) or max_age_hours <= 0:
            return jsonify(create_response(
                False,
                error="max_age_hours deve ser um número positivo",
                code="INVALID_PARAMETER"
            )), 400
        
        removed_count = file_service.cleanup_old_files(max_age_hours)
        
        logger.info(f"Limpeza concluída: {removed_count} arquivos removidos")
        return jsonify(create_response(
            True,
            {
                'message': f'Limpeza concluída',
                'removed_files': removed_count,
                'max_age_hours': max_age_hours
            }
        ))
        
    except Exception as e:
        logger.error(f"Erro durante limpeza: {e}")
        return jsonify(create_response(
            False,
            error="Erro durante limpeza",
            code="CLEANUP_ERROR",
            details={'error': str(e)}
        )), 500


@api_bp.route('/info', methods=['GET'])
def get_info() -> Dict[str, Any]:
    """
    Endpoint para obter informações sobre a API.
    
    Returns:
        Dict com informações da API
    """
    info_data = {
        'name': 'PDF Digest API',
        'version': '1.0.0',
        'description': 'API para conversão de PDFs em Markdown',
        'endpoints': {
            '/api/health': 'Verificação de saúde',
            '/api/convert': 'Conversão adaptativa (Docling/Agno conforme configuração)',
            '/api/extract-b3-trades': 'Extração de trades e fees de notas B3 (sempre Agno)',
            '/api/extract-tables': 'Extração avançada de tabelas',
            '/api/convert-enhanced': 'Conversão avançada com tabelas',
            '/api/stats': 'Estatísticas do sistema',
            '/api/cache/clear': 'Limpeza de cache',
            '/api/cleanup': 'Limpeza de arquivos antigos',
            '/api/info': 'Informações da API'
        },
        'limits': {
            'max_file_size_mb': settings.max_content_length / (1024 * 1024),
            'allowed_extensions': settings.allowed_extensions,
            'rate_limits': {
                'per_minute': settings.rate_limit_per_minute,
                'per_hour': settings.rate_limit_per_hour,
                'per_day': settings.rate_limit_per_day
            }
        }
    }
    
    return jsonify(create_response(True, info_data))


@api_bp.route('/debug-pdf-content', methods=['POST'])
@rate_limit_middleware()
def debug_pdf_content() -> Dict[str, Any]:
    """
    Endpoint para debug do conteúdo bruto lido do PDF.
    
    Mostra exatamente como o texto está sendo extraído pelo Agno
    para ajudar a diagnosticar problemas de extração.
    
    Aceita dois formatos:
    1. Upload de arquivo via multipart/form-data
    2. JSON com caminho do arquivo no servidor
    
    Returns:
        Dict com conteúdo bruto extraído e informações de debug
    """
    logger.info(f"Nova requisição de debug PDF: {request.method} {request.path}")
    
    file_info = None
    temp_file_path = None
    
    try:
        # Determina o tipo de requisição e processa o arquivo
        if request.files and 'file' in request.files:
            # Opção 1: Upload de arquivo
            logger.info("Processando upload de arquivo para debug")
            uploaded_file = request.files['file']
            
            file_info = file_service.save_uploaded_file(uploaded_file)
            temp_file_path = file_info['file_path']
            
        elif request.json and 'path' in request.json:
            # Opção 2: Arquivo já existe no servidor
            logger.info("Processando arquivo existente para debug")
            
            file_path = request.json['path']
            
            # Se path é um diretório e filename está presente
            if 'filename' in request.json:
                file_path = os.path.join(file_path, request.json['filename'])
            
            file_info = file_service.validate_existing_file(file_path)
            temp_file_path = file_info['file_path']
            
        else:
            return jsonify(create_response(
                False,
                error="Nenhum arquivo fornecido",
                code="NO_FILE_PROVIDED",
                details={
                    'instructions': 'Envie um arquivo PDF no campo "file" ou forneça "path" no JSON'
                }
            )), 400
        
        # Força uso do Agno para esta extração de debug
        from src.services.agno_service import agno_service
        if agno_service is None:
            return jsonify(create_response(
                False,
                error="Serviço Agno não disponível",
                code="AGNO_UNAVAILABLE",
                details={'message': 'Framework Agno não está configurado ou disponível'}
            )), 503
        
        # Executa debug da extração com conteúdo bruto
        logger.info(f"Iniciando debug de extração: {temp_file_path}")
        debug_result = agno_service.debug_extraction_with_raw_content(temp_file_path)
        
        # Prepara resposta de sucesso
        response_data = {
            'file_info': {
                'filename': file_info.get('filename', file_info.get('original_filename')),
                'size_bytes': file_info['file_size'],
                'size_formatted': file_info['file_size_formatted'],
                'hash': file_info['file_hash']
            },
            'raw_content': debug_result['raw_content'],
            'debug_info': debug_result['debug_info'],
            'extraction_result': debug_result['extraction_result'],
            'analysis': {
                'content_available': any(len(content) > 0 for content in debug_result['raw_content'].values() 
                                       if isinstance(content, str) and not content.startswith('ERRO')),
                'extraction_successful': len(debug_result['extraction_result'].get('trades', [])) > 0 or 
                                       len(debug_result['extraction_result'].get('fees', [])) > 0,
                'libraries_status': {
                    'pypdf': debug_result['debug_info']['pypdf_available'],
                    'pdfminer': debug_result['debug_info']['pdfminer_available'],
                    'agno': debug_result['debug_info']['agno_available']
                }
            }
        }
        
        logger.info(f"Debug de extração concluído para: {temp_file_path}")
        return jsonify(create_response(True, response_data))
        
    except ValidationError as e:
        logger.warning(f"Erro de validação: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="VALIDATION_ERROR"
        )), 400
        
    except SecurityError as e:
        logger.warning(f"Erro de segurança: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="SECURITY_ERROR"
        )), 400
        
    except ConversionError as e:
        logger.error(f"Erro de extração: {e}")
        return jsonify(create_response(
            False,
            error=str(e),
            code="EXTRACTION_ERROR"
        )), 422
        
    except PDFDigestException as e:
        logger.error(f"Erro do PDF Digest: {e}")
        return jsonify(create_response(
            False,
            error=e.message,
            code=e.code,
            details=e.details
        )), 500
        
    except Exception as e:
        logger.exception(f"Erro inesperado durante debug: {e}")
        return jsonify(create_response(
            False,
            error="Erro inesperado durante debug",
            code="UNEXPECTED_ERROR",
            details={'error': str(e)}
        )), 500
        
    finally:
        # Limpa arquivo temporário se foi um upload
        if temp_file_path and 'uploaded_file' in locals():
            file_service.cleanup_file(temp_file_path) 