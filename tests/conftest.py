import sys
from pathlib import Path

# Permet `import src...` quel que soit le répertoire de lancement de pytest.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
