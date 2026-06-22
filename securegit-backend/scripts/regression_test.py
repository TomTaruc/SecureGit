import os
import subprocess
import sys

def run_tests():
    print("Starting Regression Tests via Pytest...")
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_path = os.path.join(backend_dir, "tests", "test_regression.py")
    
    result = subprocess.run(["pytest", test_path, "-v"], cwd=backend_dir)
    sys.exit(result.returncode)

if __name__ == "__main__":
    run_tests()

