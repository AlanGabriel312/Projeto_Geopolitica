# Arquitetura do Projeto — Monitoramento Geopolítico

Este documento descreve o fluxo de dados, a modelagem multicamadas (Lakehouse) e os mecanismos de controle implementados para garantir a estabilidade do pipeline em ambiente produtivo.

## 1. Fluxo de Dados (Medallion Architecture)

O ciclo de vida do dado respeita as três divisões lógicas do Data Lakehouse, persistindo dados em formato binário otimizado (Parquet):

### Camada Bronze (Bruto)
*   **Papel**: Captura das transcrições brutas geradas pela biblioteca `youtube-transcript-api` (versão estável `1.2.4`) em formato JSON/Dicionário.
*   **Resiliência**: Caso ocorra bloqueio de IP geral (HTTP 429) ou ausência completa de legendas utilizáveis na lista de entrada, a camada Bronze aciona um **Fallback de Dados Sintéticos Determinísticos** baseado em sementes de hash fixas. O pipeline adota a lógica "8 ou 80": se ao menos 1 vídeo válido for processado, os dados sintéticos são ignorados.

### Camada Silver (Limpeza, Tipagem e Qualidade)
*   **Contrato de Dados (Pandera)**: Um esquema estrito valida tipos primitivos (`str`, `int`, `float`), restrições de completude (campos não nulos) e valores válidos (ex: durações maiores que zero).
*   **Limpeza Textual**: Conversão para minúsculo, remoção de pontuação de forma segura e eliminação total de acentos ortográficos utilizando a biblioteca nativa `unicodedata`. Aplicação de filtro de *stopwords* customizado.
*   **Quarentena**: Qualquer trecho que resulte em texto vazio ou com contagem de palavras inválida (`n_palavras < 1`) é capturado de forma silenciosa e desviado para `./datalake/silver/_quarentena/descartes.parquet`, preservando a sanidade do lake principal.

### Camada Gold (Agregação de Negócio)
*   **Motor Computacional**: DuckDB atuando diretamente sobre os arquivos Parquet em memória.
*   **Visões Analíticas**:
    1.  *Share of Voice (KPI)*: Consolidação do tempo total de exposição e menções agregados por país e traduzidos para o mapeamento internacional.
    2.  *Contexto Semântico*: Cruzamento matricial entre as nações citadas e os termos do `VOCABULARIO` de ação que residiam na mesma sentença (coocorrência frase a frase).
    3.  *Blocos Geopolíticos*: Categorização automatizada das nações em alianças estratégicas (OTAN, BRICS+, Oriente Médio).

---

## 2. Princípios de Engenharia Aplicados

Para atender às exigências não negociáveis do contrato de trabalho, o sistema foi blindado com quatro premissas:

1.  **Idempotência**: O pipeline gerencia uma camada de controle estruturada via banco SQLite (`datalake/control/ingestion.db`). Cada execução registra marcas d'água (*watermarks*) dos metadados processados. Se o ingestor for executado N vezes para o mesmo lote, ele identifica o registro no banco de estado e pula a inserção, evitando duplicações nas camadas Silver e Gold.
2.  **Tratamento de Erros**: Erros fatais de rede ou indisponibilidade de legenda do YouTube são capturados via blocos estruturados de `try/except` que isolam os módulos nativos (`NoTranscriptFound`). A falha de uma única fonte nunca derruba o processo inteiro.
3.  **Rastreabilidade**: O volume exato de linhas lidas, o número de descartes desviados para a quarentena e os registros promovidos para a Gold são quantificados em tempo de execução, permitindo auditoria pontual do Data Lake.
4.  **Observabilidade**: Todo o comportamento do agendador (`scheduler.py`) e do ingestor é canalizado para arquivos de log rotativos em produção, permitindo identificar gargalos ou bloqueios temporários de IP sem interrupção do sistema.
