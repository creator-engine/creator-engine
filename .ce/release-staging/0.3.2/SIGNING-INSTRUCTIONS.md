# Operator signing seam for ce-root-v1

The staged install spec intentionally contains the placeholder `<RESIGN-REQUIRED-ce-root-v1>`. The Operator reviews the staged artifacts, signs the canonical spec bytes with the held root key, base64-encodes the SSHSIG, and replaces only the placeholder value.

```bash
ssh-keygen -Y sign -f /path/to/ce-root-v1-private -I ce-root-v1 -n ce-spec-v1 - < llms-install.canonical > llms-install.md.sig
base64 -w0 llms-install.md.sig
```

No automated path in this command reads or invokes the root private key.
