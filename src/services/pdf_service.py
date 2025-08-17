"""
Serviço para validação e conversão de arquivos PDF para Markdown.
"""
import os
import logging
import torch
import re
import json
import csv
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.document import DoclingDocument

from src.config.settings import settings
from src.services.cache_service import cache_service
from src.utils.exceptions import ConversionError, ValidationError
from src.utils.helpers import calculate_file_hash

logger = logging.getLogger(__name__)


class PDFService:
    """
    Serviço para validar e converter PDFs para Markdown com extração avançada de tabelas.
    """

    def __init__(self):
        """
        Inicializa o conversor de documentos docling com configurações otimizadas para tabelas.
        """
        logger.info("Inicializando PDFService com capacidades avançadas de tabela")
        
        # Configura o dispositivo (GPU se disponível e habilitado, CPU caso contrário)
        if settings.gpu_enabled and torch.cuda.is_available():
            self.device = torch.device('cuda')
            logger.info("GPU disponível e habilitada")
        else:
            self.device = torch.device('cpu')
            logger.info("Usando CPU para processamento")
        
        logger.info(f"Dispositivo configurado: {self.device}")
        
        # Configurações avançadas para melhor extração de tabelas
        self._setup_advanced_converter()

    def _setup_advanced_converter(self):
        """
        Configura o conversor com pipeline otimizado para tabelas.
        """
        try:
            # Configurações do pipeline PDF otimizadas para tabelas
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_table_structure = True  # Ativa análise estrutural de tabelas
            pipeline_options.do_ocr = True  # OCR para tabelas em imagens/scans
            pipeline_options.ocr_options.force_full_page_ocr = False  # OCR inteligente
            
            # Configurações específicas do formato PDF
            pdf_options = PdfFormatOption(
                pipeline_options=pipeline_options
            )
            
            # Inicializa o conversor com as configurações
            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: pdf_options
                }
            )
            
            logger.info("DocumentConverter inicializado com pipeline avançado para tabelas")
            
            # Move o modelo para o dispositivo apropriado se possível
            if hasattr(self.converter, 'model') and hasattr(self.converter.model, 'to'):
                self.converter.model.to(self.device)
                logger.info(f"Modelo movido para {self.device}")
                
        except Exception as e:
            logger.error(f"Erro ao inicializar DocumentConverter: {e}")
            raise ConversionError(f"Falha na inicialização do conversor: {e}")

    def validate_pdf(self, file_path: str) -> bool:
        """
        Verifica se o arquivo existe e é um PDF válido.

        Args:
            file_path (str): Caminho do arquivo a ser validado.

        Returns:
            bool: True se o arquivo existir e for um PDF válido, False caso contrário.
            
        Raises:
            ValidationError: Se a validação falhar
        """
        logger.debug(f"Validando arquivo PDF: {file_path}")
        
        try:
            # Verifica se o arquivo existe
            if not os.path.isfile(file_path):
                raise ValidationError(f"O arquivo não existe: {file_path}")
            
            # Verifica se o arquivo tem extensão .pdf
            if not file_path.lower().endswith('.pdf'):
                raise ValidationError(f"O arquivo não tem extensão .pdf: {file_path}")
            
            # Verifica tamanho do arquivo
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise ValidationError("O arquivo está vazio")
            
            if file_size > settings.max_content_length:
                raise ValidationError(
                    f"Arquivo muito grande: {file_size} bytes. "
                    f"Máximo permitido: {settings.max_content_length} bytes"
                )
            
            # Verifica cabeçalho PDF
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    raise ValidationError(
                        f"O arquivo não tem o cabeçalho de PDF válido. "
                        f"Cabeçalho encontrado: {header}"
                    )
            
            logger.debug(f"Arquivo validado com sucesso: {file_path}")
            return True
            
        except ValidationError:
            logger.error(f"Validação falhou para: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado durante validação: {e}")
            raise ValidationError(f"Erro durante validação: {e}")

    def _split_by_nota_negociacao(self, markdown: str) -> List[Tuple[int, str]]:
        """
        Divide o markdown em seções baseado no marcador "NOTA DE NEGOCIAÇÃO".
        
        Args:
            markdown (str): Conteúdo completo em markdown
            
        Returns:
            List[Tuple[int, str]]: Lista de tuplas (número da página, conteúdo)
        """
        logger.debug("Dividindo markdown por 'NOTA DE NEGOCIAÇÃO'")
        
        # Encontra todas as ocorrências de "NOTA DE NEGOCIAÇÃO"
        matches = list(re.finditer(r'NOTA DE NEGOCIAÇÃO', markdown, re.IGNORECASE))
        
        if not matches:
            logger.warning("Nenhuma ocorrência de 'NOTA DE NEGOCIAÇÃO' encontrada")
            return [(1, markdown)]
            
        pages = []
        for i, match in enumerate(matches):
            start_pos = match.start()
            
            # Se for a última ocorrência, vai até o final do texto
            if i == len(matches) - 1:
                content = markdown[start_pos:]
            else:
                # Caso contrário, vai até o início da próxima ocorrência
                end_pos = matches[i + 1].start()
                content = markdown[start_pos:end_pos]
            
            pages.append((i + 1, content.strip()))
        
        logger.debug(f"Markdown dividido em {len(pages)} seções")
        return pages

    def convert_pdf_to_markdown(self, file_path: str, use_cache: bool = True) -> Dict[str, str]:
        """
        Converte um arquivo PDF para Markdown, separando por ocorrências de "NOTA DE NEGOCIAÇÃO".

        Args:
            file_path (str): Caminho do arquivo PDF a ser convertido.
            use_cache (bool): Se deve usar cache para resultados

        Returns:
            dict: Dicionário com o conteúdo de cada nota em formato Markdown.
                 Chaves são números (1-indexed) e valores são strings markdown.

        Raises:
            ValidationError: Se o arquivo não for válido
            ConversionError: Se ocorrer erro durante a conversão
        """
        logger.info(f"Iniciando conversão do PDF para Markdown: {file_path}")
        
        try:
            # Valida o arquivo
            self.validate_pdf(file_path)
            
            # Verifica cache se habilitado
            cache_key = None
            if use_cache and cache_service.enabled:
                try:
                    file_hash = calculate_file_hash(file_path)
                    cache_key = f"pdf_conversion:{file_hash}"
                    
                    cached_result = cache_service.get(cache_key)
                    if cached_result:
                        logger.info(f"Resultado encontrado no cache: {file_path}")
                        return cached_result
                except Exception as e:
                    logger.warning(f"Erro ao acessar cache: {e}")
            
            # Executa a conversão
            logger.info(f"Executando conversão com docling: {file_path}")
            result = self.converter.convert(file_path)
            
            # Verifica se o resultado da conversão é válido
            if not result or not hasattr(result, 'document'):
                raise ConversionError("Resultado da conversão inválido ou vazio")
            
            # Converte o documento inteiro para markdown
            markdown = result.document.export_to_markdown()
            
            if not markdown or not markdown.strip():
                raise ConversionError("Conteúdo markdown vazio após conversão")
            
            # Divide o markdown em páginas baseado no marcador
            pages = self._split_by_nota_negociacao(markdown)
            logger.info(f"Documento dividido em {len(pages)} notas de negociação")
            
            # Converte a lista de tuplas em um dicionário
            pages_markdown = {str(page_num): content for page_num, content in pages}
            
            # Armazena no cache se habilitado
            if use_cache and cache_service.enabled and cache_key:
                try:
                    cache_service.set(cache_key, pages_markdown)
                    logger.debug(f"Resultado armazenado no cache: {cache_key}")
                except Exception as e:
                    logger.warning(f"Erro ao armazenar no cache: {e}")
            
            logger.info(f"Conversão concluída com sucesso para: {file_path}")
            return pages_markdown
            
        except (ValidationError, ConversionError):
            raise
        except Exception as e:
            logger.error(f"Erro inesperado durante a conversão: {e}")
            raise ConversionError(f"Erro inesperado ao converter PDF: {e}")
    
    def get_device_info(self) -> Dict[str, any]:
        """
        Retorna informações sobre o dispositivo de processamento.
        
        Returns:
            Dict com informações do dispositivo
        """
        device_info = {
            'device': str(self.device),
            'gpu_available': torch.cuda.is_available(),
            'gpu_enabled': settings.gpu_enabled
        }
        
        if torch.cuda.is_available():
            device_info.update({
                'gpu_count': torch.cuda.device_count(),
                'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None,
                'gpu_memory_total': torch.cuda.get_device_properties(0).total_memory if torch.cuda.device_count() > 0 else None
            })
        
        return device_info
    
    def clear_cache(self) -> bool:
        """
        Limpa o cache de conversões.
        
        Returns:
            True se limpeza foi bem-sucedida
        """
        try:
            if cache_service.enabled:
                # Remove apenas chaves relacionadas a conversões PDF
                # Implementação simplificada - em produção seria mais específica
                return cache_service.clear_all()
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar cache: {e}")
            return False

