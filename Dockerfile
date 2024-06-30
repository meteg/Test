# Base image olarak Python 3.9 kullanıyoruz
FROM python:3.9

# Çalışma dizinini oluşturuyoruz
WORKDIR /app

# Gereken dosyaları çalışma dizinine kopyalıyoruz
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Geri kalan dosyaları kopyalıyoruz
COPY . .

# Ortam değişkenlerini belirtiyoruz
ENV SENSOR_CONFIG_PATH=sensor.yaml
ENV MQTT_BROKER=mqtt.ndx.com.tr
ENV MQTT_PORT=1883
ENV MQTT_USERNAME=ndx
ENV MQTT_PASSWORD=ndx
ENV MODBUS_HOST=172.16.70.1
ENV MODBUS_PORT=5050

# Programı çalıştırıyoruz
CMD ["python", "main.py"]
