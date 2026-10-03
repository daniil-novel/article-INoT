# Reconstructed recipe; not a byte-identical export of the historical image.
FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    NLTK_DATA=/opt/nltk_data HOME=/tmp \
    PYTHONPATH=/opt/bigcodebench OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 TF_NUM_INTRAOP_THREADS=1 TF_NUM_INTEROP_THREADS=1 \
    HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
    MPLBACKEND=Agg XDG_CACHE_HOME=/tmp/.cache
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgomp1 libtk8.6 libsndfile1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY primary/evaluation/portable/requirements-frozen.txt /opt/requirements-frozen.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /opt/requirements-frozen.txt
COPY primary/evaluation/bigcodebench-source/ /opt/bigcodebench/
COPY primary/evaluation/dataset/evaluator_dataset.jsonl /opt/data/evaluator_dataset.jsonl
COPY primary/evaluation/portable/nltk-resources-sha256.txt /opt/nltk-resources-sha256.txt
COPY primary/evaluation/portable/verify_environment.py /opt/verify_environment.py
RUN python -m nltk.downloader -d /opt/nltk_data punkt averaged_perceptron_tagger stopwords words
RUN python /opt/verify_environment.py --requirements /opt/requirements-frozen.txt --resources /opt/nltk-resources-sha256.txt
ENV BIGCODEBENCH_OVERRIDE_PATH=/opt/data/evaluator_dataset.jsonl
WORKDIR /run
ENTRYPOINT ["python", "-m", "bigcodebench.evaluate"]