<<<<<<< HEAD
    def convert_pdf_adaptive(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Converte PDF usando o processador configurado (Docling ou Agno).
        
        Args:
            file_path (str): Caminho do arquivo PDF
            use_cache (bool): Se deve usar cache
            
        Returns:
            Dict com resultado da conversão no formato apropriado
            
        Raises:
            ValidationError: Se o arquivo não for válido
            ConversionError: Se houver erro na conversão
        """
        logger.info(f"Conversão adaptativa iniciada com processador: {settings.pdf_processor}")
        
        try:
            if settings.pdf_processor.lower() == "agno":
                return self._convert_with_agno(file_path, use_cache)
            else:
                return self._convert_with_docling(file_path, use_cache)
                
        except Exception as e:
            logger.error(f"Erro na conversão adaptativa: {e}")
            raise ConversionError(f"Falha na conversão: {e}")

    def _convert_with_agno(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Converte PDF usando o serviço Agno para extrair trades e fees.
        
        Args:
            file_path (str): Caminho do arquivo PDF
            use_cache (bool): Se deve usar cache
            
        Returns:
            Dict com trades e fees extraídos
        """
        if not AGNO_SERVICE_AVAILABLE or agno_service is None:
            raise ConversionError("Serviço Agno não disponível")
        
        logger.info(f"Convertendo com Agno: {file_path}")
        
        # Extrai trades e fees usando Agno
        agno_result = agno_service.extract_trades_and_fees(file_path, use_cache)
        
        # Formata resultado para compatibilidade com a API
        result = {
            'processor': 'agno',
            'format': 'json',
            'data': agno_result,
            'summary': {
                'total_trades': len(agno_result.get('trades', [])),
                'total_fees': len(agno_result.get('fees', [])),
                'processing_info': agno_service.get_processing_info()
            }
        }
        
        logger.info(f"Conversão Agno concluída: {result['summary']['total_trades']} trades")
        return result

    def _convert_with_docling(self, file_path: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Converte PDF usando o serviço Docling (comportamento original).
        
        Args:
            file_path (str): Caminho do arquivo PDF
            use_cache (bool): Se deve usar cache
            
        Returns:
            Dict com páginas em markdown
        """
        logger.info(f"Convertendo com Docling: {file_path}")
        
        # Usa o método original do Docling
        markdown_pages = self.convert_pdf_to_markdown(file_path, use_cache)
        
        # Formata resultado para compatibilidade com a API
        result = {
            'processor': 'docling',
            'format': 'markdown',
            'data': markdown_pages,
            'summary': {
                'total_pages': len(markdown_pages),
                'processing_info': self.get_device_info()
            }
        }
        
        logger.info(f"Conversão Docling concluída: {result['summary']['total_pages']} páginas")
        return result

=======
>>>>>>> d47322e2667970c136108a363baaeee69323e063
    def extract_tables_advanced(self, file_path: str, export_format: str = "json") -> Dict[str, Any]:
        """
        Extrai tabelas de forma avançada usando as capacidades completas do Docling.

        Args:
            file_path (str): Caminho do arquivo PDF.
            export_format (str): Formato de export ('json', 'csv', 'excel', 'html').

        Returns:
            Dict com tabelas extraídas e metadados.
        """
        logger.info(f"Iniciando extração avançada de tabelas: {file_path}")
        
        try:
            # Valida o arquivo
            self.validate_pdf(file_path)
            
            # Executa a conversão com foco em tabelas
            result = self.converter.convert(file_path)
            
            if not result or not hasattr(result, 'document'):
                raise ConversionError("Resultado da conversão inválido")
            
            document: DoclingDocument = result.document
            
            # Extrai tabelas com metadados completos
            tables_data = self._extract_tables_from_document(document)
            
            # Processa e exporta conforme formato solicitado
            processed_tables = self._process_tables_for_export(tables_data, export_format)
            
            # Prepara resposta estruturada
            response = {
                'tables': processed_tables,
                'metadata': {
                    'total_tables': len(tables_data),
                    'export_format': export_format,
                    'processing_info': {
                        'device': str(self.device),
                        'pipeline_used': 'advanced_table_extraction'
                    }
                }
            }
            
            logger.info(f"Extração de tabelas concluída: {len(tables_data)} tabelas encontradas")
            return response
            
        except (ValidationError, ConversionError):
            raise
        except Exception as e:
            logger.error(f"Erro durante extração de tabelas: {e}")
            raise ConversionError(f"Erro ao extrair tabelas: {e}")

    def _extract_tables_from_document(self, document: DoclingDocument) -> List[Dict[str, Any]]:
        """
        Extrai tabelas do documento com metadados detalhados.
        
        Args:
            document: Documento Docling processado.
            
        Returns:
            Lista de tabelas com metadados.
        """
        tables_data = []
        
        # Itera através dos elementos do documento
        for element in document.iterate_elements():
            if element.label == "table":
                table_info = {
                    'id': len(tables_data) + 1,
                    'page': getattr(element, 'page', 1),
                    'bbox': getattr(element, 'bbox', None),
                    'data': None,
                    'structure': None,
                    'text_content': element.text if hasattr(element, 'text') else "",
                    'confidence': getattr(element, 'confidence', None)
                }
                
                # Tenta extrair estrutura da tabela se disponível
                if hasattr(element, 'data') and element.data:
                    table_info['structure'] = element.data
                    
                    # Converte para estrutura tabular
                    if isinstance(element.data, dict) and 'table' in element.data:
                        table_data = self._parse_table_structure(element.data['table'])
                        table_info['data'] = table_data
                
                # Se não há estrutura, tenta extrair do texto
                if not table_info['data'] and table_info['text_content']:
                    table_info['data'] = self._parse_table_from_text(table_info['text_content'])
                
                tables_data.append(table_info)
                logger.debug(f"Tabela extraída - ID: {table_info['id']}, Página: {table_info['page']}")
        
        return tables_data

    def _parse_table_structure(self, table_structure: Any) -> List[List[str]]:
        """
        Converte estrutura de tabela do Docling para formato de lista.
        
        Args:
            table_structure: Estrutura da tabela do Docling.
            
        Returns:
            Lista de listas representando a tabela.
        """
        try:
            if isinstance(table_structure, list):
                # Já está em formato de lista
                return table_structure
            
            if hasattr(table_structure, 'rows'):
                # Estrutura com atributo rows
                return [[cell.text if hasattr(cell, 'text') else str(cell) 
                        for cell in row.cells if hasattr(row, 'cells')] 
                       for row in table_structure.rows]
            
            if isinstance(table_structure, dict) and 'data' in table_structure:
                # Estrutura em dicionário
                return table_structure['data']
            
            logger.warning("Estrutura de tabela não reconhecida")
            return []
            
        except Exception as e:
            logger.warning(f"Erro ao analisar estrutura da tabela: {e}")
            return []

    def _parse_table_from_text(self, text_content: str) -> List[List[str]]:
        """
        Extrai tabela do conteúdo de texto usando heurísticas.
        
        Args:
            text_content: Texto da tabela.
            
        Returns:
            Lista de listas representando a tabela.
        """
        try:
            lines = text_content.strip().split('\n')
            table_data = []
            
            for line in lines:
                if line.strip():
                    # Tenta diferentes separadores
                    if '\t' in line:
                        cells = line.split('\t')
                    elif '|' in line:
                        cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                    else:
                        # Usa espaçamento múltiplo como separador
                        cells = re.split(r'\s{2,}', line.strip())
                    
                    if cells:
                        table_data.append([cell.strip() for cell in cells])
            
            return table_data
            
        except Exception as e:
            logger.warning(f"Erro ao extrair tabela do texto: {e}")
            return []

    def _process_tables_for_export(self, tables_data: List[Dict[str, Any]], 
                                  export_format: str) -> List[Dict[str, Any]]:
        """
        Processa tabelas para o formato de export especificado.
        
        Args:
            tables_data: Lista de tabelas extraídas.
            export_format: Formato desejado.
            
        Returns:
            Lista de tabelas processadas.
        """
        processed_tables = []
        
        for table_info in tables_data:
            if not table_info['data']:
                continue
                
            processed_table = {
                'id': table_info['id'],
                'page': table_info['page'],
                'metadata': {
                    'bbox': table_info['bbox'],
                    'confidence': table_info['confidence'],
                    'rows': len(table_info['data']) if table_info['data'] else 0,
                    'cols': len(table_info['data'][0]) if table_info['data'] and table_info['data'][0] else 0
                }
            }
            
            # Processa conforme formato
            if export_format == "json":
                processed_table['data'] = table_info['data']
                processed_table['format'] = 'json'
                
            elif export_format == "csv":
                csv_content = self._convert_table_to_csv(table_info['data'])
                processed_table['data'] = csv_content
                processed_table['format'] = 'csv'
                
            elif export_format == "excel":
                excel_data = self._convert_table_to_excel_format(table_info['data'])
                processed_table['data'] = excel_data
                processed_table['format'] = 'excel'
                
            elif export_format == "html":
                html_content = self._convert_table_to_html(table_info['data'])
                processed_table['data'] = html_content
                processed_table['format'] = 'html'
                
            else:
                # Formato padrão (JSON)
                processed_table['data'] = table_info['data']
                processed_table['format'] = 'json'
            
            processed_tables.append(processed_table)
        
        return processed_tables

    def _convert_table_to_csv(self, table_data: List[List[str]]) -> str:
        """Converte tabela para formato CSV."""
        try:
            import io
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerows(table_data)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Erro ao converter para CSV: {e}")
            return ""

    def _convert_table_to_excel_format(self, table_data: List[List[str]]) -> Dict[str, Any]:
        """Converte tabela para formato compatível com Excel."""
        try:
            if not table_data:
                return {'headers': [], 'rows': []}
                
            headers = table_data[0] if table_data else []
            rows = table_data[1:] if len(table_data) > 1 else []
            
            return {
                'headers': headers,
                'rows': rows,
                'dataframe_compatible': True
            }
        except Exception as e:
            logger.error(f"Erro ao converter para formato Excel: {e}")
            return {'headers': [], 'rows': []}

    def _convert_table_to_html(self, table_data: List[List[str]]) -> str:
        """Converte tabela para formato HTML."""
        try:
            if not table_data:
                return "<table></table>"
                
            html = ["<table border='1'>"]
            
            # Cabeçalho
            if table_data:
                html.append("<thead><tr>")
                for cell in table_data[0]:
                    html.append(f"<th>{self._escape_html(cell)}</th>")
                html.append("</tr></thead>")
            
            # Linhas de dados
            if len(table_data) > 1:
                html.append("<tbody>")
                for row in table_data[1:]:
                    html.append("<tr>")
                    for cell in row:
                        html.append(f"<td>{self._escape_html(cell)}</td>")
                    html.append("</tr>")
                html.append("</tbody>")
            
            html.append("</table>")
            return "".join(html)
            
        except Exception as e:
            logger.error(f"Erro ao converter para HTML: {e}")
            return "<table></table>"

    def _escape_html(self, text: str) -> str:
        """Escapa caracteres HTML."""
        return (str(text)
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))

    def save_tables_to_files(self, tables_result: Dict[str, Any], 
                           output_dir: str = "tables_output") -> Dict[str, List[str]]:
        """
        Salva tabelas em arquivos nos formatos especificados.
        
        Args:
            tables_result: Resultado da extração de tabelas.
            output_dir: Diretório de saída.
            
        Returns:
            Dict com caminhos dos arquivos criados por formato.
        """
        try:
            # Cria diretório se não existir
            Path(output_dir).mkdir(exist_ok=True)
            
            saved_files = {
                'csv': [],
                'excel': [],
                'json': [],
                'html': []
            }
            
            tables = tables_result.get('tables', [])
            
            for table in tables:
                table_id = table['id']
                table_format = table['format']
                
                if table_format == 'csv':
                    filename = f"{output_dir}/table_{table_id}.csv"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(table['data'])
                    saved_files['csv'].append(filename)
                    
                elif table_format == 'excel':
                    filename = f"{output_dir}/table_{table_id}.xlsx"
                    try:
                        df = pd.DataFrame(table['data']['rows'], 
                                        columns=table['data']['headers'])
                        df.to_excel(filename, index=False)
                        saved_files['excel'].append(filename)
                    except Exception as e:
                        logger.warning(f"Erro ao salvar Excel para tabela {table_id}: {e}")
                        
                elif table_format == 'html':
                    filename = f"{output_dir}/table_{table_id}.html"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(table['data'])
                    saved_files['html'].append(filename)
                    
                elif table_format == 'json':
                    filename = f"{output_dir}/table_{table_id}.json"
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(table['data'], f, ensure_ascii=False, indent=2)
                    saved_files['json'].append(filename)
            
            logger.info(f"Tabelas salvas em: {output_dir}")
            return saved_files
            
        except Exception as e:
            logger.error(f"Erro ao salvar tabelas: {e}")
            return {'csv': [], 'excel': [], 'json': [], 'html': []}


# Instância global do serviço PDF
<<<<<<< HEAD
pdf_service = PDFService()

# Import do serviço Agno (será usado para alternar entre processadores)
try:
    from src.services.agno_service import agno_service
    AGNO_SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Serviço Agno não disponível: {e}")
    agno_service = None
    AGNO_SERVICE_AVAILABLE = False 
=======
pdf_service = PDFService() 
>>>>>>> d47322e2667970c136108a363baaeee69323e063
