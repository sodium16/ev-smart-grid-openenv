# Use Python 3.10 slim
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Install git (Keeping this is fine, it's a good system utility)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of your code
COPY . .

# Hugging Face Spaces port
EXPOSE 7860

# Command to run your FastAPI app
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]