FROM python:3.10-bullseye

COPY . /opt/mc_openapi

RUN useradd -mU mc
USER mc
ENV PATH="/home/mc/.local/bin:${PATH}"
RUN pip install --upgrade pip \
    && pip install -r /opt/mc_openapi/requirements.txt
WORKDIR /opt/mc_openapi

CMD ["uvicorn", "--port", "80", "--host", "0.0.0.0", "--interface", "wsgi", "mc_openapi.app_config:app"]
