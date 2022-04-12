#!/usr/bin/env python3
# Copyright 2022 MobiledgeX, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import argparse
import json
import logging
import os

from utils.vault import vault_login, vault_get_cert
from utils.kubernetes import kubectl, create_tls_secret, delete_tls_secret

LOG_LEVEL = logging.INFO

def dump_config():
    config = {
        "configVersion": "v1",
        "kubernetes": [
            {
                "apiVersion": "stable.mobiledgex.net/v1alpha1",
                "kind": "VaultCert",
                "executeHookOnEvent": [ "Added", "Modified", "Deleted" ]
            },
        ],
    }
    print(json.dumps(config))

def handle_events():
    with open(os.environ["BINDING_CONTEXT_PATH"]) as f:
        context = json.load(f)
    for binding in context:
        type = binding["type"]
        if type == "Synchronization":
            for binding in binding["objects"]:
                create_tls_secret(binding)
        elif type == "Event":
            eventType = binding["watchEvent"]
            if eventType == "Added":
                create_tls_secret(binding)
            elif eventType == "Deleted":
                delete_tls_secret(binding)
            elif eventType == "Modified":
                delete_tls_secret(binding)
                create_tls_secret(binding)
            else:
                print(f"Unknown event type: {eventType}")
        else:
            print(f"Unhandled binding of type: {type}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=LOG_LEVEL, format="[%(levelname)s] %(message)s")

    if args.config:
        dump_config()
    else:
        handle_events()
