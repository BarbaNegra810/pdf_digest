# Guia de Deploy - PDF Digest em Produção (VM Linux)

## Pré-requisitos da VM Linux

### Especificações Mínimas Recomendadas
- **CPU**: 4 cores ou mais
- **RAM**: 8GB (16GB recomendado se usar GPU)
- **Armazenamento**: 50GB+ SSD
- **SO**: Ubuntu 20.04 LTS ou 22.04 LTS
- **GPU**: NVIDIA com suporte CUDA (opcional, mas recomendado)

### Preparação do Sistema

1. **Atualizar o sistema**:
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Instalar dependências do sistema**:
```bash
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    nginx \
    supervisor \
    curl \
    wget \
    unzip \
    build-essential \
    python3-dev
```

3. **Configurar firewall (se necessário)**:
```bash
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## Configuração de GPU (Opcional)

### Para VMs com GPU NVIDIA:

1. **Instalar drivers NVIDIA**:
```bash
sudo apt install nvidia-driver-535
```

2. **Instalar CUDA Toolkit**:
```bash
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt update
sudo apt install cuda-toolkit-11-8
```

3. **Reiniciar a VM**:
```bash
sudo reboot
```

## Deploy da Aplicação

### 1. Criar usuário para a aplicação
```bash
sudo adduser pdfdigest
sudo usermod -aG sudo pdfdigest
su - pdfdigest
```

### 2. Clonar e configurar o projeto
```bash
cd /home/pdfdigest
git clone <url-do-seu-repositorio> pdf-digest
cd pdf-digest

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

# Criar diretórios necessários
mkdir -p logs uploads
```

### 3. Configurar variáveis de ambiente
```bash
# Criar arquivo .env
cat > .env << EOF
FLASK_ENV=production
FLASK_DEBUG=False
UPLOAD_FOLDER=/home/pdfdigest/pdf-digest/uploads
LOG_LEVEL=INFO
MAX_CONTENT_LENGTH=100MB
EOF
```

### 4. Testar a aplicação
```bash
# Ativar ambiente virtual
source venv/bin/activate

# Testar localmente
python -m src.main --host 127.0.0.1 --port 5000
```

## Configuração do Supervisor

### 1. Criar arquivo de configuração do Supervisor
```bash
sudo tee /etc/supervisor/conf.d/pdfdigest.conf << EOF
[program:pdfdigest]
command=/home/pdfdigest/pdf-digest/venv/bin/python -m src.main --host 127.0.0.1 --port 5000
directory=/home/pdfdigest/pdf-digest
user=pdfdigest
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/pdfdigest/pdf-digest/logs/app.log
stdout_logfile_maxbytes=10MB
stdout_logfile_backups=5
environment=PATH="/home/pdfdigest/pdf-digest/venv/bin"
EOF
```

### 2. Iniciar e configurar o Supervisor
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start pdfdigest
sudo supervisorctl status
```

## Configuração do Nginx

### 1. Criar configuração do Nginx
```bash
sudo tee /etc/nginx/sites-available/pdfdigest << EOF
server {
    listen 80;
    server_name seu-dominio.com;  # Altere para seu domínio
    
    # Limites de upload
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts para uploads grandes
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }
    
    # Logs
    access_log /var/log/nginx/pdfdigest_access.log;
    error_log /var/log/nginx/pdfdigest_error.log;
}
EOF
```

### 2. Ativar a configuração
```bash
sudo ln -s /etc/nginx/sites-available/pdfdigest /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## Configuração de SSL com Let's Encrypt

### 1. Instalar Certbot
```bash
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

### 2. Obter certificado SSL
```bash
sudo certbot --nginx -d seu-dominio.com
```

## Scripts de Manutenção

### 1. Script de backup
```bash
sudo tee /home/pdfdigest/backup.sh << EOF
#!/bin/bash
BACKUP_DIR="/backup/pdfdigest"
DATE=\$(date +%Y%m%d_%H%M%S)

mkdir -p \$BACKUP_DIR

# Backup da aplicação
tar -czf "\$BACKUP_DIR/app_\$DATE.tar.gz" -C /home/pdfdigest pdf-digest

# Backup dos logs
tar -czf "\$BACKUP_DIR/logs_\$DATE.tar.gz" /var/log/nginx/pdfdigest_*

# Manter apenas os últimos 7 backups
find \$BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup concluído: \$DATE"
EOF

chmod +x /home/pdfdigest/backup.sh
```

### 2. Script de monitoramento
```bash
sudo tee /home/pdfdigest/monitor.sh << EOF
#!/bin/bash

# Verificar se a aplicação está rodando
if ! supervisorctl status pdfdigest | grep RUNNING > /dev/null; then
    echo "Aplicação não está rodando. Reiniciando..."
    supervisorctl restart pdfdigest
    echo "\$(date): Aplicação reiniciada" >> /home/pdfdigest/pdf-digest/logs/monitor.log
fi

# Verificar se o nginx está rodando
if ! systemctl is-active nginx > /dev/null; then
    echo "Nginx não está rodando. Reiniciando..."
    systemctl restart nginx
    echo "\$(date): Nginx reiniciado" >> /home/pdfdigest/pdf-digest/logs/monitor.log
fi
EOF

chmod +x /home/pdfdigest/monitor.sh
```

