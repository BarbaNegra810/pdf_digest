#!/bin/bash

# Script para corrigir problemas de configuração Pydantic na VM Ubuntu 20.04.1

echo "🔧 Corrigindo configurações do Pydantic..."

# 1. Parar o serviço
echo "📛 Parando o serviço..."
sudo systemctl stop pdf-digest

# 2. Navegar para o diretório do projeto
cd /home/pdfdigest/pdf-digest

# 3. Ativar ambiente virtual
echo "🐍 Ativando ambiente virtual..."
source venv/bin/activate

# 4. Criar arquivo .env se não existir
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cat > .env << 'EOF'
# Configurações do Flask/Ambiente
DEBUG=false
FLASK_ENV=production
FLASK_DEBUG=false

# Configurações do servidor  
HOST=0.0.0.0
PORT=5000

# Processador de PDF
PDF_PROCESSOR=agno

# OpenAI API (SUBSTITUA pela sua chave real!)
OPENAI_API_KEY=sk-proj-SUBSTITUA_PELA_SUA_CHAVE_AQUI

# Redis para cache
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
CACHE_TTL=3600

# Configurações de upload
UPLOAD_FOLDER=/home/pdfdigest/pdf-digest/uploads
MAX_CONTENT_LENGTH=52428800
ALLOWED_EXTENSIONS=["pdf"]

# Logging
LOG_LEVEL=INFO

# Hardware
GPU_ENABLED=false
DEVICE=cpu

# Segurança
SECRET_KEY=mude-esta-chave-em-producao-123456789
JWT_SECRET_KEY=mude-esta-chave-jwt-em-producao-987654321
JWT_ACCESS_TOKEN_EXPIRES=3600

# Rate limiting
RATE_LIMIT_PER_MINUTE=10
RATE_LIMIT_PER_HOUR=100
RATE_LIMIT_PER_DAY=1000

# Monitoramento
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
EOF
    echo "✅ Arquivo .env criado. IMPORTANTE: Edite o arquivo e adicione sua chave OpenAI real!"
else
    echo "ℹ️ Arquivo .env já existe."
fi

# 5. Verificar se a chave OpenAI está configurada
if grep -q "sk-proj-SUBSTITUA_PELA_SUA_CHAVE_AQUI" .env; then
    echo "⚠️ ATENÇÃO: Você precisa configurar sua chave OpenAI real no arquivo .env"
    echo "Execute: nano .env"
    echo "E substitua: OPENAI_API_KEY=sk-proj-SUBSTITUA_PELA_SUA_CHAVE_AQUI"
    echo "Pela sua chave real: OPENAI_API_KEY=sk-proj-SuaChaveAquiReal..."
fi

# 6. Atualizar dependências se necessário
echo "📦 Verificando dependências..."
pip install --upgrade pydantic pydantic-settings

# 7. Testar as configurações
echo "🧪 Testando configurações..."
python -c "
try:
    from src.config.settings import settings
    print('✅ Configurações carregadas com sucesso!')
    print(f'   - PDF Processor: {settings.pdf_processor}')
    print(f'   - Redis URL: {settings.redis_url}')
    print(f'   - Upload Folder: {settings.upload_folder}')
    print(f'   - OpenAI configurada: {\"Sim\" if settings.openai_api_key and not \"SUBSTITUA\" in settings.openai_api_key else \"NÃO - Configure sua chave!\"}')
except Exception as e:
    print(f'❌ Erro ao carregar configurações: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "✅ Configurações OK! Reiniciando serviço..."
    
    # 8. Reiniciar o serviço
    sudo systemctl start pdf-digest
    sudo systemctl status pdf-digest
    
    echo ""
    echo "🎉 Correção concluída!"
    echo ""
    echo "📋 Próximos passos:"
    echo "1. Verifique se sua chave OpenAI está configurada: nano .env"
    echo "2. Teste a API: curl http://localhost/api/health"
    echo "3. Monitore os logs: sudo journalctl -u pdf-digest -f"
else
    echo "❌ Ainda há problemas. Verifique os logs acima."
fi
