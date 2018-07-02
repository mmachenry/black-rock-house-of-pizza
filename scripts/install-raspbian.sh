# Reminder on how to write raspbian to the SD card. Take from:
# https://www.raspberrypi.org/documentation/installation/installing-images/linux.md
lsblk
umount /dev/sda1
sudo dd bs=4M if=2018-04-18-raspbian-stretch.img of=/dev/sda status=progress conv=fsync
