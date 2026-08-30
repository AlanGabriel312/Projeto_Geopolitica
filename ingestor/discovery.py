# -*- coding: utf-8 -*-
"""
Descoberta de videos — YouTube Data API v3 com ESTRATEGIA DE COTA.

Cota diaria: 10.000 unidades. Custo por chamada:
  - search.list ............ 100 unidades  (CARO — evitar em loop!)
  - playlistItems.list ......   1 unidade
  - videos.list .............   1 unidade
  - channels.list ...........   1 unidade

Estrategia correta (decisao de ENGENHARIA):
  1. channels.list UMA vez -> pega a playlist de uploads do canal (UU...).
  2. playlistItems.list a cada ciclo (1 unidade) -> lista uploads recentes.
  3. videos.list em lote de ate 50 IDs (1 unidade) -> metadados ricos.
Assim um canal custa ~2 unidades/ciclo em vez de 100+. Da pra rodar
dezenas de canais o dia inteiro dentro da cota gratuita.

Em modo_demo=True, nada disso e chamado: geramos metadados sinteticos
deterministicos para a aula rodar sem API key e sem gastar cota.

Descoberta de videos — YouTube Data API v3 com ESTRATEGIA DE COTA.
Otimizado para o Domínio #3: Geopolítica & Notícias.
"""
from __future__ import annotations
import os
import random
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone

log = logging.getLogger("ingestor.discovery")

@dataclass
class VideoMeta:
    video_id: str
    channel_id: str
    title: str
    description: str
    published_at: str          # ISO 8601 — usado como watermark
    duration_iso: str          # PT#M#S
    view_count: int
    like_count: int
    comment_count: int
    tags: list
    category_id: str
    default_audio_language: str
    live_broadcast_content: str

    def to_row(self) -> dict:
        d = asdict(self)
        d["tags"] = ",".join(self.tags) if self.tags else ""  # achata p/ parquet/sqlite seguro
        return d


