# ce-499-seat-ready-profile

- Added the `seat-ready` `ce validate-pr` profile for seat-side READY validation.
- Capped the profile's default pytest workers at four and moved pytest temporary storage to `~/tmp`.
- Added a seat-ready autogen repair and byte-parity gate ahead of final path-manifest validation.
