# Add Rust binaries to PATH
export PATH="/usr/local/cargo/bin:${PATH}"

# Cross-compilation environment variables
export CC_armv7_unknown_linux_musleabihf="/usr/bin/arm-linux-gnueabihf-gcc"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_MUSLEABIHF_LINKER="/usr/bin/arm-linux-gnueabihf-gcc"
export CC_armv7_unknown_linux_gnueabihf="/usr/bin/arm-linux-gnueabihf-gcc"
export CARGO_TARGET_ARMV7_UNKNOWN_LINUX_GNUEABIHF_LINKER="/usr/bin/arm-linux-gnueabihf-gcc"
