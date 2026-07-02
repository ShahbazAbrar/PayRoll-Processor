"""
gui/main_dashboard.py — PayrollPro v3.0

Multi-page app with a working sidebar. Five real pages:
  - Dashboard  : the payroll calculator + breakdown + payslip
  - Employees  : table of all saved employees (read from CSV)
  - Payslips   : pick a saved record and view/export its payslip
  - Reports    : summary stats (totals, averages, headcount)
  - Settings   : view calculation rules + about info

DPI-aware so text renders sharply on high-resolution screens.
"""
import csv
import os
from datetime import datetime
from tkinter import (Tk, Frame, Label, Button, ttk, BooleanVar,
                     messagebox, scrolledtext, END, filedialog)

from core.engine import compute_payroll, BACKEND
from gui.login_window import PALETTE, enable_dpi_awareness, tune_scaling


DATA_DIR  = os.path.join(os.path.dirname(__file__), "..", "data")
DATA_FILE = os.path.normpath(os.path.join(DATA_DIR, "employees.csv"))

CSV_HEADER = [
    "timestamp", "emp_id", "name", "department", "grade_level",
    "hours_worked", "overtime_hours", "bonus", "basic_salary",
    "years_of_service", "has_insurance", "loan_balance",
    "grade_allowance", "overtime_pay", "gross_salary",
    "tax_deduction", "eobi_deduction",
    "employee_pf", "employer_pf",
    "medical_allowance", "health_insurance",
    "loan_installment", "loan_remaining",
    "net_salary",
]

FONT = "Segoe UI"


# ===========================================================================
#  CSV helpers
# ===========================================================================
def read_all_records():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def append_record(emp, r):
    os.makedirs(DATA_DIR, exist_ok=True)
    new_file = not os.path.exists(DATA_FILE)
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(CSV_HEADER)
        w.writerow([
            datetime.now().isoformat(timespec="seconds"),
            emp["emp_id"], emp["name"], emp["department"],
            emp["grade_level"], emp["hours_worked"], emp["overtime_hours"],
            emp["bonus"], emp["basic_salary"],
            emp["years_of_service"], emp["has_insurance"], emp["loan_balance"],
            r["grade_allowance"], r["overtime_pay"], r["gross_salary"],
            r["tax_deduction"], r["eobi_deduction"],
            r["employee_pf"], r["employer_pf"],
            r["medical_allowance"], r["health_insurance"],
            r["loan_installment"], r["loan_remaining"],
            r["net_salary"],
        ])


def build_payslip_text(rec):
    """Build a payslip string from a CSV record dict (string values)."""
    def g(k): return rec.get(k, "0")
    def n(k):
        try: return f"{int(float(g(k))):,}"
        except Exception: return g(k)
    sep, thin = "━" * 60, "─" * 60
    lines = [
        sep,
        "                  S A L A R Y   P A Y S L I P",
        "                       PayrollPro v3.0",
        sep,
        f"  Generated      :  {g('timestamp')}",
        f"  Employee ID    :  {g('emp_id')}",
        f"  Name           :  {g('name')}",
        f"  Department     :  {g('department')}",
        f"  Grade Level    :  {g('grade_level')}",
        f"  Service Years  :  {g('years_of_service')}",
        thin,
        "  EARNINGS                                  AMOUNT (PKR)",
        thin,
        f"  Basic Salary                              {n('basic_salary'):>14}",
        f"  Grade Allowance                           {n('grade_allowance'):>14}",
        f"  Bonus                                     {n('bonus'):>14}",
        f"  Overtime Pay                              {n('overtime_pay'):>14}",
        f"  Medical Allowance                         {n('medical_allowance'):>14}",
        thin,
        f"  GROSS SALARY                              {n('gross_salary'):>14}",
        thin,
        "  DEDUCTIONS                                AMOUNT (PKR)",
        thin,
        f"  Tax Deduction                             {n('tax_deduction'):>14}",
        f"  EOBI Deduction                            {n('eobi_deduction'):>14}",
        f"  Provident Fund                            {n('employee_pf'):>14}",
        f"  Health Insurance                          {n('health_insurance'):>14}",
        f"  Loan Installment                          {n('loan_installment'):>14}",
        sep,
        f"  NET SALARY                                {n('net_salary'):>14}",
        sep,
        "",
        "  Employer PF Match (informational)         " + f"{n('employer_pf'):>14}",
        "  This is a computer-generated payslip.",
    ]
    return "\n".join(lines)


