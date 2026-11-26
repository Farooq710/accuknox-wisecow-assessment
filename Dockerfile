FROM debian:bookworm-slim

# Install application dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    fortune-mod \
    fortunes-min \
    cowsay \
    socat \
    && rm -rf /var/lib/apt/lists/*

# Add fortune and cowsay to PATH
ENV PATH="/usr/games:${PATH}"

# Create a dedicated non-root user
RUN groupadd --gid 10001 wisecow && \
    useradd --uid 10001 --gid 10001 --no-create-home wisecow

# Set application working directory
WORKDIR /app

# Copy application source code
COPY --chown=10001:10001 wisecow.sh .

# Configure application permissions
RUN chmod 755 wisecow.sh && \
    chown 10001:10001 /app

# Run application as non-root user
USER 10001:10001

# Expose application port
EXPOSE 4499

# Start Wisecow application
CMD ["./wisecow.sh"]
