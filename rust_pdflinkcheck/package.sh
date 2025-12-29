#!/bin/bash
# package.sh
DEST="dist_pdflinkcheck"
mkdir -p $DEST

# Build with relative library pathing
RUSTFLAGS="-C link-arg=-Wl,-rpath,\$ORIGIN" cargo build --release

# Copy necessary files
cp target/release/rust_pdflinkcheck $DEST/
cp libpdfium.so $DEST/
cp README.md $DEST/

tar -czvf pdflinkcheck-linux-x64.tar.gz $DEST/
echo "Package ready: pdflinkcheck-linux-x64.tar.gz"
