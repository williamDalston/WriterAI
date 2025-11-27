#!/bin/bash

# WriterAI Launcher

echo "🚀 Starting WriterAI..."

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "⬇️ Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Start the application
echo "✨ Launching Web Server & Real-Time Engine..."
echo "🌐 Dashboard: http://localhost:8080"
export PYTHONPATH=$PYTHONPATH:$(pwd)/prometheus_novel
python3 -m prometheus_novel.interfaces.web.app

# Deactivate on exit
deactivate
