#!/usr/bin/env python3

import argparse
import base64
import json
import logging
import os
import subprocess
from yaml import load, dump, Loader, Dumper

from utils.vault import vault_login, vault_get_cert, vault_cert_domain
from utils.kubernetes import kubectl, create_tls_secret

LOG_LEVEL = logging.INFO

def dump_config():
    config = {
        "configVersion": "v1",
        "schedule": [
            {
                "name": "Update certs every 12 hours",
                "crontab": "0 */12 * * *",
            },
        ],
    }
    print(json.dumps(config))

def get_cert_fingerprint(cert):
    p = subprocess.Popen(["openssl", "x509", "-noout", "-fingerprint"],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE,
                         text=True)
    out, err = p.communicate(input=cert)
    if p.returncode != 0:
        raise Exception(f"Failed to load cert: {p.returncode} {err}")

    if not out.startswith("SHA1 Fingerprint="):
        raise Exception(f"Error retrieving fingerprint: {out}: {err}")

    return out.strip()

def get_tls_cert_from_secret(secretname, namespace):
    p = kubectl(["get", "secret", secretname], namespace=namespace)
    secret = load(p.stdout, Loader=Loader)
    return base64.b64decode(secret["data"]["tls.crt"]).decode('ascii')

def patch_cert_in_secret(secretname, namespace, cert):
    logging.info(f"Patching {secretname} in namespace {namespace}")
    b64cert = base64.b64encode(cert["cert"].encode("ascii")).decode("ascii")
    b64key = base64.b64encode(cert["key"].encode("ascii")).decode("ascii")
    patch = dump({
        "data": {
            "tls.crt": b64cert,
            "tls.key": b64key,
        },
    }, Dumper=Dumper)
    kubectl(["patch", "secret", secretname, "--patch", patch],
            namespace=namespace)

def update_all_vaultcerts():
    p = kubectl("get vaultcerts")
    vcs = load(p.stdout, Loader=Loader)
    cert_cache = {}

    token = vault_login()

    npatched = 0
    for vc in vcs["items"]:
        name = vc["metadata"]["name"]
        namespace = vc["metadata"]["namespace"]
        domains = vc["spec"]["domain"]
        secret = vc["spec"]["secretName"]

        vcdomain = vault_cert_domain(domains)
        if vcdomain not in cert_cache:
            vcert = vault_get_cert(token, domains)
            fingerprint = get_cert_fingerprint(vcert["cert"])
            cert_cache[vcdomain] = {
                "cert": vcert,
                "fingerprint": fingerprint,
            }
        cert = cert_cache[vcdomain]

        try:
            sec_cert = get_tls_cert_from_secret(secret, namespace)
            sec_cert_fp = get_cert_fingerprint(sec_cert)
        except subprocess.CalledProcessError:
            # VC present, but TLS secret absent; create secret
            create_tls_secret({"object": vc})
            sec_cert_fp = cert["fingerprint"]
            npatched += 1

        if sec_cert_fp != cert["fingerprint"]:
            patch_cert_in_secret(secret, namespace, cert["cert"])
            npatched += 1

    logging.info(f"All certs up-to-date. {npatched} patched in this run.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=LOG_LEVEL, format="[%(levelname)s] %(message)s")

    if args.config:
        dump_config()
    else:
        update_all_vaultcerts()
