# Arquitetura e Documentação do Projeto — Monitoramento Geopolítico

O Monitoramento Geopolítico é um Data Lakehouse automatizado que extrai, limpa e analisa transcrições de canais jornalísticos de grande circulação no YouTube (como a CNN Brasil). O sistema monitora o impacto de crises internacionais nas narrativas midiáticas para apoiar analistas de risco e gestores corporativos na tomada de decisões em menos de 24 horas.

---

## 1. Identidade do Projeto

*   **Tema / Domínio**: Geopolítica & Notícias (Tema #3)
*   **Equipe**: 
    *   Alan Alvarado (alan.alvarado@edu.unifor.br)
    *   Henrique Silva Oliveira (henrique.oliveira@edu.unifor.br)
*   **Data de Início**: 26/06/2026

---

## 2. Escopo de Negócio e Objetivos

### O Problema
O monitoramento manual de notícias em vídeo gera gargalos severos de tempo, omissão de dados críticos e planilhas estáticas desatualizadas para quem precisa antecipar impactos em cadeias de suprimentos e investimentos.

### Propósito e Hipótese de Valor
Automatizar a extração contínua de transcrições de notícias (nos idiomas pt e pt-BR), cruzando menções geográficas com termos de ação (guerra, sancao, conflito, embargo, tropas, fronteira, acordo). O monitoramento contínuo do Share of Voice e do contexto semântico permite reavaliar a exposição a riscos em mercados internacionais com agilidade.

### Perguntas Analíticas Respondidas
1. Qual país detém a maior parcela de tempo de exposição (Share of Voice) nas discussões atuais?
2. Quais blocos geopolíticos (OTAN, BRICS+, Oriente Médio) concentram as maiores menções?
3. Qual é o contexto geopolitico associado a cada país? (Ex: A Rússia está mais associada a qual país?)

### Fora de Escopo
*   Análise de sentimento refinada via NLP/LLM complexo.
*   Tradução de múltiplos idiomas estrangeiros (foco exclusivo em português).
*   Monitoramento de canais de opinião pessoal não-jornalísticos.

---

## 3. Arquitetura de Dados (Medallion e Lakehouse)

O pipeline opera em ciclos de ingestão a cada 12 horas, persistindo os dados no formato binário otimizado Parquet.

[YouTube API] ──> (Bronze) ──> [Pandera/Limpeza] ──> (Silver) ──> [DuckDB] ──> (Gold) ──> [Streamlit]│└──> [_quarentena/]

### Camada Bronze (Bruto)
*   **Papel**: Captura das transcrições brutas geradas pela biblioteca `youtube-transcript-api` (versão estável 1.2.4) em formato JSON.
*   **Contingência**: Se houver bloqueio de IP (HTTP 429) ou ausência de legendas, o pipeline aplica a lógica "8 ou 80". Se ao menos 1 vídeo válido for processado, o pipeline segue. Caso zero vídeos funcionem, aciona um Fallback de Dados Sintéticos Determinísticos baseado em sementes de hash fixas para manter a integridade operacional.

### Camada Silver (Limpeza e Qualidade)
*   **Contrato de Dados**: Validação estrita de tipos (str, int, float), não-nulidade e valores válidos (ex: durações maiores que zero) utilizando a biblioteca Pandera.
*   **Sanitização**: Conversão para minúsculas, remoção segura de pontuação e eliminação de acentos com a biblioteca unicodedata, além de aplicação de stopwords customizadas.
*   **Quarentena**: Textos vazios ou com contagem inválida (n_palavras < 1) são desviados silenciosamente para `./datalake/silver/_quarentena/descartes.parquet`.

### Camada Gold (Agregação de Negócio)
*   **Motor Computacional**: DuckDB executando queries diretamente sobre os arquivos Parquet em memória.
*   **Visões Analíticas**:
    *   *Contexto Semântico*: Matriz de coocorrência frase a frase entre nações citadas e vocabulários de ação.
    *   *Blocos Geopolíticos*: Agrupamento automatizado em alianças estratégicas (OTAN, BRICS+, Oriente Médio).

---

## 4. Princípios de Engenharia Aplicados

*   **Idempotência**: Gerenciada via banco de controle SQLite (`datalake/control/ingestion.db`). Registra watermarks dos metadados processados. Se reexecutado para o mesmo lote, o ingestor pula o registro, evitando duplicidade nas camadas silver e Gold.
*   **Tratamento de Erros**: Blocos estruturados de try/except isolam falhas de rede e erros nativos como `NoTranscriptFound`. A falha de uma única fonte nunca derruba o pipeline.
*   **Rastreabilidade e Observabilidade**: Quantificação em tempo real de linhas lidas, descartes e registros promovidos. Logs rotativos em produção acompanham o comportamento do ingestor e do agendador (`scheduler.py`).

---

## 5. Runbook e Operação (VPS Linux)

### Requisitos e Deploy
O pipeline roda de forma totalmente agendada em uma VPS Linux, com uma interface visual em Streamlit exposta em URL pública. O monitoramento do agendador (`scheduler.py`) e dos serviços é gerenciado via systemd.

### Como Monitorar os Logs em Tempo Real
Para inspecionar o comportamento da ingestão e do agendador sem interromper o serviço, execute no terminal da VPS:

```bash
tail -f /scheduler.log
```

### Critérios de Sucesso (Definition of Done)
*   Pipeline operando de forma 100% agendada na VPS.
*   Dados validados e persistidos corretamente em formato Parquet nas camadas Bronze, Silver e Gold.
*   Dashboard Streamlit de análise e observabilidade operando por 7 dias contínuos sem quebras manuais.
