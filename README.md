# PicStylist

## Resources
 - Digital Ocean
 - Cloudflare
 - Sentry
 - Portainer (optional)

### Tech notes
 - Cloudflare authenticated origin pulls: https://developers.cloudflare.com/ssl/origin-configuration/authenticated-origin-pull/set-up/zone-level/
 - Cloudflare prepend www to root domain: https://developers.cloudflare.com/rules/url-forwarding/single-redirects/examples/#redirect-all-requests-to-a-different-hostname
 - Portainer installation: https://docs.portainer.io/start/install-ce/server/docker/linux

### Local deployment
 - link .env to .env.dev
 - link compose.override.yaml to compose.override-dev.yaml
 - run `bin/deploy`

### Production deployment
 - configure a new vm via host/cloud-config.yaml
 - push main branch of this repo to victor@<vm_addr>:/opt/picstylist.git
 - push main branch of picstylist-config to victor@<vm_addr>:/opt/picstylist-config.git
