# Security policy

Do not publish a suspected safety, firmware-integrity, updater, or repository
supply-chain issue as a proof-of-concept against deployed equipment. Report it
privately to the repository owner through GitHub's private vulnerability
reporting feature when available, or through the contact address on the owner's
GitHub profile.

Include the affected repository commit, source and candidate SHA-256 values,
profile name, exact observed behavior, and whether any physical device was
written. Do not attach proprietary firmware images or secrets.

Only the latest tagged release and current `main` are maintained. Static checks
and hashes establish file identity, not electrical or runtime safety.
