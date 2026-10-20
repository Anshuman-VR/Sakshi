# Dev 2: Required EZKL-to-Sakshi proof binding contract

The Lender Node never treats `ProofPayload.public_inputs` as authenticated merely
because it arrived beside a valid EZKL proof. The values in that object are
untrusted until they are matched against the public instances actually covered
by the proof.

## Required runtime artifacts

Production verification requires all of the following. The node defaults to
`SAKSHI_NODE_ENVIRONMENT=production`; local test/development use must be explicit.

- `SAKSHI_NODE_EZKL_SETTINGS_PATH`: the exact settings JSON used by the prover.
- `SAKSHI_NODE_COMPILED_CIRCUIT_PATH`: the compiled circuit artifact.
- `SAKSHI_NODE_EZKL_SETTINGS_SHA256`: a deployment-pinned SHA-256 of the exact native settings file.
- `SAKSHI_NODE_PROOF_BINDING_MANIFEST_PATH` and `SAKSHI_NODE_PROOF_BINDING_MANIFEST_SHA256`: a separate, deployment-pinned manifest; do not mutate EZKL's native settings file to add Sakshi metadata.
- `SAKSHI_NODE_ENVIRONMENT=production`, pinned API secrets and public keys; mock verification is prohibited.
- `RegisteredModel.circuit_hash`: SHA-256 of those exact compiled circuit bytes.
- The separate proof-binding manifest must contain `sakshi_public_input_binding`
  with `version: 1`, `threshold_scale` matching the signed policy's
  `fixed_point_scale`, and an `indices` map for `policy_hash_hi`, `policy_hash_lo`, `C_hi`, `C_lo`, `X_hi`,
  `X_lo`, `decision`, `threshold_scaled`, and `epoch`.
- `sakshi_policy_hash` and `sakshi_hard_rules` in the manifest matching the signed policy.
- The proof JSON `instances` array must expose those values at the declared
  indices. Hashes are represented as two unsigned 128-bit big-endian chunks;
  each chunk is a decimal field element. Threshold is fixed-point quantized
  with decimal round-half-up using the policy's scale.

The node checks these bindings **before** calling `ezkl.verify`. Missing
settings, mismatched circuit bytes, absent instance metadata, an altered public
input, or a hard-rule-list mismatch fails closed as `INVALID_PROOF`.

## Known upstream integration blocker

The current Dev 1 sample in `DEV1_PROMPT.md` generates an EZKL proof over
`input_data` and separately constructs `C`, `X`, `policy_hash`, `decision`,
`threshold`, and `epoch` in a Python object. It also contains a fallback that
serializes non-proof bytes when EZKL proving raises an exception. The sample
itself does not show these Sakshi values being exposed as circuit public
instances. The Lender Node intentionally rejects that fallback and rejects
real EZKL artifacts until the compiled circuit and separate pinned manifest implement the
binding contract above. This is a security dependency, not a reason to accept
unbound claims or change `shared/types.py`.
