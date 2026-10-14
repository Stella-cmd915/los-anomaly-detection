FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src /app/src
COPY db /app/db
COPY results /app/results

EXPOSE 8501

CMD ["streamlit", "run", "src/dashboard_app.py", "--server.address=0.0.0.0", "--server.port=8501"]