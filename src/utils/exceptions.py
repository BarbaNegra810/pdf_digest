"""
Exceções customizadas para o PDF Digest.
"""


class PDFDigestException(Exception):
    """Exceção base para o PDF Digest."""
    
    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(PDFDigestException):
    """Erro de validação de dados."""
    pass


class FileProcessingError(PDFDigestException):
    """Erro durante processamento de arquivo."""
    pass


class ConversionError(PDFDigestException):
    """Erro durante conversão de PDF."""
    pass


class SecurityError(PDFDigestException):
    """Erro relacionado à segurança."""
    pass


class ConfigurationError(PDFDigestException):
    """Erro de configuração."""
    pass


class CacheError(PDFDigestException):
    """Erro relacionado ao cache."""
    pass


class RateLimitExceeded(PDFDigestException):
    """Rate limit excedido."""
    pass 