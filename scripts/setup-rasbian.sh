# This script is not really executable. It's a series of notes on how the
# Raspberry Pi Zero W was setup for our purposes.

raspi-config
# setup wifi to connect to the correct SSID with password
# enable SSH
# enable login of just console and require or not require password
# setup locality to en-us not en-gb
# setup audio to work on 3.5mm jack not HDMI

# for audio injector
wget https://github.com/Audio-Injector/stereo-and-zero/raw/master/audio.injector.scripts_0.1-1_all.deb
sudo dpkg -i audio.injector.scripts_0.1-1_all.deb

sudo reboot now

# run one of these
# A)
#alsactl --file /usr/share/doc/audioInjector/asound.state.MIC.thru.test restore
# B)
alsactl --file /usr/share/doc/audioInjector/asound.state.RCA.thru.test restore

sudo apt-get install sox
audioInjector-test.sh # must run in xserver

# Install seren
sudo apt-get update
sudo apt-get install build-essential libasound2-dev libopus-dev libogg-dev libgmp-dev libncursesw5-dev git
git clone https://github.com/ParrotSec/seren.git
cd seren
./configure
make

# Turn off wireless power management
sudo vi /etc/rc.local
# Add this line iwconfig wlan0 power off
sudo reboot now
iwconfig # check that power management is off

# Test audio
aplay --list-devices
aplay --device plughw:1,0 /usr/share/sounds/alsa/Front_Center.wav
