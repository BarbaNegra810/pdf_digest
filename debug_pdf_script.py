#!/usr/bin/env python3
"""
Script para testar o endpoint de debug de PDF.
Mostra o conteúdo bruto que o Agno está lendo do PDF.
"""

import requests
import json
import sys
from pathlib import Path

def debug_pdf_file(pdf_path: str, api_url: str = "http://localhost:5000"):
    """
    Executa debug de um arquivo PDF usando o endpoint de debug.
    
    Args:
        pdf_path: Caminho para o arquivo PDF
        api_url: URL base da API
    """
    print(f"🔍 Debugando PDF: {pdf_path}")
    print("=" * 60)
    
    # Verifica se o arquivo existe
    if not Path(pdf_path).exists():
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    try:
        # Envia arquivo para debug
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                f"{api_url}/api/debug-pdf-content",
                files=files,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            
            if result['success']:
                data = result['data']
                
                print("✅ Debug executado com sucesso!")
                print()
                
                # Informações do arquivo
                file_info = data['file_info']
                print(f"📄 Arquivo: {file_info['filename']}")
                print(f"📏 Tamanho: {file_info['size_formatted']}")
                print(f"🔑 Hash: {file_info['hash']}")
                print()
                
                # Status das bibliotecas
                libs = data['analysis']['libraries_status']
                print("📚 Bibliotecas disponíveis:")
                print(f"   - pypdf: {'✅' if libs['pypdf'] else '❌'}")
                print(f"   - pdfminer: {'✅' if libs['pdfminer'] else '❌'}")
                print(f"   - agno: {'✅' if libs['agno'] else '❌'}")
                print()
                
                # Análise do conteúdo
                analysis = data['analysis']
                print("🔍 Análise:")
                print(f"   - Conteúdo disponível: {'✅' if analysis['content_available'] else '❌'}")
                print(f"   - Extração bem-sucedida: {'✅' if analysis['extraction_successful'] else '❌'}")
                print()
                
                # Resultados da extração
                extraction = data['extraction_result']
                print("📊 Resultados da extração:")
                print(f"   - Trades encontrados: {len(extraction.get('trades', []))}")
                print(f"   - Fees encontrados: {len(extraction.get('fees', []))}")
                print()
                
                # Conteúdo bruto extraído
                raw_content = data['raw_content']
                print("📝 Conteúdo bruto extraído:")
                
                for method, content in raw_content.items():
                    print(f"\n--- {method.upper()} ---")
                    
                    if isinstance(content, str):
                        if content.startswith('ERRO'):
                            print(f"❌ {content}")
                        elif len(content) == 0:
                            print("⚠️  Nenhum conteúdo extraído")
                        else:
                            # Mostra uma amostra do conteúdo
                            print(f"✅ {len(content)} caracteres extraídos")
                            print("\n📖 Primeiros 1000 caracteres:")
                            print("-" * 40)
                            print(content[:1000])
                            if len(content) > 1000:
                                print("...")
                                print(f"\n[{len(content) - 1000} caracteres restantes]")
                            print("-" * 40)
                    else:
                        print(f"⚠️  Conteúdo não é string: {type(content)}")
                
                # Se não encontrou trades, mostra dicas
                if len(extraction.get('trades', [])) == 0:
                    print("\n💡 DICAS PARA DEBUGGING:")
                    print("1. Verifique se o PDF contém texto extraível (não é apenas imagem)")
                    print("2. Procure por seções como 'Negócios realizados' no conteúdo extraído")
                    print("3. Verifique se o formato da nota B3 é reconhecível")
                    print("4. O PDF pode precisar de OCR se for escaneado")
                
            else:
                print(f"❌ Erro no debug: {result.get('error', 'Erro desconhecido')}")
                
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Detalhes: {error_data.get('error', 'Erro desconhecido')}")
            except:
                print(f"   Resposta: {response.text[:500]}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar à API. Certifique-se de que o servidor está rodando em http://localhost:5000")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

def main():
    if len(sys.argv) != 2:
        print("Uso: python debug_pdf_script.py <caminho_do_pdf>")
        print("Exemplo: python debug_pdf_script.py uploads/nota_corretagem.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    debug_pdf_file(pdf_path)

if __name__ == "__main__":
    main()
