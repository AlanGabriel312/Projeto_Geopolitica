# Deploy do projeto (ingestor + dashboard) — adicionado pelo professor para publicar na VPS (Coolify).
# Layout deste repo: todo o código está em youtube_ingestor/ (base: projeto_modelo).
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

# Deps (achata youtube_ingestor/ em /app para os imports absolutos "from ingestor..." funcionarem).
COPY youtube_ingestor/requirements.txt .
# python-dotenv: o scheduler.py faz load_dotenv() mas a lib não está no requirements.
RUN pip install --upgrade pip && pip install -r requirements.txt && pip install python-dotenv

COPY youtube_ingestor/ /app/
RUN mkdir -p /app/datalake
EXPOSE 8501
