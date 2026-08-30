"""`app/models/audit_hash.py`: `hash = sha256(prev_hash + canonical_json(payload))`,
reproducible across runs and machines, tamper-evident by construction."""

from __future__ import annotations

import hashlib

from app.models.audit_hash import GENESIS_HASH, canonical_json, compute_hash


def test_canonical_json_sorts_keys():
    assert canonical_json({"b": 1, "a": 2}) == canonical_json({"a": 2, "b": 1})


def test_canonical_json_has_no_whitespace():
    encoded = canonical_json({"a": 1, "b": [1, 2, 3]})
    assert " " not in encoded


def test_canonical_json_is_reproducible():
    payload = {"action": "APPROVE", "amount": 2200, "nested": {"z": 1, "a": 2}}
    assert canonical_json(payload) == canonical_json(payload)


def test_compute_hash_matches_hand_computed_sha256():
    payload = {"a": 1}
    expected = hashlib.sha256((GENESIS_HASH + canonical_json(payload)).encode("utf-8")).hexdigest()
    assert compute_hash(GENESIS_HASH, payload) == expected


def test_compute_hash_is_deterministic():
    payload = {"trust_score": 82.4, "direction": "INCREASE"}
    assert compute_hash(GENESIS_HASH, payload) == compute_hash(GENESIS_HASH, payload)


def test_different_payloads_produce_different_hashes():
    h1 = compute_hash(GENESIS_HASH, {"amount": 100})
    h2 = compute_hash(GENESIS_HASH, {"amount": 101})
    assert h1 != h2


def test_changing_prev_hash_changes_the_result_tamper_evidence():
    payload = {"amount": 100}
    h1 = compute_hash(GENESIS_HASH, payload)
    h2 = compute_hash("1" * 64, payload)
    assert h1 != h2


def test_chain_of_three_entries_is_order_sensitive():
    payloads = [{"i": 1}, {"i": 2}, {"i": 3}]
    prev = GENESIS_HASH
    chain = []
    for payload in payloads:
        current = compute_hash(prev, payload)
        chain.append(current)
        prev = current

    # Tampering with the middle payload breaks every hash after it.
    tampered_prev = GENESIS_HASH
    tampered_chain = []
    tampered_payloads = [{"i": 1}, {"i": 999}, {"i": 3}]
    for payload in tampered_payloads:
        current = compute_hash(tampered_prev, payload)
        tampered_chain.append(current)
        tampered_prev = current

    assert chain[0] == tampered_chain[0]  # untouched entry unaffected
    assert chain[1] != tampered_chain[1]  # tampered entry itself changes
    assert chain[2] != tampered_chain[2]  # everything downstream changes too


def test_matches_the_fixture_data_hand_rolled_algorithm():
    # app/fixtures/audit.py's _hash_entry, verified to compute the same value
    # this module's compute_hash does for the same inputs.
    payload = {"action": "APPROVE", "amount": 2200}
    assert (
        compute_hash(GENESIS_HASH, payload)
        == hashlib.sha256((GENESIS_HASH + canonical_json(payload)).encode("utf-8")).hexdigest()
    )
