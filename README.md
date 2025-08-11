# PDF Digest 📄➡️📝

**Serviço web para conversão inteligente de arquivos PDF em Markdown** utilizando a biblioteca Docling com suporte a GPU para aceleração de performance.

## 🚀 Funcionalidades Principais

- ✅ **Conversão PDF → Markdown** com alta qualidade
- ✅ **Extração avançada de tabelas** com estrutura preservada
- ✅ **Múltiplos formatos de export** (JSON, CSV, Excel, HTML)
- ✅ **Suporte a GPU** para processamento acelerado
- ✅ **API REST** robusta e bem documentada
- ✅ **Cache Redis** para melhor performance
- ✅ **Rate Limiting** e segurança aprimorada
- ✅ **Pipeline otimizado** baseado no Docling 2.26+
- ✅ **Processamento específico** para "Notas de Negociação"
- ✅ **Monitoramento** e métricas completas
- ✅ **Containerização** com Docker
- ✅ **Logging estruturado** com rotação
- ✅ **Testes automatizados** com alta cobertura

## 🏗️ Arquitetura

### Estrutura do Projeto
```
pdf-digest/
├── src/
│   ├── api/                    # Camada de API
│   │   ├── __init__.py
│   │   ├── app.py             # Factory da aplicação Flask
│   │   ├── routes.py          # Endpoints da API
│   │   └── middlewares.py     # Middlewares (segurança, rate limiting)
│   ├── config/                # Configurações
│   │   ├── __init__.py
│   │   ├── settings.py        # Configurações centralizadas (Pydantic)
│   │   └── logging.yaml       # Configuração de logging
│   ├── services/              # Lógica de negócio
│   │   ├── __init__.py
│   │   ├── pdf_service.py     # Conversão de PDF
│   │   ├── file_service.py    # Gestão de arquivos
│   │   └── cache_service.py   # Cache Redis
│   ├── utils/                 # Utilitários
│   │   ├── __init__.py
│   │   ├── exceptions.py      # Exceções customizadas
│   │   └── helpers.py         # Funções auxiliares
│   ├── __init__.py
│   └── main.py               # Entry point
├── tests/                    # Testes automatizados
│   ├── test_pdf_service.py
│   ├── test_file_service.py
│   ├── test_cache_service.py
│   ├── test_api.py
│   └── __init__.py
├── logs/                     # Logs da aplicação
├── uploads/                  # Arquivos temporários
├── Dockerfile               # Containerização
├── docker-compose.yml       # Orquestração
├── requirements.txt         # Dependências Python
├── .pre-commit-config.yaml  # Hooks de qualidade
├── env.example             # Exemplo de variáveis de ambiente
└── README.md
```

### Componentes Principais

#### 🔧 **Configuração Centralizada**
- **Pydantic Settings** para validação e gerenciamento de configurações
- **Suporte a variáveis de ambiente** (.env)
- **Validação automática** de tipos e valores

#### 🛡️ **Segurança Aprimorada**
- **Headers de segurança** automáticos (CSP, HSTS, X-Frame-Options)
- **Rate limiting** por IP com limites configuráveis
- **Validação robusta** de arquivos (magic bytes, path traversal)
- **Sanitização** de logs para dados sensíveis

#### 📊 **Cache Inteligente**
- **Redis** para cache de conversões
- **Hash de arquivos** para evitar reprocessamento
- **TTL configurável** e limpeza automática

#### 🔍 **Monitoramento e Observabilidade**
- **Health checks** detalhados com verificação de componentes
- **Métricas** de sistema (CPU, memória, disco)
- **Logging estruturado** com múltiplos níveis
- **Estatísticas** de uso e performance

## 📦 Instalação e Configuração

### 1. Pré-requisitos
```bash
# Python 3.11+
python --version

# Redis (opcional, para cache)
redis-server --version

# Docker (opcional, para containerização)
docker --version
docker-compose --version
```

### 2. Instalação via Git
```bash
# Clone o repositório
git clone <repository-url>
cd pdf-digest

# Crie ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate     # Windows

# Instale dependências
pip install -r requirements.txt
```

### 3. Configuração

#### Configuração básica (arquivo .env)
```bash
# Copie o arquivo de exemplo
cp env.example .env

# Edite as configurações conforme necessário
nano .env
```

#### Principais configurações:
```env
# Servidor
HOST=0.0.0.0
PORT=5000
DEBUG=false

# Upload
MAX_CONTENT_LENGTH=16777216  # 16MB
UPLOAD_FOLDER=uploads

# Cache
CACHE_ENABLED=true
REDIS_URL=redis://localhost:6379

# Hardware
GPU_ENABLED=true

# Segurança
RATE_LIMIT_PER_MINUTE=5
SECRET_KEY=your-secret-key-here
```

## 🚀 Execução

### Método 1: Execução Direta
```bash
# Ative o ambiente virtual
source .venv/bin/activate

# Inicie o servidor
python -m src.main

# Ou com parâmetros customizados
python -m src.main --host 127.0.0.1 --port 8000 --debug
```

### Método 2: Docker Compose (Recomendado)
```bash
# Inicie todos os serviços
docker-compose up -d

# Verifique os logs
docker-compose logs -f pdf-digest

# Pare os serviços
docker-compose down
```

