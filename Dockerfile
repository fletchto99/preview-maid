FROM python:3.14-slim

LABEL org.opencontainers.image.title="preview-maid" \
      org.opencontainers.image.description="Find missing Plex preview thumbnails, voice activity data, and markers" \
      org.opencontainers.image.source="https://github.com/fletchto99/preview-maid"

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/requirements.txt requirements.txt
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --no-create-home appuser

COPY app/previewmaid.py .

USER appuser

HEALTHCHECK --interval=60s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import schedule; import plexapi" || exit 1

CMD ["python", "previewmaid.py"]