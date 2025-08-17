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
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Executando extração com agente Agno (tentativa {attempt + 1}/{max_retries}): {file_path}")
                
                # Cria prompt mais direto baseado na tentativa
                if attempt == 0:
                    prompt = self._create_json_extraction_prompt(file_path)
                elif attempt == 1:
                    prompt = self._create_simple_extraction_prompt(file_path)
                else:
                    prompt = self._create_fallback_extraction_prompt(file_path)
                
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
                
                logger.debug(f"Resposta bruta do Agno (tentativa {attempt + 1}): {content[:500]}...")
                
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
