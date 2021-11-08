## WEPN Pod Package


[WEPN](https://we-pn.com) allows running various VPN and tunnel servers from a Raspberry Pi hosted at your home. It requires our 3 branches of software: code in this repo on the RPi Pod;
 credentials for our server; and the mobile app on your phone. Each of these 3 packages are hosted in their own repositories: [source.we-pn.com](https://source.we-pn.com)
 
For full transparency and easier debugging, the entire file structure for the Debian package is listed here.


Our debian package is not completely standard now (it changes settings from other packages), but we are moving to clean things up. 
While a more tech savvy user can run other software on the RPi as well as WEPN, we must caution that WEPN could potentially interfere with some settings and customizations.

For more information:

- health of our server/software, based on daliy self tests on live device: [status.we-pn.com](https://status.we-pn.com)

- our design docs folder: [go.we-pn.com/design-docs](https://go.we-pn.com/design-docs)

- manual for brining your own device (needs credentials from our server): [go.we-pn.com/byod](https://go.we-pn.com/byod)

## Supported Applications

Our current main application is **Shadowsocks**. We started from **OpenVPN**, added **Stunnel** to wrap the OpenVPN in it. These are disabled now since there are limintations to their usage.
We are also in the process of adding **Tor**, **OONI**, and **WireGuard**.

Through our mobile app, the owner of the Pod (Provider) can decide who has access, and which of these apps these end users can utilize.

