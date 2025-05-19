import os
import sys

# Manually set PYTHONPATH for this script's execution, mimicking the Uvicorn command
project_src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
print(f"DEBUG_SCRIPT: Adding to sys.path: {project_src_path}")
sys.path.insert(0, project_src_path) # Add to front of sys.path

# Also try setting PYTHONDONTWRITEBYTECODE, though it's less critical for a direct run
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

print(f"DEBUG_SCRIPT: Current sys.path = {sys.path}")

print("--- Attempting to load instabids.memory ---")
try:
    print("DEBUG_SCRIPT: Attempting: import instabids.memory")
    import instabids.memory
    print(f"DEBUG_SCRIPT: SUCCESS: instabids.memory imported.")
    print(f"DEBUG_SCRIPT: instabids.memory.__file__ is: {instabids.memory.__file__}")
    print(f"DEBUG_SCRIPT: instabids.memory path from spec: {instabids.memory.__spec__.origin if instabids.memory.__spec__ else 'No spec'}")

    # Check content of instabids/memory/__init__.py
    init_path = instabids.memory.__file__
    if init_path and os.path.exists(init_path):
        print(f"DEBUG_SCRIPT: Content of {init_path}:")
        with open(init_path, 'r') as f:
            print(f.read())
    else:
        print(f"DEBUG_SCRIPT: Could not read {init_path}")
    print("--- End of instabids.memory loading attempt ---")


    print("\n--- Attempting to import PersistentMemory ---")
    print("DEBUG_SCRIPT: Attempting: from instabids.memory.persistent_memory import PersistentMemory")
    from instabids.memory.persistent_memory import PersistentMemory
    print("DEBUG_SCRIPT: SUCCESS: from instabids.memory.persistent_memory import PersistentMemory")
    print(f"DEBUG_SCRIPT: PersistentMemory type: {type(PersistentMemory)}")
    print("--- End of PersistentMemory import attempt ---")

except ModuleNotFoundError as e:
    print(f"DEBUG_SCRIPT: ERROR: ModuleNotFoundError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"DEBUG_SCRIPT: ERROR: Other Exception: {e}")
    import traceback
    traceback.print_exc()

print("\nDEBUG_SCRIPT: Script finished.")
