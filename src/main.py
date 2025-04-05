"""
Script principal para iniciar o serviço de conversão de PDF para Markdown.
"""
import argparse
import sys

from src.api import start_api


def saudacao(nome: str) -> str:
    """
    Retorna uma mensagem de saudação personalizada.
    
    Args:
        nome (str): Nome da pessoa a ser saudada
        
    Returns:
        str: Mensagem de saudação
    """
    return f"Olá, {nome}! Bem-vindo ao projeto!"


def main():
    """
    Função principal que inicia a API.
    """
    parser = argparse.ArgumentParser(description='Serviço de conversão de PDF para Markdown')
    parser.add_argument('--host', default='0.0.0.0', help='Host para iniciar o servidor')
    parser.add_argument('--port', type=int, default=5000, help='Porta para iniciar o servidor')
    parser.add_argument('--debug', action='store_true', help='Iniciar o servidor em modo debug')
    
    args = parser.parse_args()
    
    print(f"Iniciando servidor PDF-to-Markdown em {args.host}:{args.port} (debug: {args.debug})")
    start_api(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main() 