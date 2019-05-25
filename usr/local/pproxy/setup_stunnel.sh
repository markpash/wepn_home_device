openssl genrsa -out key.pem 2048
openssl req -new -x509 -key key.pem -out cert.pem -days 1095
cat key.pem cert.pem >> /etc/stunnel/stunnel.pem
cp stunnel.conf /etc/stunnel/
echo "ENABLED=1 in /etc/default/stunnel4"