### Método 3: Docker Manual
```bash
# Build da imagem
docker build -t pdf-digest .

# Execute o container
docker run -p 5000:5000 \
  -e CACHE_ENABLED=false \
  -v $(pwd)/uploads:/app/uploads \
  pdf-digest
```

## 🔍 Uso da API

### Endpoints Disponíveis

#### 📊 Health Check
```bash
GET /api/health
```
**Resposta:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-20T10:30:00Z",
    "checks": {
      "api": true,
      "cache": true,
      "disk_space": true,
      "memory_usage": true,
      "gpu_available": true
    }
  }
}
```

#### 📄 Conversão de PDF

**Upload de arquivo:**
```bash
curl -X POST http://localhost:5000/api/convert \
  -F "file=@documento.pdf"
```

**Arquivo no servidor:**
```bash
curl -X POST http://localhost:5000/api/convert \
  -H "Content-Type: application/json" \
  -d '{"path": "/caminho/para/arquivo.pdf"}'
```

**Resposta de sucesso:**
```json
{
  "success": true,
  "data": {
    "pages": {
      "1": "# NOTA DE NEGOCIAÇÃO\n\nConteúdo da primeira nota...",
      "2": "# NOTA DE NEGOCIAÇÃO\n\nConteúdo da segunda nota..."
    },
    "file_info": {
      "filename": "documento.pdf",
      "size_bytes": 1048576,
      "size_formatted": "1.0 MB",
      "hash": "abc123...",
      "pages_count": 2
    },
    "processing_info": {
      "device": "cuda",
      "cached": false
    }
  }
}
```

#### 📈 Estatísticas
```bash
GET /api/stats
```

#### 🧹 Operações de Manutenção
```bash
# Limpar cache
POST /api/cache/clear

# Limpar arquivos antigos
POST /api/cleanup
# Body: {"max_age_hours": 24}
```

### Códigos de Resposta
- **200**: Sucesso
- **400**: Erro de validação
- **413**: Arquivo muito grande
- **422**: Erro de conversão
- **429**: Rate limit excedido
- **500**: Erro interno

## 🧪 Testes

### Executar Testes
```bash
# Todos os testes
python -m pytest

# Testes específicos
python -m pytest tests/test_pdf_service.py

# Com cobertura
python -m pytest --cov=src --cov-report=html
```

### Tipos de Testes
- **Unitários**: Testam componentes isolados
- **Integração**: Testam a API completa
- **Segurança**: Validam proteções implementadas

## 🛠️ Desenvolvimento

### Setup para Desenvolvimento
```bash
# Instale dependências de desenvolvimento
pip install -r requirements.txt

# Configure pre-commit hooks
pre-commit install

# Execute hooks manualmente
pre-commit run --all-files
```

### Qualidade de Código
- **Black**: Formatação de código
- **Flake8**: Linting
- **MyPy**: Type checking
- **Bandit**: Security linting
- **isort**: Organização de imports

### Commit Guidelines
```bash
# O pre-commit garante qualidade automaticamente
git add .
git commit -m "feat: adiciona cache Redis"
git push
```

## 📊 Monitoramento

### Logs
```bash
# Logs em desenvolvimento
tail -f logs/app.log

# Logs estruturados (JSON)
tail -f logs/app.log | jq .

# Logs de erro
tail -f logs/error.log
```

### Métricas Disponíveis
- **Sistema**: CPU, memória, disco
- **Aplicação**: Requisições, erros, latência
- **Cache**: Hits, misses, tamanho
- **Arquivos**: Uploads, limpezas, tamanhos

### Health Checks
```bash
# Health check simples
curl http://localhost:5000/api/health

# Com Docker
docker-compose exec pdf-digest curl http://localhost:5000/api/health
```

## 🔧 Troubleshooting

### Problemas Comuns

#### GPU não detectada
```bash
# Verifique se CUDA está instalado
nvidia-smi

# Configure para usar CPU
export GPU_ENABLED=false
```

#### Redis não conecta
```bash
# Verifique se Redis está rodando
redis-cli ping

# Configure para usar sem cache
export CACHE_ENABLED=false
```

#### Erro de permissão nos uploads
```bash
# Ajuste permissões
chmod 755 uploads/
chown -R $USER:$USER uploads/
```

#### Arquivo muito grande
```bash
# Aumente o limite (em bytes)
export MAX_CONTENT_LENGTH=33554432  # 32MB
```

### Logs de Debug
```bash
# Ative debug mode
export DEBUG=true
export LOG_LEVEL=DEBUG

# Reinicie a aplicação
python -m src.main
```

## 🤝 Contribuição

1. **Fork** o projeto
2. **Crie** uma branch feature (`git checkout -b feature/nova-funcionalidade`)
3. **Commit** suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
5. **Abra** um Pull Request

### Padrões de Código
- Siga o **PEP 8**
- Use **type hints**
- Documente **funções públicas**
- Escreva **testes** para novas funcionalidades
- Mantenha **cobertura > 80%**

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 🙏 Agradecimentos

- **Docling** pela excelente biblioteca de conversão
- **Flask** pelo framework web robusto
- **Redis** pelo sistema de cache eficiente
- **Comunidade Python** pelo ecossistema fantástico

---

**Desenvolvido com ❤️ para processamento inteligente de documentos** 