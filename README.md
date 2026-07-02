# PayrollPro v3.0

University Assembly Language project: Tkinter GUI + NASM x86-64 backend.

## What's fixed/new in v3.0
- SHARP rendering — DPI-aware (no more blur on high-res screens)
- Working sidebar with 5 real pages:
    Dashboard  - the payroll calculator
    Employees  - table of all saved employees
    Payslips   - pick any saved record and view its payslip
    Reports    - totals, averages, per-department breakdown
    Settings   - calculation rules + app info
- Cleaner login screen (no marketing fluff)
- 492 lines of assembly across 4 modules (Core, PF, Health, Loan)

## Setup
1. Build the DLL:
       cd asm
       build_windows.bat
2. Run:
       cd ..
       python main.py
3. Login: admin / admin123

## Pages need data
Employees / Payslips / Reports read from data/employees.csv, which is created
when you click "Save to CSV" on the Dashboard. Save a few records first, then
those pages fill with content.
