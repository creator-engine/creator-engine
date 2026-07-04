CLI unification slice 1:

- Renames the v3 public adoption command from `onboard` to `install`.
- Moves the v1 dispatch planner to `ce pickup dispatch-plan`.
- Adds subprocess-only `ce` forwarding shims for the v3 public command groups except `playbook`.
- Keeps a one-release-cycle `onboard` alias on the `cev3 install` subparser (with an explicit `_DISPATCH` entry, since argparse surfaces the literal alias string rather than the canonical subcommand name) so the release-signed `docs/install.sh` and the slow-tier `test_install_bootstrap.py` keep working unchanged; `docs/install.sh` migrates to `install` on the next release cut (release-coupled, deliberately deferred out of this PR).
