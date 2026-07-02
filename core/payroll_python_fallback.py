"""
core/payroll_python_fallback.py
-------------------------------
Mirrors payroll.asm exactly. Used automatically when payroll.dll fails to load.
"""

# Module 1 constants
GRADE_RATE     = 2000
OVERTIME_RATE  = 500
EOBI_AMOUNT    = 370
TAX_SLABS = [
    (50000,   0),
    (100000,  5),
    (200000, 10),
    (None,   15),
]

# Module 2 constants
PF_TABLE = [
    (2,   5),
    (5,   7),
    (10,  9),
    (None, 12),
]
EMPLOYER_PF_MATCH = 100   # 100% match

# Module 3 constants
INSURANCE_BASE     = 2500
MEDICAL_PER_GRADE  = 150
MEDICAL_BASE       = 1000

# Module 4 constants
LOAN_TABLE = [
    (10000,   6),
    (50000,   12),
    (100000,  24),
    (None,    36),
]
MAX_LOAN_PCT = 35


# ------- Module 1
def calc_grade_allowance(grade): return grade * GRADE_RATE
def calc_overtime_pay(hours):    return hours * OVERTIME_RATE
def calc_gross(b, g, bn, ot):    return b + calc_grade_allowance(g) + bn + calc_overtime_pay(ot)

def calc_tax(gross):
    for limit, percent in TAX_SLABS:
        if limit is None or gross <= limit:
            return gross * percent // 100
    return 0

def calc_eobi():                 return EOBI_AMOUNT
def calc_net_salary(g, t, e):    return max(0, g - t - e)


# ------- Module 2
def calc_pf_rate(years):
    for upper, percent in PF_TABLE:
        if upper is None or years <= upper:
            return percent
    return 0

def calc_provident_fund(basic, years):
    return basic * calc_pf_rate(years) // 100

def calc_employer_pf(emp_pf):
    return emp_pf * EMPLOYER_PF_MATCH // 100


# ------- Module 3
def calc_health_insurance(has):
    return INSURANCE_BASE if has else 0

def calc_medical_allowance(grade):
    return MEDICAL_BASE + grade * MEDICAL_PER_GRADE


# ------- Module 4
def calc_loan_installment(loan_balance, gross):
    if loan_balance <= 0:
        return 0
    for upper, months in LOAN_TABLE:
        if upper is None or loan_balance <= upper:
            base = loan_balance // months
            cap  = gross * MAX_LOAN_PCT // 100
            return min(base, cap)
    return 0

def calc_loan_remaining(balance, inst):
    return max(0, balance - inst)


def calc_final_net(gross, extra_earnings, total_deductions):
    return max(0, gross + extra_earnings - total_deductions)


# ------- High-level
def compute_payroll(emp: dict) -> dict:
    basic    = emp["basic_salary"]
    grade    = emp["grade_level"]
    bonus    = emp["bonus"]
    ot_hours = emp["overtime_hours"]
    years    = emp["years_of_service"]
    has_ins  = emp["has_insurance"]
    loan_bal = emp["loan_balance"]

    grade_allow  = calc_grade_allowance(grade)
    overtime_pay = calc_overtime_pay(ot_hours)
    gross        = calc_gross(basic, grade, bonus, ot_hours)
    tax          = calc_tax(gross)
    eobi         = calc_eobi()

    pf_rate      = calc_pf_rate(years)
    employee_pf  = calc_provident_fund(basic, years)
    employer_pf  = calc_employer_pf(employee_pf)

    insurance    = calc_health_insurance(1 if has_ins else 0)
    medical      = calc_medical_allowance(grade)

    loan_inst    = calc_loan_installment(loan_bal, gross)
    loan_remain  = calc_loan_remaining(loan_bal, loan_inst)

    total_extra_earnings = medical
    total_deductions     = tax + eobi + employee_pf + insurance + loan_inst
    net                  = calc_final_net(gross, total_extra_earnings, total_deductions)

    return {
        "basic_salary":      basic,
        "grade_allowance":   grade_allow,
        "bonus":             bonus,
        "overtime_pay":      overtime_pay,
        "gross_salary":      gross,
        "tax_deduction":     tax,
        "eobi_deduction":    eobi,
        "pf_rate":           pf_rate,
        "employee_pf":       employee_pf,
        "employer_pf":       employer_pf,
        "medical_allowance": medical,
        "health_insurance":  insurance,
        "loan_balance":      loan_bal,
        "loan_installment":  loan_inst,
        "loan_remaining":    loan_remain,
        "total_earnings":    basic + grade_allow + bonus + overtime_pay + medical,
        "total_deductions":  total_deductions,
        "net_salary":        net,
    }
