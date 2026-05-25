#!/usr/bin/env bash
# Script to automatically query and update Cloudflare WARP version in PKGBUILDs

# Exit on error
set -e

# Change to project root directory
cd "$(dirname "$0")/.."

echo "Querying latest Cloudflare WARP version from noble repository..."
LATEST_WARP=$(curl -s https://pkg.cloudflareclient.com/dists/noble/main/binary-amd64/Packages | awk -F': ' '/^Version:/ {print $2}')

if [ -z "$LATEST_WARP" ]; then
    echo "Error: Could not retrieve Cloudflare WARP version."
    exit 1
fi

echo "Latest version found: $LATEST_WARP"

# Update PKGBUILD
echo "Updating PKGBUILD..."
sed -i "s/_warpver=.*/_warpver=${LATEST_WARP}/" PKGBUILD

# Update PKGBUILD.local
echo "Updating PKGBUILD.local..."
sed -i "s/_warpver=.*/_warpver=${LATEST_WARP}/" PKGBUILD.local

# Re-run updpkgsums for both files
echo "Updating checksums for PKGBUILD..."
updpkgsums PKGBUILD

echo "Updating checksums for PKGBUILD.local..."
updpkgsums PKGBUILD.local

# Regenerate .SRCINFO
echo "Regenerating .SRCINFO..."
makepkg --printsrcinfo > .SRCINFO

echo "Cloudflare WARP update completed successfully!"
