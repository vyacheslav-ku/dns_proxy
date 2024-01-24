FROM python:3.10-slim-bullseye as python
#  prevents python from buffering logs before printout to stderr stdout
ENV PYTHONUNBUFFERED=true
# prevents python from creating pyc files
ENV PYTHONDONTWRITEBYTECODE=true
WORKDIR /app
RUN apt-get update && apt-get install -y iptables curl default-mysql-client nano && rm -fr /var/lib/apt/lists/*

FROM python as poetry
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN python -c 'from urllib.request import urlopen; print(urlopen("https://install.python-poetry.org").read().decode())' | python -
COPY . ./
RUN poetry install --no-interaction --no-ansi -vvv



FROM python as runtime
ENV PATH="/app/.venv/bin:$PATH"
COPY --from=poetry /app /app
EXPOSE 8000
WORKDIR /app/
CMD python proxy_dns.py

#HEALTHCHECK CMD http://localhost:8000/app_health