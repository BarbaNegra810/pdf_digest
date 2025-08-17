"""
Aplicação Flask principal do PDF Digest.
"""
import logging
from flask import Flask

from src.config.settings import settings
from src.api.routes import api_bp
from src.api.middlewares import setup_all_middlewares

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """
    Factory function para criar e configurar a aplicação Flask.
    
    Returns:
        Instância configurada da aplicação Flask
    """
    # Cria a aplicação Flask
    app = Flask(__name__)
    
    # Configurações da aplicação
    app.config.update({
        'SECRET_KEY': settings.secret_key,
        'MAX_CONTENT_LENGTH': settings.max_content_length,
        'UPLOAD_FOLDER': settings.upload_folder,
        'DEBUG': settings.debug,
        'TESTING': False,
        'JSON_SORT_KEYS': False,
        'JSONIFY_PRETTYPRINT_REGULAR': True
    })
    
    # Configura todos os middlewares
    setup_all_middlewares(app)
    
    # Registra blueprints
    app.register_blueprint(api_bp)
    
    # Rota raiz básica
    @app.route('/')
    def root():
        return {
            'name': 'PDF Digest API',
            'version': '2.0.0',
            'status': 'running',
            'processor': 'agno',
            'description': 'API para extração de dados estruturados de PDFs usando Agno',
            'endpoints': {
                'health': '/api/health',
                'convert': '/api/convert',
                'extract-b3-trades': '/api/extract-b3-trades',
                'debug-pdf-content': '/api/debug-pdf-content',
                'stats': '/api/stats',
                'info': '/api/info'
            }
        }
    
    logger.info("Aplicação Flask configurada com sucesso")
    return app 