#!/bin/bash
# Build Lambda Layer using Docker

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"

echo "🔨 Building Lambda Layer..."

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Build Docker image
echo "📦 Building Docker image..."
docker build -t accommodation-scraper-layer "${SCRIPT_DIR}"

# Run container to extract layer.zip
echo "📤 Extracting layer.zip..."
docker run --rm -v "${OUTPUT_DIR}:/output" accommodation-scraper-layer

# Check result
if [ -f "${OUTPUT_DIR}/layer.zip" ]; then
    echo "✅ Layer built successfully: ${OUTPUT_DIR}/layer.zip"
    ls -lh "${OUTPUT_DIR}/layer.zip"
else
    echo "❌ Failed to build layer"
    exit 1
fi
