## Installation

```
kubectl create ns vault-cert
kubectl apply -f shell-operator-rbac.yaml
kubectl apply -f crd-vaultcert.yaml
kubectl apply -f shell-operator-deploy.yaml
```

## Obtaining cert for a domain

Create a VaultCert request:

```
kubectl apply -f vaultcert-test.yaml
```

In a few seconds, the operator will create a TLS secret with the name specified
in the VaultCert request:

```
kubectl get secret test-mobiledgex-net-tls
```

The cert will be created in the namespace the VaultCert request is in.

```
kubectl create ns test
kubectl -n test apply -f vaultcert-test.yaml
kubectl -n test get secret test-mobiledgex-net-tls
```

## Troubleshooting

Check the logs of the operator:

```
kubectl -n vault-cert logs -f -l operator=shell-operator
```
