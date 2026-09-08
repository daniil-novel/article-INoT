FROM bcb-scale40:v2

COPY requirements.txt /tmp/heldout200-requirements.txt
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r /tmp/heldout200-requirements.txt \
    && mkdir -p /opt/nltk_data \
    && python -m nltk.downloader -d /opt/nltk_data punkt averaged_perceptron_tagger stopwords words \
    && test -d /opt/nltk_data/tokenizers/punkt \
    && test -d /opt/nltk_data/corpora/stopwords \
    && test -d /opt/nltk_data/corpora/words

ENV NLTK_DATA=/opt/nltk_data \
    NLTK_DOWNLOADER_FORCE_INTERACTIVE_SHELL=false
