import requests

def vault_login(vault_addr, vault_role_id, vault_secret_id):
    r = requests.post(f"{vault_addr}/v1/auth/approle/login",
                      json={"role_id": vault_role_id,
                            "secret_id": vault_secret_id})
    r.raise_for_status()
    return r.json()["auth"]["client_token"]

def vault_get_cert(vault_addr, token, domainlist):
    domains = ",".join(sorted(set(domainlist)))
    url = f"{vault_addr}/v1/certs/cert/{domains}"
    r = requests.get(url, headers={"X-Vault-Token": token})
    if r.status_code != requests.codes.ok:
        sys.exit(f"{url}: {r.status_code} {r.text}")

    return r.json()["data"]
