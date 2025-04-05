"""
API para serviço de conversão de PDF para Markdown.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Union

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from src.pdf_service import PDFService


# Configuração de logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
pdf_service = PDFService()

# Configuração para upload de arquivos
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    logger.info(f"Diretório de uploads criado: {UPLOAD_FOLDER}")
else:
    logger.info(f"Diretório de uploads já existe: {UPLOAD_FOLDER}")
    
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limita uploads a 16MB
logger.info(f"Tamanho máximo de upload definido: {app.config['MAX_CONTENT_LENGTH']/1024/1024}MB")


@app.route('/health', methods=['GET'])
def health_check() -> Dict[str, str]:
    """
    Endpoint para verificar a saúde da API.
    
    Returns:
        Dict[str, str]: Status da API.
    """
    logger.info("Verificação de saúde solicitada")
    return jsonify({'status': 'ok'})


@app.route('/api/convert', methods=['POST'])
def convert_pdf() -> Dict[str, Any]:
    """
    Endpoint para converter um arquivo PDF para Markdown.
    Espera receber um JSON com os seguintes campos:
    - path: caminho do diretório no servidor
    - filename: nome do arquivo (obrigatório quando path é um diretório)
    - file: arquivo enviado (opcional se path+filename forem fornecidos)
    
    Returns:
        Dict[str, Any]: Resultado da conversão ou mensagem de erro.
    """
    logger.info(f"Nova requisição de conversão recebida: {request.method} {request.path}")
    logger.debug(f"Headers: {dict(request.headers)}")
    logger.debug(f"Content-Type: {request.content_type}")
    
    try:
        # Verifica qual método está sendo usado: arquivo enviado ou caminho no servidor
        file_path = None
        
        # Log detalhado do conteúdo da requisição
        if request.content_type and 'application/json' in request.content_type:
            logger.info("Requisição JSON detectada")
            try:
                logger.debug(f"Corpo JSON: {request.get_json(silent=True)}")
            except Exception as e:
                logger.error(f"Erro ao processar JSON: {str(e)}")
        
        if request.files:
            logger.info(f"Arquivos detectados: {list(request.files.keys())}")
        
        if request.form:
            logger.info(f"Dados de formulário detectados: {list(request.form.keys())}")
        
        # Opção 1: JSON com path e opcionalmente filename
        if request.json:
            # Se ambos path e filename forem fornecidos, concatene-os
            if 'path' in request.json and 'filename' in request.json:
                base_path = request.json['path']
                filename = request.json['filename']
                file_path = os.path.join(base_path, filename)
                logger.info(f"Combinando path ({base_path}) e filename ({filename}): {file_path}")
            
            # Se apenas path for fornecido e for um arquivo completo
            elif 'path' in request.json:
                file_path = request.json['path']
                logger.info(f"Usando apenas o caminho fornecido: {file_path}")
            
            # Verifique se o arquivo existe
            if file_path:
                if not os.path.exists(file_path):
                    logger.error(f"Arquivo não encontrado: {file_path}")
                    return jsonify({'error': f'Arquivo não encontrado: {file_path}'}), 404
        
        # Opção 2: Arquivo enviado no request
        elif 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                logger.error("Arquivo enviado sem nome")
                return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
            
            # Salva o arquivo enviado
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            logger.info(f"Salvando arquivo enviado: {filename} -> {file_path}")
            file.save(file_path)
            logger.info(f"Arquivo salvo com sucesso: {file_path}")
            
            # Verifica se o arquivo foi realmente salvo
            if not os.path.exists(file_path):
                logger.error(f"Falha ao salvar o arquivo: {file_path}")
                return jsonify({'error': 'Falha ao salvar o arquivo enviado'}), 500
                
            logger.debug(f"Tamanho do arquivo salvo: {os.path.getsize(file_path)} bytes")
        
        else:
            logger.error("Nenhum arquivo ou caminho fornecido na requisição")
            return jsonify({
                'error': 'Nenhum arquivo ou caminho fornecido',
                'instruções': 'Envie um arquivo PDF no campo "file" ou forneça "path" e "filename" no JSON'
            }), 400

        # Valida e converte o PDF
        logger.info(f"Iniciando validação do PDF: {file_path}")
        is_valid = pdf_service.validate_pdf(file_path)
        if not is_valid:
            logger.error(f"Validação falhou para: {file_path}")
            return jsonify({'error': 'Arquivo inválido ou não é um PDF'}), 400
        
        # Converte o PDF para Markdown
        logger.info(f"Iniciando conversão para Markdown: {file_path}")
        markdown_content = pdf_service.convert_pdf_to_markdown(file_path)
        logger.info(f"Conversão concluída. Tamanho do conteúdo Markdown: {len(markdown_content)} caracteres")
        
        # Limpa o arquivo temporário se foi enviado (não se for um caminho)
        if 'file' in request.files:
            logger.info(f"Removendo arquivo temporário: {file_path}")
            try:
                os.remove(file_path)
                logger.info(f"Arquivo temporário removido com sucesso: {file_path}")
            except Exception as e:
                logger.warning(f"Não foi possível remover o arquivo temporário: {str(e)}")
        
        logger.info("Enviando resposta de sucesso")
        return jsonify({
            'success': True,
            'markdown': markdown_content
        })
    
    except ValueError as e:
        logger.error(f"Erro de validação: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.exception(f"Erro inesperado durante a conversão: {str(e)}")
        return jsonify({'error': f'Erro inesperado: {str(e)}'}), 500


def start_api(host: str = '0.0.0.0', port: int = 5000, debug: bool = True) -> None:
    """
    Inicia o servidor da API.
    
    Args:
        host (str): Host para iniciar o servidor. Por padrão, '0.0.0.0'.
        port (int): Porta para iniciar o servidor. Por padrão, 5000.
        debug (bool): Se True, inicia o servidor em modo debug. Por padrão, False.
    """
    logger.info(f"Iniciando o servidor em {host}:{port} (debug: {debug})")
    app.run(host=host, port=port, debug=debug) 