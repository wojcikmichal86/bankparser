FROM python:3.10-slim

# Zainstaluj Javę i inne zależności
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    curl \
    build-essential \
    && apt-get clean

# Ustaw JAVA_HOME i dodaj do PATH
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Ustaw katalog roboczy
WORKDIR /app

# Zainstaluj zależności Pythona
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Skopiuj cały kod projektu
COPY . .

# Uruchom migracje i serwer Gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn bankparser.wsgi:application --bind 0.0.0.0:8000"]