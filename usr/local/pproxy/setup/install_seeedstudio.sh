aplay -l | grep seeed &> /dev/null
if [ $? == 0 ]; then
   echo "SeeedStudio already installed"
else
   echo "installing seeedstudio, restarted needed after"
   git clone https://github.com/respeaker/seeed-voicecard.git
   cd seeed-voicecard
   ./install.sh
   cd ..
fi
