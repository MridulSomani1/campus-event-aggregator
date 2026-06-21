FROM python:3.9

# Create a non-root user (Hugging Face Spaces requires uid 1000).
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Install Python dependencies first to leverage Docker layer caching.
COPY --chown=user requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application.
COPY --chown=user . .

# Hugging Face Spaces expects the app on port 7860.
EXPOSE 7860

CMD ["python", "app.py"]
