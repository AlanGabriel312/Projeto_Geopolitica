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
    """Especialização da Camada Gold para Geopolítica usando DuckDB + Parquet particionado."""
    src = f"./datalake/silver/dominio={dominio}/**/*.parquet"
    
    # Lista Massiva de Países para Monitoramento na Gold
    paises_monitorados = [
        "russia", "ucrania", "ira", "israel", "china", "venezuela", "brasil",
        "eua", "estados unidos", "siria", "libano", "iemen", "palestina", 
        "taiwan", "coreia", "japao", "india", "reino unido", "franca", 
        "alemanha", "italia", "espanha", "portugal", "canada", "mexico", 
        "colombia", "argentina", "chile", "cuba", "egito", "arabia saudita", 
        "turquia", "pakistan", "afeganistao", "nigeria", "africa do sul"
    ]
    
     # === MODIFICADO: Se o vocabulario vier vazio, aplica a lista padrão por segurança ===
    termos_conflito = vocabulario if vocabulario else ["guerra", "sancao", "conflito", "embargo", "tropas", "fronteira", "acordo"]
    
    con = duckdb.connect()
    lista_paises_sql = "', '".join(paises_monitorados)
    lista_termos_sql = "', '".join(termos_conflito)
    
    try:
        # QUERY 1: Filtra e aceita apenas os vídeos que contém os termos do seu vocabulário yaml
        gold_individual = con.execute(r"""
            WITH s AS (SELECT * FROM read_parquet('""" + src + r"""')),
                 alvo_pais AS (SELECT UNNEST(['""" + lista_paises_sql + r"""']) AS pais),
                 alvo_termo AS (SELECT UNNEST(['""" + lista_termos_sql + r"""']) AS termo),
                 
                 videos_validos AS (
                     SELECT DISTINCT s.video_id 
                     FROM s
                     JOIN alvo_termo t ON REGEXP_MATCHES(s.texto_limpo, '(^|\s)' || t.termo || '($|\s)')
                 )
            SELECT a.pais, 
                   COUNT(*) AS mencoes
            FROM s 
            JOIN videos_validos vv ON s.video_id = vv.video_id
            JOIN alvo_pais a ON REGEXP_MATCHES(s.texto_limpo, '(^|\s)' || a.pais || '($|\s)')
            GROUP BY a.pais 
            ORDER BY mencoes DESC
        """).df()
        
        # QUERY 2: Coocorrência Geopolítica restrita apenas aos vídeos do vocabulário
        gold_conexoes = con.execute(r"""
            WITH s AS (SELECT * FROM read_parquet('""" + src + r"""')),
                 alvo_pais AS (SELECT UNNEST(['""" + lista_paises_sql + r"""']) AS pais),
                 alvo_termo AS (SELECT UNNEST(['""" + lista_termos_sql + r"""']) AS termo),
                 
                 videos_validos AS (
                     SELECT DISTINCT s.video_id 
                     FROM s
                     JOIN alvo_termo t ON REGEXP_MATCHES(s.texto_limpo, '(^|\s)' || t.termo || '($|\s)')
                 ),
                 mencoes_por_trecho AS (
                     SELECT s.video_id, s.ordem, a.pais
                     FROM s
                     JOIN videos_validos vv ON s.video_id = vv.video_id
                     JOIN alvo_pais a ON REGEXP_MATCHES(s.texto_limpo, '(^|\s)' || a.pais || '($|\s)')
                 )
            SELECT 
                m1.pais AS pais_a, 
                m2.pais AS pais_b, 
                COUNT(*) AS mencoes_juntos
            FROM mencoes_por_trecho m1
            JOIN mencoes_por_trecho m2 ON m1.video_id = m2.video_id AND m1.ordem = m2.ordem
            WHERE m1.pais < m2.pais
            GROUP BY m1.pais, m2.pais
            ORDER BY mencoes_juntos DESC
        """).df()

        out = Path("./datalake/gold")
        out.mkdir(parents=True, exist_ok=True)
        
        gold_individual.to_parquet(out / "clipping_geopolitica.parquet", index=False)
        gold_conexoes.to_parquet(out / "coocorrencia_paises.parquet", index=False)
        
        log.info("📊 Camada Gold processada com sucesso aplicando o vocabulário do canais.yaml.")
        return gold_individual
        
    except duckdb.IOException:
        log.warning("⚠️ DuckDB: Ainda não existem arquivos Silver Parquet para processar a Gold.")
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

        # === CORRIGIDO: Passa a flag is_demo corrigida para a extração ===
        trechos = extrair_transcricao(
            v.video_id, glob_cfg.get("idiomas_legenda", ["pt", "pt-BR"]),
            vocab, is_demo)
            
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

    if novos:
        store.update_watermark(cid, max_pub, ingeridos)
        
    # === COMPATIBILIZADO: Envia o vocabulário lido do .yaml direto para as regras SQL ===
    _gold(dom, vocab)

    res = {"canal": canal["nome"], "descobertos": novos, "ingeridos": ingeridos,
           "pulados_idempotencia": pulados, "falhas": falhas}
    log.info("ciclo %s -> %s", canal["nome"], res)
    return res
