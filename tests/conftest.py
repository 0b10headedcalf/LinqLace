import os
import sys

# Allow `from tools...`, `from agents...` imports without installing the package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
