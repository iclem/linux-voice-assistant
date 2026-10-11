FROM ghcr.io/ohf-voice/linux-voice-assistant@sha256:5a6ecf5ad5ee871851331c47885b0b0fdf81b2a5e6e33824093b557028d619b6
COPY patch_followup.py /tmp/patch_followup.py
RUN /app/.venv/bin/python /tmp/patch_followup.py
