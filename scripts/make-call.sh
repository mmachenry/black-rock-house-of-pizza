# Test script to setup an auto accept seren session with a USB sound card.
seren -NS -n handset -C 0 -d plughw:1,0 -D plughw:1,0 -a
