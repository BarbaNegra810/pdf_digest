#!/usr/bin/env python3
"""
Exemplo de uso da API PDF Digest com processamento Agno
para extração de trades e fees de notas de corretagem da B3.
"""

import requests
import json
from pathlib import Path

# Configuração da API
API_BASE_URL = "http://localhost:5000/api"

def test_agno_endpoint():
    """
    Testa o endpoint específico para extração de dados B3 com Agno.
    """
    print("=== Teste do Endpoint /extract-b3-trades (Agno) ===")
    
    # Exemplo de arquivo PDF de nota de corretagem
    # Substitua pelo caminho real do seu arquivo
    pdf_file_path = "exemplo_nota_corretagem_b3.pdf"
    
    if not Path(pdf_file_path).exists():
        print(f"⚠️  Arquivo não encontrado: {pdf_file_path}")
        print("   Criando arquivo de exemplo para demonstração...")
        return
    
    # Fazer upload do arquivo
    url = f"{API_BASE_URL}/extract-b3-trades"
    
    try:
        with open(pdf_file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['success']:
                result = data['data']
                
                print("✅ Extração bem-sucedida!")
                print(f"📊 Total de trades: {result['processing_info']['total_trades']}")
                print(f"💰 Total de fees: {result['processing_info']['total_fees']}")
                print(f"🔧 Processador: {result['processing_info']['processor']}")
                
                # Exibe alguns trades de exemplo
                if result['trades']:
                    print("\n--- Exemplos de Trades ---")
                    for i, trade in enumerate(result['trades'][:3]):  # Primeiros 3
                        print(f"Trade {i+1}:")
                        print(f"  Ticker: {trade['ticker']}")
                        print(f"  Operação: {'Compra' if trade['operationType'] == 'C' else 'Venda'}")
                        print(f"  Quantidade: {trade['quantity']}")
                        print(f"  Preço: R$ {trade['price']:.2f}")
                        print(f"  Valor Total: R$ {trade['totalValue']:.2f}")
                        print()
                
                # Exibe fees
                if result['fees']:
                    print("--- Taxas por Nota ---")
                    for fee in result['fees']:
                        print(f"Nota {fee['orderNumber']}: R$ {fee['totalFees']:.2f}")
                
                # Salva resultado em arquivo
                with open('resultado_agno.json', 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print("\n💾 Resultado salvo em: resultado_agno.json")
                
            else:
                print("❌ Erro na extração:")
                print(f"   {data['error']}")
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            print(f"   {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

def test_adaptive_endpoint():
    """
    Testa o endpoint adaptativo /convert que escolhe automaticamente
    entre Docling e Agno baseado na configuração.
    """
    print("\n=== Teste do Endpoint /convert (Adaptativo) ===")
    
    # Primeiro verifica o status da API
    status_url = f"{API_BASE_URL}/health"
    try:
        response = requests.get(status_url)
        if response.status_code == 200:
            health_data = response.json()
            print(f"📡 API Status: {health_data['data']['status']}")
        
    except Exception as e:
        print(f"⚠️  Erro ao verificar status: {e}")
    
    # Teste usando arquivo já existente no servidor
    url = f"{API_BASE_URL}/convert"
    
    # Exemplo usando arquivo no servidor
    payload = {
        "path": "uploads",  # Diretório
        "filename": "exemplo_nota_corretagem_b3.pdf"  # Nome do arquivo
    }
    
    try:
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            
            if data['success']:
                result = data['data']
                processor = result.get('processor', 'unknown')
                format_type = result.get('format', 'unknown')
                
                print(f"✅ Conversão bem-sucedida!")
                print(f"🔧 Processador usado: {processor}")
                print(f"📄 Formato: {format_type}")
                
                if processor == 'agno':
                    print(f"📊 Trades extraídos: {result['processing_info']['total_trades']}")
                    print(f"💰 Fees extraídos: {result['processing_info']['total_fees']}")
                else:
                    print(f"📄 Páginas convertidas: {result['file_info']['pages_count']}")
                
            else:
                print("❌ Erro na conversão:")
                print(f"   {data['error']}")
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            print(f"   {response.text}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

def get_api_info():
    """
    Obtém informações sobre a API e endpoints disponíveis.
    """
    print("\n=== Informações da API ===")
    
    url = f"{API_BASE_URL}/info"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            if data['success']:
                info = data['data']
                print(f"📱 {info['name']} v{info['version']}")
                print(f"📝 {info['description']}")
                
                print("\n--- Endpoints Disponíveis ---")
                for endpoint, description in info['endpoints'].items():
                    print(f"  {endpoint}: {description}")
                
                print(f"\n--- Limites ---")
                print(f"  Tamanho máximo: {info['limits']['max_file_size_mb']} MB")
                print(f"  Extensões: {', '.join(info['limits']['allowed_extensions'])}")
                
            else:
                print("❌ Erro ao obter informações da API")
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

def check_agno_setup():
    """
    Verifica se o Agno está configurado corretamente.
    """
    print("\n=== Verificação da Configuração Agno ===")
    
    url = f"{API_BASE_URL}/health"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            
            if data['success']:
                health_info = data['data']
                print("📊 Status da API:")
                for check, status in health_info['checks'].items():
                    emoji = "✅" if status else "❌"
                    print(f"   {emoji} {check}: {status}")
                
                # Verifica configuração específica do Agno
                print("\n🔧 Configuração Agno:")
                print("   ⚠️  Certifique-se de que:")
                print("   1. OPENAI_API_KEY está configurada no .env")
                print("   2. PDF_PROCESSOR=agno no .env")
                print("   3. Dependências do Agno estão instaladas")
            else:
                print("❌ Erro ao verificar status da API")
        else:
            print(f"❌ Erro HTTP {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro na requisição: {e}")

def main():
    """
    Executa todos os testes.
    """
    print("🚀 Testando API PDF Digest com Agno REAL")
    print("==========================================")
    
    # Verifica configuração do Agno
    check_agno_setup()
    
    # Obtém informações da API
    get_api_info()
    
    # Testa endpoint específico do Agno
    test_agno_endpoint()
    
    # Testa endpoint adaptativo
    test_adaptive_endpoint()
    
    print("\n✨ Testes concluídos!")
    print("\n📚 Para usar o Agno real:")
    print("   1. Configure OPENAI_API_KEY no arquivo .env")
    print("   2. Configure PDF_PROCESSOR=agno no arquivo .env")
    print("   3. Instale dependências: pip install agno openai")
    print("   4. Reinicie a aplicação")
    print("   5. O Agno usará GPT-4 Omni para extrair dados estruturados")

if __name__ == "__main__":
    main()
