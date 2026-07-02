"""
core/engine.py — Single import point used by the GUI.
"""
try:
    from core.payroll_bridge import compute_payroll
    BACKEND = "Assembly (NASM)"
except Exception as e:
    from core.payroll_python_fallback import compute_payroll
    BACKEND = f"Python fallback ({e.__class__.__name__})"
