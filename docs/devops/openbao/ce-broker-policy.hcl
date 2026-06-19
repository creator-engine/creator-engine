# Least-privilege policy for the CE broker AppRole.
# Adjust secret data paths only by adding explicit per-dev or per-service paths.

path "sys/audit" {
  capabilities = ["read", "sudo"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "auth/token/revoke-self" {
  capabilities = ["update"]
}

path "ce-kv/data/devs/+/runtime/*" {
  capabilities = ["read"]
}

path "ce-kv/metadata/devs/+/runtime/*" {
  capabilities = ["read", "list"]
}
