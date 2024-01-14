# Pic Stylist

## Prerequisites
 - Before deploying, create the conf/ssl directory and put server.pem and server.key in it. The key file should be root owned with mode 600.

## Resources
 - Digital Ocean
 - Cloudflare

### Tech Notes
 - Self-signed SSL certificate generator for development: https://www.samltool.com/self_signed_certs.php
   - must set key size to 2048 bits to prevent nginx error
