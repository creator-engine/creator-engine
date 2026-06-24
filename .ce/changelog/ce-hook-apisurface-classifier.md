Add a Ring-1 hook classifier for destructive GitHub REST calls issued through
`gh api` and `curl https://api.github.com/...`, closing the gh-api/REST bypass
of the existing git deny-map for repo ref deletion, repo settings, hooks,
secrets, branch protection, and related high-blast repository API mutations.
