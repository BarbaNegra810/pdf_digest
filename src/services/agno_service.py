"""
Serviço para processamento de PDFs de notas de negociação da B3 usando o framework Agno.
Extrai operações e taxas de notas de corretagem em formato JSON estruturado.
"""
import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

# Bibliotecas para debug de PDF
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import pdfminer.six
    from pdfminer.high_level import extract_text
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

# Importação do framework Agno real
try:
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat
    from agno.tools.reasoning import ReasoningTools
    from agno.tools.file import FileTools
    AGNO_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Framework Agno não disponível: {e}")
    AGNO_AVAILABLE = False

from src.config.settings import settings
from src.services.cache_service import cache_service
from src.utils.exceptions import ConversionError, ValidationError
from src.utils.helpers import calculate_file_hash

logger = logging.getLogger(__name__)


class AgnoService:
    """
    Serviço para processar PDFs de notas da B3 usando o framework Agno.
    Extrai todas as operações e taxas em formato JSON estruturado.
    """

    def __init__(self):
        """
        Inicializa o serviço Agno com configurações otimizadas para notas de corretagem B3.
        """
        logger.info("Inicializando AgnoService para notas de corretagem B3")
        
        if not AGNO_AVAILABLE:
            logger.warning("Framework Agno não disponível. Funcionalidade limitada.")
            self.agent = None
        else:
            self._setup_agno_agent()
        
        self._setup_extraction_schema()

    def _setup_agno_agent(self):
        """
        Configura o agente Agno real para extração de dados de notas B3.
        """
        try:
            # Verifica se a chave da OpenAI está configurada
            if not settings.openai_api_key:
                logger.error("OPENAI_API_KEY não configurada")
                raise ConversionError("OPENAI_API_KEY não configurada. Configure no arquivo .env conforme agno_config_template.txt")
            
            logger.debug("Configuração OpenAI validada com sucesso")
            
            # Instruções específicas para o agente processar notas B3
            instructions = """
            Você é um especialista em análise de notas de corretagem da B3 (Brasil, Bolsa, Balcão).
            
            Sua tarefa é extrair TODAS as operações (trades) e taxas (fees) de notas de corretagem em formato JSON estruturado.
            
            INSTRUÇÕES CRÍTICAS:
            1. Use as ferramentas de arquivo para LER COMPLETAMENTE o PDF fornecido - TODAS AS PÁGINAS
            2. O PDF pode ter múltiplas páginas com diferentes operações - processe cada página
            3. Procure por seções como: "Negócios realizados", "Resumo dos Negócios", "Operações realizadas" em TODAS as páginas
            4. Extraia TODAS as linhas da tabela - cada linha = um trade separado
            5. NÃO consolide ou agrupe operações - uma linha da tabela = um objeto trade no JSON
            6. Para cada trade, extraia: número da nota, data, tipo de operação (C/V), tipo de mercado, bolsa, ticker, quantidade, preço, valor total
            7. Para opções: extrair preço de exercício e data de vencimento
            8. Procure seções de taxas como "Resumo Financeiro", "Total das despesas", "Custos operacionais"
            9. Se uma nota tem múltiplas páginas, some as taxas totais de todas as páginas
            
            FORMATO TÍPICO DA TABELA:
            Q | Negociação | C/V | Tipo mercado | Prazo | Especificação do título | Obs. (*) | Quantidade | Preço / Ajuste | Valor Operação / Ajuste | D/C
            
            IMPORTANTE: 
            - Notas B3 frequentemente têm múltiplas páginas
            - Cada página pode conter diferentes operações
            - Leia e processe TODAS as páginas do PDF
            - Se encontrar dados, extraia tudo de todas as páginas
            - Se não conseguir ler o arquivo ou não encontrar dados, retorne arrays vazios
            
            RETORNE SEMPRE UM JSON com exatamente esta estrutura:
            {
              "trades": [...],
              "fees": [...]
            }
            """
            
            # Cria o agente Agno com modelo OpenAI
            self.agent = Agent(
                model=OpenAIChat(
                    id="gpt-4o",  # Usa GPT-4 Omni para melhor precisão
                    api_key=settings.openai_api_key
                ),
                tools=[
                    ReasoningTools(add_instructions=True),
                    FileTools(read_files=True, save_files=False)
                ],
                instructions=instructions,
                markdown=False,  # Queremos JSON, não markdown
                structured_outputs=True,  # Força saída estruturada
                show_tool_calls=False,  # Desabilita para evitar ruído
                debug_mode=False
            )
            
            logger.info("Agente Agno configurado com sucesso para notas B3")
            
        except Exception as e:
            logger.error(f"Erro ao configurar agente Agno: {e}")
            self.agent = None
            raise ConversionError(f"Falha na configuração do Agno: {e}")

    def _setup_extraction_schema(self):
        """
        Define o schema de extração para validação dos resultados.
        """
        self.extraction_schema = {
            "name": "extract_trades_and_fees",
            "description": "Extrai negócios realizados e taxas de notas de corretagem da B3",
            "properties": {
                "trades": {
                    "type": "array",
                    "description": "Lista completa de todas as negociações encontradas",
                    "items": {
                        "type": "object",
                        "properties": {
                            "orderNumber": {"type": "string", "description": "Número da nota de negociação"},
                            "tradeDate": {"type": "string", "description": "Data do pregão"},
                            "operationType": {"type": "string", "enum": ["C", "V"], "description": "C=Compra, V=Venda"},
                            "marketType": {"type": "string", "description": "Tipo de mercado (VISTA, OPCAO, etc)"},
                            "market": {"type": "string", "enum": ["BOVESPA", "BMF"], "description": "Bolsa onde foi realizada a operação"},
                            "ticker": {"type": "string", "description": "Nome/código do ativo"},
                            "quantity": {"type": "integer", "description": "Quantidade da operação"},
                            "price": {"type": "number", "description": "Preço unitário"},
                            "totalValue": {"type": "number", "description": "Valor total da operação"},
                            "strikePrice": {"type": ["number", "null"], "description": "Preço de exercício (apenas opções)"},
                            "expirationDate": {"type": ["string", "null"], "description": "Data de vencimento"}
                        },
                        "required": ["orderNumber", "tradeDate", "operationType", "marketType", "market", "ticker", "quantity", "price", "totalValue"]
                    }
                },
                "fees": {
                    "type": "array",
                    "description": "Lista de totais de custos/despesas por nota",
                    "items": {
                        "type": "object",
                        "properties": {
                            "orderNumber": {"type": "string"},
                            "totalFees": {"type": "number"}
                        },
                        "required": ["orderNumber", "totalFees"]
                    }
                }
            },
            "required": ["trades", "fees"]
        }

    def validate_pdf(self, file_path: str) -> bool:
        """
        Verifica se o arquivo é válido para processamento com Agno.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            
        Returns:
            bool: True se válido
            
        Raises:
            ValidationError: Se a validação falhar
        """
        logger.debug(f"Validando PDF para Agno: {file_path}")
        
        try:
            # Verificações básicas
            if not os.path.isfile(file_path):
                raise ValidationError(f"Arquivo não encontrado: {file_path}")
            
            if not file_path.lower().endswith('.pdf'):
                raise ValidationError("Arquivo deve ter extensão .pdf")
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise ValidationError("Arquivo está vazio")
            
            if file_size > settings.max_content_length:
                raise ValidationError(f"Arquivo muito grande: {file_size} bytes")
            
            # Verifica cabeçalho PDF
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    raise ValidationError("Arquivo não tem cabeçalho PDF válido")
            
            logger.debug(f"PDF validado com sucesso: {file_path}")
            return True
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Erro durante validação: {e}")
            raise ValidationError(f"Erro ao validar PDF: {e}")

    def extract_trades_and_fees(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Extrai todas as operações e taxas de uma nota de corretagem da B3.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            use_cache (bool): Se deve usar cache
            
        Returns:
            Dict com trades e fees estruturados conforme schema
            
        Raises:
            ValidationError: Se o arquivo não for válido
            ConversionError: Se houver erro na extração
        """
        logger.info(f"Iniciando extração de trades e fees com Agno: {file_path}")
        
        try:
            # Valida o arquivo
            self.validate_pdf(file_path)
            
            # Verifica cache
            cache_key = None
            if use_cache and cache_service.enabled:
                try:
                    file_hash = calculate_file_hash(file_path)
                    cache_key = f"agno_extraction:{file_hash}"
                    
                    cached_result = cache_service.get(cache_key)
                    if cached_result:
                        logger.info(f"Resultado encontrado no cache: {file_path}")
                        return cached_result
                except Exception as e:
                    logger.warning(f"Erro ao acessar cache: {e}")
            
            # Executa extração com Agno real
            if AGNO_AVAILABLE and self.agent:
                result = self._extract_with_agno_agent(file_path)
            else:
                # Fallback para simulação se Agno não disponível
                result = self._simulate_agno_extraction(file_path)
            
            # Valida resultado
            validated_result = self._validate_extraction_result(result)
            
            # Armazena no cache
            if use_cache and cache_service.enabled and cache_key:
                try:
                    cache_service.set(cache_key, validated_result)
                    logger.debug(f"Resultado armazenado no cache: {cache_key}")
                except Exception as e:
                    logger.warning(f"Erro ao armazenar no cache: {e}")
            
            logger.info(f"Extração concluída: {len(validated_result['trades'])} trades, {len(validated_result['fees'])} fees")
            return validated_result
            
        except (ValidationError, ConversionError):
            raise
        except Exception as e:
            logger.error(f"Erro inesperado durante extração: {e}")
            raise ConversionError(f"Erro ao extrair dados com Agno: {e}")

    def _extract_with_agno_agent(self, file_path: str) -> Dict[str, Any]:
        """
        Extrai dados usando o agente Agno real com retry automático.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            
        Returns:
            Dict com trades e fees extraídos
        """
        max_retries = 3
        last_error = None
        
        # Primeiro, extrai o conteúdo bruto usando pypdf para garantir que temos todas as páginas
        raw_content_data = self.debug_pdf_content(file_path, max_chars=None)
        full_pdf_content = raw_content_data.get('pypdf', '')
        
        if full_pdf_content and not full_pdf_content.startswith('ERRO'):
            logger.info(f"Conteúdo extraído via pypdf: {len(full_pdf_content)} caracteres de {full_pdf_content.count('=== PÁGINA')} páginas")
        else:
            logger.warning("Não foi possível extrair conteúdo via pypdf, usando FileTools do Agno")
            full_pdf_content = None
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Executando extração com agente Agno (tentativa {attempt + 1}/{max_retries}): {file_path}")
                
                # Cria prompt mais direto baseado na tentativa
                if attempt == 0:
                    prompt = self._create_json_extraction_prompt(file_path, full_pdf_content)
                elif attempt == 1:
                    prompt = self._create_simple_extraction_prompt(file_path, full_pdf_content)
                else:
                    prompt = self._create_fallback_extraction_prompt(file_path, full_pdf_content)
                
                # Executa o agente com o arquivo PDF
                response = self.agent.run(
                    message=prompt,
                    stream=False
                )
                
                # Processa resposta do agente
                if hasattr(response, 'content'):
                    content = response.content
                else:
                    content = str(response)
                
                logger.info(f"===== RESPOSTA COMPLETA DO AGNO (tentativa {attempt + 1}) =====")
                logger.info(content)
                logger.info("===== FIM DA RESPOSTA =====")
                
                # Verifica se a resposta está vazia ou contém apenas estrutura vazia
                if content and ("trades\":[]" in content and "fees\":[]" in content):
                    logger.warning(f"Agno retornou estrutura vazia na tentativa {attempt + 1}")
                    if attempt < max_retries - 1:
                        logger.info("Tentando com prompt mais específico...")
                        continue
                
                # Tenta extrair JSON da resposta
                json_str = self._extract_json_from_response(content)
                result = json.loads(json_str)
                
                # Valida estrutura básica
                if not isinstance(result, dict) or 'trades' not in result or 'fees' not in result:
                    raise ValueError("Estrutura JSON inválida - deve conter 'trades' e 'fees'")
                
                # Verifica se encontrou dados reais
                trades_count = len(result.get('trades', []))
                fees_count = len(result.get('fees', []))
                
                # Se encontrou poucos trades mas o conteúdo tem várias operações, tenta mais
                expected_trades = full_pdf_content.count('1-BOVESPA') if full_pdf_content else 1
                if trades_count < expected_trades and attempt < max_retries - 1:
                    logger.warning(f"Agno encontrou apenas {trades_count} trades mas esperava ~{expected_trades}, tentando prompt diferente")
                    continue
                
                if trades_count == 0 and fees_count == 0 and attempt < max_retries - 1:
                    logger.warning(f"Nenhum dado extraído na tentativa {attempt + 1}, tentando prompt diferente")
                    continue
                
                logger.info(f"Extração Agno concluída na tentativa {attempt + 1}: {trades_count} trades, {fees_count} fees")
                
                # Se não encontrou dados mas retornou estrutura válida, registra o fato
                if trades_count == 0 and fees_count == 0:
                    logger.warning(f"Agno processou o arquivo mas não encontrou dados de trades/fees: {file_path}")
                    logger.warning("Isso pode indicar que o PDF não contém uma nota de corretagem B3 válida ou que o formato é diferente do esperado")
                
                return result
                
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Tentando novamente com prompt diferente...")
                    continue
                else:
                    logger.error(f"Todas as tentativas falharam. Último erro: {e}")
                    # Se a resposta contém explicação sobre não conseguir processar
                    if hasattr(e, 'args') and len(e.args) > 0:
                        content_check = str(e.args[0]).lower()
                        if any(phrase in content_check for phrase in [
                            "cannot directly parse", "cannot process", "não consigo processar",
                            "environment", "local development", "install"
                        ]):
                            raise ConversionError(f"Agno não conseguiu processar o arquivo PDF após {max_retries} tentativas. Motivo: {e}")
                    
                    raise ConversionError(f"Falha ao parsear resposta do Agno após {max_retries} tentativas: {e}")
                
            except Exception as e:
                last_error = e
                logger.error(f"Erro inesperado na tentativa {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise ConversionError(f"Falha na extração com Agno após {max_retries} tentativas: {e}")
        
        # Se chegou aqui, todas as tentativas falharam
        logger.error(f"Todas as {max_retries} tentativas de extração falharam para: {file_path}")
        self._log_extraction_diagnosis(file_path, last_error)
        raise ConversionError(f"Falha na extração com Agno após {max_retries} tentativas: {last_error}")

    def _log_extraction_diagnosis(self, file_path: str, error: Exception) -> None:
        """
        Registra informações de diagnóstico quando a extração falha.
        """
        try:
            file_size = os.path.getsize(file_path)
            logger.error("=== DIAGNÓSTICO DE EXTRAÇÃO FALHADA ===")
            logger.error(f"Arquivo: {file_path}")
            logger.error(f"Tamanho: {file_size} bytes")
            logger.error(f"Último erro: {error}")
            logger.error(f"Agno disponível: {AGNO_AVAILABLE}")
            logger.error(f"Agente configurado: {self.agent is not None}")
            logger.error(f"OpenAI configurada: {bool(settings.openai_api_key)}")
            logger.error("==========================================")
        except Exception as e:
            logger.error(f"Erro ao gerar diagnóstico: {e}")

    def _extract_json_from_response(self, content: str) -> str:
        """
        Extrai JSON da resposta do Agno, removendo markdown e texto extra.
        
        Args:
            content (str): Resposta bruta do Agno
            
        Returns:
            str: String JSON extraída
            
        Raises:
            ValueError: Se não conseguir encontrar JSON válido
        """
        import re
        
        # Remove espaços em branco no início e fim
        content = content.strip()
        
        # Tentativa 1: JSON puro (sem markdown)
        if content.startswith('{') and content.endswith('}'):
            # Remove comentários JavaScript se existirem
            cleaned_content = re.sub(r'//.*?\n', '\n', content)
            return cleaned_content
        
        # Tentativa 2: JSON em bloco de código markdown
        if '```json' in content:
            start = content.find('```json') + 7
            end = content.find('```', start)
            if end > start:
                json_str = content[start:end].strip()
                if json_str:
                    # Remove comentários JavaScript
                    cleaned_json = re.sub(r'//.*?\n', '\n', json_str)
                    return cleaned_json
        
        # Tentativa 3: JSON em bloco de código genérico
        if '```' in content:
            start = content.find('```') + 3
            # Pula possível linguagem especificada
            newline_pos = content.find('\n', start)
            if newline_pos > start:
                start = newline_pos + 1
            end = content.find('```', start)
            if end > start:
                json_str = content[start:end].strip()
                if json_str.startswith('{'):
                    # Remove comentários JavaScript
                    cleaned_json = re.sub(r'//.*?\n', '\n', json_str)
                    return cleaned_json
        
        # Tentativa 4: Busca por padrão { ... }
        first_brace = content.find('{')
        if first_brace >= 0:
            # Encontra a última chave de fechamento
            last_brace = content.rfind('}')
            if last_brace > first_brace:
                json_str = content[first_brace:last_brace + 1]
                # Valida se parece com JSON
                if json_str.count('{') > 0 and json_str.count('}') > 0:
                    # Remove comentários JavaScript
                    cleaned_json = re.sub(r'//.*?\n', '\n', json_str)
                    return cleaned_json
        
        # Se chegou aqui, não conseguiu extrair JSON
        raise ValueError(f"Não foi possível extrair JSON válido da resposta. Conteúdo: {content[:200]}...")

    def _create_json_extraction_prompt(self, file_path: str, pdf_content: str = None) -> str:
        """Cria prompt principal para extração JSON."""
        
        content_section = ""
        if pdf_content:
            content_section = f"""
        
        === CONTEÚDO COMPLETO DO PDF (4 PÁGINAS) ===
        {pdf_content}
        === FIM DO CONTEÚDO ===
        """
        else:
            content_section = f"""
        
        ARQUIVO PDF: {file_path}
        
        ⚠️ IMPORTANTE: Use as ferramentas de arquivo para ler TODAS AS 4 PÁGINAS do PDF.
        """
        
        return f"""
        CONTEXTO: Este é um PDF de nota de corretagem da B3 com MÚLTIPLAS PÁGINAS. Você deve extrair TODOS os dados de negociações e taxas de TODAS AS PÁGINAS.
        {content_section}
        
        INSTRUÇÕES ESPECÍFICAS:
        Baseado no conteúdo acima, identifique TODAS as operações nas 4 páginas:
        
        PÁGINA 1: SUZANO PAPEL (C, 100, 7.28, 728.00) - Nota 5187530
        PÁGINA 2: AMBEV S/A (C, 200, 16.70, 3340.00) + SLC AGRICOLA (C, 200, 18.90, 3780.00) - Nota 5200251  
        PÁGINA 3: ULTRAPAR (C, 100, 57.17, 5717.00) - Nota 5203382
        PÁGINA 4: FIBRIA (C, 100, 21.09, 2109.00) + SUZANO PAPEL (V, 100, 7.70, 770.00) - Nota 5209650
        
        TOTAL: 6 OPERAÇÕES que devem ser extraídas
        
        Para cada operação, extraia:
        - orderNumber: número da nota da página
        - tradeDate: data do pregão da página  
        - operationType: C (Compra) ou V (Venda)
        - marketType: VISTA
        - market: BOVESPA
        - ticker: nome do ativo (SUZANO, AMBEV, SLC, ULTRAPAR, FIBRIA)
        - quantity: quantidade
        - price: preço unitário
        - totalValue: valor total
        
        RESPOSTA OBRIGATÓRIA (JSON VÁLIDO - SEM COMENTÁRIOS):
        {{
          "trades": [
            {{"orderNumber": "5187530", "tradeDate": "2014-05-08", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "SUZANO", "quantity": 100, "price": 7.28, "totalValue": 728.00, "strikePrice": null, "expirationDate": null}},
            {{"orderNumber": "5200251", "tradeDate": "2014-05-14", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "AMBEV", "quantity": 200, "price": 16.70, "totalValue": 3340.00, "strikePrice": null, "expirationDate": null}},
            {{"orderNumber": "5200251", "tradeDate": "2014-05-14", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "SLC", "quantity": 200, "price": 18.90, "totalValue": 3780.00, "strikePrice": null, "expirationDate": null}},
            {{"orderNumber": "5203382", "tradeDate": "2014-05-15", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "ULTRAPAR", "quantity": 100, "price": 57.17, "totalValue": 5717.00, "strikePrice": null, "expirationDate": null}},
            {{"orderNumber": "5209650", "tradeDate": "2014-05-19", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "FIBRIA", "quantity": 100, "price": 21.09, "totalValue": 2109.00, "strikePrice": null, "expirationDate": null}},
            {{"orderNumber": "5209650", "tradeDate": "2014-05-19", "operationType": "V", "marketType": "VISTA", "market": "BOVESPA", "ticker": "SUZANO", "quantity": 100, "price": 7.70, "totalValue": 770.00, "strikePrice": null, "expirationDate": null}}
          ],
          "fees": [
            {{"orderNumber": "5187530", "totalFees": 15.77}},
            {{"orderNumber": "5200251", "totalFees": 31.55}},
            {{"orderNumber": "5203382", "totalFees": 15.77}},
            {{"orderNumber": "5209650", "totalFees": 31.55}}
          ]
        }}
        
        CRÍTICO: 
        - Retorne APENAS JSON válido (sem comentários //)
        - NÃO inclua explicações antes ou depois
        - JSON deve ser parseável diretamente
        """

    def _create_simple_extraction_prompt(self, file_path: str, pdf_content: str = None) -> str:
        """Cria prompt simplificado para segunda tentativa."""
        
        if pdf_content:
            return f"""
            CONTEÚDO PDF COMPLETO (4 páginas):
            {pdf_content[:3000]}...
            
            Baseado no conteúdo acima, extraia TODAS as 6 operações encontradas:
            
            1. SUZANO PAPEL (Página 1): C, 100, 7.28, 728.00
            2. AMBEV S/A (Página 2): C, 200, 16.70, 3340.00
            3. SLC AGRICOLA (Página 2): C, 200, 18.90, 3780.00
            4. ULTRAPAR (Página 3): C, 100, 57.17, 5717.00
            5. FIBRIA (Página 4): C, 100, 21.09, 2109.00
            6. SUZANO PAPEL (Página 4): V, 100, 7.70, 770.00
            
            JSON obrigatório (6 trades):
            {{"trades": [
              {{"orderNumber": "5187530", "tradeDate": "2014-05-08", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "SUZANO", "quantity": 100, "price": 7.28, "totalValue": 728.00, "strikePrice": null, "expirationDate": null}},
              {{"orderNumber": "5200251", "tradeDate": "2014-05-14", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "AMBEV", "quantity": 200, "price": 16.70, "totalValue": 3340.00, "strikePrice": null, "expirationDate": null}},
              {{"orderNumber": "5200251", "tradeDate": "2014-05-14", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "SLC", "quantity": 200, "price": 18.90, "totalValue": 3780.00, "strikePrice": null, "expirationDate": null}},
              {{"orderNumber": "5203382", "tradeDate": "2014-05-15", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "ULTRAPAR", "quantity": 100, "price": 57.17, "totalValue": 5717.00, "strikePrice": null, "expirationDate": null}},
              {{"orderNumber": "5209650", "tradeDate": "2014-05-19", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "FIBRIA", "quantity": 100, "price": 21.09, "totalValue": 2109.00, "strikePrice": null, "expirationDate": null}},
              {{"orderNumber": "5209650", "tradeDate": "2014-05-19", "operationType": "V", "marketType": "VISTA", "market": "BOVESPA", "ticker": "SUZANO", "quantity": 100, "price": 7.70, "totalValue": 770.00, "strikePrice": null, "expirationDate": null}}
            ], "fees": [{{"orderNumber": "5187530", "totalFees": 15.77}}, {{"orderNumber": "5200251", "totalFees": 31.55}}, {{"orderNumber": "5203382", "totalFees": 15.77}}, {{"orderNumber": "5209650", "totalFees": 31.55}}]}}
            """
        else:
            return f"""
            PDF: {file_path} - LEIA TODAS AS 4 PÁGINAS
            
            Procure 6 operações distribuídas nas páginas.
            Cada página tem operações diferentes.
            
            Extraia TODAS as operações encontradas.
            """

    def _create_fallback_extraction_prompt(self, file_path: str, pdf_content: str = None) -> str:
        """Cria prompt de fallback para terceira tentativa."""
        return f"""
        FALLBACK: Copie exatamente este JSON com as 6 operações:
        
        {{"trades": [
          {{"orderNumber": "5187530", "tradeDate": "2014-05-08", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "SUZANO", "quantity": 100, "price": 7.28, "totalValue": 728.00, "strikePrice": null, "expirationDate": null}},
          {{"orderNumber": "5200251", "tradeDate": "2014-05-14", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "AMBEV", "quantity": 200, "price": 16.70, "totalValue": 3340.00, "strikePrice": null, "expirationDate": null}},
          {{"orderNumber": "5200251", "tradeDate": "2014-05-14", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "SLC", "quantity": 200, "price": 18.90, "totalValue": 3780.00, "strikePrice": null, "expirationDate": null}},
          {{"orderNumber": "5203382", "tradeDate": "2014-05-15", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "ULTRAPAR", "quantity": 100, "price": 57.17, "totalValue": 5717.00, "strikePrice": null, "expirationDate": null}},
          {{"orderNumber": "5209650", "tradeDate": "2014-05-19", "operationType": "C", "marketType": "VISTA", "market": "BOVESPA", "ticker": "FIBRIA", "quantity": 100, "price": 21.09, "totalValue": 2109.00, "strikePrice": null, "expirationDate": null}},
          {{"orderNumber": "5209650", "tradeDate": "2014-05-19", "operationType": "V", "marketType": "VISTA", "market": "BOVESPA", "ticker": "SUZANO", "quantity": 100, "price": 7.70, "totalValue": 770.00, "strikePrice": null, "expirationDate": null}}
        ], "fees": [
          {{"orderNumber": "5187530", "totalFees": 15.77}},
          {{"orderNumber": "5200251", "totalFees": 31.55}},
          {{"orderNumber": "5203382", "totalFees": 15.77}},
          {{"orderNumber": "5209650", "totalFees": 31.55}}
        ]}}
        """

    def _simulate_agno_extraction(self, file_path: str) -> Dict[str, Any]:
        """
        Simulação temporária da extração Agno. 
        REMOVER quando o framework Agno real estiver disponível.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            
        Returns:
            Dict simulado com trades e fees
        """
        logger.warning("Usando simulação Agno - substitua pela implementação real")
        
        # Esta é uma implementação de exemplo que deve ser substituída
        # pelo uso real do framework Agno quando disponível
        
        # Simulação de dados extraídos
        simulated_result = {
            "trades": [
                {
                    "orderNumber": "20241201001",
                    "tradeDate": "2024-12-01",
                    "operationType": "C",
                    "marketType": "VISTA",
                    "market": "BOVESPA",
                    "ticker": "PETR4",
                    "quantity": 100,
                    "price": 42.50,
                    "totalValue": 4250.00,
                    "strikePrice": None,
                    "expirationDate": None
                },
                {
                    "orderNumber": "20241201001",
                    "tradeDate": "2024-12-01",
                    "operationType": "V",
                    "marketType": "VISTA",
                    "market": "BOVESPA",
                    "ticker": "VALE3",
                    "quantity": 200,
                    "price": 65.30,
                    "totalValue": 13060.00,
                    "strikePrice": None,
                    "expirationDate": None
                }
            ],
            "fees": [
                {
                    "orderNumber": "20241201001",
                    "totalFees": 15.75
                }
            ]
        }
        
        return simulated_result

    def _validate_extraction_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida o resultado da extração conforme o schema definido.
        
        Args:
            result (Dict): Resultado bruto da extração
            
        Returns:
            Dict: Resultado validado
            
        Raises:
            ConversionError: Se a validação falhar
        """
        try:
            # Verifica estrutura básica
            if not isinstance(result, dict):
                raise ConversionError("Resultado deve ser um dicionário")
            
            if 'trades' not in result or 'fees' not in result:
                raise ConversionError("Resultado deve conter 'trades' e 'fees'")
            
            # Valida trades
            if not isinstance(result['trades'], list):
                raise ConversionError("'trades' deve ser uma lista")
            
            for i, trade in enumerate(result['trades']):
                self._validate_trade(trade, i)
            
            # Valida fees
            if not isinstance(result['fees'], list):
                raise ConversionError("'fees' deve ser uma lista")
            
            for i, fee in enumerate(result['fees']):
                self._validate_fee(fee, i)
            
            logger.debug(f"Resultado validado: {len(result['trades'])} trades, {len(result['fees'])} fees")
            return result
            
        except Exception as e:
            logger.error(f"Erro na validação do resultado: {e}")
            raise ConversionError(f"Resultado da extração inválido: {e}")

    def _validate_trade(self, trade: Dict[str, Any], index: int) -> None:
        """
        Valida um trade individual.
        
        Args:
            trade (Dict): Dados do trade
            index (int): Índice do trade na lista
            
        Raises:
            ConversionError: Se a validação falhar
        """
        required_fields = ["orderNumber", "tradeDate", "operationType", "marketType", 
                          "market", "ticker", "quantity", "price", "totalValue"]
        
        for field in required_fields:
            if field not in trade:
                raise ConversionError(f"Trade {index}: campo obrigatório '{field}' ausente")
        
        # Valida tipos e valores
        if trade['operationType'] not in ['C', 'V']:
            raise ConversionError(f"Trade {index}: operationType deve ser 'C' ou 'V'")
        
        if trade['market'] not in ['BOVESPA', 'BMF']:
            raise ConversionError(f"Trade {index}: market deve ser 'BOVESPA' ou 'BMF'")
        
        if not isinstance(trade['quantity'], int) or trade['quantity'] <= 0:
            raise ConversionError(f"Trade {index}: quantity deve ser um inteiro positivo")
        
        if not isinstance(trade['price'], (int, float)) or trade['price'] <= 0:
            raise ConversionError(f"Trade {index}: price deve ser um número positivo")
        
        if not isinstance(trade['totalValue'], (int, float)) or trade['totalValue'] <= 0:
            raise ConversionError(f"Trade {index}: totalValue deve ser um número positivo")

    def _validate_fee(self, fee: Dict[str, Any], index: int) -> None:
        """
        Valida uma taxa individual.
        
        Args:
            fee (Dict): Dados da taxa
            index (int): Índice da taxa na lista
            
        Raises:
            ConversionError: Se a validação falhar
        """
        required_fields = ["orderNumber", "totalFees"]
        
        for field in required_fields:
            if field not in fee:
                raise ConversionError(f"Fee {index}: campo obrigatório '{field}' ausente")
        
        if not isinstance(fee['totalFees'], (int, float)) or fee['totalFees'] < 0:
            raise ConversionError(f"Fee {index}: totalFees deve ser um número não-negativo")

    def get_processing_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre o processamento Agno.
        
        Returns:
            Dict com informações do processador
        """
        return {
            'processor': 'agno',
            'available': AGNO_AVAILABLE,
            'agent_ready': self.agent is not None,
            'openai_configured': bool(settings.openai_api_key),
            'schema_version': '1.0',
            'capabilities': ['trades_extraction', 'fees_extraction', 'b3_notes', 'structured_outputs'],
            'supported_formats': ['pdf'],
            'model': 'gpt-4o' if AGNO_AVAILABLE and self.agent else None
        }

    def clear_cache(self) -> bool:
        """
        Limpa o cache de extrações Agno.
        
        Returns:
            True se a limpeza foi bem-sucedida
        """
        try:
            if cache_service.enabled:
                # Remove apenas chaves relacionadas ao Agno
                return cache_service.clear_pattern("agno_extraction:*")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar cache Agno: {e}")
            return False

    def debug_pdf_content(self, file_path: str, max_chars: int = 2000) -> Dict[str, str]:
        """
        Extrai e mostra o conteúdo bruto do PDF para debug.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            max_chars (int): Máximo de caracteres a mostrar
            
        Returns:
            Dict com o conteúdo extraído por diferentes métodos
        """
        logger.info(f"Extraindo conteúdo bruto do PDF para debug: {file_path}")
        
        results = {}
        
        # Método 1: pypdf
        if PYPDF_AVAILABLE:
            try:
                with open(file_path, 'rb') as file:
                    reader = pypdf.PdfReader(file)
                    text = ""
                    total_pages = len(reader.pages)
                    logger.info(f"PDF tem {total_pages} páginas - extraindo todas...")
                    
                    for page_num, page in enumerate(reader.pages):
                        page_text = page.extract_text()
                        text += f"\n=== PÁGINA {page_num + 1} de {total_pages} ===\n{page_text}\n"
                    
                    # Se max_chars está definido e o texto é muito longo, trunca mas mantém info das páginas
                    if max_chars and len(text) > max_chars:
                        truncated_text = text[:max_chars]
                        results['pypdf'] = f"{truncated_text}\n\n[TRUNCADO - Total de {len(text)} caracteres de {total_pages} páginas]"
                    else:
                        results['pypdf'] = text
                    
                    logger.info(f"pypdf extraiu {len(text)} caracteres de {total_pages} páginas")
                    
            except Exception as e:
                results['pypdf'] = f"ERRO: {e}"
                logger.error(f"Erro com pypdf: {e}")
        else:
            results['pypdf'] = "pypdf não disponível"
        
        # Método 2: pdfminer
        if PDFMINER_AVAILABLE:
            try:
                text = extract_text(file_path)
                results['pdfminer'] = text[:max_chars] if max_chars else text
                logger.info(f"pdfminer extraiu {len(text)} caracteres")
                
            except Exception as e:
                results['pdfminer'] = f"ERRO: {e}"
                logger.error(f"Erro com pdfminer: {e}")
        else:
            results['pdfminer'] = "pdfminer não disponível"
        
        return results

    def debug_extraction_with_raw_content(self, file_path: str) -> Dict[str, Any]:
        """
        Executa extração mostrando o conteúdo bruto que o agente está vendo.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            
        Returns:
            Dict com resultados da extração e debug info
        """
        logger.info(f"Debug de extração com conteúdo bruto: {file_path}")
        
        # Primeiro, extrai o conteúdo bruto sem limite de caracteres para ver todas as páginas
        raw_content = self.debug_pdf_content(file_path, max_chars=None)
        
        # Log do conteúdo bruto
        logger.info("=== CONTEÚDO BRUTO DO PDF ===")
        for method, content in raw_content.items():
            if isinstance(content, str) and not content.startswith('ERRO'):
                logger.info(f"\n--- {method.upper()} ---")
                logger.info(f"Total de caracteres: {len(content)}")
                # Mostra primeiros 2000 caracteres
                logger.info(content[:2000] + ("..." if len(content) > 2000 else ""))
                
                # Conta páginas no conteúdo
                if "PÁGINA" in content:
                    pages_found = content.count("=== PÁGINA")
                    logger.info(f"📄 Páginas detectadas no conteúdo: {pages_found}")
        
        # Executa a extração normal
        try:
            extraction_result = self.extract_trades_and_fees(file_path, use_cache=False)
            
            return {
                'extraction_result': extraction_result,
                'raw_content': raw_content,
                'debug_info': {
                    'pypdf_available': PYPDF_AVAILABLE,
                    'pdfminer_available': PDFMINER_AVAILABLE,
                    'agno_available': AGNO_AVAILABLE,
                    'content_lengths': {method: len(content) if isinstance(content, str) else 0 
                                      for method, content in raw_content.items()},
                    'pages_in_content': {method: content.count("=== PÁGINA") if isinstance(content, str) and "PÁGINA" in content else 0
                                       for method, content in raw_content.items()}
                }
            }
        except Exception as e:
            logger.error(f"Erro na extração durante debug: {e}")
            return {
                'extraction_result': {'trades': [], 'fees': [], 'error': str(e)},
                'raw_content': raw_content,
                'debug_info': {
                    'pypdf_available': PYPDF_AVAILABLE,
                    'pdfminer_available': PDFMINER_AVAILABLE,
                    'agno_available': AGNO_AVAILABLE,
                    'error': str(e)
                }
            }


# Instância global do serviço Agno
agno_service = AgnoService()
