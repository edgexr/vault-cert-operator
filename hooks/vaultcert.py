#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import tempfile

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

def get_vault_cert(binding):
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
        print(f"Secret exists: {secretname}")
    else:
        # Create secret
        crt = tempfile.NamedTemporaryFile(suffix=".crt")
        key = tempfile.NamedTemporaryFile(suffix=".key")
        print(f"Creating TLS secret {secretname} for {name}")
        ## DEBUG - echo
        subprocess.run(["echo", "kubectl", f"--namespace={namespace}",
                        "create", "secret", "tls",
                        secretname, f"--cert={crt.name}",
                        f"--key={key.name}"], check=True)

        crt.close()
        key.close()

def handle_events():
    with open(os.environ["BINDING_CONTEXT_PATH"]) as f:
        context = json.load(f)
    for binding in context:
        type = binding["type"]
        if type == "Synchronization":
            for binding in binding["objects"]:
                get_vault_cert(binding)
        elif type == "Event":
            get_vault_cert(binding)
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
