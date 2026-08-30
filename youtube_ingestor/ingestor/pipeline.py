# -*- coding: utf-8 -*-
"""
Pipeline de ingestao perene — orquestra um ciclo completo para UM canal.

Fluxo de um ciclo:
  descobrir (incremental via watermark)
    -> para cada video novo e nao-ingerido (idempotencia):
         captar transcricao  (BRONZE)
         limpar + contrato    (SILVER)
       persiste parquet + atualiza estado SQLite
    -> roda analitico do dominio (GOLD)
    -> avanca o watermark do canal

Tudo escrito de forma que rodar o mesmo ciclo duas vezes NAO duplica dados.
"""
from __future__ import annotations
import unicodedata
import re
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import duckdb
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

from .state import StateStore, content_hash
from .discovery import get_discovery
from .transcript import extrair_transcricao

import time
import random

log = logging.getLogger("ingestor")

STOPWORDS = {"entao", "olha", "ne", "tipo", "veja", "bem", "o", "a", "que",
             "de", "e", "aqui", "isso", "na", "pratica", "com", "para"}

# Mesmo contrato Silver dos 10 notebooks (Desafio 1), incluindo n_palavras.
SILVER_SCHEMA = DataFrameSchema({
    "video_id":    Column(str, nullable=False),
    "ordem":       Column(int, Check.ge(0)),
    "texto_limpo": Column(str, Check.str_length(min_value=1)),
    "start":       Column(float, Check.ge(0)),
    "duration":    Column(float, Check.gt(0)),
    "n_palavras":  Column(int, Check.ge(1)),
}, coerce=True)


def _limpar(texto: str) -> str:
    """Aplica a sua limpeza avançada removendo acentos e pontuações de forma segura."""
    # 1. Converte para minúsculo
    texto = texto.lower()
    # 2. Remove TODOS os acentos ortográficos (Transforma 'rússia' em 'russia')
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    # 3. Mantém apenas letras de 'a' a 'z' e espaços, removendo pontuações
    texto = re.sub(r"[^a-z\s]", " ", texto)
    # 4. Remove as stopwords e palavras muito curtas
    tokens = [t for t in texto.split() if t not in STOPWORDS and len(t) > 2]
    return " ".join(tokens)


def _bronze_silver(video_id, trechos) -> pd.DataFrame:
    df = pd.DataFrame([
        {"video_id": video_id, "ordem": i, "texto": t["text"],
         "start": float(t["start"]), "duration": float(t["duration"])}
        for i, t in enumerate(trechos)
    ])
    df["texto_limpo"] = df["texto"].apply(_limpar)
    df = df[df["texto_limpo"].str.len() > 0].copy()
    df["n_palavras"] = df["texto_limpo"].str.split().str.len().fillna(0).astype(int)
    return SILVER_SCHEMA.validate(df[["video_id", "ordem", "texto_limpo",
                                      "start", "duration", "n_palavras"]])


def _persistir(df: pd.DataFrame, dominio: str, video_id: str):
    dia = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    base = Path(f"./datalake/silver/dominio={dominio}/dt={dia}")
    base.mkdir(parents=True, exist_ok=True)
    df.to_parquet(base / f"{video_id}.parquet", index=False)


