FROM python:3.7

# Create a group and user
RUN addgroup websocket-service && useradd -g websocket-service websocket-service

WORKDIR /opt/funcx-websocket-service

# copy over this package and install
RUN pip install -U pip
COPY . /opt/funcx-websocket-service
RUN pip install .

USER websocket-service
EXPOSE 6000
CMD bash entrypoint.sh
