FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y libltdl7 libkrb5-3 libgssapi-krb5-2 && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /usr/src/app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

ENTRYPOINT [ "python", "-m" , "main"]