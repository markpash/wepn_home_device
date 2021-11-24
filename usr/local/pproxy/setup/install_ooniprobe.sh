sudo apt-key adv --verbose --keyserver hkp://keyserver.ubuntu.com --recv-keys 'B5A08F01796E7F521861B449372D1FF271F2DD50'
echo "deb http://deb.ooni.org/ unstable main" | sudo tee /etc/apt/sources.list.d/ooniprobe.list
sudo apt-get update
sudo apt-get install ooniprobe-cli

# ooniprobe has a smart onboarding, evem in cli,
# which takes a quiz of the information
# we can bypass it by --yes BUT only if we got consent by proxy
# in our WEPN mobile app
# below line is just for reference
# has to be done by user running the process
# ooniprobe onboard --yes

