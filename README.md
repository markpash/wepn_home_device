Scripts that run on the Raspberry Pi clients.

Our debian package is not completely standard now (it changes settings from other packages), but we are moving towards allowing users to bring their own devices.

## Changes in Structure

We moved from OpenVPN to OpenVPN+sTuennl to ShadowSocks. We may have to add ShadowSocks+OpenVPN if clients start supporting it. As a result, some of the files in this folder are not currently in use but will be re-activated.

This folder is used to generate the APT package. Main WEPN files are located under usr/local/pproxy


