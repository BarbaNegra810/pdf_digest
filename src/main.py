"""
Script principal para iniciar o serviço de conversão de PDF para Markdown.
"""
import argparse
import sys
import logging
import logging.config
import yaml
from pathlib import Path

from src.config.settings import settings
from src.api.app import create_app


def setup_logging():
    """Configura o sistema de logging."""
    try:
        # Tenta carregar configuração do YAML
        logging_config_path = Path(__file__).parent / 'config' / 'logging.yaml'
        
        if logging_config_path.exists():
            with open(logging_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Cria diretório de logs se necessário
            logs_dir = Path('logs')
            logs_dir.mkdir(exist_ok=True)
            
            logging.config.dictConfig(config)
            logger = logging.getLogger(__name__)
            logger.info("Sistema de logging configurado via YAML")
        else:
            # Fallback para configuração básica
            logging.basicConfig(
                level=getattr(logging, settings.log_level),
                format=settings.log_format
            )
            logger = logging.getLogger(__name__)
            logger.warning("Arquivo de configuração de logging não encontrado, usando configuração básica")
            
    except Exception as e:
        # Configuração de emergência
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao configurar logging: {e}")


def main():
    """
    Função principal que inicia a API.
    """
    # Configura logging primeiro
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Parser de argumentos de linha de comando
    parser = argparse.ArgumentParser(description='Serviço de conversão de PDF para Markdown')
    parser.add_argument('--host', default=settings.host, help='Host para iniciar o servidor')
    parser.add_argument('--port', type=int, default=settings.port, help='Porta para iniciar o servidor')
    parser.add_argument('--debug', action='store_true', default=settings.debug, help='Iniciar o servidor em modo debug')
    
    args = parser.parse_args()
    
    try:
        logger.info("Iniciando PDF Digest API")
        logger.info(f"Configurações: Host={args.host}, Port={args.port}, Debug={args.debug}")
        logger.info(f"Upload folder: {settings.upload_folder}")
        logger.info(f"Max file size: {settings.max_content_length / (1024 * 1024):.1f} MB")
        logger.info(f"Cache enabled: {settings.cache_enabled}")
        logger.info(f"GPU enabled: {settings.gpu_enabled}")
        
        # Cria e configura a aplicação Flask
        app = create_app()
        
        # Inicia o servidor
        logger.info(f"Iniciando servidor em {args.host}:{args.port}")
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            threaded=True
        )
        
    except KeyboardInterrupt:
        logger.info("Serviço interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro fatal durante inicialização: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 