FROM python:3.10-bookworm

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt upgrade -y && \
    apt install -y \
        git \
        curl \
        python3-pip \
        ffmpeg \
        wget \
        bash \
        neofetch \
        software-properties-common \
        libglib2.0-0 libsm6 libxrender1 libxext6 libmediainfo0v5 && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip3 install --no-cache-dir wheel && \
    pip3 install --no-cache-dir -r requirements.txt

WORKDIR /app

COPY . .

EXPOSE 5000

CMD ["python3", "-m", "devgagan"]
