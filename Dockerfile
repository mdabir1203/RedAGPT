FROM python:3.11-slim


WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget \
    && wget -O /usr/local/bin/dumb-init https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_x86_64 \
    && chmod +x /usr/local/bin/dumb-init \
    && apt-get purge -y --auto-remove wget \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Copy dependency manifests first to leverage Docker layer caching
COPY requirements.txt ./

RUN uv venv --python 3.11 /opt/venv \

    && uv pip install --python /opt/venv -r requirements.txt

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Copy the rest of your application code to the container
COPY . .

# Set the entry point for your application
ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]
CMD ["python", "main.py"]
