# MedOrigin community governance

MedOrigin is an Apache-2.0 open-source **research software** project, developed
in public with community contributions. It is not a medical device and does not
permit real-patient data or clinical deployment.

## Participation and decisions

- **Everyone** may report reproducible bugs, ask questions, propose changes,
  review open pull requests, and contribute documentation, tests, fixtures,
  accessibility, and code.
- **Maintainers** triage work, ask for evidence, moderate discussions, and merge
  contributions that satisfy the protected-branch checks. The repository owner
  currently acts as lead maintainer. This is an invitation to collaboration,
  not a claim that a governing committee already exists.
- **Research and security authorities** follow the existing
  [program rules](docs/governance/rules.md), [roles and authority](docs/governance/roles_and_authority.md),
  accepted architecture decisions, and research/release gates. Public votes,
  reactions, or an issue cannot override those controls.

## Decision process

1. For simple fixes, open an [issue](https://github.com/AbdulazizShehri/MedOrigin/issues)
   with reproducible evidence, or propose a focused PR linked to an issue.
2. For new functionality, open a [discussion](https://github.com/AbdulazizShehri/MedOrigin/discussions)
   explaining the problem, alternatives, accessibility, maintenance burden,
   privacy impact, and measurable acceptance criteria.
3. For changes to architecture, public APIs, research protocols, governance,
   or compatibility, propose an ADR according to
   [the contributor guide](CONTRIBUTING.md). Historical/frozen evidence stays
   untouched; successor inputs require explicit scientific authorization.
4. Maintainers communicate rationale in the relevant public issue/PR, resolve
   review comments, require CI checks, and merge through the protected branch.
   If a proposal is declined, contributors can ask for reconsideration with
   new evidence. Security reports remain private.

## Becoming a maintainer

Contributors who repeatedly deliver tested, well-documented changes, respond
constructively to review, respect evidence boundaries, and help others may be
invited to take on scoped maintainer responsibilities. The current owner retains
the ability to grant or revoke GitHub permissions and assign CODEOWNERS. No
maintainer title or permissions are automatic.

## Community safety and boundaries

Follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report vulnerabilities via
[SECURITY.md](SECURITY.md), never in public issues. Do not submit patient
records, credentials, or unlawfully reused code. Preserve third-party
copyright/license notices and [research provenance](THIRD_PARTY_NOTICES.md).
Discussions and issues provide a way to propose work; neither implies that
a model, benchmark, package, or clinical deployment is approved for release.

## Transparency

Use [the roadmap](ROADMAP.md) for direction and canonical specs/PRs/checks for
actual status. Project-wide decisions should leave a linked issue, PR, or ADR.
Community contributions are recognized through the repository's public
commit/PR history and applicable attribution notices.
