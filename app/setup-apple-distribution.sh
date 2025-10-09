#!/bin/bash

# Apple Distribution Setup Script
# This script helps you set up your environment for Apple distribution

set -e

echo "🍎 Apple Distribution Setup Script"
echo "=================================="

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script must be run on macOS"
    exit 1
fi

# Check if Xcode is installed
if ! command -v xcodebuild &> /dev/null; then
    echo "❌ Xcode is not installed. Please install Xcode from the Mac App Store."
    exit 1
fi

echo "✅ Xcode is installed"

# Check if we're in the right directory
if [ ! -f "tutor.spec" ]; then
    echo "❌ Please run this script from the app/ directory"
    exit 1
fi

echo "✅ Running from correct directory"

# Create configuration file if it doesn't exist
if [ ! -f "Apple-Developer-Config.env" ]; then
    if [ -f "Apple-Developer-Config.env.example" ]; then
        cp Apple-Developer-Config.env.example Apple-Developer-Config.env
        echo "✅ Created Apple-Developer-Config.env from template"
        echo "⚠️  Please edit Apple-Developer-Config.env with your actual Apple Developer details"
    else
        echo "❌ Apple-Developer-Config.env.example not found"
        exit 1
    fi
else
    echo "✅ Apple-Developer-Config.env already exists"
fi

# Check if Python dependencies are installed
echo "📦 Checking Python dependencies..."

if ! python3 -c "import dotenv" 2>/dev/null; then
    echo "Installing python-dotenv..."
    pip3 install python-dotenv
    echo "✅ Installed python-dotenv"
else
    echo "✅ python-dotenv is already installed"
fi

# Check if PyInstaller is installed
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo "Installing PyInstaller..."
    pip3 install PyInstaller
    echo "✅ Installed PyInstaller"
else
    echo "✅ PyInstaller is already installed"
fi

# Make build script executable
chmod +x build-apple-distribution.py
echo "✅ Made build script executable"

# Check for required certificates
echo "🔐 Checking for code signing certificates..."

# Check for Developer ID Application certificate
if security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
    echo "✅ Developer ID Application certificate found"
else
    echo "⚠️  Developer ID Application certificate not found"
    echo "   You'll need this for direct distribution (outside App Store)"
    echo "   Create it in Xcode > Preferences > Accounts > Manage Certificates"
fi

# Check for Mac App Store certificate
if security find-identity -v -p codesigning | grep -q "Mac App Store"; then
    echo "✅ Mac App Store certificate found"
else
    echo "⚠️  Mac App Store certificate not found"
    echo "   You'll need this for App Store distribution"
    echo "   Create it in Xcode > Preferences > Accounts > Manage Certificates"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit Apple-Developer-Config.env with your Apple Developer details"
echo "2. Create your app record in App Store Connect"
echo "3. Run: python3 build-apple-distribution.py --mode direct"
echo ""
echo "For detailed instructions, see: APPLE_DEVELOPER_SETUP.md"
