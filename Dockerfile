FROM python:3.7

# Create a group and user
RUN addgroup uwsgi && useradd -g uwsgi uwsgi

WORKDIR /opt/funcx-ws

COPY ./requirements.txt .

RUN pip install -r requirements.txt
# RUN pip install --disable-pip-version-check uwsgi

# COPY uwsgi.ini .
COPY ./funcx_ws/ ./funcx_ws/
COPY run.py .

USER uwsgi
EXPOSE 6000

CMD [ "python", "./run.py" ]
# CMD sh web-entrypoint.sh
