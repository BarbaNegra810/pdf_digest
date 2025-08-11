# Dockerfile para PDF Digest
FROM python:3.11-slim

# Argumentos de build
ARG APP_ENV=production

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=${APP_ENV} \
    PYTHONPATH=/app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Cria diretórios necessários
WORKDIR /app
RUN mkdir -p /app/logs /app/uploads && \
    chown -R appuser:appuser /app

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação
COPY . .
RUN chown -R appuser:appuser /app

# Muda para usuário não-root
USER appuser

# Expõe a porta
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Comando padrão
CMD ["python", "-m", "src.main", "--host", "0.0.0.0", "--port", "5000"] 