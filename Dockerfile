FROM python:3-alpine


ENV APP_HOME /app
ENV WORKDIR /workdir
ENV PATH $PATH:$APP_HOME
ENV PYTHONUNBUFFERED=1

COPY requirements.txt requirements.txt
#RUN apk add --no-cache build-base postgresql-libs libxml2-dev libxslt-dev postgresql-dev && \
RUN    pip install --trusted-host '*' --no-cache-dir -r requirements.txt && rm requirements.txt
#    apk del build-base

COPY docker-entrypoint.sh /

COPY syncd.py $APP_HOME/

WORKDIR $WORKDIR
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["syncd.py"]