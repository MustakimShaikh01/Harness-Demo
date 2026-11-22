import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from banking_agent.config.settings import DATA_DIR
from banking_agent.storage.recovery import recover_pending_operations


def main() -> None:
    recovered = recover_pending_operations(DATA_DIR)
    print(json.dumps({"recovered_operations": recovered, "count": len(recovered)}, indent=2))


if __name__ == "__main__":
    main()
