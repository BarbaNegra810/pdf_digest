#!/usr/bin/env python3
"""
Exemplo prático de uso das novas funcionalidades de extração de tabelas do PDF Digest.

Este script demonstra:
1. Extração básica de tabelas
2. Múltiplos formatos de export
3. Salvamento automático em arquivos
4. Conversão combinada (Markdown + Tabelas)
"""

import requests
import json
import os
from pathlib import Path
from typing import Dict, Any


class PDFTableExtractionDemo:
    """
    Demonstração das funcionalidades avançadas de extração de tabelas.
    """
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        
    def health_check(self) -> bool:
        """Verifica se o serviço está ativo."""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def extract_tables_basic(self, pdf_path: str, format: str = "json") -> Dict[str, Any]:
        """
        Demonstra extração básica de tabelas.
        
        Args:
            pdf_path: Caminho para o arquivo PDF
            format: Formato de saída ('json', 'csv', 'excel', 'html')
        """
        print(f"\n🔍 Extraindo tabelas em formato {format.upper()}...")
        
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': f}
                params = {'format': format}
                
                response = requests.post(
                    f"{self.api_url}/extract-tables",
                    files=files,
                    params=params,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                tables_count = len(result['data']['tables'])
                print(f"✅ Sucesso! {tables_count} tabelas extraídas")
                
                # Mostra informações das tabelas
                for table in result['data']['tables']:
                    print(f"   📊 Tabela {table['id']}: {table['metadata']['rows']}x{table['metadata']['cols']} (página {table['page']})")
                
                return result
            else:
                print(f"❌ Erro: {response.status_code}")
                print(response.text)
                return {}
                
        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return {}
    
    def extract_tables_with_files(self, pdf_path: str, format: str = "json") -> Dict[str, Any]:
        """
        Demonstra extração com salvamento automático de arquivos.
        """
        print(f"\n💾 Extraindo tabelas com salvamento automático...")
        
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': f}
                params = {'format': format, 'save_files': 'true'}
                
                response = requests.post(
                    f"{self.api_url}/extract-tables",
                    files=files,
                    params=params,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                export_info = result['data']['export_info']
                
                if export_info['files_saved']:
                    saved_files = export_info['saved_files']
                    print(f"✅ Arquivos salvos:")
                    for file_type, file_list in saved_files.items():
                        if file_list:
                            print(f"   📁 {file_type.upper()}: {len(file_list)} arquivos")
                            for file_path in file_list:
                                print(f"      └── {file_path}")
                
                return result
            else:
                print(f"❌ Erro: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Erro na extração: {e}")
            return {}
    
    def convert_enhanced(self, pdf_path: str, table_format: str = "json") -> Dict[str, Any]:
        """
        Demonstra conversão combinada (Markdown + Tabelas).
        """
        print(f"\n🔄 Conversão avançada (Markdown + Tabelas)...")
        
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': f}
                params = {
                    'include_tables': 'true',
                    'table_format': table_format
                }
                
                response = requests.post(
                    f"{self.api_url}/convert-enhanced",
                    files=files,
                    params=params,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                data = result['data']
                
                markdown_pages = len(data['markdown']['pages'])
                tables_count = len(data['tables']['tables']) if data['tables'] else 0
                
                print(f"✅ Conversão concluída!")
                print(f"   📝 Markdown: {markdown_pages} páginas")
                print(f"   📊 Tabelas: {tables_count} extraídas")
                
                return result
            else:
                print(f"❌ Erro: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"❌ Erro na conversão: {e}")
            return {}
    
    def demonstrate_all_formats(self, pdf_path: str):
        """
        Demonstra extração em todos os formatos disponíveis.
        """
        print("\n🎯 Demonstrando todos os formatos disponíveis:")
        
        formats = ['json', 'csv', 'excel', 'html']
        results = {}
        
        for fmt in formats:
            result = self.extract_tables_basic(pdf_path, fmt)
            if result:
                results[fmt] = result
        
        return results
    
    def show_table_preview(self, table_data: Dict[str, Any], max_rows: int = 3):
        """
        Mostra preview dos dados da tabela.
        """
        if not table_data.get('data'):
            return
        
        print(f"\n👀 Preview da Tabela {table_data['id']} (formato {table_data['format']}):")
        
        if table_data['format'] == 'array' or table_data['format'] == 'json':
            data = table_data['data']
            if isinstance(data, list) and data:
                for i, row in enumerate(data[:max_rows]):
                    print(f"   {i+1}: {row}")
                if len(data) > max_rows:
                    print(f"   ... (mais {len(data) - max_rows} linhas)")
        
        elif table_data['format'] == 'csv':
            lines = table_data['data'].strip().split('\n')
            for i, line in enumerate(lines[:max_rows]):
                print(f"   {i+1}: {line}")
            if len(lines) > max_rows:
                print(f"   ... (mais {len(lines) - max_rows} linhas)")
        
        elif table_data['format'] == 'html':
            print(f"   HTML: {len(table_data['data'])} caracteres")
            print(f"   Preview: {table_data['data'][:100]}...")


def main():
    """
    Função principal de demonstração.
    """
    print("🚀 PDF Digest - Demonstração de Extração Avançada de Tabelas")
    print("=" * 60)
    
    # Inicializa o demonstrador
    demo = PDFTableExtractionDemo()
    
    # Verifica se o serviço está ativo
    if not demo.health_check():
        print("❌ Serviço PDF Digest não está disponível!")
        print("   Certifique-se de que está rodando em http://localhost:5000")
        return
    
    print("✅ Serviço PDF Digest está ativo!")
    
    # Solicita arquivo PDF para teste
    pdf_path = input("\n📄 Digite o caminho para um arquivo PDF: ").strip()
    
    if not os.path.exists(pdf_path):
        print(f"❌ Arquivo não encontrado: {pdf_path}")
        return
    
    # Demonstra diferentes funcionalidades
    try:
        # 1. Extração básica em JSON
        result_json = demo.extract_tables_basic(pdf_path, "json")
        if result_json and result_json['data']['tables']:
            demo.show_table_preview(result_json['data']['tables'][0])
        
        # 2. Extração com salvamento automático
        demo.extract_tables_with_files(pdf_path, "csv")
        
        # 3. Conversão combinada
        demo.convert_enhanced(pdf_path, "excel")
        
        # 4. Todos os formatos
        demo.demonstrate_all_formats(pdf_path)
        
        print("\n🎉 Demonstração concluída com sucesso!")
        print("\nFuncionalidades demonstradas:")
        print("  ✅ Extração básica de tabelas")
        print("  ✅ Múltiplos formatos (JSON, CSV, Excel, HTML)")
        print("  ✅ Salvamento automático em arquivos")
        print("  ✅ Conversão combinada (Markdown + Tabelas)")
        
    except KeyboardInterrupt:
        print("\n\n👋 Demonstração interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante demonstração: {e}")


if __name__ == "__main__":
    main() 