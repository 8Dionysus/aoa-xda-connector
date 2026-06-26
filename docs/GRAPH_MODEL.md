# Graph Model

The graph contains source nodes and claim nodes.

## Source Nodes

- `topic:<thread_id>`
- `post:<post_id>`
- `entity:<kind>:<value>`

## Claim Nodes

Claim nodes use the portable schema `aoa_connector_claim_v1`.

Claim kinds:

- `method`
- `warning`
- `status`
- `context`
- `risk`

## Claim Relations

Claim relation edges use the portable relation vocabulary:

- `source_supports_claim`
- `source_warns_about_claim`
- `source_updates_claim`
- `method_uses_tool`
- `method_targets_object`
- `method_requires_condition`
- `warning_targets_object`
- `warning_targets_action`
- `claim_contextualizes_claim`
- `claim_supersedes_claim`
- `claim_contradicts_claim`
- `claim_deprecated_for_context`
- `claim_refines_claim`
- `claim_scope_limited_by`
- `claim_unknown_for_context`
- `claim_requires_manual_review`

Non-claim edges such as `topic_contains_post` and `post_mentions_entity` remain
source-local graph support.
