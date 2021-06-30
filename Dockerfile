FROM python:3.7 as base

# Create a group and user
RUN addgroup websocket-service && useradd -g websocket-service websocket-service

WORKDIR /opt/funcx-websocket-service

# copy over this package and install
RUN pip install -U pip
COPY . /opt/funcx-websocket-service
RUN pip install .

# build: docker build -t <tag> --target build .
FROM base as build
USER websocket-service
EXPOSE 6000
CMD bash entrypoint.sh

# run tests with: docker build -t <tag> --target test .
# test must come after build because we don't want the additional test requirements
# as part of a non-testing build
FROM base as test
RUN pip install -r test-requirements.txt
RUN pytest funcx_websocket_service/tests
