#!/usr/bin/env bash
# Create the throwaway AVD this rig runs on.
#
# avdmanager needs a JDK that this project does not otherwise need, so the AVD
# is written by hand: an AVD is a directory with a config.ini and a pointer
# file, nothing more. The emulator creates the disk images on first boot.
source "$(dirname "$0")/lib.sh"

IMAGE_DIR="$SDK/$SYSTEM_IMAGE"
[ -d "$IMAGE_DIR" ] || {
    echo "System image missing: $IMAGE_DIR" >&2
    echo "Install it with: sdkmanager \"${SYSTEM_IMAGE%/}\"" >&2
    echo "(replace system-images/ with system-images; and / with ; in the name)" >&2
    exit 1
}

if [ -d "$AVD_DIR" ]; then
    echo "$AVD_NAME already exists at $AVD_DIR — nothing to do."
    exit 0
fi

mkdir -p "$AVD_DIR"
cat > "$AVD_HOME/$AVD_NAME.ini" <<EOF
avd.ini.encoding=UTF-8
path=$AVD_DIR
path.rel=avd/$AVD_NAME.avd
target=$API_TARGET
EOF

# A box-shaped profile: 2 GB, 800x480 landscape at 160 dpi, no camera.
# Cold boot every time, because a restored snapshot would hide boot problems.
cat > "$AVD_DIR/config.ini" <<EOF
avd.id=$AVD_NAME
avd.name=$AVD_NAME
avd.ini.encoding=UTF-8
abi.type=arm64-v8a
hw.cpu.arch=arm64
hw.cpu.ncore=4
hw.ramSize=2048
vm.heapSize=192M
image.sysdir.1=$SYSTEM_IMAGE
tag.id=google_apis_playstore
tag.ids=google_apis_playstore
tag.display=Google Play
target=$API_TARGET
PlayStore.enabled=no
disk.cachePartition=yes
disk.cachePartition.size=66MB
disk.dataPartition.size=6G
hw.lcd.width=800
hw.lcd.height=480
hw.lcd.density=160
hw.lcd.depth=32
hw.initialOrientation=landscape
hw.screen=multi-touch
hw.keyboard=yes
hw.gpu.enabled=no
hw.gpu.mode=auto
hw.audioInput=no
hw.audioOutput=no
hw.camera.back=none
hw.camera.front=none
hw.gps=no
hw.sdCard=yes
sdcard.size=128 MB
hw.device.name=pixel_7
hw.device.manufacturer=Google
hw.useext4=yes
fastboot.forceColdBoot=yes
fastboot.forceFastBoot=no
firstboot.bootFromDownloadableSnapshot=no
firstboot.bootFromLocalSnapshot=no
kernel.newDeviceNaming=autodetect
kernel.supportsYaffs2=autodetect
EOF

echo "Created $AVD_NAME at $AVD_DIR"
echo "Start it with tests/emu/start.sh"
