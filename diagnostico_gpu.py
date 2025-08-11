#!/usr/bin/env python3
"""
Script de diagnóstico para verificar configuração da GPU/CUDA.
"""
import subprocess
import sys
import os


def run_command(command, description=""):
    """Executa comando e retorna resultado."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)


def check_nvidia_driver():
    """Verifica se drivers NVIDIA estão instalados."""
    print("🔍 Verificando drivers NVIDIA...")
    
    success, stdout, stderr = run_command("nvidia-smi")
    if success:
        print("✅ Drivers NVIDIA detectados!")
        print("📊 Informações da GPU:")
        lines = stdout.split('\n')
        for line in lines:
            if 'NVIDIA' in line or 'CUDA Version' in line:
                print(f"   {line.strip()}")
        return True
    else:
        print("❌ nvidia-smi não encontrado!")
        print(f"   Erro: {stderr}")
        return False


def check_cuda_toolkit():
    """Verifica se CUDA Toolkit está instalado."""
    print("\n🔍 Verificando CUDA Toolkit...")
    
    # Verifica nvcc
    success, stdout, stderr = run_command("nvcc --version")
    if success:
        print("✅ CUDA Toolkit detectado!")
        print(f"   Versão: {stdout}")
        return True
    else:
        print("❌ CUDA Toolkit (nvcc) não encontrado!")
        
        # Verifica variável de ambiente
        cuda_path = os.environ.get('CUDA_PATH')
        if cuda_path:
            print(f"   CUDA_PATH encontrado: {cuda_path}")
        else:
            print("   CUDA_PATH não definido!")
        
        return False


def check_pytorch_cuda():
    """Verifica se PyTorch tem suporte CUDA."""
    print("\n🔍 Verificando PyTorch CUDA...")
    
    try:
        import torch
        print(f"✅ PyTorch {torch.__version__} instalado!")
        
        cuda_available = torch.cuda.is_available()
        print(f"   CUDA disponível: {cuda_available}")
        
        if cuda_available:
            print(f"   Versão CUDA do PyTorch: {torch.version.cuda}")
            print(f"   Número de GPUs: {torch.cuda.device_count()}")
            
            for i in range(torch.cuda.device_count()):
                gpu_name = torch.cuda.get_device_name(i)
                print(f"   GPU {i}: {gpu_name}")
        else:
            print("   ⚠️ PyTorch não consegue acessar CUDA!")
            
        return cuda_available
        
    except ImportError:
        print("❌ PyTorch não instalado!")
        return False
    except Exception as e:
        print(f"❌ Erro ao verificar PyTorch: {e}")
        return False


def check_pytorch_installation():
    """Verifica a instalação do PyTorch."""
    print("\n🔍 Verificando instalação do PyTorch...")
    
    try:
        import torch
        print(f"   Versão: {torch.__version__}")
        print(f"   Compilado com CUDA: {torch.version.cuda}")
        print(f"   Compilado com cuDNN: {torch.backends.cudnn.version()}")
        
        # Verifica se foi instalado com suporte CPU-only
        if "+cpu" in torch.__version__:
            print("   ⚠️ DETECTADO: PyTorch CPU-only!")
            print("   Esta versão não tem suporte GPU!")
            return False
        
        return True
        
    except Exception as e:
        print(f"   Erro: {e}")
        return False


def suggest_fixes(has_nvidia, has_cuda, has_pytorch_cuda):
    """Sugere correções baseadas nos problemas encontrados."""
    print("\n" + "="*50)
    print("🛠️ SUGESTÕES DE CORREÇÃO:")
    print("="*50)
    
    if not has_nvidia:
        print("\n❌ PROBLEMA: Drivers NVIDIA não detectados")
        print("🔧 SOLUÇÃO:")
        print("   1. Baixe e instale os drivers mais recentes:")
        print("      https://www.nvidia.com/Download/index.aspx")
        print("   2. Reinicie o computador após instalação")
        print("   3. Execute: nvidia-smi para testar")
    
    if not has_cuda:
        print("\n❌ PROBLEMA: CUDA Toolkit não detectado")
        print("🔧 SOLUÇÃO:")
        print("   1. Baixe CUDA Toolkit 11.8 ou 12.x:")
        print("      https://developer.nvidia.com/cuda-downloads")
        print("   2. Instale seguindo as instruções do site")
        print("   3. Adicione ao PATH se necessário")
    
    if has_nvidia and has_cuda and not has_pytorch_cuda:
        print("\n❌ PROBLEMA: PyTorch sem suporte CUDA")
        print("🔧 SOLUÇÃO - Reinstalar PyTorch com CUDA:")
        print("   1. Desinstale PyTorch atual:")
        print("      pip uninstall torch torchvision torchaudio")
        print("   2. Visite: https://pytorch.org/get-started/locally/")
        print("   3. Selecione sua configuração CUDA")
        print("   4. Execute o comando sugerido")
        print("\n   📋 COMANDOS SUGERIDOS:")
        
        # Comandos mais comuns
        print("\n   Para CUDA 11.8:")
        print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118")
        
        print("\n   Para CUDA 12.1:")
        print("   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121")
        
        print("\n   Para versão mais recente:")
        print("   pip install torch torchvision torchaudio")
    
    if has_nvidia and has_cuda and has_pytorch_cuda:
        print("\n✅ TUDO PARECE OK!")
        print("🔧 POSSÍVEIS SOLUÇÕES:")
        print("   1. Reinicie o Python/aplicação")
        print("   2. Verifique se não há conflitos de ambiente virtual")
        print("   3. Execute: python -c \"import torch; print(torch.cuda.is_available())\"")


def main():
    """Função principal do diagnóstico."""
    print("🔧 DIAGNÓSTICO GPU/CUDA - PDF Digest")
    print("="*50)
    
    # Executa verificações
    has_nvidia = check_nvidia_driver()
    has_cuda = check_cuda_toolkit()
    has_pytorch_cuda = check_pytorch_cuda()
    
    # Informações do sistema
    print(f"\n💻 SISTEMA:")
    print(f"   Python: {sys.version}")
    print(f"   OS: {os.name}")
    
    # Verifica instalação PyTorch
    check_pytorch_installation()
    
    # Sugere correções
    suggest_fixes(has_nvidia, has_cuda, has_pytorch_cuda)
    
    print("\n" + "="*50)
    print("✅ Diagnóstico concluído!")
    print("📚 Para mais ajuda, consulte:")
    print("   - PyTorch: https://pytorch.org/get-started/locally/")
    print("   - CUDA: https://developer.nvidia.com/cuda-downloads")


if __name__ == "__main__":
    main() 