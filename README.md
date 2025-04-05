# PDF Digest

Este projeto fornece um serviço para conversão de arquivos PDF para Markdown usando a biblioteca Docling.

## Instalação

1. Clone este repositório
2. Crie um ambiente virtual:
   ```
   python -m venv venv
   ```
3. Ative o ambiente virtual:
   - Windows:
     ```
     .\venv\Scripts\activate
     ```
   - Linux/Mac:
     ```
     source venv/bin/activate
     ```
4. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

## Estrutura do Projeto

```
.
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── api.py
│   ├── main.py
│   └── pdf_service.py
└── tests/
    ├── __init__.py
    └── test_pdf_service.py
```

## Como Usar

### Iniciar o Serviço

Para iniciar o serviço API:

```
python -m src.main --host 0.0.0.0 --port 5000 --debug
```

### Endpoints da API

#### Verificação de Saúde

```
GET /health
```

Retorno:
```json
{
    "status": "ok"
}
```

#### Converter PDF para Markdown

```
POST /api/convert
```

Existem duas maneiras de usar este endpoint:

1. **Enviando um arquivo PDF**:
   - Faça uma requisição `multipart/form-data` com o arquivo PDF no campo `file`.

2. **Usando um caminho de arquivo no servidor**:
   - Faça uma requisição `application/json` com um dos seguintes formatos:
     
     a) Fornecendo caminho do diretório e nome do arquivo separadamente:
     ```json
     {
         "path": "/caminho/para/diretorio",
         "filename": "arquivo.pdf"
     }
     ```
     
     b) Fornecendo o caminho completo do arquivo:
     ```json
     {
         "path": "/caminho/completo/para/arquivo.pdf"
     }
     ```

Retorno em caso de sucesso:
```json
{
    "success": true,
    "markdown": "# Conteúdo do PDF convertido para Markdown\n\nTexto convertido..."
}
```

Retorno em caso de erro:
```json
{
    "error": "Mensagem de erro"
}
```

## Desenvolvimento

- Use `black` para formatação de código
- Use `flake8` para linting
- Execute testes com `pytest`

### Executar Testes

```
pytest
``` 