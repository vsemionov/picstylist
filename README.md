# Pic Stylist

## Prerequisites
 - Before deploying, create the /opt/picstylist/etc/nginx/ssl directory and put server.pem and server.key in it. The key file should be root owned with mode 600.
 - Put the client certificate in conf/ssl/client.pem.

## Resources
 - Digital Ocean
 - Cloudflare

### Tech Notes
 - Self-signed SSL certificate generator for development: https://www.samltool.com/self_signed_certs.php
   - must set key size to 2048 bits to prevent nginx error
 - Cloudflare authenticated origin pulls: https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/set-up/zone-level/
