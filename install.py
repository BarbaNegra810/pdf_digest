#!/usr/bin/env python3
"""
Script de instalação automatizada para o PDF Digest.
Este script resolve automaticamente os problemas de dependências.
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Executa um comando e trata erros."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} concluído com sucesso!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro em {description}:")
        print(f"   Comando: {command}")
        print(f"   Erro: {e.stderr}")
        return False


def check_python_version():
    """Verifica se a versão do Python é adequada."""
    print("🔍 Verificando versão do Python...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} está OK!")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} não é suportado!")
        print("   É necessário Python 3.8 ou superior.")
        return False


def install_dependencies():
    """Instala dependências em ordem específica para evitar conflitos."""
    print("📦 Instalando dependências...")
    
    # Dependências críticas primeiro
    critical_deps = [
        "pip>=23.0",
        "setuptools>=65.0",
        "wheel",
        "pydantic>=2.6.0,<3.0.0",
        "pydantic-settings>=2.0.0"
    ]
    
    for dep in critical_deps:
        if not run_command(f"pip install '{dep}'", f"Instalando {dep}"):
            return False
    
    # Instala dependências mínimas
    if not run_command("pip install -r requirements-minimal.txt", "Instalando dependências mínimas"):
        return False
    
    return True


def create_directories():
    """Cria diretórios necessários."""
    print("📁 Criando diretórios necessários...")
    
    dirs = ['uploads', 'logs']
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✅ Diretório '{dir_name}' criado/verificado!")
    
    return True


def create_env_file():
    """Cria arquivo .env se não existir."""
    if not os.path.exists('.env'):
        print("⚙️ Criando arquivo de configuração .env...")
        try:
            with open('env.example', 'r') as src, open('.env', 'w') as dst:
                dst.write(src.read())
            print("✅ Arquivo .env criado com configurações padrão!")
        except FileNotFoundError:
            print("⚠️ Arquivo env.example não encontrado, criando .env básico...")
            with open('.env', 'w') as f:
                f.write("""# Configurações básicas do PDF Digest
DEBUG=true
LOG_LEVEL=INFO
CACHE_ENABLED=false
GPU_ENABLED=true
""")
            print("✅ Arquivo .env básico criado!")
    else:
        print("✅ Arquivo .env já existe!")
    
    return True


def test_installation():
    """Testa se a instalação foi bem-sucedida."""
    print("🧪 Testando a instalação...")
    
    try:
        # Testa imports críticos
        import pydantic
        import pydantic_settings
        import flask
        print(f"✅ Pydantic {pydantic.VERSION} instalado!")
        print(f"✅ Flask {flask.__version__} instalado!")
        
        # Testa configurações
        from src.config.settings import settings
        print(f"✅ Configurações carregadas! Upload folder: {settings.upload_folder}")
        
        print("🎉 Instalação concluída com sucesso!")
        return True
        
    except ImportError as e:
        print(f"❌ Erro ao importar módulos: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro durante teste: {e}")
        return False


def main():
    """Função principal do script de instalação."""
    print("🚀 Iniciando instalação do PDF Digest...")
    print("=" * 50)
    
    steps = [
        ("Verificação do Python", check_python_version),
        ("Instalação de dependências", install_dependencies),
        ("Criação de diretórios", create_directories),
        ("Configuração do ambiente", create_env_file),
        ("Teste da instalação", test_installation)
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 Etapa: {step_name}")
        if not step_func():
            print(f"\n💥 Falha na etapa: {step_name}")
            print("🔧 Tente executar manualmente:")
            print("   pip install pydantic-settings")
            print("   pip install -r requirements-minimal.txt")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 INSTALAÇÃO CONCLUÍDA COM SUCESSO!")
    print("\n📋 Próximos passos:")
    print("   1. Execute: python -m src.main")
    print("   2. Acesse: http://localhost:5000/api/health")
    print("   3. Teste a API: http://localhost:5000/api/info")
    print("\n📚 Documentação completa no README.md")


if __name__ == "__main__":
    main() 