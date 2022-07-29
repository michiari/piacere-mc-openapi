FROM python:3.9.12-bullseye

COPY . /opt/mc_openapi

RUN useradd -mU mc
USER mc
ENV PATH="/home/mc/.local/bin:${PATH}"
RUN pip install -r /opt/mc_openapi/requirements.txt
WORKDIR /opt/mc_openapi

CMD ["uwsgi", "--http", ":80", "--yaml", "uwsgi_config.yaml"]
