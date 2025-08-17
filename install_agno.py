#!/usr/bin/env python3
"""
Script para instalar o framework Agno e suas dependências.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """
    Executa um comando e mostra o resultado.
    """
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} concluído com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro durante {description}:")
        print(f"   Código de erro: {e.returncode}")
        print(f"   Saída: {e.stdout}")
        print(f"   Erro: {e.stderr}")
        return False

def check_python_version():
    """
    Verifica se a versão do Python é compatível.
    """
    print("🐍 Verificando versão do Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} é compatível")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} não é compatível")
        print("   Requisito: Python 3.8 ou superior")
        return False

def install_agno_dependencies():
    """
    Instala o Agno e suas dependências.
    """
    dependencies = [
        "agno",
        "openai",
        "duckduckgo-search",
        "yfinance",
        "lancedb",
        "tantivy",
        "pypdf",
        "exa-py",
        "newspaper4k",
        "lxml_html_clean",
        "sqlalchemy"
    ]
    
    print(f"📦 Instalando {len(dependencies)} dependências do Agno...")
    
    for dep in dependencies:
        if not run_command(f"pip install {dep}", f"Instalando {dep}"):
            print(f"⚠️  Falha ao instalar {dep}, continuando...")
    
    print("\n✅ Instalação das dependências concluída!")

def verify_installation():
    """
    Verifica se a instalação foi bem-sucedida.
    """
    print("\n🔍 Verificando instalação...")
    
    try:
        import agno
        print("✅ Framework Agno importado com sucesso")
        
        # Tenta importar componentes principais
        from agno.agent import Agent
        print("✅ Agent importado com sucesso")
        
        from agno.models.openai import OpenAIChat
        print("✅ OpenAI model importado com sucesso")
        
        from agno.tools.reasoning import ReasoningTools
        print("✅ ReasoningTools importado com sucesso")
        
        from agno.tools.file import FileTools
        print("✅ FileTools importado com sucesso")
        
        print("\n🎉 Agno instalado e configurado com sucesso!")
        return True
        
    except ImportError as e:
        print(f"❌ Erro ao importar Agno: {e}")
        print("   Verifique se a instalação foi concluída corretamente")
        return False

def create_env_template():
    """
    Cria template de configuração para o .env.
    """
    print("\n📝 Criando template de configuração...")
    
    env_content = """
# =======================================================
# CONFIGURAÇÃO AGNO - ADICIONE AO SEU ARQUIVO .env
# =======================================================

# Processador PDF (docling ou agno)
PDF_PROCESSOR=agno

# Chave da API OpenAI (OBRIGATÓRIA para o Agno)
OPENAI_API_KEY=your-openai-api-key-here

# =======================================================
# INSTRUÇÕES:
# 1. Copie as linhas acima para o seu arquivo .env
# 2. Substitua 'your-openai-api-key-here' pela sua chave real da OpenAI
# 3. Reinicie a aplicação
# =======================================================
"""
    
    try:
        with open("agno_config_template.txt", "w", encoding="utf-8") as f:
            f.write(env_content.strip())
        
        print("✅ Template criado: agno_config_template.txt")
        print("   📋 Copie o conteúdo para o seu arquivo .env")
        
    except Exception as e:
        print(f"❌ Erro ao criar template: {e}")

def main():
    """
    Função principal do instalador.
    """
    print("🚀 Instalador do Framework Agno para PDF Digest")
    print("=" * 50)
    
    # Verifica versão do Python
    if not check_python_version():
        print("\n❌ Instalação cancelada: versão do Python incompatível")
        sys.exit(1)
    
    # Instala dependências
    install_agno_dependencies()
    
    # Verifica instalação
    if verify_installation():
        print("\n✨ Instalação concluída com sucesso!")
        
        # Cria template de configuração
        create_env_template()
        
        print("\n📚 Próximos passos:")
        print("   1. Configure OPENAI_API_KEY no arquivo .env")
        print("   2. Configure PDF_PROCESSOR=agno no arquivo .env")
        print("   3. Reinicie a aplicação")
        print("   4. Teste com: python exemplo_chamada_api_agno.py")
        
        print(f"\n🎯 O Agno está pronto para processar notas de corretagem B3!")
        
    else:
        print("\n❌ Falha na verificação da instalação")
        print("   Verifique os erros acima e tente novamente")
        sys.exit(1)

if __name__ == "__main__":
    main()
