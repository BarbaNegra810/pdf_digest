# Implementação do Framework Agno para Notas de Corretagem B3

## Visão Geral

Este documento descreve a implementação do framework Agno no sistema PDF Digest para processamento de notas de negociação de ativos da B3 (Brasil, Bolsa, Balcão).

## Funcionalidades Implementadas

### 1. Configuração Adaptativa
- **Parâmetro de configuração**: `PDF_PROCESSOR` no arquivo `.env`
- **Valores suportados**: `"docling"` (padrão) ou `"agno"`
- **Transparência**: O endpoint `/convert` escolhe automaticamente o processador

### 2. Novos Endpoints

#### `/api/extract-b3-trades`
- **Método**: POST
- **Propósito**: Extração específica de trades e fees de notas B3
- **Processador**: Sempre usa Agno
- **Formato de saída**: JSON estruturado

#### `/api/convert` (Modificado)
- **Método**: POST
- **Propósito**: Conversão adaptativa baseada na configuração
- **Processador**: Docling ou Agno conforme configuração
- **Transparência**: Usuários não precisam mudar código cliente

### 3. Schema de Extração

```json
{
  "trades": [
    {
      "orderNumber": "string",
      "tradeDate": "date",
      "operationType": "C|V",
      "marketType": "string",
      "market": "BOVESPA|BMF",
      "ticker": "string",
      "quantity": "integer",
      "price": "number",
      "totalValue": "number",
      "strikePrice": "number|null",
      "expirationDate": "date|null"
    }
  ],
  "fees": [
    {
      "orderNumber": "string",
      "totalFees": "number"
    }
  ]
}
```

## Arquitetura

### Componentes Principais

1. **AgnoService** (`src/services/agno_service.py`)
   - Gerencia integração com framework Agno
   - Valida resultados conforme schema
   - Implementa cache específico

2. **PDFService Adaptativo** (`src/services/pdf_service.py`)
   - Método `convert_pdf_adaptive()` escolhe processador
   - Formatação unificada de respostas
   - Compatibilidade com ambos os sistemas

3. **Rotas da API** (`src/api/routes.py`)
   - Endpoint específico para B3
   - Endpoint adaptativo transparente
   - Tratamento de erros unificado

### Configuração

```bash
# .env
PDF_PROCESSOR=agno  # ou "docling"
```

## Instalação e Configuração

### 1. Instalação Automática do Agno
```bash
# Execute o script de instalação automática
python install_agno.py
```

### 2. Instalação Manual das Dependências
```bash
# Framework Agno e dependências
pip install agno openai duckduckgo-search yfinance lancedb tantivy pypdf exa-py newspaper4k lxml_html_clean sqlalchemy
```

### 3. Configuração de Variáveis de Ambiente
```bash
# Configuração obrigatória no .env
OPENAI_API_KEY=your-openai-api-key-here  # OBRIGATÓRIO para Agno
PDF_PROCESSOR=agno  # Para usar Agno
# PDF_PROCESSOR=docling  # Para usar Docling (padrão)
```

### 4. Configuração do Agno
O serviço Agno é configurado automaticamente com:
- **Modelo**: GPT-4 Omni para máxima precisão
- **Ferramentas**: ReasoningTools e FileTools
- **Schema**: Otimizado para notas de corretagem B3
- **Instruções**: Especializadas em extração de trades e fees

## Uso da API

### Extração Específica B3 (Sempre Agno)
```python
import requests

# Upload de arquivo
with open('nota_corretagem.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/extract-b3-trades',
        files={'file': f}
    )

# Arquivo no servidor
response = requests.post(
    'http://localhost:5000/api/extract-b3-trades',
    json={'path': 'uploads/nota_corretagem.pdf'}
)

result = response.json()['data']
trades = result['trades']
fees = result['fees']
```

### Conversão Adaptativa
```python
# Usa processador configurado (transparente)
response = requests.post(
    'http://localhost:5000/api/convert',
    files={'file': pdf_file}
)

result = response.json()['data']
processor = result['processor']  # 'agno' ou 'docling'

if processor == 'agno':
    trades = result['trades']
    fees = result['fees']
else:
    pages = result['pages']
```

## Respostas da API

### Formato Agno (JSON Estruturado)
```json
{
  "success": true,
  "data": {
    "processor": "agno",
    "format": "json",
    "trades": [...],
    "fees": [...],
    "file_info": {
      "filename": "nota.pdf",
      "size_bytes": 1024,
      "hash": "abc123"
    },
    "processing_info": {
      "total_trades": 5,
      "total_fees": 1,
      "processor": "agno"
    }
  }
}
```

### Formato Docling (Markdown)
```json
{
  "success": true,
  "data": {
    "processor": "docling",
    "format": "markdown",
    "pages": {
      "1": "# NOTA DE NEGOCIAÇÃO...",
      "2": "# NOTA DE NEGOCIAÇÃO..."
    },
    "file_info": {
      "pages_count": 2
    },
    "processing_info": {
      "device": "cuda:0"
    }
  }
}
```

## Validação de Dados