def _gold(dominio: str, vocabulario: list[str]):
    """Camada Gold para Geopolítica."""

    src = f"./datalake/silver/dominio={dominio}/**/*.parquet"

    paises_monitorados = [
        "russia", "ucrania", "ira", "israel", "china", "venezuela",
        "brasil", "eua", "estados unidos", "siria", "libano",
        "iemen", "palestina", "taiwan", "coreia", "japao",
        "india", "reino unido", "franca", "alemanha", "italia",
        "espanha", "portugal", "canada", "mexico", "colombia",
        "argentina", "chile", "cuba", "egito", "arabia saudita",
        "turquia", "paquistao", "afeganistao", "nigeria",
        "africa do sul"
    ]

    termos_conflito = (
        vocabulario
        if vocabulario
        else [
            "guerra",
            "sancao",
            "conflito",
            "embargo",
            "tropas",
            "fronteira",
            "acordo",
        ]
    )

    con = duckdb.connect()

    try:

        con.register(
            "paises_df",
            pd.DataFrame({"pais": paises_monitorados})
        )

        padrao = "|".join(
            rf"(^|\s){re.escape(t)}($|\s)"
            for t in termos_conflito
        )

        #
        # 1) Junta todos os trechos de cada vídeo.
        #
        videos_validos = con.execute(f"""
            SELECT
                video_id,
                string_agg(texto_limpo, ' ') AS texto_video
            FROM read_parquet('{src}')
            GROUP BY video_id
        """).df()

        #
        # 2) Mantém somente vídeos geopolíticos.
        #
        videos_validos = videos_validos[
            videos_validos["texto_video"].str.contains(
                padrao,
                regex=True,
                na=False,
            )
        ]

        if videos_validos.empty:
            log.info("Nenhum vídeo geopolítico encontrado.")

            out = Path("./datalake/gold")
            out.mkdir(parents=True, exist_ok=True)

            pd.DataFrame(columns=["pais", "mencoes"]).to_parquet(
                out / "clipping_geopolitica.parquet",
                index=False,
            )

            pd.DataFrame(
                columns=["pais_a", "pais_b", "mencoes_juntos"]
            ).to_parquet(
                out / "coocorrencia_paises.parquet",
                index=False,
            )

            return pd.DataFrame()

        con.register("videos_validos", videos_validos[["video_id"]])

        #
        # 3) Conta países.
        #
        gold_individual = con.execute(f"""
            WITH s AS (
                SELECT *
                FROM read_parquet('{src}')
            )

            SELECT
                p.pais,
                COUNT(*) AS mencoes
            FROM s

            JOIN videos_validos v
                ON s.video_id = v.video_id

            JOIN paises_df p
                ON regexp_matches(
                    s.texto_limpo,
                    '(^|\\s)' || p.pais || '($|\\s)'
                )

            GROUP BY p.pais

            ORDER BY mencoes DESC
        """).df()

        #
        # 4) Coocorrência.
        #
        gold_conexoes = con.execute(f"""
            WITH s AS (
                SELECT *
                FROM read_parquet('{src}')
            ),

            mencoes AS (
                SELECT
                    s.video_id,
                    s.ordem,
                    p.pais
                FROM s

                JOIN videos_validos v
                    ON s.video_id = v.video_id

                JOIN paises_df p
                    ON regexp_matches(
                        s.texto_limpo,
                        '(^|\\s)' || p.pais || '($|\\s)'
                    )
            )

            SELECT
                a.pais AS pais_a,
                b.pais AS pais_b,
                COUNT(*) AS mencoes_juntos

            FROM mencoes a

            JOIN mencoes b

                ON a.video_id = b.video_id
               AND a.ordem = b.ordem

            WHERE a.pais < b.pais

            GROUP BY
                a.pais,
                b.pais

            ORDER BY mencoes_juntos DESC
        """).df()

        out = Path("./datalake/gold")
        out.mkdir(parents=True, exist_ok=True)

        gold_individual.to_parquet(
            out / "clipping_geopolitica.parquet",
            index=False,
        )

        gold_conexoes.to_parquet(
            out / "coocorrencia_paises.parquet",
            index=False,
        )

        log.info(
            "Camada Gold recalculada (%d vídeos geopolíticos).",
            len(videos_validos),
        )

        return gold_individual

    except duckdb.IOException:

        log.warning("Ainda não existem arquivos Silver.")

        return pd.DataFrame()

    finally:
        con.close()


def rodar_ciclo(canal: dict, glob_cfg: dict, store: StateStore) -> dict:
    """Executa um ciclo completo de ingestao para um canal. Idempotente."""
    cid, dom = canal["channel_id"], canal["dominio"]
    vocab = canal.get("vocabulario", [])
    
    # === CORRIGIDO: Busca o modo_demo do yaml de forma segura, com fallback padrão FALSO ===
    is_demo = glob_cfg.get("modo_demo", False)
    disc = get_discovery(is_demo)

    watermark = store.get_watermark(cid)
    videos = disc.descobrir(cid, watermark,
                            canal.get("max_videos_por_ciclo", 5),
                            glob_cfg.get("janela_descoberta_dias", 30))

    novos, ingeridos, pulados, falhas, max_pub = 0, 0, 0, 0, watermark or ""
    for v in videos:
        store.marcar_descoberto(v.video_id, cid, dom, v.published_at, v.title)
        max_pub = max(max_pub, v.published_at or "")
        novos += 1
    
        # Ignora transmissões ao vivo
        if v.live_broadcast_content == "live":
            log.info(f"Pulando live em andamento: {v.title}")
            pulados += 1
            continue

        # === CORRIGIDO: Passa a flag is_demo corrigida para a extração ===
        trechos = extrair_transcricao(
            v.video_id, 
            glob_cfg.get("idiomas_legenda", ["pt", "pt-BR"]),
            vocab, 
            is_demo
        )

        # Evita muitas requisições consecutivas ao YouTube
        espera = random.randint(3, 8)
        log.info(f"Aguardando {espera}s antes do próximo vídeo...")
        time.sleep(espera)
                    
        if not trechos:
            store.marcar_falha(v.video_id, "sem legenda")
            falhas += 1
            continue

        texto_total = " ".join(t["text"] for t in trechos)
        h = content_hash(texto_total)
        if store.ja_ingerido(v.video_id, h):   # IDEMPOTENCIA
            pulados += 1
            continue
        try:
            df = _bronze_silver(v.video_id, trechos)
            _persistir(df, dom, v.video_id)
            store.marcar_ingerido(v.video_id, h, len(df))
            ingeridos += 1
        except (pa.errors.SchemaError, Exception) as e:
            store.marcar_falha(v.video_id, e)
            falhas += 1

    if ingeridos > 0:
        store.update_watermark(cid, max_pub, ingeridos)
        
    # === COMPATIBILIZADO: Envia o vocabulário lido do .yaml direto para as regras SQL ===
    _gold(dom, vocab)

    res = {"canal": canal["nome"], "descobertos": novos, "ingeridos": ingeridos,
           "pulados_idempotencia": pulados, "falhas": falhas}
    store.log_run(canal, res)   # registra o ciclo para o dashboard de Observacao
    log.info("ciclo %s -> %s", canal["nome"], res)
    return res
