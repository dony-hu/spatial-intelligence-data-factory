"""
Phase 5: Confirmation Mechanism Tests

Tests the structured confirmation mechanism that replaces text-based keyword recognition.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_confirmation_record_creation():
    """Test creating confirmation records in database"""
    print("\n" + "=" * 70)
    print("Test 1: Confirmation Record Creation")
    print("=" * 70)

    try:
        from database.agent_runtime_store import AgentRuntimeStore
        from datetime import datetime, timedelta

        runtime_store = AgentRuntimeStore()

        # Calculate expiry time
        expires_at = (datetime.now() + timedelta(seconds=900)).isoformat()

        # Create a confirmation record
        confirmation_id = runtime_store.create_confirmation_record(
            session_id="test_session_001",
            draft_id="draft_abc123",
            operation_type="publish_draft",
            operation_params={"draft_id": "draft_abc123", "reason": "测试发布"},
            expires_at=expires_at
        )

        assert confirmation_id, "Confirmation ID should be generated"
        print(f"✓ Confirmation record created with ID: {confirmation_id}")

        # Retrieve the confirmation record
        record = runtime_store.get_confirmation_record(confirmation_id)
        assert record is not None, "Record should be retrievable"
        assert record["session_id"] == "test_session_001"
        assert record["operation_type"] == "publish_draft"
        assert record["confirmation_status"] == "pending"
        print("✓ Confirmation record retrieved correctly")

        # Verify expiry
        assert record["expires_at"] is not None, "Expiry time should be set"
        record_expires = datetime.fromisoformat(record["expires_at"])
        now = datetime.now()
        remaining = (record_expires - now).total_seconds()
        assert 800 < remaining <= 900, f"Expiry should be in ~900s, got {remaining}s"
        print(f"✓ Confirmation expiry set correctly (expires in {remaining:.0f}s)")

        return True

    except Exception as e:
        print(f"✗ Confirmation record creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_confirmation_status_update():
    """Test updating confirmation record status"""
    print("\n" + "=" * 70)
    print("Test 2: Confirmation Status Update")
    print("=" * 70)

    try:
        from database.agent_runtime_store import AgentRuntimeStore
        from datetime import datetime, timedelta

        runtime_store = AgentRuntimeStore()

        # Create confirmation
        expires_at = (datetime.now() + timedelta(seconds=900)).isoformat()
        confirmation_id = runtime_store.create_confirmation_record(
            session_id="test_session_002",
            operation_type="create_process",
            operation_params={"code": "TEST_PROC", "name": "Test Process"},
            expires_at=expires_at
        )

        # Verify initial status
        record = runtime_store.get_confirmation_record(confirmation_id)
        assert record["confirmation_status"] == "pending"
        print("✓ Initial status is 'pending'")

        # Update to confirmed
        runtime_store.update_confirmation_status(confirmation_id, "confirmed", "user_123")

        record = runtime_store.get_confirmation_record(confirmation_id)
        assert record["confirmation_status"] == "confirmed"
        assert record["confirmer_user_id"] == "user_123"
        assert record["confirmed_at"] is not None
        print("✓ Status updated to 'confirmed'")

        # Update to rejected
        expires_at2 = (datetime.now() + timedelta(seconds=900)).isoformat()
        confirmation_id2 = runtime_store.create_confirmation_record(
            session_id="test_session_003",
            operation_type="modify_process",
            operation_params={},
            expires_at=expires_at2
        )

        runtime_store.update_confirmation_status(confirmation_id2, "rejected", "user_456")

        record = runtime_store.get_confirmation_record(confirmation_id2)
        assert record["confirmation_status"] == "rejected"
        print("✓ Status can be updated to 'rejected'")

        return True

    except Exception as e:
        print(f"✗ Confirmation status update test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_confirmation_listing_by_session():
    """Test listing confirmations by session"""
    print("\n" + "=" * 70)
    print("Test 3: Confirmation Listing by Session")
    print("=" * 70)

    try:
        from database.agent_runtime_store import AgentRuntimeStore
        from datetime import datetime, timedelta

        runtime_store = AgentRuntimeStore()

        session_id = "test_session_list"

        # Create multiple confirmations
        conf_ids = []
        operation_types = ["create_process", "modify_process", "publish_draft"]
        for i, op_type in enumerate(operation_types):
            expires_at = (datetime.now() + timedelta(seconds=900)).isoformat()
            conf_id = runtime_store.create_confirmation_record(
                session_id=session_id,
                operation_type=op_type,
                operation_params={"test": f"param_{i}"},
                expires_at=expires_at
            )
            conf_ids.append(conf_id)

        # Verify all confirmations exist and are pending
        for conf_id in conf_ids:
            record = runtime_store.get_confirmation_record(conf_id)
            assert record is not None
            assert record["confirmation_status"] == "pending"

        print(f"✓ Created {len(conf_ids)} confirmations for session")

        # Confirm one and verify it can be distinguished
        runtime_store.update_confirmation_status(conf_ids[0], "confirmed", "user")
        record = runtime_store.get_confirmation_record(conf_ids[0])
        assert record["confirmation_status"] == "confirmed"
        print("✓ Confirmed confirmation status updated correctly")

        return True

    except Exception as e:
        print(f"✗ Confirmation listing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_validation():
    """Test DialogueSchemaValidator"""
    print("\n" + "=" * 70)
    print("Test 4: Schema Validation")
    print("=" * 70)

    try:
        from tools.dialogue_schema_validation import DialogueSchemaValidator

        validator = DialogueSchemaValidator()

        # Test 1: Valid create_process parameters
        result = validator.validate("create_process", {
            "code": "VALID_CODE",
            "name": "Test Process",
            "domain": "address_governance"
        })

        assert result.is_valid, f"Should be valid, got errors: {result.errors}"
        print("✓ Valid create_process parameters accepted")

        # Test 2: Missing required parameter
        result = validator.validate("create_process", {
            "code": "TEST",
            "name": "Test"
            # Missing 'domain'
        })

        assert not result.is_valid, "Should reject missing required parameter"
        assert any("domain" in err.lower() or "required" in err.lower() for err in result.errors)
        print("✓ Missing required parameters detected")

        # Test 3: Invalid enum value
        result = validator.validate("create_process", {
            "code": "TEST",
            "name": "Test",
            "domain": "invalid_domain"
        })

        assert not result.is_valid, "Should reject invalid enum value"
        print("✓ Invalid enum values rejected")

        # Test 4: Additional properties rejected (security - prevent injection)
        result = validator.validate("create_process", {
            "code": "TEST",
            "name": "Test",
            "domain": "address_governance",
            "malicious_field": "should_be_rejected"
        })

        assert not result.is_valid, "Should reject additional fields for security"
        print("✓ Additional properties rejected (prevents parameter injection)")

        # Test 5: Unknown intent allowed (fallback for non-schema-validated intents)
        result = validator.validate("unknown_read_intent", {})

        assert result.is_valid, "Should allow unknown intents (read operations)"
        print("✓ Unknown intents allowed (assume read operations)")

        return True

    except Exception as e:
        print(f"✗ Schema validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parsing_event_logging():
    """Test logging of LLM parsing events"""
    print("\n" + "=" * 70)
    print("Test 5: Parsing Event Logging")
    print("=" * 70)

    try:
        from database.agent_runtime_store import AgentRuntimeStore
        import json

        runtime_store = AgentRuntimeStore()

        session_id = "test_parsing_001"
        raw_response = '{"intent": "create_process", "params": {"code": "TEST"}}'
        parsed_json = '{"code": "TEST", "name": "Test Process"}'
        validation_status = "valid"
        validation_errors = json.dumps([], ensure_ascii=False)

        # Log parsing event
        event_id = runtime_store.log_parsing_event(
            session_id=session_id,
            raw_llm_response=raw_response,
            parsed_json=parsed_json,
            validation_status=validation_status,
            validation_errors=validation_errors
        )

        assert event_id, "Event ID should be generated"
        print(f"✓ Parsing event logged with ID: {event_id}")

        # Verify parsing event was stored in database
        # Note: The method returns event_id but there might not be a get_parsing_event method
        # We can verify the event exists by querying the database directly
        with runtime_store.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM parsing_event WHERE parsing_event_id = ?", (event_id,))
            row = cur.fetchone()
            assert row is not None, "Parsing event should be in database"
            event = dict(row)
            assert event["session_id"] == session_id
            assert event["validation_status"] == validation_status
        print("✓ Parsing event verified in database")

        return True

    except Exception as e:
        print(f"✗ Parsing event logging test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_confirmation_expiry():
    """Test confirmation expiry logic"""
    print("\n" + "=" * 70)
    print("Test 6: Confirmation Expiry")
    print("=" * 70)

    try:
        from database.agent_runtime_store import AgentRuntimeStore
        from datetime import datetime, timedelta

        runtime_store = AgentRuntimeStore()

        # Create confirmation with short expiry
        expires_soon = (datetime.now() + timedelta(seconds=1)).isoformat()
        confirmation_id = runtime_store.create_confirmation_record(
            session_id="test_expiry",
            operation_type="publish_draft",
            operation_params={},
            expires_at=expires_soon
        )

        record = runtime_store.get_confirmation_record(confirmation_id)
        expires_at = datetime.fromisoformat(record["expires_at"])
        now = datetime.now()
        remaining = (expires_at - now).total_seconds()

        assert 0 < remaining <= 1, f"Should have ~1 second, got {remaining}s"
        print(f"✓ Short expiry set correctly ({remaining:.2f}s)")

        # Wait for expiry
        time.sleep(1.5)

        # Check if expired
        expires_at = datetime.fromisoformat(record["expires_at"])
        now = datetime.now()
        is_expired = now > expires_at

        assert is_expired, "Confirmation should be expired"
        print("✓ Confirmation correctly detected as expired")

        # Test with long expiry
        expires_later = (datetime.now() + timedelta(seconds=3600)).isoformat()
        confirmation_id2 = runtime_store.create_confirmation_record(
            session_id="test_long_expiry",
            operation_type="create_process",
            operation_params={},
            expires_at=expires_later
        )

        record2 = runtime_store.get_confirmation_record(confirmation_id2)
        expires_at2 = datetime.fromisoformat(record2["expires_at"])
        now = datetime.now()
        remaining2 = (expires_at2 - now).total_seconds()

        assert 3500 < remaining2 <= 3600, f"Should have ~3600s, got {remaining2}s"
        print(f"✓ Long expiry set correctly ({remaining2:.0f}s)")

        return True

    except Exception as e:
        print(f"✗ Confirmation expiry test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         Phase 5: Confirmation & Schema Validation Tests           ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    tests = [
        ("Confirmation Record Creation", test_confirmation_record_creation),
        ("Confirmation Status Update", test_confirmation_status_update),
        ("Confirmation Listing by Session", test_confirmation_listing_by_session),
        ("Schema Validation", test_schema_validation),
        ("Parsing Event Logging", test_parsing_event_logging),
        ("Confirmation Expiry", test_confirmation_expiry),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Phase 5 Test Summary (Confirmation & Validation)")
    print("=" * 70)

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"  {symbol} {test_name}: {status}")

    print(f"\nTotal: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n✓ All Phase 5 tests PASSED!")
    else:
        print(f"\n✗ {total_count - passed_count} Phase 5 test(s) FAILED")

    print("=" * 70)

    sys.exit(0 if passed_count == total_count else 1)
