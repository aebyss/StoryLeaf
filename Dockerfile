FROM docker.io/library/python:3.12-slim
WORKDIR /app
COPY server.py .
COPY public ./public
RUN useradd --uid 10001 --create-home app && mkdir /data && chown app:app /data
USER app
EXPOSE 8080
CMD ["python", "server.py"]
