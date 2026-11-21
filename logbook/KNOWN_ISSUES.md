# Known issues

- The npm audit reports four moderate advisories in the development-only shadcn CLI dependency chain. No production advisory was reported. The suggested forced remediation replaces the CLI with an incompatible major version; track the upstream fix instead.
- Phase 01 does not provide protection, persistence, integrations or a dashboard. Liveness is not a readiness or security assessment.
