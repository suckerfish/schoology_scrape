#!/bin/bash
# Docker build and test script for Schoology Grade Scraper

set -e  # Exit on any error

echo "🐳 Building Schoology Grade Scraper Docker image..."

# Create required directories
echo "📁 Creating required directories..."
mkdir -p data logs

# Build the Docker image
echo "🔨 Building Docker image..."
docker compose build

# Test the image
echo "🧪 Testing Docker image..."

# Test 1: Check Chromium installation
echo "  ✅ Testing Chromium installation..."
docker compose run --rm schoology-scraper chromium --version --headless --no-sandbox

# Test 2: Check Python dependencies
echo "  ✅ Testing Python dependencies..."
docker compose run --rm schoology-scraper python -c "
import selenium
import boto3
import streamlit
import deepdiff
import google.generativeai
print('✅ All Python dependencies loaded successfully')
"

# Test 3: Check application can import
echo "  ✅ Testing application imports..."
docker compose run --rm schoology-scraper python -c "
from pipeline.orchestrator import GradePipeline
from pipeline.scraper import GradeScraper
from shared.config import get_config
print('✅ Application imports successful')
"

echo "🎉 Docker build and basic tests completed successfully!"
echo ""
echo "Next steps:"
echo "1. Ensure your .env file contains all required credentials"
echo "2. Test with: docker-compose up"
echo "3. For scheduled runs: docker-compose --profile scheduler up -d"
echo ""
echo "Monitor with:"
echo "  docker-compose logs -f"
echo "  docker stats"