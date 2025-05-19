import sys
import os
import importlib

print(f"--- ENV_CHECK ---")
print(f"sys.executable: {sys.executable}")
print(f"sys.version: {sys.version}")
print(f"sys.prefix (used for site-packages): {sys.prefix}")
print(f"sys.base_prefix (main Python install if in venv): {sys.base_prefix}")
print(f"PYTHONPATH environment variable: {os.environ.get('PYTHONPATH')}")
print(f"Current Working Directory: {os.getcwd()}")
print(f"sys.path: {sys.path}")
print(f"--- END ENV_CHECK PREAMBLE ---")

# Attempt to import instabids and instabids.memory as a further diagnostic
try:
    print("\n--- ENV_CHECK: Attempting to import 'instabids' package ---")
    # This should trigger instabids/__init__.py which contains our importlib hack
    import instabids
    print(f"--- ENV_CHECK: 'instabids' imported. Location: {instabids.__file__ if hasattr(instabids, '__file__') else 'N/A - namespace?'}")
    
    if 'instabids.memory' in sys.modules:
        print(f"--- ENV_CHECK: 'instabids.memory' IS in sys.modules (likely due to hack in instabids/__init__.py).")
        instabids_memory_module = sys.modules['instabids.memory']
        print(f"--- ENV_CHECK: instabids.memory from sys.modules. Location: {instabids_memory_module.__file__ if hasattr(instabids_memory_module, '__file__') else 'N/A - built-in or namespace?'}")
        
        # Check content of our known instabids.memory.__init__.py
        # Assuming instabids.__file__ gives path to instabids/__init__.py
        _memory_init_path_check = os.path.join(os.path.dirname(instabids.__file__), 'memory', '__init__.py')
        print(f"--- ENV_CHECK: Content of expected instabids.memory.__init__.py at '{_memory_init_path_check}':")
        if os.path.exists(_memory_init_path_check):
            with open(_memory_init_path_check, 'r') as f_mem_init:
                for line_num, line_content in enumerate(f_mem_init):
                    print(f"    L{line_num}: {line_content.rstrip()}")
        else:
            print(f"    ERROR: Expected {_memory_init_path_check} not found!")

        print("--- ENV_CHECK: Attempting 'from instabids.memory import persistent_memory' ---")
        try:
            # If instabids.memory is our correct one (with just a print statement), 
            # this import will fail as 'persistent_memory' is not an attribute of the minimal module.
            # The goal is to see IF the 'instabids.memory' loaded is our controlled one,
            # or if the 'phantom' one somehow still gets priority for this sub-import.
            from instabids.memory import persistent_memory 
            print(f"--- ENV_CHECK: 'from instabids.memory import persistent_memory' SUCCEEDED. Location: {persistent_memory.__file__ if hasattr(persistent_memory, '__file__') else 'N/A'}")
        except ImportError as e_pm:
            print(f"--- ENV_CHECK: ImportError for 'from instabids.memory import persistent_memory': {e_pm}")
            print(f"    This is EXPECTED if instabids.memory.__init__.py is our minimal one with just a print statement.")
        except AttributeError as ae:
            print(f"--- ENV_CHECK: AttributeError for 'from instabids.memory import persistent_memory': {ae}")
            print(f"    This is also EXPECTED if instabids.memory.__init__.py is our minimal one.")
    else:
        print(f"--- ENV_CHECK: 'instabids.memory' NOT in sys.modules after importing 'instabids'. This means the hack in instabids/__init__.py may not have fully completed or was bypassed.")

except ModuleNotFoundError as e_instabids:
    print(f"--- ENV_CHECK: ModuleNotFoundError when importing 'instabids': {e_instabids}")
    print(f"    This is critical. If 'instabids' itself cannot be found by this script, PYTHONPATH is likely not set or respected correctly in this execution context.")
except Exception as e_global:
    print(f"--- ENV_CHECK: General exception during 'instabids' import attempts: {e_global}")
    import traceback
    traceback.print_exc()

print(f"\n--- END ENV_CHECK ---")
