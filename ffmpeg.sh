#!/bin/bash
# Install FFmpeg for video processing

if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    sudo apt-get update
    sudo apt-get install -y ffmpeg
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    brew install ffmpeg
else
    echo "Please install FFmpeg manually for your OS"
fi

echo "FFmpeg installation complete!"
