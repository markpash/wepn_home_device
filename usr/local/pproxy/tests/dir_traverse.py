import os
#prevent directory traversal attacks by checking final path
def get_vpn_file(username):
    basedir = "/var/local/pproxy/"
    vpn_file = basedir + username + ".ovpn"
    if os.path.abspath(vpn_file).startswith(basedir):
        return vpn_file
    else:
        return None

print(get_vpn_file('abc.efg'))
print(get_vpn_file('/../../../../global_openvpn_config'))
