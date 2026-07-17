# -*- coding: utf-8 -*-
"""
Captacao da transcricao (camada Bronze). Resiliente: se a legenda nao existe
ou o ambiente esta sem rede, cai num gerador sintetico deterministico.
Customizado com a API moderna 1.2.4 e pausas de segurança.
"""
from __future__ import annotations
import time
import random
import logging

log = logging.getLogger("ingestor.transcript")

def _sintetico(video_id: str, vocabulario: list[str], n=160) -> list[dict]:
    rng = random.Random(hash(video_id) & 0xFFFFFFFF)
    base = ["entao", "olha", "o ponto aqui", "veja bem", "na pratica",
            "vale destacar", "o dado mostra", "repare que"]
    trechos, t = [], 0.0
    for _ in range(n):
        palavras = rng.sample(base, k=2)
        if rng.random() < 0.30 and vocabulario:
            palavras.append(rng.choice(vocabulario))
        dur = round(rng.uniform(2.0, 6.0), 2)
        trechos.append({"text": " ".join(palavras), "start": round(t, 2),
                        "duration": dur})
        t += dur
    return trechos


def extrair_transcricao(video_id: str, idiomas: list[str],
                        vocabulario: list[str], modo_demo: bool) -> list[dict]:
    if modo_demo or video_id.startswith("demo_"):
        return _sintetico(video_id, vocabulario)
        
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        # 1. Cria a instância exigida pela nova arquitetura da API 1.2.4
        api = YouTubeTranscriptApi()                  
        
        # 2. Faz o fetch forçando os idiomas e extrai os dados brutos convertidos
        fetched = api.fetch(video_id, languages=idiomas).to_raw_data()
        
        # 3. Pausa inteligente e aleatória para evitar bloqueios de IP no 5G/VPS
        tempo_espera = random.randint(12, 18)
        log.info(f"-> Transcrição de {video_id} extraída. Aguardando {tempo_espera}s...")
        time.sleep(tempo_espera)
        
        # CORRIGIDO: Acessa os campos usando chaves de dicionário ["text"] e não pontos .text
        return [{"text": s["text"], "start": float(s["start"]), "duration": float(s["duration"])}
                for s in fetched]
                
    except Exception as e:
        log.warning(
            f"Erro ao capturar legenda real do vídeo {video_id}: "
            f"{type(e).__name__} - {e}"
        )
        return []
