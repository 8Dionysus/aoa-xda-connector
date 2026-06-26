# XDA Source Policy

## Allowed

- Public XDA forum/thread/post pages.
- Public source URLs needed for evidence references.
- Bounded crawl windows explicitly listed in profile seeds.
- Sanitized local fixtures that preserve public page shape.

## Forbidden

- Login, account, conversations, private messages, or account-gated pages.
- Attachments, downloads, mirrors, binaries, firmware packages, or file pulls.
- Write routes such as post, reply, edit, quote-reply, like, report, or follow.
- Hidden APIs or routes that bypass public page boundaries.
- Broad unbounded crawling.
- XDA internal search as a crawler or corpus source.

## Search Rule

Do not use XDA internal search as the data source. Build local deep search over
allowed public snapshots.

## Runtime Rule

The starter proof is no-network and read-only. Any live expansion must be
bounded by a seed profile, produce receipts, and store generated artifacts
outside Git.
