"""
Apple Distribution Build Script for Tutor App

This script automates the process of building, signing, notarizing, and uploading
the Tutor app to Apple's distribution systems (App Store or direct distribution).

Prerequisites:
1. Apple Developer Program membership
2. Xcode installed
3. Apple Developer certificates installed in Keychain
4. App Store Connect API key (for automated uploads)

Usage:
    python build-apple-distribution.py --mode [app-store|direct]
"""

import os
import sys
import subprocess
import argparse
import shutil
import zipfile
from pathlib import Path
from dotenv import load_dotenv

def load_config():
    """Load Apple Developer configuration from environment file"""
    config_file = Path(__file__).parent / "Apple-Developer-Config.env"
    if not config_file.exists():
        print(f"❌ Configuration file not found: {config_file}")
        print("Please copy Apple-Developer-Config.env.example to Apple-Developer-Config.env")
        print("and fill in your Apple Developer Program details.")
        sys.exit(1)
    
    load_dotenv(config_file)
    
    required_vars = [
        'APPLE_TEAM_ID',
        'APPLE_DEVELOPER_EMAIL', 
        'CODE_SIGN_IDENTITY',
        'BUNDLE_IDENTIFIER'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Missing required configuration: {', '.join(missing_vars)}")
        print("Please update your Apple-Developer-Config.env file.")
        sys.exit(1)
    
    return {
        'team_id': os.getenv('APPLE_TEAM_ID'),
        'email': os.getenv('APPLE_DEVELOPER_EMAIL'),
        'code_sign_identity': os.getenv('CODE_SIGN_IDENTITY'),
        'bundle_id': os.getenv('BUNDLE_IDENTIFIER'),
        'api_key_id': os.getenv('APP_STORE_CONNECT_API_KEY_ID'),
        'api_issuer_id': os.getenv('APP_STORE_CONNECT_ISSUER_ID'),
        'api_key_path': os.getenv('APP_STORE_CONNECT_API_KEY_PATH'),
        'app_id': os.getenv('APP_STORE_CONNECT_APP_ID')
    }

def run_command(cmd, description):
    """Run a shell command and handle errors"""
    print(f"🔄 {description}...")
    print(f"   Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"   Error: {e.stderr.strip()}")
        if e.stdout:
            print(f"   Output: {e.stdout.strip()}")
        sys.exit(1)

def clean_build_directories():
    """Clean previous build artifacts"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"🧹 Cleaning {dir_name}/")
            shutil.rmtree(dir_name)

def build_app():
    """Build the app using PyInstaller"""
    print("🔨 Building Tutor app with PyInstaller...")
    
    # Ensure we're in the app directory
    app_dir = Path(__file__).parent
    os.chdir(app_dir)
    
    # Run PyInstaller
    cmd = ['python', '-m', 'PyInstaller', 'tutor.spec', '--clean']
    run_command(cmd, "PyInstaller build")

def sign_and_notarize_app(config, mode):
    """Sign and notarize the app bundle"""
    app_path = "dist/Tutor.app"
    
    if not os.path.exists(app_path):
        print(f"❌ App bundle not found: {app_path}")
        sys.exit(1)
    
    # Sign the app
    print(f"🔐 Signing app with identity: {config['code_sign_identity']}")
    sign_cmd = [
        'codesign',
        '--force',
        '--verify',
        '--verbose',
        '--sign', config['code_sign_identity'],
        '--options', 'runtime',
        '--entitlements', 'entitlements.plist',
        app_path
    ]
    run_command(sign_cmd, "Code signing")
    
    # Verify signature
    verify_cmd = ['codesign', '--verify', '--verbose', app_path]
    run_command(verify_cmd, "Signature verification")
    
    if mode == 'direct':
        # Create a zip file for notarization
        zip_path = "dist/Tutor.zip"
        print(f"📦 Creating zip file for notarization: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(app_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_path = os.path.relpath(file_path, os.path.dirname(app_path))
                    zipf.write(file_path, arc_path)
        
        # Submit for notarization
        notarize_cmd = [
            'xcrun', 'notarytool', 'submit',
            zip_path,
            '--apple-id', config['email'],
            '--team-id', config['team_id'],
            '--wait'
        ]
        
        if config['api_key_id'] and config['api_issuer_id'] and config['api_key_path']:
            # Use API key authentication
            notarize_cmd.extend([
                '--key', config['api_key_path'],
                '--key-id', config['api_key_id'],
                '--issuer', config['api_issuer_id']
            ])
        
        run_command(notarize_cmd, "Notarization submission")
        
        # Staple the notarization ticket
        staple_cmd = ['xcrun', 'stapler', 'staple', app_path]
        run_command(staple_cmd, "Stapling notarization ticket")
        
        print(f"✅ App ready for direct distribution: {app_path}")
        print(f"✅ Notarized zip file: {zip_path}")

def upload_to_app_store(config):
    """Upload the app to App Store Connect"""
    if not all([config['api_key_id'], config['api_issuer_id'], config['api_key_path']]):
        print("⚠️  App Store Connect API credentials not configured.")
        print("   Skipping automatic upload. You can manually upload using Xcode or Transporter.")
        return
    
    app_path = "dist/Tutor.app"
    
    # Upload using altool (deprecated but still works)
    upload_cmd = [
        'xcrun', 'altool',
        '--upload-app',
        '--type', 'macos',
        '--file', app_path,
        '--apiKey', config['api_key_id'],
        '--apiIssuer', config['api_issuer_id']
    ]
    
    run_command(upload_cmd, "App Store Connect upload")
    print("✅ App uploaded to App Store Connect")

def create_distribution_package(mode):
    """Create the final distribution package"""
    if mode == 'direct':
        # For direct distribution, we already have the notarized zip
        source_zip = "dist/Tutor.zip"
        final_zip = f"dist/Tutor-{mode}-mac.zip"
        
        if os.path.exists(source_zip):
            shutil.copy2(source_zip, final_zip)
            print(f"✅ Direct distribution package: {final_zip}")
        else:
            print(f"❌ Source zip not found: {source_zip}")
    
    elif mode == 'app-store':
        # For App Store, the .app bundle is ready
        app_path = "dist/Tutor.app"
        if os.path.exists(app_path):
            print(f"✅ App Store bundle ready: {app_path}")
        else:
            print(f"❌ App bundle not found: {app_path}")

def main():
    parser = argparse.ArgumentParser(description='Build Tutor app for Apple distribution')
    parser.add_argument('--mode', choices=['app-store', 'direct'], required=True,
                       help='Distribution mode: app-store or direct')
    parser.add_argument('--clean-only', action='store_true',
                       help='Only clean build directories')
    
    args = parser.parse_args()
    
    if args.clean_only:
        clean_build_directories()
        print("✅ Build directories cleaned")
        return
    
    print(f"🚀 Building Tutor app for {args.mode} distribution")
    
    # Load configuration
    config = load_config()
    print(f"📋 Using bundle ID: {config['bundle_id']}")
    print(f"📋 Using team ID: {config['team_id']}")
    
    # Clean and build
    clean_build_directories()
    build_app()
    
    # Sign and notarize
    sign_and_notarize_app(config, args.mode)
    
    # Upload to App Store Connect if app-store mode
    if args.mode == 'app-store':
        upload_to_app_store(config)
    
    # Create final distribution package
    create_distribution_package(args.mode)
    
    print(f"🎉 Build completed successfully for {args.mode} distribution!")

if __name__ == '__main__':
    main()
