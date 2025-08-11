#!/usr/bin/env python3
"""
Exemplo prático para chamar a API /api/convert do PDF Digest.

Este script demonstra como fazer requisições para converter PDFs em Markdown
usando diferentes métodos (upload e arquivo existente).
"""

import requests
import json
import os
from pathlib import Path


class PDFDigestClient:
    """Cliente para interagir com a API PDF Digest."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
    
    def health_check(self) -> bool:
        """Verifica se a API está funcionando."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def convert_pdf_upload(self, file_path: str) -> dict:
        """
        Converte PDF fazendo upload do arquivo.
        
        Args:
            file_path: Caminho para o arquivo PDF local
            
        Returns:
            Dicionário com o resultado da conversão
        """
        print(f"📤 Fazendo upload e conversão de: {file_path}")
        
        if not os.path.exists(file_path):
            print(f"❌ Arquivo não encontrado: {file_path}")
            return {}
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f"{self.api_url}/convert",
                    files=files,
                    timeout=60  # 60 segundos de timeout
                )
            
            if response.status_code == 200:
                result = response.json()
                pages_count = len(result['data']['pages'])
                file_size = result['data']['file_info']['size_formatted']
                
                print(f"✅ Conversão concluída!")
                print(f"   📄 Páginas: {pages_count}")
                print(f"   📏 Tamanho: {file_size}")
                print(f"   🖥️ Device: {result['data']['processing_info']['device']}")
                
                return result['data']
            else:
                print(f"❌ Erro HTTP {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Detalhes: {error_detail.get('error', 'Erro desconhecido')}")
                except:
                    print(f"   Resposta: {response.text}")
                return {}
                
        except requests.exceptions.Timeout:
            print("❌ Timeout na requisição (arquivo muito grande?)")
            return {}
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
            return {}
    
    def convert_pdf_existing(self, file_path: str, filename: str = None) -> dict:
        """
        Converte PDF que já existe no servidor.
        
        Args:
            file_path: Caminho do diretório no servidor
            filename: Nome do arquivo (opcional, se não informado será extraído do path)
            
        Returns:
            Dicionário com o resultado da conversão
        """
        if filename is None:
            # Se filename não foi informado, assume que file_path é o caminho completo
            full_path = file_path
            file_path = str(Path(file_path).parent)
            filename = Path(full_path).name
        
        print(f"📁 Convertendo arquivo existente: {filename}")
        print(f"   📂 Diretório: {file_path}")
        
        try:
            data = {
                "path": file_path,
                "filename": filename
            }
            
            response = requests.post(
                f"{self.api_url}/convert",
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                pages_count = len(result['data']['pages'])
                file_size = result['data']['file_info']['size_formatted']
                
                print(f"✅ Conversão concluída!")
                print(f"   📄 Páginas: {pages_count}")
                print(f"   📏 Tamanho: {file_size}")
                print(f"   🖥️ Device: {result['data']['processing_info']['device']}")
                
                return result['data']
            else:
                print(f"❌ Erro HTTP {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Detalhes: {error_detail.get('error', 'Erro desconhecido')}")
                except:
                    print(f"   Resposta: {response.text}")
                return {}
                
        except requests.exceptions.Timeout:
            print("❌ Timeout na requisição")
            return {}
        except Exception as e:
            print(f"❌ Erro na requisição: {e}")
            return {}
    
    def show_pages_preview(self, result: dict, max_chars: int = 200):
        """Mostra preview das páginas convertidas."""
        if not result or 'pages' not in result:
            return
        
        print(f"\n📖 Preview das páginas convertidas:")
        print("=" * 50)
        
        for page_num, content in result['pages'].items():
            print(f"\n📄 Página {page_num}:")
            print("-" * 30)
            preview = content[:max_chars]
            if len(content) > max_chars:
                preview += "..."
            print(preview)
    
    def save_to_files(self, result: dict, output_dir: str = "output"):
        """Salva as páginas convertidas em arquivos markdown."""
        if not result or 'pages' not in result:
            return
        
        # Cria diretório de saída
        Path(output_dir).mkdir(exist_ok=True)
        
        filename_base = result.get('file_info', {}).get('filename', 'documento')
        filename_base = Path(filename_base).stem  # Remove extensão
        
        saved_files = []
        
        # Salva arquivo combinado
        combined_file = f"{output_dir}/{filename_base}_completo.md"
        with open(combined_file, 'w', encoding='utf-8') as f:
            f.write(f"# {filename_base}\n\n")
            for page_num, content in result['pages'].items():
                f.write(f"## Página {page_num}\n\n")
                f.write(content)
                f.write("\n\n---\n\n")
        saved_files.append(combined_file)
        
        # Salva páginas individuais
        for page_num, content in result['pages'].items():
            page_file = f"{output_dir}/{filename_base}_pagina_{page_num}.md"
            with open(page_file, 'w', encoding='utf-8') as f:
                f.write(content)
            saved_files.append(page_file)
        
        print(f"\n💾 Arquivos salvos em: {output_dir}")
        for file_path in saved_files:
            print(f"   📝 {file_path}")
        
        return saved_files


def main():
    """Função principal de demonstração."""
    print("🚀 PDF Digest - Cliente da API /api/convert")
    print("=" * 50)
    
    # Inicializa cliente
    client = PDFDigestClient()
    
    # Verifica se API está ativa
    if not client.health_check():
        print("❌ API PDF Digest não está disponível!")
        print("   Certifique-se de que está rodando em http://localhost:5000")
        return
    
    print("✅ API PDF Digest está ativa!")
    
    # Menu de opções
    print("\nEscolha uma opção:")
    print("1. Upload de arquivo local")
    print("2. Arquivo existente no servidor")
    print("3. Exemplo com arquivo de teste dos logs")
    
    choice = input("\nDigite sua escolha (1-3): ").strip()
    
    result = None
    
    if choice == "1":
        file_path = input("Digite o caminho do arquivo PDF: ").strip()
        result = client.convert_pdf_upload(file_path)
        
    elif choice == "2":
        file_path = input("Digite o caminho do diretório no servidor: ").strip()
        filename = input("Digite o nome do arquivo: ").strip()
        result = client.convert_pdf_existing(file_path, filename)
        
    elif choice == "3":
        # Exemplo baseado nos logs
        print("📋 Usando exemplo dos logs...")
        result = client.convert_pdf_existing(
            "C:/Users/jotae/OneDrive/Dev/IA Dev/Investdash/data/665f1f62633e1b04b75feec7",
            "XPINC_NOTA_NEGOCIACAO_B3_5_2014.pdf"
        )
    else:
        print("❌ Opção inválida!")
        return
    
    # Mostra resultados
    if result:
        client.show_pages_preview(result)
        
        # Pergunta se quer salvar
        save = input("\n💾 Deseja salvar os arquivos? (s/n): ").strip().lower()
        if save in ['s', 'sim', 'y', 'yes']:
            client.save_to_files(result)
        
        print("\n🎉 Conversão concluída com sucesso!")
    else:
        print("\n❌ Falha na conversão!")


if __name__ == "__main__":
    main() 