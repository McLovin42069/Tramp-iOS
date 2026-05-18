#!/bin/bash
set -e

echo "=========================================="
echo "Tramp iOS Code Signing Setup Helper"
echo "=========================================="
echo ""
echo "This script helps convert your Apple"
echo "Developer certificate to the format"
echo "Codemagic needs (.p12)."
echo ""

# Check if .cer file exists
CER_FILE=""
for f in ~/Desktop/*.cer; do
    if [ -f "$f" ]; then
        CER_FILE="$f"
        break
    fi
done

if [ -z "$CER_FILE" ]; then
    echo "❌ No .cer file found on Desktop."
    echo ""
    echo "Please download your Apple Distribution"
    echo "certificate from the Apple Developer Portal"
    echo "and save it to your Desktop."
    echo ""
    echo "Steps:"
    echo "1. Go to developer.apple.com/account/resources/certificates/list"
    echo "2. Click '+' → Apple Distribution"
    echo "3. Upload Tramp.certSigningRequest"
    echo "4. Download the .cer file to Desktop"
    exit 1
fi

echo "✅ Found certificate: $(basename "$CER_FILE")"
echo ""

# Check if private key exists
KEY_FILE=""
for f in ~/Desktop/*.key; do
    if [ -f "$f" ]; then
        KEY_FILE="$f"
        break
    fi
done

if [ -z "$KEY_FILE" ]; then
    echo "❌ No .key file found on Desktop."
    echo "The private key should have been generated"
    echo "along with the CSR (Tramp.key)."
    exit 1
fi

echo "✅ Found private key: $(basename "$KEY_FILE")"
echo ""

# Ask for .p12 password
echo "Enter a password for the .p12 export file."
echo "(You'll need this when uploading to Codemagic)"
read -s -p "Password: " P12_PASSWORD
echo ""

# Create output directory
OUTPUT_DIR="$HOME/Desktop/Tramp_Signing_Files"
mkdir -p "$OUTPUT_DIR"

# Convert to .p12
echo ""
echo "🔧 Converting certificate to .p12..."
openssl pkcs12 -export \
    -in "$CER_FILE" \
    -inkey "$KEY_FILE" \
    -out "$OUTPUT_DIR/Tramp_Distribution.p12" \
    -passout pass:"$P12_PASSWORD"

echo "✅ Created: Tramp_Distribution.p12"
echo ""

# Copy .mobileprovision files if found
echo "📋 Looking for provisioning profiles..."
FOUND_PROV=0
for f in ~/Desktop/*.mobileprovision; do
    if [ -f "$f" ]; then
        cp "$f" "$OUTPUT_DIR/"
        echo "✅ Copied: $(basename "$f")"
        FOUND_PROV=1
    fi
done

if [ $FOUND_PROV -eq 0 ]; then
    echo "⚠️  No .mobileprovision files found on Desktop."
    echo "   Download them from Apple Developer Portal:"
    echo "   - Tramp Ad Hoc (for device installation)"
    echo "   - Tramp App Store (for TestFlight)"
fi

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Files ready for Codemagic:"
ls -la "$OUTPUT_DIR/"
echo ""
echo "Next steps:"
echo "1. Go to codemagic.io → your Tramp project"
echo "2. Click 'Settings' → 'Code signing identities'"
echo "3. Upload: Tramp_Distribution.p12"
echo "   (use password: $P12_PASSWORD)"
echo "4. Upload: any .mobileprovision files"
echo "5. Push to GitHub to trigger a signed build!"
echo ""
