# Hermes Fork / Upstream Sync Incident Record

**Status**: Immediate incident remediated outside this repository; long-term remediation open.
**Backlog id**: `post-sprint-0/hermes-fork-upstream-sync`.
**Mutation posture**: This record is docs-only. It authorizes no Hermes install mutation, fork reset, plugin relocation, plugin enablement, package publication, GitHub settings change, or runtime deployment.
**Owning artifact**: PCO completion-gate plugin manifest (`plugin.yaml`, `kind: standalone`).

---

## 1. Purpose

This record makes the Hermes fork/upstream sync incident discoverable from the tracked Creator Engine repository. It summarizes the blocking update failure, the immediate remediation already performed, and the open long-term decision to move the PCO completion-gate plugin out of a Hermes fork and into CE-owned/user-plugin hosting.

The external incident report that supplied the detailed session facts is not linked here by local filesystem path. This record is the repo-visible route for future backlog, Source-ratification, and implementation planning.

## 2. Incident summary

A Hermes update operation did not bring the active install current with upstream Hermes. The fork used by the active install carried Creator Engine customization commits on its tracked `main` branch. The Hermes updater detected that the fork was ahead of upstream and conservatively skipped upstream synchronization to avoid trampling local changes.

The practical effect was that the active install could remain far behind upstream while still appearing to update from the fork. The observed incident involved a fork that was hundreds of upstream commits behind while also carrying a small number of fork-only customization commits.

The root cause is not the existence of a customization by itself. The root cause is that the customization lives as commits on the fork's tracked `main` branch, which is also the branch the updater treats as the update target.

## 3. Customization being protected

The customization is the PCO completion-gate plugin for Creator Engine work. Its manifest identifies it as a standalone plugin and describes it as an opt-in runtime completion-report gate for Source-ratified Creator Engine work.

The plugin is additive: it consists of plugin code, tests, and fixtures, without modifying upstream Hermes files. That additive property makes relocation feasible. A plugin that must patch upstream Hermes internals would require a different decision because fork divergence would become harder to avoid.

## 4. Immediate remediation already performed

The incident report records that the active Hermes fork was manually synchronized with upstream, dependencies were reinstalled, and smoke tests passed. The PCO completion-gate plugin still imported and its existing tests passed after the sync.

That remediation restored the active install to a healthy current state, but it did not remove the structural recurrence risk. As long as the plugin remains on the fork's tracked `main`, future upstream syncs can hit the same ahead-of-upstream skip path and require manual merge/push/reinstall handling.

## 5. Open long-term decision

The recommended long-term remediation is Option A from the incident analysis:

1. Host the standalone PCO completion-gate plugin in this Creator Engine repository.
2. Deploy it through Hermes's user-plugin mechanism rather than bundling it in the Hermes fork.
3. Record deployed plugin provenance: the CE commit/tag or equivalent source identifier that produced the live deployed plugin.
4. Verify the plugin loads from the user-plugin location and preserves the same runtime behavior before any fork reset or fork retirement.
5. Only after successful relocation, restore the active Hermes update path so upstream synchronization can proceed without fork-ahead skip behavior.

Other options remain possible but are not currently preferred:

- a dedicated standalone plugin repository;
- a package distributed through Hermes plugin entry points;
- keeping customization on a non-`main` fork branch.

The current recommendation favors CE-owned hosting because the plugin is a CE governance artifact and should be versioned and reviewed in the CE repository rather than entangled with upstream Hermes history.

## 6. Acceptance criteria for the future remediation

A future Source-ratified implementation envelope should not be considered complete until all of the following are proven:

1. The PCO completion-gate plugin is versioned in a CE-owned source location.
2. The active Hermes install loads the plugin from outside the Hermes fork.
3. The plugin's tests pass from the new source location.
4. The active runtime proves the completion-gate hooks still fire as expected.
5. A provenance record identifies the deployed plugin source version.
6. Hermes upstream updates no longer skip because the active fork carries CE-only plugin commits on its tracked `main`.
7. The old fork-coupled plugin copy is either retired or explicitly documented as non-authoritative after relocation.

## 7. Boundaries for this record

This record and the companion backlog row do not authorize implementation. In particular, they do not authorize:

- modifying the active Hermes install;
- copying, moving, symlinking, or enabling the plugin;
- resetting or retiring any Hermes fork;
- changing Hermes configuration;
- publishing a package;
- changing any GitHub settings;
- mutating CE validator/runtime/schema surfaces.

The future remediation remains at `Backlog` until Source ratifies the next bounded envelope.
