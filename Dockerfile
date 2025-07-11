FROM openjdk:17-slim

# Zainstaluj Pythona i potrzebne narzędzia
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    build-essential \
    curl \
    && apt-get clean

# Ustaw alias
RUN ln -s /usr/bin/python3 /usr/bin/python

# Skopiuj i zainstaluj zależności
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false"]