### Trades
- **Campos obrigatórios**: orderNumber, tradeDate, operationType, marketType, market, ticker, quantity, price, totalValue
- **Validações**: 
  - operationType: 'C' ou 'V'
  - market: 'BOVESPA' ou 'BMF'
  - quantity: inteiro positivo
  - price/totalValue: números positivos

### Fees
- **Campos obrigatórios**: orderNumber, totalFees
- **Validações**: totalFees >= 0

## Cache

- **Chave Agno**: `agno_extraction:{file_hash}`
- **Chave Docling**: `pdf_conversion:{file_hash}`
- **Limpeza**: Métodos específicos por processador

## Monitoramento

### Logs
```
INFO - Conversão adaptativa iniciada com processador: agno
INFO - Convertendo com Agno: /path/to/file.pdf
INFO - Extração concluída: 5 trades, 1 fees
```

### Métricas
- Total de trades extraídos
- Total de fees extraídos
- Processador utilizado
- Tempo de processamento

## Compatibilidade

### Backward Compatibility
- APIs existentes continuam funcionando
- Configuração padrão usa Docling
- Sem breaking changes

### Forward Compatibility
- Estrutura preparada para framework Agno real
- Schema flexível para extensões
- Interface estável

## Implementação Real do Agno

✅ **IMPLEMENTADO**: A implementação agora usa o framework Agno real com agentes especializados.

### Como Funciona o Agno Real:
1. **Agente GPT-4 Omni**: Modelo avançado para extração precisa
2. **Ferramentas Especializadas**: ReasoningTools + FileTools para análise de PDFs
3. **Instruções Específicas**: Prompt otimizado para notas de corretagem B3
4. **Saída Estruturada**: JSON validado conforme schema definido

### Fluxo de Processamento:
```python
# 1. Agente recebe PDF e instruções específicas
agent = Agent(
    model=OpenAI(id="gpt-4o"),
    tools=[ReasoningTools(), FileTools()],
    instructions="Extrair trades e fees de notas B3..."
)

# 2. Processa arquivo com prompt especializado
response = agent.run(message=prompt_with_file_path)

# 3. Extrai JSON estruturado da resposta
result = extract_json_from_response(response.content)

# 4. Valida conforme schema definido
validated_result = validate_extraction_result(result)
```

## Troubleshooting

### Erros Comuns

1. **"OPENAI_API_KEY não configurada"**
   - Chave da OpenAI não definida no .env
   - Solução: Configure OPENAI_API_KEY=sua-chave

2. **"Framework Agno não disponível"**
   - Framework Agno não instalado
   - Solução: Execute `python install_agno.py`

3. **"Resultado da extração inválido"**
   - Resposta do GPT não está em JSON válido
   - Schema não compatível com dados extraídos

4. **"PDF processor deve ser um de: ['docling', 'agno']"**
   - Valor inválido na configuração
   - Verificar arquivo .env

5. **"Erro ao parsear resposta do Agno"**
   - GPT retornou texto não-JSON
   - Prompt pode precisar de ajuste

### Debug
```python
# Verificar configuração
from src.config.settings import settings
print(f"Processador configurado: {settings.pdf_processor}")
print(f"OpenAI API Key configurada: {bool(settings.openai_api_key)}")

# Verificar disponibilidade do Agno
from src.services.agno_service import agno_service, AGNO_AVAILABLE
print(f"Agno disponível: {AGNO_AVAILABLE}")
print(f"Agente pronto: {agno_service.agent is not None}")

# Info completa do processamento
info = agno_service.get_processing_info()
for key, value in info.items():
    print(f"{key}: {value}")
```

## Próximos Passos

1. ✅ **Integração Real**: Framework Agno implementado com GPT-4 Omni
2. **Otimizações**: Ajuste fino de prompts para melhor precisão
3. **Novos Formatos**: Suporte a outros tipos de documentos financeiros
4. **Analytics**: Métricas avançadas de extração e confiabilidade
5. **Validação**: Regras de negócio específicas da B3
6. **Fallback Inteligente**: Combinar Agno + Docling para máxima robustez

## Conclusão

A implementação do framework Agno foi realizada de forma:
- **Transparente**: Usuários não precisam alterar código
- **Configurável**: Fácil alternância entre processadores
- **Extensível**: Preparada para futuras melhorias
- **Robusta**: Validação completa de dados
- **Compatível**: Mantém funcionalidades existentes

A solução oferece uma API moderna e flexível para processamento de notas de corretagem B3, combinando a potência do Docling para conversão geral com a especialização do Agno (GPT-4 Omni) para extração estruturada de dados financeiros.

### 🚀 **Framework Agno Real Implementado!**

- ✅ **GPT-4 Omni**: Modelo mais avançado da OpenAI
- ✅ **Ferramentas Especializadas**: ReasoningTools + FileTools
- ✅ **Prompts Otimizados**: Instruções específicas para notas B3
- ✅ **Validação Rigorosa**: Schema JSON completo
- ✅ **Cache Inteligente**: Performance otimizada
- ✅ **Fallback Robusto**: Docling como backup
- ✅ **API Transparente**: Mudança de processador sem quebrar código

**Resultado**: Sistema híbrido que combina o melhor da análise tradicional (Docling) com inteligência artificial avançada (Agno/GPT-4) para extrair dados financeiros com máxima precisão!
