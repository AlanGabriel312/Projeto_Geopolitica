# Carta do Projeto — Monitoramento Geopolítico

---

## 1. Identidade

| Campo | Preenchimento |
| :--- | :--- |
| **Nome do projeto** | Análise Guerra Rússia x Ucrânia |
| **Tema / domínio** | Geopolítica & Notícias (Tema #3) |
| **Equipe** | Alan Alvarado<br>Henrique Silva Oliveira |
| **E-mail** | alan.alvarado@edu.unifor.br<br>henrique.oliveira@edu.unifor.br |
| **Data de início** | 26/06/2026 |

---

## 2. Problema e propósito

| Campo | Preenchimento |
| :--- | :--- |
| **Problema** | Analistas de risco e gestores corporativos precisam acompanhar crises internacionais em tempo real para antecipar impactos em cadeias de suprimentos e investimentos. Fazer esse monitoramento de forma manual (assistindo a vídeos de notícias no YouTube) gera gargalos severos de tempo, omissão de informações e planilhas estáticas desatualizadas. |
| **Propósito** | O sistema automatiza a extração contínua de transcrições de canais de notícias de alta relevância, limpando o texto e cruzando menções geográficas com termos de ação. Ele consolida uma visão unificada e em tempo real sobre quais eixos e blocos geopolíticos estão dominando o cenário macroeconômico. |
| **Público-alvo** | Analistas de inteligência de mercado, gestores de risco corporativo e diretores de relações internacionais. |
| **Hipótese de valor** | Se monitorarmos de forma contínua o Share of Voice de países e seus contextos semânticos nas mídias líderes, conseguiremos reavaliar e decidir nossa exposição a riscos em mercados internacionais em menos de 24 horas. |

---

## 3. Escopo técnico

| Campo | Preenchimento |
| :--- | :--- |
| **Fontes de dados** | Vídeos e canais jornalísticos de grande circulação no YouTube (como CNN Brasil). Idiomas prioritários de legenda: `pt` e `pt-BR`. Vocabulário-alvo de ação: *guerra, sancao, conflito, embargo, tropas, fronteira, acordo*. |
| **Frequência de ingestão** | A cada 12 horas. Justificativa: O ritmo das pautas jornalísticas geopolíticas consolida-se em ciclos diários (manhã/noite), não exigindo processamento em tempo real (streaming), poupando chamadas de rede e reduzindo riscos de bloqueio de IP. |
| **Métrica principal (KPI)** | **Share of Voice (Tempo de Exposição)**: O volume acumulado em minutos em que cada nação ou bloco econômico ocupa o centro da narrativa midiática monitorada. |
| **Perguntas analíticas** | 1. Qual país detém a maior parcela de tempo de exposição (Share of Voice) nas discussões atuais?<br>2. Quais blocos geopolíticos (OTAN, BRICS+, Oriente Médio) estão concentrando as maiores menções?<br>3. Qual é o contexto semântico associado a cada país? (Ex: A Rússia está mais associada a 'guerra' ou a 'acordo'?) |
| **Fora de escopo** | Não faremos análise de sentimento refinada por Machine Learning (NLP/LLM complexo), tradução de legendas de múltiplos idiomas estrangeiros além do português nativo, e monitoramento de canais de opinião pessoal não-jornalísticos. |

---

## 4. Critérios de sucesso

| Campo | Preenchimento |
| :--- | :--- |
| **Definição de pronto** | Pipeline de dados operando de forma totalmente agendada na VPS, persistindo em formato Parquet nas camadas Bronze, Silver e Gold. Contrato de dados validado via Pandera (com descarte para quarentena) e dashboard Streamlit analitico e de observabilidade interativo publicado em URL pública operando por 7 dias contínuos sem quebras manuais. |
| **Riscos e Planos B** | **1. Bloqueio de IP por Scraping (HTTP 429)**: Contornado com pausas de segurança dinâmicas e aleatórias (12-20s) no 5G/VPS. Caso o bloqueio ocorra, o pipeline ativa o **Fallback de Dados Sintéticos Determinísticos** na Bronze, mantendo a integridade da aula.<br>**2. Vídeo sem legendas**: Tratado capturando o erro nativo `NoTranscriptFound`, direcionando o fluxo para os dados sintéticos em nível de contingência geral (lógica 8 ou 80).<br>**3. Indisponibilidade da VPS**: Monitoramento de logs locais (`scheduler.log`) e plano de reinicialização automática via `systemd`. |
