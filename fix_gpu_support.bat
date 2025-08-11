@echo off
echo 🔧 CORRIGINDO SUPORTE GPU PARA PDF DIGEST
echo ========================================

echo.
echo 📋 PASSO 1: Desinstalando PyTorch CPU-only...
pip uninstall -y torch torchvision torchaudio

echo.
echo 📋 PASSO 2: Instalando PyTorch com suporte CUDA 12.1...
echo (Compatível com CUDA 12.7 detectado)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

echo.
echo 📋 PASSO 3: Verificando instalação...
python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda if torch.cuda.is_available() else 'None')"

echo.
echo ✅ Instalação concluída!
echo.
echo 🔧 PRÓXIMOS PASSOS:
echo 1. Se CUDA ainda não for detectado, instale CUDA Toolkit:
echo    https://developer.nvidia.com/cuda-12-1-0-download-archive
echo 2. Reinicie o servidor: python src/main.py
echo 3. Verifique o health check: http://localhost:5000/health
echo.
pause 