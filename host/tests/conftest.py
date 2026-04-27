import subprocess
import sys
import os

def pytest_sessionfinish(session, exitstatus):
    """
    Automatically regenerates the traceability matrix after every
    pytest session completes.
    """
    print("\n\n--- Regenerating Traceability Matrix ---")
    gen_script = os.path.join(
        os.path.dirname(__file__), "..", "tools", "gen_traceability.py" 
    )
    result = subprocess.run(
        [sys.executable, gen_script],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"WARNING: Traceability generation failed!\n{result.stderr}")
