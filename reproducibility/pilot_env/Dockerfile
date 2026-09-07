FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg

WORKDIR /workspace
COPY reproducibility/pilot_env/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /tmp/requirements.txt

# Source and data are supplied as read-only runtime mounts. Results use /out.
ENTRYPOINT ["python", "/workspace/reproducibility/bcb_pilot_evaluator.py"]
