FROM bcb-official-cli:dev
RUN apt-get update \
    && apt-get install -y --no-install-recommends docker.io docker-cli \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir \
    docker==7.1.0 \
    python-dotenv==1.0.1 \
    unidiff==0.7.5 \
    typer==0.16.1 \
    ghapi==1.0.6 \
    GitPython==3.1.43 \
    modal==0.73.75 \
    tenacity==9.0.0 \
    PyYAML==6.0.2 \
    requests==2.32.3 \
    beautifulsoup4==4.12.3 \
    chardet==5.2.0 \
    huggingface_hub==0.27.1
ENTRYPOINT ["python"]