### 3. Configurar cron jobs
```bash
crontab -e
# Adicionar as seguintes linhas:
# Backup diário às 2h
0 2 * * * /home/pdfdigest/backup.sh

# Monitoramento a cada 5 minutos
*/5 * * * * /home/pdfdigest/monitor.sh
```

## Configuração de Logs

### 1. Configurar logrotate
```bash
sudo tee /etc/logrotate.d/pdfdigest << EOF
/home/pdfdigest/pdf-digest/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 pdfdigest pdfdigest
    postrotate
        supervisorctl restart pdfdigest
    endscript
}
EOF
```

## Configurações de Segurança

### 1. Configurar iptables básico
```bash
sudo iptables -A INPUT -i lo -j ACCEPT
sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 80 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -j DROP

# Salvar regras
sudo iptables-save > /etc/iptables/rules.v4
```

### 2. Configurar fail2ban
```bash
sudo apt install fail2ban -y

sudo tee /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = iptables-multiport[name=ReqLimit, port="http,https", protocol=tcp]
logpath = /var/log/nginx/*error.log
findtime = 600
bantime = 7200
maxretry = 10
EOF

sudo systemctl restart fail2ban
```

## Monitoramento e Performance

### 1. Instalar htop e iotop
```bash
sudo apt install htop iotop -y
```

### 2. Configurar monitoramento de recursos
```bash
# Script de monitoramento de recursos
sudo tee /home/pdfdigest/resource_monitor.sh << EOF
#!/bin/bash
LOG_FILE="/home/pdfdigest/pdf-digest/logs/resources.log"

while true; do
    echo "\$(date): \$(free -h | grep Mem:), \$(df -h / | tail -1)" >> \$LOG_FILE
    sleep 300  # A cada 5 minutos
done &
EOF

chmod +x /home/pdfdigest/resource_monitor.sh
```

## Comandos Úteis para Manutenção

### Status dos serviços
```bash
# Status da aplicação
sudo supervisorctl status pdfdigest

# Status do nginx
sudo systemctl status nginx

# Logs da aplicação
tail -f /home/pdfdigest/pdf-digest/logs/app.log

# Logs do nginx
tail -f /var/log/nginx/pdfdigest_access.log
tail -f /var/log/nginx/pdfdigest_error.log
```

### Reinicialização
```bash
# Reiniciar aplicação
sudo supervisorctl restart pdfdigest

# Reiniciar nginx
sudo systemctl restart nginx

# Reiniciar todos os serviços
sudo supervisorctl restart all && sudo systemctl restart nginx
```

### Atualização da aplicação
```bash
cd /home/pdfdigest/pdf-digest
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart pdfdigest
```

## Testes de Funcionamento

### 1. Teste de health check
```bash
curl http://localhost/health
```

### 2. Teste de conversão com arquivo
```bash
curl -X POST -F "file=@test.pdf" http://localhost/api/convert
```

### 3. Teste de conversão com caminho
```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"path": "/caminho/para/arquivo.pdf"}' \
     http://localhost/api/convert
```

## Troubleshooting

### Problemas comuns:

1. **Aplicação não inicia**:
   - Verificar logs: `tail -f /home/pdfdigest/pdf-digest/logs/app.log`
   - Verificar dependências: `source venv/bin/activate && pip check`

2. **Nginx retorna 502**:
   - Verificar se a aplicação está rodando: `supervisorctl status`
   - Verificar configuração do nginx: `sudo nginx -t`

3. **Upload falha**:
   - Verificar limites no nginx: `client_max_body_size`
   - Verificar espaço em disco: `df -h`

4. **Performance lenta**:
   - Verificar uso de recursos: `htop`
   - Verificar se GPU está sendo usada (se disponível)
   - Considerar aumentar recursos da VM

## Backup e Recuperação

### Backup completo
```bash
tar -czf pdfdigest_backup_$(date +%Y%m%d).tar.gz \
    /home/pdfdigest/pdf-digest \
    /etc/nginx/sites-available/pdfdigest \
    /etc/supervisor/conf.d/pdfdigest.conf
```

### Restauração
```bash
# Parar serviços
sudo supervisorctl stop pdfdigest
sudo systemctl stop nginx

# Restaurar arquivos
tar -xzf pdfdigest_backup_YYYYMMDD.tar.gz -C /

# Reiniciar serviços
sudo supervisorctl start pdfdigest
sudo systemctl start nginx
```

---

## Checklist Final

- [ ] VM Linux preparada com dependências
- [ ] Usuário pdfdigest criado
- [ ] Aplicação clonada e configurada
- [ ] Supervisor configurado e rodando
- [ ] Nginx configurado como proxy reverso
- [ ] SSL configurado (se necessário)
- [ ] Scripts de backup e monitoramento criados
- [ ] Cron jobs configurados
- [ ] Firewall e segurança configurados
- [ ] Testes de funcionamento realizados
- [ ] Documentação de troubleshooting revisada

Com essa configuração, seu projeto PDF Digest estará rodando de forma robusta e segura em produção! 