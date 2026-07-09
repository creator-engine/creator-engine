The release-finalize integration fixture now skips build outputs, distribution
artifacts, and editable-install metadata while copying the repository under
test. This keeps parallel test workers from racing against transient artifact
trees during fixture setup.
