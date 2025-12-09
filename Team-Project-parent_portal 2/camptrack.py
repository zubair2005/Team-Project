import os
import sys


def _project_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    # Ensure the data directory exists
    data_dir = os.path.join(_project_root(), "data")
    os.makedirs(data_dir, exist_ok=True)

    # Initialize database and seed baseline data
    try:
        from database import init_db, seed_initial_data
    except Exception as exc:  # pragma: no cover
        print("Failed to import database module:", exc)
        sys.exit(1)

    init_db()
    seed_initial_data()

    # Try to launch the GUI login if available; otherwise print a message
    try:
        from ui import login as login_ui
        if hasattr(login_ui, "launch_login"):
            login_ui.launch_login()
        else:
            print("CampTrack initialized. GUI login not implemented yet.")
    except Exception as exc:  # pragma: no cover
        print("CampTrack initialized. GUI login not implemented yet.")
        print("(Details:", exc, ")")


if __name__ == "__main__":
    main()


