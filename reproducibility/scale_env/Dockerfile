FROM bcb-official-cli:dev

COPY requirements.txt /tmp/scale-requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /tmp/scale-requirements.txt \
    && mkdir -p /opt/nltk_data \
    && python -m nltk.downloader -d /opt/nltk_data punkt averaged_perceptron_tagger \
    && test -d /opt/nltk_data/tokenizers/punkt \
    && test -d /opt/nltk_data/taggers/averaged_perceptron_tagger

ENV NLTK_DATA=/opt/nltk_data \
    NLTK_DOWNLOADER_FORCE_INTERACTIVE_SHELL=false
