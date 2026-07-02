"""
core/payroll_bridge.py  -- PayrollPro v2.0
------------------------------------------
ctypes wrapper around the NASM-compiled payroll.dll.

Exposed assembly functions (every one calls into payroll.asm):

  Module 1 (core):
    calc_grade_allowance, calc_overtime_pay, calc_gross,
    calc_tax, calc_eobi, calc_net_salary

  Module 2 (provident fund):
    calc_pf_rate, calc_provident_fund, calc_employer_pf

  Module 3 (health):
    calc_health_insurance, calc_medical_allowance

  Module 4 (loan):
    calc_loan_installment, calc_loan_remaining

  Aggregator:
    calc_final_net

Plus a high-level helper:  compute_payroll(employee_dict) -> dict
"""
import ctypes
import os
import platform


# ---------------------------------------------------------------------------
# Locate the shared library  ../lib/payroll.dll (Windows)  ../lib/libpayroll.so (Linux)
# ---------------------------------------------------------------------------
_HERE    = os.path.dirname(os.path.abspath(__file__))
_LIB_DIR = os.path.normpath(os.path.join(_HERE, "..", "lib"))

if platform.system() == "Windows":
    _LIB_PATH = os.path.join(_LIB_DIR, "payroll.dll")
else:
    _LIB_PATH = os.path.join(_LIB_DIR, "libpayroll.so")


def _load_library():
    if not os.path.exists(_LIB_PATH):
        raise FileNotFoundError(
            f"Assembly library not found at {_LIB_PATH}\n\n"
            "Build it first:\n"
            "  Windows:    cd asm && build_windows.bat\n"
            "  Linux/Mac:  cd asm && bash build_linux.sh"
        )
    return ctypes.CDLL(_LIB_PATH)


_lib = _load_library()


# ---------------------------------------------------------------------------
# All assembly functions take/return 64-bit signed integers.
# ---------------------------------------------------------------------------
_I = ctypes.c_longlong


def _bind(name, n_args):
    fn = getattr(_lib, name)
    fn.argtypes = [_I] * n_args
    fn.restype  = _I
    return fn


# Module 1
_calc_grade_allowance  = _bind("calc_grade_allowance",  1)
_calc_overtime_pay     = _bind("calc_overtime_pay",     1)
_calc_gross            = _bind("calc_gross",            4)
_calc_tax              = _bind("calc_tax",              1)
_calc_eobi             = _bind("calc_eobi",             0)
_calc_net_salary       = _bind("calc_net_salary",       3)

# Module 2
_calc_pf_rate          = _bind("calc_pf_rate",          1)
_calc_provident_fund   = _bind("calc_provident_fund",   2)
_calc_employer_pf      = _bind("calc_employer_pf",      1)

# Module 3
_calc_health_insurance = _bind("calc_health_insurance", 1)
_calc_medical_allowance= _bind("calc_medical_allowance",1)

# Module 4
_calc_loan_installment = _bind("calc_loan_installment", 2)
_calc_loan_remaining   = _bind("calc_loan_remaining",   2)

# Aggregator
_calc_final_net        = _bind("calc_final_net",        3)


# ---------------------------------------------------------------------------
# Public Python wrappers
# ---------------------------------------------------------------------------
def calc_grade_allowance(grade_level):    return int(_calc_grade_allowance(int(grade_level)))
def calc_overtime_pay(hours):             return int(_calc_overtime_pay(int(hours)))
def calc_gross(b, g, bn, ot):             return int(_calc_gross(int(b), int(g), int(bn), int(ot)))
def calc_tax(gross):                      return int(_calc_tax(int(gross)))
def calc_eobi():                          return int(_calc_eobi())
def calc_net_salary(g, t, e):             return int(_calc_net_salary(int(g), int(t), int(e)))

def calc_pf_rate(years):                  return int(_calc_pf_rate(int(years)))
def calc_provident_fund(basic, years):    return int(_calc_provident_fund(int(basic), int(years)))
def calc_employer_pf(emp_pf):             return int(_calc_employer_pf(int(emp_pf)))

def calc_health_insurance(has):           return int(_calc_health_insurance(int(has)))
def calc_medical_allowance(grade):        return int(_calc_medical_allowance(int(grade)))

def calc_loan_installment(bal, gross):    return int(_calc_loan_installment(int(bal), int(gross)))
def calc_loan_remaining(bal, inst):       return int(_calc_loan_remaining(int(bal), int(inst)))

def calc_final_net(g, extra, deduct):     return int(_calc_final_net(int(g), int(extra), int(deduct)))


# ---------------------------------------------------------------------------
# High-level helper used by the GUI
# ---------------------------------------------------------------------------
def compute_payroll(emp: dict) -> dict:
    """
    emp must contain:
        basic_salary, grade_level, bonus, hours_worked, overtime_hours,
        years_of_service, has_insurance (0/1), loan_balance
    Returns a dict with every value needed for the payslip.
    """
    basic    = emp["basic_salary"]
    grade    = emp["grade_level"]
    bonus    = emp["bonus"]
    ot_hours = emp["overtime_hours"]
    years    = emp["years_of_service"]
    has_ins  = emp["has_insurance"]
    loan_bal = emp["loan_balance"]

    # ---- Module 1 -- core
    grade_allow  = calc_grade_allowance(grade)
    overtime_pay = calc_overtime_pay(ot_hours)
    gross        = calc_gross(basic, grade, bonus, ot_hours)
    tax          = calc_tax(gross)
    eobi         = calc_eobi()

    # ---- Module 2 -- provident fund
    pf_rate      = calc_pf_rate(years)
    employee_pf  = calc_provident_fund(basic, years)
    employer_pf  = calc_employer_pf(employee_pf)

    # ---- Module 3 -- health
    insurance    = calc_health_insurance(1 if has_ins else 0)
    medical      = calc_medical_allowance(grade)

    # ---- Module 4 -- loan
    loan_inst    = calc_loan_installment(loan_bal, gross)
    loan_remain  = calc_loan_remaining(loan_bal, loan_inst)

    # ---- Aggregate
    total_extra_earnings = medical
    total_deductions     = tax + eobi + employee_pf + insurance + loan_inst
    net                  = calc_final_net(gross, total_extra_earnings, total_deductions)

    return {
        # core
        "basic_salary":      basic,
        "grade_allowance":   grade_allow,
        "bonus":             bonus,
        "overtime_pay":      overtime_pay,
        "gross_salary":      gross,
        "tax_deduction":     tax,
        "eobi_deduction":    eobi,

        # provident fund
        "pf_rate":           pf_rate,
        "employee_pf":       employee_pf,
        "employer_pf":       employer_pf,

        # health
        "medical_allowance": medical,
        "health_insurance":  insurance,

        # loan
        "loan_balance":      loan_bal,
        "loan_installment":  loan_inst,
        "loan_remaining":    loan_remain,

        # totals
        "total_earnings":    basic + grade_allow + bonus + overtime_pay + medical,
        "total_deductions":  total_deductions,
        "net_salary":        net,
    }


# Smoke test
if __name__ == "__main__":
    sample = dict(basic_salary=60000, grade_level=10, bonus=5000,
                  hours_worked=180, overtime_hours=12,
                  years_of_service=5, has_insurance=1, loan_balance=30000)
    print("Input :", sample)
    print("Output:", compute_payroll(sample))
