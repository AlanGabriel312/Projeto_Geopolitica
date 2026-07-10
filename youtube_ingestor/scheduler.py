# -*- coding: utf-8 -*-
"""
Entrypoint da ingestao perene. Usa APScheduler para agendar CADA canal no
seu proprio intervalo (decisao de negocio definida em config/canais.yaml).
"""
from __future__ import annotations
import sys
import logging
from pathlib import Path
from datetime import datetime

# === ADICIONADO: Força o Python a ler o seu arquivo oculto .env no Linux ===
from dotenv import load_dotenv
load_dotenv() 

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ingestor.state import StateStore
from ingestor.pipeline import rodar_ciclo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("scheduler")

CONFIG = Path(__file__).parent / "config" / "canais.yaml"


def carregar_config() -> dict:
    with open(CONFIG, encoding="utf-8") as f:
        return yaml.safe_load(f)


def rodar_uma_vez(cfg: dict, store: StateStore):
    glob = cfg.get("global", {})
    for canal in cfg["canais"]:
        if canal.get("ativo", True):
            rodar_ciclo(canal, glob, store)


def main():
    cfg = carregar_config()
    store = StateStore()

    if "--status" in sys.argv:
        print("Estado de ingestao:", store.resumo())
        return
    if "--once" in sys.argv:
        log.info("Execucao unica (--once)")
        rodar_uma_vez(cfg, store)
        print("Resumo final:", store.resumo())
        return

    sched = BlockingScheduler(timezone="America/Fortaleza")
    glob = cfg.get("global", {})
    for canal in cfg["canais"]:
        if not canal.get("ativo", True):
            continue
        intervalo = canal.get("intervalo_min", 60)
        
        # Agendamento contínuo
        sched.add_job(
            rodar_ciclo, IntervalTrigger(minutes=intervalo),
            args=[canal, glob, store],
            id=canal["channel_id"], name=canal["nome"],
            max_instances=1, coalesce=True,    # nao acumula execucoes atrasadas
            # MODIFICADO: datetime.now() faz o robô rodar o primeiro ciclo IMEDIATAMENTE
            # ao ligar, sem esperar o intervalo de 15 minutos passar (melhor para auditoria)
            next_run_time=datetime.now())                
        log.info("agendado: %s a cada %d min", canal["nome"], intervalo)

    log.info("Ingestor perene iniciado. Ctrl+C para encerrar.")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("encerrando...")


if __name__ == "__main__":
    main()