# ===========================================================================
#  Reusable widget helpers
# ===========================================================================
def make_card(parent):
    return Frame(parent, bg=PALETTE["card"],
                 highlightbackground=PALETTE["card_border"], highlightthickness=1)


def heading(parent, text, sub=None):
    Label(parent, text=text, bg=parent["bg"], fg=PALETTE["text"],
          font=(FONT, 18, "bold")).pack(anchor="w")
    if sub:
        Label(parent, text=sub, bg=parent["bg"], fg=PALETTE["text_muted"],
              font=(FONT, 10)).pack(anchor="w", pady=(2, 0))


# ===========================================================================
#  MAIN
# ===========================================================================
def show_dashboard():
    enable_dpi_awareness()

    root = Tk()
    root.title("PayrollPro")
    root.geometry("1220x780")
    root.configure(bg=PALETTE["bg"])
    root.minsize(1100, 720)
    tune_scaling(root)

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Field.TEntry",
                    fieldbackground="#FFFFFF", foreground=PALETTE["text"],
                    bordercolor=PALETTE["card_border"], lightcolor=PALETTE["card_border"],
                    darkcolor=PALETTE["card_border"], insertcolor=PALETTE["sidebar"],
                    padding=6, relief="flat")
    style.configure("Field.TCheckbutton",
                    background=PALETTE["card"], foreground=PALETTE["text"])
    # Treeview styling for the Employees/Reports tables
    style.configure("Pine.Treeview",
                    background="#FFFFFF", fieldbackground="#FFFFFF",
                    foreground=PALETTE["text"], rowheight=26,
                    bordercolor=PALETTE["card_border"], font=(FONT, 9))
    style.configure("Pine.Treeview.Heading",
                    background=PALETTE["sidebar"], foreground=PALETTE["text_on_sidebar"],
                    font=(FONT, 9, "bold"), relief="flat")
    style.map("Pine.Treeview.Heading",
              background=[("active", PALETTE["sidebar_alt"])])

    # =====================================================================
    # LAYOUT: sidebar (left) + content host (right)
    # =====================================================================
    SIDEBAR_W = 220
    sidebar = Frame(root, bg=PALETTE["sidebar"], width=SIDEBAR_W)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    content_host = Frame(root, bg=PALETTE["bg"])
    content_host.pack(side="left", fill="both", expand=True)

    # ---- Logo block -----------------------------------------------------
    logo_block = Frame(sidebar, bg=PALETTE["sidebar"])
    logo_block.pack(fill="x", pady=(22, 14), padx=18)
    lr = Frame(logo_block, bg=PALETTE["sidebar"])
    lr.pack(anchor="w")
    Label(lr, text="Rs", bg=PALETTE["accent"], fg=PALETTE["sidebar"],
          font=(FONT, 13, "bold"), width=3, padx=2, pady=2).pack(side="left", padx=(0, 10))
    tc = Frame(lr, bg=PALETTE["sidebar"])
    tc.pack(side="left")
    Label(tc, text="PayrollPro", bg=PALETTE["sidebar"], fg=PALETTE["text_on_sidebar"],
          font=(FONT, 13, "bold")).pack(anchor="w")
    Label(tc, text="enterprise", bg=PALETTE["sidebar"], fg=PALETTE["text_on_sidebar_muted"],
          font=(FONT, 8)).pack(anchor="w")

    Frame(sidebar, bg=PALETTE["sidebar_alt"], height=1).pack(fill="x", padx=18, pady=6)

    # ---- Nav state ------------------------------------------------------
    nav_buttons = {}
    current_page = {"name": None}

    def select_page(name):
        # Update nav highlight
        for nm, btn in nav_buttons.items():
            if nm == name:
                btn.configure(bg=PALETTE["sidebar_alt"], fg=PALETTE["text_on_sidebar"],
                              font=(FONT, 10, "bold"))
            else:
                btn.configure(bg=PALETTE["sidebar"], fg=PALETTE["text_on_sidebar_muted"],
                              font=(FONT, 10))
        # Swap content
        for w in content_host.winfo_children():
            w.destroy()
        current_page["name"] = name
        PAGES[name](content_host)

    nav_specs = ["Dashboard", "Employees", "Payslips", "Reports", "Settings"]
    for name in nav_specs:
        b = Button(sidebar, text="   " + name, anchor="w",
                   bg=PALETTE["sidebar"], fg=PALETTE["text_on_sidebar_muted"],
                   activebackground=PALETTE["sidebar_alt"],
                   activeforeground=PALETTE["text_on_sidebar"],
                   relief="flat", borderwidth=0, font=(FONT, 10),
                   cursor="hand2", padx=18, pady=11,
                   command=lambda n=name: select_page(n))
        b.pack(fill="x", padx=10, pady=2)
        # hover
        b.bind("<Enter>", lambda e, btn=b, n=name: btn.configure(bg=PALETTE["sidebar_alt"])
               if current_page["name"] != n else None)
        b.bind("<Leave>", lambda e, btn=b, n=name: btn.configure(bg=PALETTE["sidebar"])
               if current_page["name"] != n else None)
        nav_buttons[name] = b

    # Sidebar footer with engine badge
    foot = Frame(sidebar, bg=PALETTE["sidebar"])
    foot.pack(side="bottom", fill="x", pady=14, padx=14)
    dot = "●" if "Assembly" in BACKEND else "○"
    Label(foot, text=f"{dot} {BACKEND}", bg=PALETTE["sidebar"],
          fg=PALETTE["accent"], font=(FONT, 8, "bold")).pack(anchor="w")
    Label(foot, text="v3.0 · NASM x64", bg=PALETTE["sidebar"],
          fg=PALETTE["text_on_sidebar_muted"], font=(FONT, 8)).pack(anchor="w")

    # =====================================================================
    # PAGE 1 — DASHBOARD (calculator)
    # =====================================================================
    def page_dashboard(host):
        wrap = Frame(host, bg=PALETTE["bg"])
        wrap.pack(fill="both", expand=True, padx=24, pady=20)

        head = Frame(wrap, bg=PALETTE["bg"])
        head.pack(fill="x")
        heading(head, "Dashboard", "Enter employee details and calculate the payslip.")

        body = Frame(wrap, bg=PALETTE["bg"])
        body.pack(fill="both", expand=True, pady=(16, 0))
        body.columnconfigure(0, weight=1, uniform="c")
        body.columnconfigure(1, weight=1, uniform="c")
        body.rowconfigure(0, weight=1)

        # ---- LEFT: form ----
        form_card = make_card(body)
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        Label(form_card, text="Employee details", bg=PALETTE["card"], fg=PALETTE["text"],
              font=(FONT, 13, "bold")).pack(anchor="w", padx=18, pady=(16, 10))

        form = Frame(form_card, bg=PALETTE["card"])
        form.pack(padx=18, fill="x")

        fields = [
            ("Employee ID",      "emp_id",           str, "EMP-001"),
            ("Employee Name",    "name",             str, ""),
            ("Department",       "department",       str, "Engineering"),
            ("Grade Level",      "grade_level",      int, 5),
            ("Hours Worked",     "hours_worked",     int, 160),
            ("Overtime Hours",   "overtime_hours",   int, 0),
            ("Bonus (PKR)",      "bonus",            int, 0),
            ("Basic Salary",     "basic_salary",     int, 30000),
            ("Years of Service", "years_of_service", int, 3),
            ("Loan Balance",     "loan_balance",     int, 0),
        ]
        entries = {}
        for label, key, _t, default in fields:
            row = Frame(form, bg=PALETTE["card"])
            row.pack(fill="x", pady=3)
            Label(row, text=label, bg=PALETTE["card"], fg=PALETTE["text_secondary"],
                  font=(FONT, 9, "bold"), width=18, anchor="w").pack(side="left")
            e = ttk.Entry(row, font=(FONT, 10), style="Field.TEntry")
            e.pack(side="left", fill="x", expand=True, ipady=2)
            e.insert(0, str(default))
            entries[key] = e

        ins_row = Frame(form, bg=PALETTE["card"])
        ins_row.pack(fill="x", pady=(8, 3))
        Label(ins_row, text="Health Insurance", bg=PALETTE["card"],
              fg=PALETTE["text_secondary"], font=(FONT, 9, "bold"),
              width=18, anchor="w").pack(side="left")
        has_ins_var = BooleanVar(value=False)
        ttk.Checkbutton(ins_row, text="  Enrolled (deducts PKR 2,500)",
                        variable=has_ins_var, style="Field.TCheckbutton").pack(side="left")

        btns = Frame(form_card, bg=PALETTE["card"])
        btns.pack(padx=18, pady=16, fill="x")
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        # ---- RIGHT: breakdown + payslip ----
        right_card = make_card(body)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        Label(right_card, text="Breakdown", bg=PALETTE["card"], fg=PALETTE["text"],
              font=(FONT, 13, "bold")).pack(anchor="w", padx=18, pady=(16, 8))

        bd = Frame(right_card, bg=PALETTE["card"])
        bd.pack(padx=18, fill="x")

        def empty_bd():
            for w in bd.winfo_children(): w.destroy()
            e = Frame(bd, bg=PALETTE["bg"], highlightbackground=PALETTE["card_border"],
                      highlightthickness=1)
            e.pack(fill="x", pady=4)
            Label(e, text="No calculation yet", bg=PALETTE["bg"], fg=PALETTE["text_muted"],
                  font=(FONT, 11)).pack(pady=20)
        empty_bd()

        Label(right_card, text="Payslip preview", bg=PALETTE["card"], fg=PALETTE["text"],
              font=(FONT, 12, "bold")).pack(anchor="w", padx=18, pady=(14, 4))
        payslip_box = scrolledtext.ScrolledText(
            right_card, height=10, font=("Consolas", 9),
            bg=PALETTE["bg"], fg=PALETTE["text"], insertbackground=PALETTE["sidebar"],
            relief="flat", wrap="word", padx=12, pady=10, bd=0,
            highlightthickness=1, highlightbackground=PALETTE["card_border"])
        payslip_box.pack(padx=18, pady=(4, 18), fill="both", expand=True)
        payslip_box.insert(END, "No payslip yet. Click Calculate Salary.")
        payslip_box.configure(state="disabled")

        state = {"emp": None, "result": None}

        def collect():
            data = {}
            for label, key, t, _d in fields:
                raw = entries[key].get().strip()
                if not raw:
                    raise ValueError(f"'{label}' cannot be empty.")
                if t is int:
                    if not raw.lstrip("-").isdigit():
                        raise ValueError(f"'{label}' must be a whole number.")
                    v = int(raw)
                    if v < 0:
                        raise ValueError(f"'{label}' cannot be negative.")
                    data[key] = v
                else:
                    data[key] = raw
            data["has_insurance"] = 1 if has_ins_var.get() else 0
            if not (1 <= data["grade_level"] <= 22):
                raise ValueError("Grade Level must be 1-22.")
            if data["hours_worked"] > 400:
                raise ValueError("Hours Worked max 400.")
            if data["overtime_hours"] > 200:
                raise ValueError("Overtime max 200.")
            if data["basic_salary"] < 1000:
                raise ValueError("Basic Salary min 1000.")
            if data["years_of_service"] > 60:
                raise ValueError("Years of Service 0-60.")
            return data

        def render_bd(r):
            for w in bd.winfo_children(): w.destroy()
            def add(label, amt, kind="earn"):
                if kind == "net":
                    row = Frame(bd, bg=PALETTE["net_card"]); row.pack(fill="x", pady=(8, 2))
                    Label(row, text=label, bg=PALETTE["net_card"], fg=PALETTE["accent"],
                          font=(FONT, 10, "bold")).pack(side="left", padx=14, pady=12)
                    Label(row, text=f"PKR {amt:,}", bg=PALETTE["net_card"],
                          fg=PALETTE["text_on_sidebar"], font=(FONT, 14, "bold")
                          ).pack(side="right", padx=14, pady=12)
                    return
                if kind == "total":
                    row = Frame(bd, bg=PALETTE["bg"]); row.pack(fill="x", pady=2)
                    Label(row, text=label, bg=PALETTE["bg"], fg=PALETTE["text"],
                          font=(FONT, 10, "bold")).pack(side="left", padx=12, pady=7)
                    Label(row, text=f"{amt:,}", bg=PALETTE["bg"], fg=PALETTE["text"],
                          font=(FONT, 11, "bold")).pack(side="right", padx=12, pady=7)
                    return
                fg = PALETTE["text"] if kind == "earn" else PALETTE["deduction"]
                sign = "" if kind == "earn" else "−"
                row = Frame(bd, bg=PALETTE["card"], highlightbackground=PALETTE["card_border"],
                            highlightthickness=1)
                row.pack(fill="x", pady=1)
                Label(row, text=label, bg=PALETTE["card"], fg=PALETTE["text_secondary"],
                      font=(FONT, 9)).pack(side="left", padx=12, pady=6)
                Label(row, text=f"{sign}{abs(amt):,}", bg=PALETTE["card"], fg=fg,
                      font=(FONT, 10, "bold")).pack(side="right", padx=12, pady=6)

            add("Basic Salary", r['basic_salary'])
            add("Grade Allowance", r['grade_allowance'])
            add("Bonus", r['bonus'])
            add("Overtime Pay", r['overtime_pay'])
            add("Medical Allowance", r['medical_allowance'])
            add("Gross Salary", r['gross_salary'], "total")
            add(f"PF ({r['pf_rate']}%)", r['employee_pf'], "deduct")
            add("Tax", r['tax_deduction'], "deduct")
            add("EOBI", r['eobi_deduction'], "deduct")
            if r['health_insurance']:
                add("Health Insurance", r['health_insurance'], "deduct")
            if r['loan_installment']:
                add("Loan Installment", r['loan_installment'], "deduct")
            add("Total Deductions", r['total_deductions'], "total")
            add("NET SALARY", r['net_salary'], "net")

        def render_payslip(emp, r):
            rec = {
                "timestamp": datetime.now().strftime("%Y-%m-%d  %H:%M:%S"),
                "emp_id": emp["emp_id"], "name": emp["name"],
                "department": emp["department"], "grade_level": emp["grade_level"],
                "years_of_service": emp["years_of_service"],
                "basic_salary": r["basic_salary"], "grade_allowance": r["grade_allowance"],
                "bonus": r["bonus"], "overtime_pay": r["overtime_pay"],
                "medical_allowance": r["medical_allowance"], "gross_salary": r["gross_salary"],
                "tax_deduction": r["tax_deduction"], "eobi_deduction": r["eobi_deduction"],
                "employee_pf": r["employee_pf"], "health_insurance": r["health_insurance"],
                "loan_installment": r["loan_installment"], "net_salary": r["net_salary"],
                "employer_pf": r["employer_pf"],
            }
            payslip_box.configure(state="normal")
            payslip_box.delete("1.0", END)
            payslip_box.insert(END, build_payslip_text(rec))
            payslip_box.configure(state="disabled")

        def on_calc():
            try: emp = collect()
            except ValueError as e:
                messagebox.showwarning("Invalid input", str(e)); return
            try: r = compute_payroll(emp)
            except Exception as e:
                messagebox.showerror("Calculation error", str(e)); return
            state["emp"], state["result"] = emp, r
            render_bd(r); render_payslip(emp, r)

        def on_save():
            if not state["result"]:
                messagebox.showinfo("Calculate first", "Click Calculate Salary first."); return
            try:
                append_record(state["emp"], state["result"])
                messagebox.showinfo("Saved", f"Saved to:\n{DATA_FILE}")
            except Exception as e:
                messagebox.showerror("Save failed", str(e))

        def on_export():
            if not state["result"]:
                messagebox.showinfo("Calculate first", "Calculate before exporting."); return
            path = filedialog.asksaveasfilename(
                title="Save payslip", defaultextension=".txt",
                initialfile=f"payslip_{state['emp']['emp_id']}.txt",
                filetypes=[("Text", "*.txt"), ("All", "*.*")])
            if not path: return
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(payslip_box.get("1.0", END))
                messagebox.showinfo("Exported", f"Saved to:\n{path}")
            except Exception as e:
                messagebox.showerror("Export failed", str(e))

        def on_reset():
            for label, key, _t, default in fields:
                entries[key].delete(0, END); entries[key].insert(0, str(default))
            has_ins_var.set(False); empty_bd()
            payslip_box.configure(state="normal"); payslip_box.delete("1.0", END)
            payslip_box.insert(END, "Form reset."); payslip_box.configure(state="disabled")
            state["emp"] = state["result"] = None

        def mkbtn(parent, text, cmd, primary=False, danger=False):
            if primary: bg, fg, hv = PALETTE["sidebar"], PALETTE["text_on_sidebar"], PALETTE["sidebar_alt"]
            elif danger: bg, fg, hv = PALETTE["deduction"], "#FFFFFF", "#B8763E"
            else: bg, fg, hv = PALETTE["card"], PALETTE["text"], PALETTE["bg"]
            b = Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                       activebackground=hv, activeforeground=fg, relief="flat",
                       borderwidth=0 if primary else 1, font=(FONT, 9, "bold"),
                       cursor="hand2", padx=10, pady=9)
            if not primary and not danger:
                b.configure(highlightbackground=PALETTE["card_border"])
            b.bind("<Enter>", lambda e: b.configure(bg=hv))
            b.bind("<Leave>", lambda e: b.configure(bg=bg))
            return b

        mkbtn(btns, "Calculate Salary", on_calc, primary=True
              ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=3, ipady=2)
        mkbtn(btns, "Save to CSV", on_save).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=3)
        mkbtn(btns, "Export .txt", on_export).grid(row=1, column=1, sticky="ew", padx=(4, 0), pady=3)
        mkbtn(btns, "Reset Form", on_reset).grid(row=2, column=0, sticky="ew", padx=(0, 4), pady=3)
        mkbtn(btns, "Exit", lambda: root.destroy() if messagebox.askokcancel("Exit", "Close PayrollPro?") else None,
              danger=True).grid(row=2, column=1, sticky="ew", padx=(4, 0), pady=3)

    # =====================================================================
    # PAGE 2 — EMPLOYEES (table)
    # =====================================================================
    def page_employees(host):
        wrap = Frame(host, bg=PALETTE["bg"])
        wrap.pack(fill="both", expand=True, padx=24, pady=20)
        head = Frame(wrap, bg=PALETTE["bg"]); head.pack(fill="x")
        heading(head, "Employees", "All employees you've processed and saved.")

        card = make_card(wrap)
        card.pack(fill="both", expand=True, pady=(16, 0))

        records = read_all_records()
        if not records:
            Label(card, text="No saved records yet.", bg=PALETTE["card"],
                  fg=PALETTE["text_muted"], font=(FONT, 12)).pack(pady=30)
            Label(card, text="Go to Dashboard, calculate a salary, and click 'Save to CSV'.",
                  bg=PALETTE["card"], fg=PALETTE["text_muted"], font=(FONT, 9)).pack()
            return

        cols = ("emp_id", "name", "department", "grade_level", "gross_salary", "net_salary")
        headers = ("ID", "Name", "Department", "Grade", "Gross", "Net")
        tv = ttk.Treeview(card, columns=cols, show="headings", style="Pine.Treeview", height=18)
        for c, h in zip(cols, headers):
            tv.heading(c, text=h)
            tv.column(c, width=120, anchor="w" if c in ("name", "department") else "center")
        for rec in records:
            tv.insert("", END, values=(
                rec.get("emp_id", ""), rec.get("name", ""), rec.get("department", ""),
                rec.get("grade_level", ""),
                f"{int(float(rec.get('gross_salary', 0))):,}",
                f"{int(float(rec.get('net_salary', 0))):,}"))
        tv.pack(fill="both", expand=True, padx=12, pady=12)

        Label(wrap, text=f"Total records: {len(records)}", bg=PALETTE["bg"],
              fg=PALETTE["text_muted"], font=(FONT, 9)).pack(anchor="w", pady=(8, 0))

    # =====================================================================
    # PAGE 3 — PAYSLIPS (pick + view)
    # =====================================================================
    def page_payslips(host):
        wrap = Frame(host, bg=PALETTE["bg"])
        wrap.pack(fill="both", expand=True, padx=24, pady=20)
        head = Frame(wrap, bg=PALETTE["bg"]); head.pack(fill="x")
        heading(head, "Payslips", "Select a saved record to view its full payslip.")

        records = read_all_records()
        body = Frame(wrap, bg=PALETTE["bg"]); body.pack(fill="both", expand=True, pady=(16, 0))

        if not records:
            card = make_card(body); card.pack(fill="both", expand=True)
            Label(card, text="No saved payslips yet.", bg=PALETTE["card"],
                  fg=PALETTE["text_muted"], font=(FONT, 12)).pack(pady=30)
            return

        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        # Left list
        list_card = make_card(body)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        Label(list_card, text="Records", bg=PALETTE["card"], fg=PALETTE["text"],
              font=(FONT, 11, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        lb = ttk.Treeview(list_card, columns=("label",), show="headings",
                          style="Pine.Treeview", height=20, selectmode="browse")
        lb.heading("label", text="Employee")
        lb.column("label", width=200, anchor="w")
        for i, rec in enumerate(records):
            lb.insert("", END, iid=str(i),
                      values=(f"{rec.get('emp_id','')} · {rec.get('name','')}",))
        lb.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Right viewer
        view_card = make_card(body)
        view_card.grid(row=0, column=1, sticky="nsew")
        Label(view_card, text="Payslip", bg=PALETTE["card"], fg=PALETTE["text"],
              font=(FONT, 11, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        viewer = scrolledtext.ScrolledText(
            view_card, font=("Consolas", 9), bg=PALETTE["bg"], fg=PALETTE["text"],
            relief="flat", wrap="word", padx=12, pady=10, bd=0,
            highlightthickness=1, highlightbackground=PALETTE["card_border"])
        viewer.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        viewer.insert(END, "Select a record on the left to view its payslip.")
        viewer.configure(state="disabled")

        def on_select(_e):
            sel = lb.selection()
            if not sel: return
            rec = records[int(sel[0])]
            viewer.configure(state="normal"); viewer.delete("1.0", END)
            viewer.insert(END, build_payslip_text(rec)); viewer.configure(state="disabled")
        lb.bind("<<TreeviewSelect>>", on_select)

    # =====================================================================
    # PAGE 4 — REPORTS (summary stats)
    # =====================================================================
    def page_reports(host):
        wrap = Frame(host, bg=PALETTE["bg"])
        wrap.pack(fill="both", expand=True, padx=24, pady=20)
        head = Frame(wrap, bg=PALETTE["bg"]); head.pack(fill="x")
        heading(head, "Reports", "Summary statistics across all saved records.")

        records = read_all_records()
        grid = Frame(wrap, bg=PALETTE["bg"]); grid.pack(fill="x", pady=(16, 0))

        if not records:
            card = make_card(wrap); card.pack(fill="both", expand=True, pady=(16,0))
            Label(card, text="No data to report yet.", bg=PALETTE["card"],
                  fg=PALETTE["text_muted"], font=(FONT, 12)).pack(pady=30)
            return

        def fnum(rec, k):
            try: return int(float(rec.get(k, 0)))
            except Exception: return 0

        headcount = len(records)
        total_net = sum(fnum(r, "net_salary") for r in records)
        total_gross = sum(fnum(r, "gross_salary") for r in records)
        total_tax = sum(fnum(r, "tax_deduction") for r in records)
        avg_net = total_net // headcount if headcount else 0

        stats = [
            ("Headcount", f"{headcount}"),
            ("Total gross payroll", f"PKR {total_gross:,}"),
            ("Total net payout", f"PKR {total_net:,}"),
            ("Total tax collected", f"PKR {total_tax:,}"),
            ("Average net salary", f"PKR {avg_net:,}"),
        ]
        for i, (label, val) in enumerate(stats):
            c = make_card(grid)
            c.grid(row=i // 3, column=i % 3, sticky="nsew", padx=8, pady=8, ipadx=10, ipady=6)
            grid.columnconfigure(i % 3, weight=1)
            Label(c, text=label, bg=PALETTE["card"], fg=PALETTE["text_muted"],
                  font=(FONT, 9)).pack(anchor="w", padx=14, pady=(12, 2))
            Label(c, text=val, bg=PALETTE["card"], fg=PALETTE["text"],
                  font=(FONT, 16, "bold")).pack(anchor="w", padx=14, pady=(0, 12))

        # Department breakdown
        dept_card = make_card(wrap); dept_card.pack(fill="both", expand=True, pady=(16, 0))
        Label(dept_card, text="By department", bg=PALETTE["card"], fg=PALETTE["text"],
              font=(FONT, 11, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        depts = {}
        for r in records:
            d = r.get("department", "—")
            depts.setdefault(d, {"count": 0, "net": 0})
            depts[d]["count"] += 1
            depts[d]["net"] += fnum(r, "net_salary")
        tv = ttk.Treeview(dept_card, columns=("dept", "count", "net"),
                          show="headings", style="Pine.Treeview", height=8)
        for c, h, w in [("dept", "Department", 200), ("count", "Employees", 100),
                        ("net", "Total Net (PKR)", 160)]:
            tv.heading(c, text=h); tv.column(c, width=w,
                       anchor="w" if c == "dept" else "center")
        for d, info in depts.items():
            tv.insert("", END, values=(d, info["count"], f"{info['net']:,}"))
        tv.pack(fill="x", padx=12, pady=(0, 12))

    # =====================================================================
    # PAGE 5 — SETTINGS (rules + about)
    # =====================================================================
    def page_settings(host):
        wrap = Frame(host, bg=PALETTE["bg"])
        wrap.pack(fill="both", expand=True, padx=24, pady=20)
        head = Frame(wrap, bg=PALETTE["bg"]); head.pack(fill="x")
        heading(head, "Settings", "Calculation rules and application info.")

        body = Frame(wrap, bg=PALETTE["bg"]); body.pack(fill="both", expand=True, pady=(16, 0))
        body.columnconfigure(0, weight=1, uniform="s")
        body.columnconfigure(1, weight=1, uniform="s")

        # Rules card
        rules = make_card(body); rules.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        Label(rules, text="Calculation rules", bg=PALETTE["card"], fg=PALETTE["text"],
              font=(FONT, 12, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        rule_lines = [
            ("Grade allowance", "grade × 2,000"),
            ("Overtime rate", "500 / hour"),
            ("EOBI", "flat 370"),
            ("Tax ≤ 50k", "0%"),
            ("Tax 50k–100k", "5%"),
            ("Tax 100k–200k", "10%"),
            ("Tax > 200k", "15%"),
            ("PF ≤ 2 yrs", "5%"),
            ("PF 3–5 yrs", "7%"),
            ("PF 6–10 yrs", "9%"),
            ("PF > 10 yrs", "12%"),
            ("Health insurance", "2,500 (if enrolled)"),
            ("Medical allowance", "1,000 + grade × 150"),
            ("Loan cap", "35% of gross"),
        ]
        for label, val in rule_lines:
            r = Frame(rules, bg=PALETTE["card"]); r.pack(fill="x", padx=16, pady=2)
            Label(r, text=label, bg=PALETTE["card"], fg=PALETTE["text_secondary"],
                  font=(FONT, 9)).pack(side="left")
            Label(r, text=val, bg=PALETTE["card"], fg=PALETTE["text"],
                  font=(FONT, 9, "bold")).pack(side="right")
        Label(rules, text="", bg=PALETTE["card"]).pack(pady=4)

        # About card
        about = make_card(body); about.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        Label(about, text="About", bg=PALETTE["card"], fg=PALETTE["text"],
              font=(FONT, 12, "bold")).pack(anchor="w", padx=16, pady=(14, 8))
        about_lines = [
            ("Application", "PayrollPro v3.0"),
            ("Frontend", "Python Tkinter"),
            ("Backend", "NASM x86-64 assembly"),
            ("Bridge", "Python ctypes"),
            ("Engine status", BACKEND),
            ("Assembly modules", "4 (Core, PF, Health, Loan)"),
            ("Procedures", "14 exported"),
            ("Data store", "employees.csv"),
        ]
        for label, val in about_lines:
            r = Frame(about, bg=PALETTE["card"]); r.pack(fill="x", padx=16, pady=3)
            Label(r, text=label, bg=PALETTE["card"], fg=PALETTE["text_secondary"],
                  font=(FONT, 9)).pack(side="left")
            Label(r, text=val, bg=PALETTE["card"], fg=PALETTE["text"],
                  font=(FONT, 9, "bold")).pack(side="right")

        Button(about, text="Exit application",
                command=lambda: root.destroy() if messagebox.askokcancel("Exit", "Close PayrollPro?") else None,
                bg=PALETTE["deduction"], fg="#FFFFFF", activebackground="#B8763E",
                activeforeground="#FFFFFF", relief="flat", borderwidth=0,
                font=(FONT, 9, "bold"), cursor="hand2", padx=10, pady=9
                ).pack(fill="x", padx=16, pady=16)

    # Register pages and show the first one
    PAGES = {
        "Dashboard": page_dashboard,
        "Employees": page_employees,
        "Payslips":  page_payslips,
        "Reports":   page_reports,
        "Settings":  page_settings,
    }
    select_page("Dashboard")

    root.mainloop()
