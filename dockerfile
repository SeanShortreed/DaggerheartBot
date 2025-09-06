FROM python:3.11-slim

# Metadata
LABEL maintainer="seanshortreed@gmail.com"
LABEL org.opencontainers.image.description="Discord bot for daggerheart organisation"
LABEL org.opencontainers.image.source="https://github.com/SeanShortreed/DaggerheartBot"

# Install git for potential updates
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY bot.py .
COPY tags_data.py .
COPY posts_data.py .

# Create directories for persistent data
RUN mkdir -p /config /logs /data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "print('healthy')" || exit 1

# Run the bot
CMD ["python", "-u", "bot.py"]