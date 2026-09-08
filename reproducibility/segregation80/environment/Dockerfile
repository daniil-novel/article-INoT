FROM bcb-heldout200:v3
COPY requirements.txt /tmp/segregation80-requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /tmp/segregation80-requirements.txt
ENV TF_NUM_INTRAOP_THREADS=1 TF_NUM_INTEROP_THREADS=1
