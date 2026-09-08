FROM bcb-segregation80:v3
RUN apt-get update && apt-get install -y --no-install-recommends libtk8.6 libsndfile1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/scale1000-requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /tmp/scale1000-requirements.txt
