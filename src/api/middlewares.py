"""
Middlewares para a API do PDF Digest.
"""
import time
import logging
from functools import wraps
from typing import Dict, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta

from flask import Flask, request, jsonify, g
from werkzeug.exceptions import TooManyRequests

from src.config.settings import settings
from src.utils.exceptions import RateLimitExceeded
from src.utils.helpers import sanitize_log_data

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter simples em memória."""
    
    def __init__(self):
        self.requests = defaultdict(lambda: {
            'minute': deque(),
            'hour': deque(), 
            'day': deque()
        })
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Verifica se a requisição está dentro dos limites.
        
        Args:
            identifier: Identificador único (IP, user_id, etc.)
            
        Returns:
            True se permitido, False caso contrário
        """
        now = datetime.now()
        user_requests = self.requests[identifier]
        
        # Limpa requisições antigas
        self._cleanup_old_requests(user_requests, now)
        
        # Verifica limites
        limits = [
            (user_requests['minute'], settings.rate_limit_per_minute, 60),
            (user_requests['hour'], settings.rate_limit_per_hour, 3600),
            (user_requests['day'], settings.rate_limit_per_day, 86400)
        ]
        
        for request_queue, limit, window in limits:
            if len(request_queue) >= limit:
                return False
        
        # Registra a requisição atual
        timestamp = now.timestamp()
        user_requests['minute'].append(timestamp)
        user_requests['hour'].append(timestamp)
        user_requests['day'].append(timestamp)
        
        return True
    
    def _cleanup_old_requests(self, user_requests: Dict, now: datetime):
        """Remove requisições antigas das filas."""
        windows = {
            'minute': 60,
            'hour': 3600,
            'day': 86400
        }
        
        for period, window_seconds in windows.items():
            cutoff = now.timestamp() - window_seconds
            queue = user_requests[period]
            
            while queue and queue[0] < cutoff:
                queue.popleft()


# Instância global do rate limiter
rate_limiter = RateLimiter()


def setup_security_headers(app: Flask):
    """Configura headers de segurança."""
    
    @app.after_request
    def set_security_headers(response):
        # Headers de segurança
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HTTPS enforcement (apenas em produção)
        if not settings.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy básico
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        
        return response


def setup_cors(app: Flask):
    """Configura CORS."""
    
    @app.after_request
    def after_request(response):
        # CORS headers básicos
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
    @app.route('/options', methods=['OPTIONS'])
    def handle_options():
        return jsonify({'status': 'ok'}), 200


def setup_logging_middleware(app: Flask):
    """Configura middleware de logging."""
    
    @app.before_request
    def log_request_info():
        g.start_time = time.time()
        
        # Log da requisição (com dados sanitizados)
        request_data = {
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_length': request.content_length
        }
        
        # Sanitiza dados sensíveis
        sanitized_data = sanitize_log_data(request_data)
        logger.info(f"Requisição recebida: {sanitized_data}")
    
    @app.after_request
    def log_response_info(response):
        if hasattr(g, 'start_time'):
            duration = time.time() - g.start_time
            
            response_data = {
                'status_code': response.status_code,
                'content_length': response.content_length,
                'duration_ms': round(duration * 1000, 2)
            }
            
            logger.info(f"Resposta enviada: {response_data}")
        
        return response


def rate_limit_middleware():
    """Decorator para rate limiting."""
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Usa IP como identificador (em produção seria mais sofisticado)
            identifier = request.remote_addr or 'unknown'
            
            if not rate_limiter.is_allowed(identifier):
                logger.warning(f"Rate limit excedido para {identifier}")
                raise RateLimitExceeded(
                    "Muitas requisições. Tente novamente mais tarde.",
                    code="RATE_LIMIT_EXCEEDED",
                    details={
                        'limits': {
                            'per_minute': settings.rate_limit_per_minute,
                            'per_hour': settings.rate_limit_per_hour,
                            'per_day': settings.rate_limit_per_day
                        }
                    }
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def setup_error_handlers(app: Flask):
    """Configura handlers de erro."""
    
    @app.errorhandler(RateLimitExceeded)
    def handle_rate_limit_exceeded(error):
        return jsonify({
            'success': False,
            'error': {
                'message': error.message,
                'code': error.code,
                'details': error.details
            }
        }), 429
    
    @app.errorhandler(413)
    def handle_file_too_large(error):
        return jsonify({
            'success': False,
            'error': {
                'message': 'Arquivo muito grande',
                'code': 'FILE_TOO_LARGE',
                'details': {
                    'max_size_mb': settings.max_content_length / (1024 * 1024)
                }
            }
        }), 413
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            'success': False,
            'error': {
                'message': 'Endpoint não encontrado',
                'code': 'NOT_FOUND'
            }
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': {
                'message': 'Método não permitido',
                'code': 'METHOD_NOT_ALLOWED'
            }
        }), 405
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error(f"Erro interno do servidor: {error}")
        return jsonify({
            'success': False,
            'error': {
                'message': 'Erro interno do servidor',
                'code': 'INTERNAL_ERROR'
            }
        }), 500


def setup_request_validation(app: Flask):
    """Configura validação de requisições."""
    
    @app.before_request
    def validate_content_type():
        # Valida Content-Type para endpoints que esperam arquivos
        if request.endpoint in ['convert_pdf'] and request.method == 'POST':
            content_type = request.content_type
            
            # Permite multipart/form-data (upload de arquivo) e application/json
            if content_type and not (
                content_type.startswith('multipart/form-data') or
                content_type.startswith('application/json')
            ):
                return jsonify({
                    'success': False,
                    'error': {
                        'message': 'Content-Type não suportado',
                        'code': 'UNSUPPORTED_CONTENT_TYPE',
                        'details': {
                            'received': content_type,
                            'expected': ['multipart/form-data', 'application/json']
                        }
                    }
                }), 400


def setup_all_middlewares(app: Flask):
    """Configura todos os middlewares."""
    setup_security_headers(app)
    setup_cors(app)
    setup_logging_middleware(app)
    setup_error_handlers(app)
    setup_request_validation(app) 