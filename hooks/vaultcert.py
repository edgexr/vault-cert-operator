#!/usr/bin/env python3

import argparse
import json
import os
import requests
import subprocess
import tempfile

vault_addr = os.environ["VAULT_ADDR"]
vault_role_id = os.environ["VAULT_ROLE_ID"]
vault_secret_id = os.environ["VAULT_SECRET_ID"]

def dump_config():
    config = {
        "configVersion": "v1",
        "kubernetes": [
            {
                "apiVersion": "stable.mobiledgex.net/v1alpha1",
                "kind": "VaultCert",
                "executeHookOnEvent": [ "Added", "Modified" ]
            },
        ],
    }
    print(json.dumps(config))

def vault_login():
    r = requests.post(f"{vault_addr}/v1/auth/approle/login",
                      json={"role_id": vault_role_id,
                            "secret_id": vault_secret_id})
    r.raise_for_status()
    return r.json()["auth"]["client_token"]

def vault_get_cert(token, domainlist):
    domains = ",".join(sorted(set(domainlist)))
    url = f"{vault_addr}/v1/certs/cert/{domains}"
    r = requests.get(url, headers={"X-Vault-Token": token})
    if r.status_code != requests.codes.ok:
        os.exit(f"{url}: {r.status_code} {r.text}")

    return r.json()["data"]

def create_tls_secret(binding):
    meta = binding["object"]["metadata"]
    name = meta["name"]
    namespace = meta["namespace"]

    spec = binding["object"]["spec"]
    domains = spec["domain"]
    secretname = spec["secretName"]

    p = subprocess.run(["kubectl", f"--namespace={namespace}",
                        "get", "secret", secretname],
                       check=False, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
    if p.returncode == 0:
        print(f"Secret {secretname} exists in namespace {namespace}")
    else:
        # Create secret
        crt = tempfile.NamedTemporaryFile(mode="w", suffix=".crt", delete=False)
        key = tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False)

        print(f"Creating TLS secret {secretname} for {name} in namespace {namespace}")
        vcert = vault_get_cert(vault_login(), domains)

        crt.write(vcert["cert"])
        crt.close()

        key.write(vcert["key"])
        key.close()

        subprocess.run(["kubectl", f"--namespace={namespace}",
                        "create", "secret", "tls",
                        secretname, f"--cert={crt.name}",
                        f"--key={key.name}"], check=True)

        os.unlink(crt.name)
        os.unlink(key.name)

def handle_events():
    with open(os.environ["BINDING_CONTEXT_PATH"]) as f:
        context = json.load(f)
    for binding in context:
        type = binding["type"]
        if type == "Synchronization":
            for binding in binding["objects"]:
                create_tls_secret(binding)
        elif type == "Event":
            create_tls_secret(binding)
        else:
            print(f"Unhandled event of type: {type}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", action="store_true")
    args = parser.parse_args()

    if args.config:
        dump_config()
    else:
        handle_events()
