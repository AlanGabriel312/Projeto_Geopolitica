# -*- coding: utf-8 -*-
"""
Estado de ingestao em SQLite — a FONTE DA VERDADE do pipeline.

Responde as tres perguntas do engenheiro de dados:
  1. O que ja ingeri?        -> tabela ingestion_state (PK = video_id)
  2. O que mudou desde a ultima vez? -> watermark por canal (max publishedAt)
  3. Como evito duplicar/corromper?  -> UPSERT idempotente + content_hash

Nada de ORM pesado aqui: SQLite puro, zero setup, didatico.
"""
from __future__ import annotations
import sqlite3
import hashlib
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DDL = """
CREATE TABLE IF NOT EXISTS ingestion_state (
    video_id        TEXT PRIMARY KEY,
    channel_id      TEXT NOT NULL,
    dominio         TEXT NOT NULL,
    published_at    TEXT,                 -- ISO 8601 (watermark)
    title           TEXT,
    status          TEXT NOT NULL,        -- DISCOVERED|INGESTED|FAILED|SKIPPED
    content_hash    TEXT,                 -- hash da transcricao (detecta mudanca)
    transcript_len  INTEGER DEFAULT 0,
    error           TEXT,
    discovered_at   TEXT NOT NULL,
    ingested_at     TEXT,
    attempts        INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS channel_watermark (
    channel_id          TEXT PRIMARY KEY,
    last_published_at   TEXT,             -- maior publishedAt ja processado
    last_run_at         TEXT,
    videos_total        INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_state_channel ON ingestion_state(channel_id);
CREATE INDEX IF NOT EXISTS idx_state_status  ON ingestion_state(status);

-- Historico de ciclos de ingestao (1 linha por canal por execucao).
-- Fonte para o dashboard de OBSERVACAO: quantos ciclos rodaram, quando, e o
-- balanco descobertos/ingeridos/pulados/falhas de cada um.
CREATE TABLE IF NOT EXISTS ingestion_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at        TEXT NOT NULL,          -- ISO 8601 (fim do ciclo)
    canal         TEXT,
    channel_id    TEXT,
    dominio       TEXT,
    descobertos   INTEGER DEFAULT 0,
    ingeridos     INTEGER DEFAULT 0,
    pulados       INTEGER DEFAULT 0,
    falhas        INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_runs_at ON ingestion_runs(run_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def content_hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


class StateStore:
    def __init__(self, db_path: str = "./datalake/control/ingestion.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        with self._conn() as c:
            c.executescript(DDL)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # --- WATERMARK: incrementalidade -------------------------------------
    def get_watermark(self, channel_id: str) -> str | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT last_published_at FROM channel_watermark WHERE channel_id=?",
                (channel_id,)).fetchone()
            return row["last_published_at"] if row else None

    def update_watermark(self, channel_id: str, published_at: str,
                         novos: int) -> None:
        with self._conn() as c:
            c.execute("""
                INSERT INTO channel_watermark
                    (channel_id, last_published_at, last_run_at, videos_total)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    last_published_at = MAX(excluded.last_published_at,
                                            channel_watermark.last_published_at),
                    last_run_at       = excluded.last_run_at,
                    videos_total      = channel_watermark.videos_total + excluded.videos_total
            """, (channel_id, published_at or "", _now(), novos))

    # --- IDEMPOTENCIA: já processei este video? --------------------------
    def ja_ingerido(self, video_id: str, novo_hash: str | None = None) -> bool:
        """True se o video ja esta INGESTED e o conteudo nao mudou."""
        with self._conn() as c:
            row = c.execute(
                "SELECT status, content_hash FROM ingestion_state WHERE video_id=?",
                (video_id,)).fetchone()
        if not row or row["status"] != "INGESTED":
            return False
        if novo_hash is not None and row["content_hash"] != novo_hash:
            return False   # legenda mudou -> reprocessa
        return True

    def marcar_descoberto(self, video_id, channel_id, dominio,
                          published_at, title) -> None:
        with self._conn() as c:
            c.execute("""
                INSERT INTO ingestion_state
                    (video_id, channel_id, dominio, published_at, title,
                     status, discovered_at)
                VALUES (?, ?, ?, ?, ?, 'DISCOVERED', ?)
                ON CONFLICT(video_id) DO NOTHING
            """, (video_id, channel_id, dominio, published_at, title, _now()))

    def marcar_ingerido(self, video_id, c_hash, t_len) -> None:
        with self._conn() as c:
            c.execute("""
                UPDATE ingestion_state
                SET status='INGESTED', content_hash=?, transcript_len=?,
                    ingested_at=?, attempts=attempts+1, error=NULL
                WHERE video_id=?
            """, (c_hash, t_len, _now(), video_id))

    def marcar_falha(self, video_id, erro) -> None:
        with self._conn() as c:
            c.execute("""
                UPDATE ingestion_state
                SET status='FAILED', error=?, attempts=attempts+1
                WHERE video_id=?
            """, (str(erro)[:300], video_id))

    # --- Observabilidade --------------------------------------------------
    def resumo(self) -> dict:
        with self._conn() as c:
            rows = c.execute(
                "SELECT status, COUNT(*) n FROM ingestion_state GROUP BY status"
            ).fetchall()
            return {r["status"]: r["n"] for r in rows}

    def log_run(self, canal: dict, res: dict) -> None:
        """Grava uma linha por ciclo de ingestao (alimenta o dashboard de Observacao)."""
        with self._conn() as c:
            c.execute("""
                INSERT INTO ingestion_runs
                    (run_at, canal, channel_id, dominio,
                     descobertos, ingeridos, pulados, falhas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (_now(), canal.get("nome"), canal.get("channel_id"),
                  canal.get("dominio"),
                  res.get("descobertos", 0), res.get("ingeridos", 0),
                  res.get("pulados_idempotencia", 0), res.get("falhas", 0)))

    # --- Leituras para o dashboard de Observacao (retornam list[dict]) ----
    def _rows(self, sql: str, args: tuple = ()) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute(sql, args).fetchall()]

    def runs(self, limite: int = 500) -> list[dict]:
        """Ciclos de ingestao, mais recentes primeiro."""
        return self._rows(
            "SELECT * FROM ingestion_runs ORDER BY run_at DESC LIMIT ?", (limite,))

    def watermarks(self) -> list[dict]:
        """Estado de incrementalidade por canal."""
        return self._rows(
            "SELECT * FROM channel_watermark ORDER BY last_run_at DESC")

    def ingestoes_por_dia(self) -> list[dict]:
        """Videos ingeridos por dia (evolucao ao longo do periodo de observacao)."""
        return self._rows("""
            SELECT substr(ingested_at, 1, 10) AS dia, COUNT(*) AS ingeridos
            FROM ingestion_state
            WHERE status='INGESTED' AND ingested_at IS NOT NULL
            GROUP BY dia ORDER BY dia
        """)

    def falhas(self, limite: int = 200) -> list[dict]:
        """Videos que falharam, com o motivo (para diagnostico)."""
        return self._rows("""
            SELECT video_id, channel_id, dominio, error, attempts, discovered_at
            FROM ingestion_state WHERE status='FAILED'
            ORDER BY discovered_at DESC LIMIT ?
        """, (limite,))

    def ultima_execucao(self) -> str | None:
        """Timestamp ISO do ciclo mais recente (para o indicador de saude)."""
        with self._conn() as c:
            row = c.execute(
                "SELECT MAX(run_at) AS ult FROM ingestion_runs").fetchone()
            return row["ult"] if row else None
