FROM python:3.7

# Create a group and user
RUN addgroup uwsgi && useradd -g uwsgi uwsgi

WORKDIR /opt/funcx-websocket-service

RUN pip install -U pip
COPY . /opt/funcx-websocket-service
RUN pip install .

# run tests
RUN pip install -r test-requirements.txt
RUN pytest funcx_websocket_service/tests

USER uwsgi
EXPOSE 6000

CMD bash entrypoint.sh
