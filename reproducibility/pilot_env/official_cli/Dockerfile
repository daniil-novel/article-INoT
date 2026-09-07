FROM bcb-pilot:dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    PYTHONPATH=/workspace/reproducibility/vendor/bigcodebench \
    HOME=/tmp \
    XDG_CACHE_HOME=/tmp/.cache \
    HF_DATASETS_OFFLINE=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt /tmp/official-cli-requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check \
    -r /tmp/official-cli-requirements.txt

WORKDIR /workspace
ENTRYPOINT ["python", "-m", "bigcodebench.evaluate"]
