FROM python:3.10-bullseye

COPY . /opt/mc_openapi

RUN useradd -mU mc
USER mc
ENV PATH="/home/mc/.local/bin:${PATH}"
RUN pip install --upgrade pip \
    && pip install -r /opt/mc_openapi/requirements.txt
WORKDIR /opt/mc_openapi

ENV UVICORN_PORT=8080 \
    UVICORN_HOST=0.0.0.0

CMD ["uvicorn", "--interface", "wsgi", "mc_openapi.app_config:app"]
