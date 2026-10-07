# Issue tracker: GitHub

Issues and specifications for this repository live in GitHub Issues. Use the `gh` CLI for all operations and infer the repository from `git remote -v`.

## Conventions

- Create, read, comment on, label and close work through `gh issue`.
- Supply multiline issue and pull-request bodies through a temporary body file.
- Pull requests are not a triage request surface.
- GitHub shares one number space across issues and pull requests; resolve an ambiguous number before acting on it.

## Publishing and fetching

When a skill says “publish to the issue tracker”, create a GitHub issue. When it says “fetch the relevant ticket”, read the issue and its comments with `gh issue view`.

## Wayfinding operations

- **Map**: one issue labelled `wayfinder:map`, containing Destination, Notes, Decisions so far, Not yet specified and Out of scope.
- **Child ticket**: a GitHub sub-issue of the map where supported. Otherwise add it to the map task list and put `Part of #<map>` at the top of the child.
- **Ticket labels**: `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling` or `wayfinder:task`.
- **Blocking**: use GitHub native issue dependencies where available. Otherwise use a `Blocked by: #<number>` line in the child body.
- **Frontier**: open children with no open blocker and no assignee, in map order.
- **Claim**: assign the issue to the driving developer before work starts.
- **Resolve**: comment with the answer, close the issue, and add a one-line linked gist to the map’s Decisions so far.

The remote is `https://github.com/giniluwolar-design/ActuarialLibrary.git`.
