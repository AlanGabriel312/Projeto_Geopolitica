# -*- coding: utf-8 -*-
"""
Captacao da transcricao (camada Bronze).
VERSÃO DE DIAGNÓSTICO
"""

from __future__ import annotations

import time
import random
import traceback


def _sintetico(video_id: str, vocabulario: list[str], n=160) -> list[dict]:
    rng = random.Random(hash(video_id) & 0xFFFFFFFF)
    base = [
        "entao", "olha", "o ponto aqui", "veja bem",
        "na pratica", "vale destacar", "o dado mostra",
        "repare que"
    ]

    trechos = []
    t = 0.0

    for _ in range(n):
        palavras = rng.sample(base, k=2)

        if rng.random() < 0.30 and vocabulario:
            palavras.append(rng.choice(vocabulario))

        dur = round(rng.uniform(2.0, 6.0), 2)

        trechos.append({
            "text": " ".join(palavras),
            "start": round(t, 2),
            "duration": dur
        })

        t += dur

    return trechos


def extrair_transcricao(
    video_id: str,
    idiomas: list[str],
    vocabulario: list[str],
    modo_demo: bool,
) -> list[dict]:

    print("=" * 80)
    print("ENTROU EM extrair_transcricao")
    print(f"VIDEO: {video_id}")
    print(f"MODO DEMO: {modo_demo}")
    print(f"IDIOMAS: {idiomas}")
    print("=" * 80)

    if modo_demo or video_id.startswith("demo_"):
        print(">>> USANDO MODO DEMO <<<")
        return _sintetico(video_id, vocabulario)

    try:

        print("Importando youtube_transcript_api...")

        from youtube_transcript_api import YouTubeTranscriptApi

        print("Import OK")

        print("Criando instancia...")

        api = YouTubeTranscriptApi()

        print("Instancia criada")

        print("Chamando fetch...")

        fetched = api.fetch(
            video_id,
            languages=idiomas
        )

        print("FETCH OK")

        print("Convertendo para raw_data...")

        dados = fetched.to_raw_data()

        print(f"TOTAL TRECHOS: {len(dados)}")

        tempo = random.randint(2, 3)

        print(f"Dormindo {tempo}s")

        time.sleep(tempo)

        resultado = [
            {
                "text": s["text"],
                "start": float(s["start"]),
                "duration": float(s["duration"]),
            }
            for s in dados
        ]

        print(f"RETORNANDO {len(resultado)} TRECHOS")

        return resultado

    except Exception as e:

        print()
        print("#" * 80)
        print("ERRO NA TRANSCRIÇÃO")
        print("#" * 80)

        print("TIPO:")
        print(type(e))

        print()

        print("MENSAGEM:")
        print(e)

        print()

        print("TRACEBACK COMPLETO:")

        traceback.print_exc()

        print("#" * 80)
        print()

        return []
