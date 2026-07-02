"""
main.py — Entry point for PayrollPro v2.0

Run from the project root:
    python main.py
"""
from gui.login_window   import show_login
from gui.main_dashboard import show_dashboard


def main():
    show_login(on_success=show_dashboard)


if __name__ == "__main__":
    main()
