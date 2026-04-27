import os
import pytest
import time

from hil_client import PicoClient


@pytest.mark.skipif("PICO_PORT" not in os.environ, reason="Set PICO_PORT env var to run HIL tests")
def test_ping():
    REQS = ["REQ-001"]
    dut = PicoClient(os.environ["PICO_PORT"])
    _boot = dut.read_line()
    resp = dut.cmd("PING")
    dut.close()
    assert resp == "OK PONG"

@pytest.fixture
def dut():
    client = PicoClient(os.environ["PICO_PORT"])
    client.read_line()          # Clear boot message
    client.cmd("SET_STATE 0")   # Reset to STANDBY before each test
    yield client
    client.close()


def test_get_state(dut):
    REQS = ["REQ-002"]
    resp = dut.cmd("GET_STATE")
    assert resp in ["OK STATE STANDBY", "OK STATE ACTIVE", "OK STATE FAILSAFE"]

def test_set_state_robustness(dut):
    REQS = ["REQ-003"]
    # Test valid boundaries
    assert dut.cmd("SET_STATE 0") == "OK STATE STANDBY"
    assert dut.cmd("SET_STATE 2") == "OK STATE FAILSAFE"

    # Test invalid boundaries (Robustness)
    assert dut.cmd("SET_STATE -1") == "ERR BAD_STATE"
    assert dut.cmd("SET_STATE 3") == "ERR BAD_STATE"

def test_ping_timing(dut):
    REQS = ["REQ-004"]
    start_time = time.perf_counter()
    resp = dut.cmd("PING", wait=0)  # Bypass the 50ms delay
    end_time = time.perf_counter()

    latency_ms = (end_time - start_time) * 1000
    assert resp == "OK PONG"
    assert latency_ms < 15.0, f"System too slow! Took {latency_ms:.2f} ms"

def test_unknown_command_robustness(dut):
    REQS = ["REQ-005"]
    assert dut.cmd("INVALID_CMD") == "ERR UNKNOWN_CMD"
    assert dut.cmd("!@#$%^&*") == "ERR UNKNOWN_CMD"
    assert dut.cmd("") == "ERR UNKNOWN_CMD" # Empty command

def test_buffer_overflow_protection(dut):
    REQS = ["REQ-006"]
    # Create a string of 150 'A's
    long_string = "A" * 150 
    resp = dut.cmd(long_string)
    assert resp == "ERR LINE_TOO_LONG"

def test_illegal_state_transition(dut):
    REQS = ["REQ-007"]
    # Put system into Failsafe
    assert dut.cmd("SET_STATE 2") == "OK STATE FAILSAFE"
    # Attempt illegal jump straight to Active
    assert dut.cmd("SET_STATE 1") == "ERR ILLEGAL_TRANSITION"
    # Verify it safely remained in Failsafe
    assert dut.cmd("GET_STATE") == "OK STATE FAILSAFE"

def test_version(dut):
    REQS = ["REQ-008"]
    assert dut.cmd("VERSION") == "OK VERSION 0.1"

def test_full_state_sequence(dut):
    REQS = ["REQ-009"]
    # Walk through every valid state in sequence
    assert dut.cmd("SET_STATE 0") == "OK STATE STANDBY"
    assert dut.cmd("SET_STATE 1") == "OK STATE ACTIVE"
    assert dut.cmd("SET_STATE 2") == "OK STATE FAILSAFE"

def test_return_to_standby_from_any_state(dut):
    REQS = ["REQ-010"]
    # From ACTIVE back to STANDBY
    assert dut.cmd("SET_STATE 1") == "OK STATE ACTIVE"
    assert dut.cmd("SET_STATE 0") == "OK STATE STANDBY"

    # From FAILSAFE back to STANDBY
    assert dut.cmd("SET_STATE 2") == "OK STATE FAILSAFE"
    assert dut.cmd("SET_STATE 0") == "OK STATE STANDBY"

def test_case_sensitivity(dut):
    REQS = ["REQ-011"]
    # Lowercase versions must NOT be accepted as valid commands
    assert dut.cmd("ping") == "ERR UNKNOWN_CMD"
    assert dut.cmd("get_state") == "ERR UNKNOWN_CMD"
    assert dut.cmd("set_state 1") == "ERR UNKNOWN_CMD"

def test_set_state_non_integer(dut):
    REQS = ["REQ-012"]
    # Letters, floats, and symbols are not valid state values
    assert dut.cmd("SET_STATE A") == "ERR UNKNOWN_CMD"
    assert dut.cmd("SET_STATE 1.5") == "ERR UNKNOWN_CMD"
    assert dut.cmd("SET_STATE !") == "ERR UNKNOWN_CMD"

def test_whitespace_handling(dut):
    REQS = ["REQ-013"]
    # Extra spaces before or after should not crash the board
    resp = dut.cmd("  PING  ")
    assert resp in ["OK PONG", "ERR UNKNOWN_CMD"] 

def test_ping_stress(dut):
    REQS = ["REQ-014"]
    # Fire 50 PINGs in a row and verify every single response
    for i in range(50):
        assert dut.cmd("PING") == "OK PONG", f"PING failed on iteration {i+1}"

def test_recovery_after_bad_command(dut):
    REQS = ["REQ-015"]
    dut.cmd("TOTAL_GARBAGE_XYZ")
    assert dut.cmd("PING") == "OK PONG"
    assert dut.cmd("GET_STATE") in ["OK STATE STANDBY", "OK STATE ACTIVE", "OK STATE FAILSAFE"]

def test_boot_state(dut):
    REQS = ["REQ-016"]
    # Immediately after boot system must be in STANDBY
    assert dut.cmd("GET_STATE") == "OK STATE STANDBY"

def test_state_unchanged_after_bad_command(dut):
    REQS = ["REQ-017"]
    # Set a known state
    assert dut.cmd("SET_STATE 1") == "OK STATE ACTIVE"
    # Send an invalid command
    dut.cmd("INVALID_CMD")
    dut.cmd("SET_STATE 99")
    # Verify state did NOT change
    assert dut.cmd("GET_STATE") == "OK STATE ACTIVE"