# ---------------------------------------------------------------------------
# Implementacao REAL (Data API v3)
# ---------------------------------------------------------------------------
class YouTubeDiscovery:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        self._yt = None

    def _client(self):
        if self._yt is None:
            if not self.api_key:
                log.warning("⚠️ YOUTUBE_API_KEY não localizada nas variáveis de ambiente (.env).")
            from googleapiclient.discovery import build
            self._yt = build("youtube", "v3", developerKey=self.api_key,
                             cache_discovery=False)
        return self._yt

    def _uploads_playlist(self, channel_id: str) -> str:
        try:
            resp = self._client().channels().list(
                part="contentDetails,snippet", id=channel_id).execute()
            items = resp.get("items", [])
            if not items:
                raise ValueError(f"Canal nao encontrado no YouTube: {channel_id}")
            return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        except Exception as e:
            log.error(f"❌ Falha crítica ao resolver playlist de uploads do canal {channel_id}: {e}")
            raise e

    def descobrir(self, channel_id: str, since_iso: str | None,
                max_videos: int, janela_dias: int) -> list[VideoMeta]:

        print("=" * 80)
        print(f"CANAL: {channel_id}")
        print(f"WATERMARK: {since_iso}")
        print("=" * 80)

        try:
            uploads = self._uploads_playlist(channel_id)
            print("UPLOAD PLAYLIST:", uploads)

            corte = datetime.now(timezone.utc) - timedelta(days=janela_dias)

            page_count = 0
            ids = []
            page = None

            while len(ids) < max_videos:

                page_count += 1

                if page_count > 2:
                    print("Limite de páginas atingido")
                    break

                resp = self._client().playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads,
                    maxResults=5,
                    pageToken=page,
                ).execute()

                print(f"\nPágina da API: {page or 'primeira'}")

                for it in resp.get("items", []):

                    vid = it["contentDetails"]["videoId"]
                    pub = it["snippet"]["publishedAt"]

                    print(f"VIDEO: {vid} | {pub}")

                    # watermark normal
                    if since_iso and pub <= since_iso:
                        print(">>> VIDEO ANTIGO, IGNORANDO <<<")
                        continue

                    # dentro da janela
                    if pub >= corte.isoformat():
                        print("   -> NOVO VIDEO")
                        ids.append(vid)
                    else:
                        print("   -> FORA DA JANELA")


                page = resp.get("nextPageToken")

                if not page:
                    print("Fim da playlist.")
                    break

            videos = self._hidratar(channel_id, ids[:max_videos])

            # Remove lives agendadas
            videos_validos = []

            for v in videos:

                if v.live_broadcast_content == "upcoming":
                    print(f">>> LIVE AGENDADA IGNORADA: {v.title}")
                    continue

                # aceita live acontecendo mesmo se published_at for antigo
                if v.live_broadcast_content == "live":
                    print(f">>> LIVE EM ANDAMENTO IGNORADA: {v.title}")
                    continue

                videos_validos.append(v)

            print("\nVIDEOS QUE SERAO PROCESSADOS:")
            print([v.video_id for v in videos_validos])

            return videos_validos


        except Exception as e:
            log.error(
                f"⚠️ Erro no processo de descoberta do canal {channel_id}: {e}"
            )
            return []

    def _hidratar(self, channel_id: str, ids: list[str]) -> list[VideoMeta]:
        if not ids:
            return []
        resp = self._client().videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(ids), maxResults=50).execute()
        out = []
        for it in resp.get("items", []):
            sn, st = it["snippet"], it.get("statistics", {})
            cd = it.get("contentDetails", {})
            out.append(VideoMeta(
                video_id=it["id"],
                channel_id=channel_id,
                title=sn.get("title", ""),
                description=sn.get("description", "")[:500],
                published_at=sn.get("publishedAt", ""),
                duration_iso=cd.get("duration", ""),
                view_count=int(st.get("viewCount", 0)),
                like_count=int(st.get("likeCount", 0)),
                comment_count=int(st.get("commentCount", 0)),
                tags=sn.get("tags", []) if sn.get("tags") else [],
                category_id=sn.get("categoryId", ""),
                default_audio_language=sn.get("defaultAudioLanguage", ""),
                live_broadcast_content=sn.get("liveBroadcastContent", "none"),
            ))
        return out


# ---------------------------------------------------------------------------
# Implementacao DEMO (sintetica, deterministica) — mesma interface
# ---------------------------------------------------------------------------
class DemoDiscovery:
    """Substitui a API real. Gera videos 'novos' a cada ciclo de forma
    deterministica por canal+dia, para demonstrar watermark/incrementalidade."""
    def descobrir(self, channel_id: str, since_iso: str | None,
                  max_videos: int, janela_dias: int) -> list[VideoMeta]:
        rng = random.Random(f"{channel_id}-{datetime.now().strftime('%Y%m%d%H')}")
        n = rng.randint(1, max_videos)
        agora = datetime.now(timezone.utc)
        out = []
        for i in range(n):
            pub = (agora - timedelta(hours=rng.randint(0, 24 * janela_dias)))
            pub_iso = pub.isoformat()
            if since_iso and pub_iso <= since_iso:
                continue  # respeita o watermark, como a API real faria
            vid = f"demo_{channel_id[-4:]}_{pub.strftime('%j%H')}_{i}"
            out.append(VideoMeta(
                video_id=vid, channel_id=channel_id,
                title=f"Video {i} do canal {channel_id[-4:]}",
                description="conteudo sintetico para a aula",
                published_at=pub_iso, duration_iso=f"PT{rng.randint(3,40)}M",
                view_count=rng.randint(1_000, 500_000),
                like_count=rng.randint(50, 30_000),
                comment_count=rng.randint(0, 5_000),
                tags=["demo", "aula", "eng-dados"],
                category_id="27", default_audio_language="pt",
            ))
        return out


def get_discovery(modo_demo: bool):
    return DemoDiscovery() if modo_demo else YouTubeDiscovery()
