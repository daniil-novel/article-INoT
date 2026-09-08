FROM bcb-scale1000:v1

COPY reproducibility/scale1000/environment-v2/requirements.txt /tmp/scale1000-v2-requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /tmp/scale1000-v2-requirements.txt
