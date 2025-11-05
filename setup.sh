#!/bin/bash

# YouTube Video Automation - Quick Setup Script
# This script helps you get started quickly with the automation pipeline

set -e  # Exit on any error

echo "🚀 YouTube Video Automation Setup"
echo "=================================="
echo

# Check Python version
echo "📋 Checking Python version..."
python3 --version || {
    echo "❌ Python 3 is required but not found"
    echo "Please install Python 3.8 or higher"
    exit 1
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Please run this script from the video automation directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p videos/input videos/processed logs config docs

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env configuration file..."
    cp .env.example .env
    echo "📝 Please edit .env file with your Google API credentials"
else
    echo "✅ .env file already exists"
fi

# Make main.py executable
chmod +x main.py

echo
echo "✅ Setup completed!"
echo
echo "Next steps:"
echo "1. Edit .env file with your Google API credentials"
echo "2. Follow docs/SETUP_GUIDE.md to configure YouTube API"
echo "3. Run: python main.py status"
echo
echo "Quick commands:"
echo "  python main.py status          # Check system status"
echo "  python main.py monitor         # Start continuous monitoring"
echo "  python main.py schedule -i 30  # Check every 30 minutes"
echo
echo "📖 See README.md for detailed documentation"