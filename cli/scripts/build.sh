#!/bin/bash

set -e

# Build script for drycc-resources CLI
# Builds binaries for multiple platforms

VERSION=${VERSION:-"dev"}
OUTPUT_DIR="_dist"

# Platforms to build for
PLATFORMS=(
    "linux/amd64"
    "linux/arm64"
    "darwin/amd64"
    "darwin/arm64"
    "windows/amd64"
)

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Building drycc-resources CLI version $VERSION"
echo "=========================================="

for platform in "${PLATFORMS[@]}"; do
    IFS='/' read -r GOOS GOARCH <<< "$platform"
    
    output_name="drycc-resources-${VERSION}-${GOOS}-${GOARCH}"
    if [ "$GOOS" = "windows" ]; then
        output_name="${output_name}.exe"
    fi
    
    echo "Building for ${GOOS}/${GOARCH}..."
    
    GOOS=$GOOS GOARCH=$GOARCH go build \
        -ldflags "-X main.version=$VERSION" \
        -o "${OUTPUT_DIR}/${output_name}" \
        .
    
    echo "  -> ${OUTPUT_DIR}/${output_name}"
done

echo ""
echo "Build complete! Binaries are in ${OUTPUT_DIR}/"
ls -lh "$OUTPUT_DIR"
