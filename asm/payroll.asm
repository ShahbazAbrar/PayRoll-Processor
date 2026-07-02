; ============================================================================
;  payroll.asm  --  PayrollPro v2.0 -- Assembly calculation core
;  
;  Output  : payroll.dll (linked by gcc / MinGW)
;
;  Demonstrates every required Assembly Language concept:
;    * Arithmetic operations  ......... ADD, SUB, IMUL, IDIV
;    * Arrays ......................... tax_slabs[], pf_table[], loan_table[]
;    * Loops .......................... LOOP, conditional walks
;    * Conditional statements ......... CMP, JG, JLE, JZ, JGE, TEST
;    * Registers ...................... RAX, RBX, RCX, RDX, R8-R15
;    * Memory variables ............... .data section constants
;    * Input validation ............... clamp negatives in net_salary
;    * Procedures / functions ......... 11 exported procedures
;    * Formatting / arithmetic logic .. percent calc via gross*p/100
;
;  MODULE LAYOUT
;  -------------
;    MODULE 1  ::  Core Payroll  (gross, tax, EOBI, net)
;    MODULE 2  ::  Provident Fund  (PF lookup + employer share)
;    MODULE 3  ::  Health Insurance & Medical Allowance
;    MODULE 4  ::  Loan Repayment  (installment + remaining balance)
;
;  Microsoft x64 calling convention:
;     1st arg -> RCX
;     2nd arg -> RDX
;     3rd arg -> R8
;     4th arg -> R9
;     return  -> RAX
;     RBX, RBP, RDI, RSI, R12-R15 are CALLEE-SAVED (push/pop when used).
; ============================================================================


;═════════════════════════════════════════════════════════════════════════════
;  .data section   ::  All memory variables and lookup tables
;═════════════════════════════════════════════════════════════════════════════

section .data

    ;----------------------------- Module 1 constants ------------------------
    grade_rate          dq  2000        ; PKR allowance per grade level
    overtime_rate       dq  500         ; PKR per overtime hour
    eobi_amount         dq  370         ; flat EOBI deduction

    ; Tax slab ARRAY -- pairs of [upper_limit, percent].
    tax_slabs:
        dq  50000,   0      ; 0%   if gross <= 50,000
        dq  100000,  5      ; 5%   if 50,001 - 100,000
        dq  200000,  10     ; 10%  if 100,001 - 200,000
        dq  0,       15     ; 15%  sentinel (everything above)
    tax_slabs_count     equ 4

    ;----------------------------- Module 2 constants ------------------------
    ; PF contribution slab ARRAY -- pairs of [years_of_service, percent_rate]
    ; Walked in a LOOP to find the right contribution percentage.
    pf_table:
        dq  2,   5          ; 5%   if years <= 2
        dq  5,   7          ; 7%   if 3-5 years
        dq  10,  9          ; 9%   if 6-10 years
        dq  0,   12         ; 12%  sentinel (10+ years)
    pf_table_count      equ 4

    employer_pf_match   dq  100         ; employer matches 100% of employee PF

    ;----------------------------- Module 3 constants ------------------------
    insurance_base      dq  2500        ; flat health insurance premium
    medical_per_grade   dq  150         ; medical allowance per grade level
    medical_base        dq  1000        ; minimum medical allowance

    ;----------------------------- Module 4 constants ------------------------
    ; Loan repayment ARRAY -- pairs of [loan_amount_threshold, months_to_repay]
    loan_table:
        dq  10000,   6      ; <= 10k:  6-month repayment
        dq  50000,   12     ; <= 50k:  12-month repayment
        dq  100000,  24     ; <= 100k: 24-month repayment
        dq  0,       36     ; sentinel: 36-month repayment for big loans
    loan_table_count    equ 4

    max_loan_pct        dq  35          ; loan installment max 35% of gross


;═════════════════════════════════════════════════════════════════════════════
;  .text section   ::  Exported procedures
;═════════════════════════════════════════════════════════════════════════════

section .text

    ; -- Module 1
    global calc_grade_allowance
    global calc_overtime_pay
    global calc_gross
    global calc_tax
    global calc_eobi
    global calc_net_salary

    ; -- Module 2
    global calc_pf_rate
    global calc_provident_fund
    global calc_employer_pf

    ; -- Module 3
    global calc_health_insurance
    global calc_medical_allowance

    ; -- Module 4
    global calc_loan_installment
    global calc_loan_remaining

    ; -- Final aggregator
    global calc_final_net


;═════════════════════════════════════════════════════════════════════════════
;═                                                                            ═
;═          MODULE 1  ::  CORE PAYROLL  (gross, tax, EOBI, net)               ═
;═                                                                            ═
;═════════════════════════════════════════════════════════════════════════════

; ----------------------------------------------------------------------------
;  long calc_grade_allowance(long grade_level)
;      returns grade_level * 2000
; ----------------------------------------------------------------------------
calc_grade_allowance:
    mov     rax, rcx                 ; rax = grade_level
    mov     rbx, [rel grade_rate]    ; rbx = 2000
    imul    rax, rbx                 ; rax = grade_level * 2000
    ret


; ----------------------------------------------------------------------------
;  long calc_overtime_pay(long overtime_hours)
;      returns overtime_hours * 500
; ----------------------------------------------------------------------------
calc_overtime_pay:
    mov     rax, rcx
    mov     rbx, [rel overtime_rate]
    imul    rax, rbx
    ret


; ----------------------------------------------------------------------------
;  long calc_gross(long basic, long grade_level, long bonus, long ot_hours)
;     gross = basic + (grade_level * 2000) + bonus + (ot_hours * 500)
; ----------------------------------------------------------------------------
calc_gross:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15

    mov     r12, rcx                  ; r12 = basic
    mov     r13, rdx                  ; r13 = grade_level
    mov     r14, r8                   ; r14 = bonus
    mov     r15, r9                   ; r15 = ot_hours

    ; grade_allowance = grade_level * 2000
    mov     rax, r13
    imul    rax, [rel grade_rate]
    mov     rbx, rax

    ; overtime_pay = ot_hours * 500
    mov     rax, r15
    imul    rax, [rel overtime_rate]
    mov     rcx, rax

    ; sum it all together
    mov     rax, r12
    add     rax, rbx
    add     rax, r14
    add     rax, rcx

    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret


; ----------------------------------------------------------------------------
;  long calc_tax(long gross)
;      Walks the tax_slabs ARRAY in a LOOP, finds the matching slab,
;      then computes  tax = gross * percent / 100.
; ----------------------------------------------------------------------------
calc_tax:
    push    rbx
    push    r12
    push    r13

    mov     r12, rcx                  ; r12 = gross
    lea     rbx, [rel tax_slabs]      ; rbx = base of slab array
    mov     rcx, tax_slabs_count      ; loop counter

.find_slab:
    mov     rax, [rbx]                ; upper_limit
    mov     r13, [rbx + 8]            ; percent

    test    rax, rax
    jz      .matched                  ; sentinel (limit=0)

    cmp     r12, rax
    jle     .matched                  ; gross <= limit -> use this slab

    add     rbx, 16                   ; advance to next slab (16 bytes per pair)
    loop    .find_slab

.matched:
    mov     rax, r12
    imul    rax, r13                  ; gross * percent
    mov     rbx, 100
    cqo
    idiv    rbx                       ; rax = (gross * percent) / 100

    pop     r13
    pop     r12
    pop     rbx
    ret


; ----------------------------------------------------------------------------
;  long calc_eobi(void)
;      Returns flat EOBI deduction.
; ----------------------------------------------------------------------------
calc_eobi:
    mov     rax, [rel eobi_amount]
    ret


; ----------------------------------------------------------------------------
;  long calc_net_salary(long gross, long tax, long eobi)
;      net = gross - tax - eobi  (clamped at 0)
; ----------------------------------------------------------------------------
calc_net_salary:
    mov     rax, rcx                  ; rax = gross
    sub     rax, rdx                  ; rax -= tax
    sub     rax, r8                   ; rax -= eobi
    cmp     rax, 0
    jge     .done
    xor     rax, rax                  ; clamp to 0
.done:
    ret


;═════════════════════════════════════════════════════════════════════════════
;═                                                                            ═
;═          MODULE 2  ::  PROVIDENT FUND  (employee + employer share)         ═
;═                                                                            ═
;═════════════════════════════════════════════════════════════════════════════
; PF (Provident Fund) is a long-term savings scheme.
; Employees contribute a percentage of basic salary based on years of service.
; Employer matches 100% of employee contribution.
; Higher service years = higher contribution rate.
;═════════════════════════════════════════════════════════════════════════════

; ----------------------------------------------------------------------------
;  long calc_pf_rate(long years_of_service)
;      Walks pf_table ARRAY in a LOOP, returns the matching percentage.
;      Demonstrates: arrays, loops, conditional branching.
; ----------------------------------------------------------------------------
calc_pf_rate:
    push    rbx
    push    r12
    push    r13

    mov     r12, rcx                  ; r12 = years_of_service
    lea     rbx, [rel pf_table]       ; rbx = base of PF table
    mov     rcx, pf_table_count       ; loop counter

.find_pf_slab:
    mov     rax, [rbx]                ; rax = upper years threshold
    mov     r13, [rbx + 8]            ; r13 = percent for this slab

    test    rax, rax
    jz      .pf_matched               ; sentinel -> use this rate

    cmp     r12, rax                  ; years <= threshold?
    jle     .pf_matched

    add     rbx, 16                   ; next slab
    loop    .find_pf_slab

.pf_matched:
    mov     rax, r13                  ; return the matched percent

    pop     r13
    pop     r12
    pop     rbx
    ret


; ----------------------------------------------------------------------------
;  long calc_provident_fund(long basic, long years_of_service)
;      Employee PF contribution = basic * pf_rate(years) / 100
;      Calls calc_pf_rate as a sub-procedure (demonstrates nested calls).
; ----------------------------------------------------------------------------
calc_provident_fund:
    push    rbx
    push    r12
    sub     rsp, 32                   ; reserve 32-byte shadow space for callee

    mov     r12, rcx                  ; r12 = basic

    ; Call calc_pf_rate(years_of_service)
    mov     rcx, rdx                  ; arg = years_of_service
    call    calc_pf_rate
    mov     rbx, rax                  ; rbx = pf_percent

    ; pf = basic * percent / 100
    mov     rax, r12
    imul    rax, rbx
    mov     rcx, 100
    cqo
    idiv    rcx                       ; rax = (basic * pf_percent) / 100

    add     rsp, 32
    pop     r12
    pop     rbx
    ret


; ----------------------------------------------------------------------------
;  long calc_employer_pf(long employee_pf)
;      Employer matches employee contribution 100%.
;      Computed as: employee_pf * employer_pf_match / 100
; ----------------------------------------------------------------------------
calc_employer_pf:
    mov     rax, rcx                  ; rax = employee_pf
    imul    rax, [rel employer_pf_match]  ; * 100
    mov     rbx, 100
    cqo
    idiv    rbx                       ; / 100  (i.e. same value, but shows math)
    ret


;═════════════════════════════════════════════════════════════════════════════
;═                                                                            ═
;═          MODULE 3  ::  HEALTH INSURANCE & MEDICAL ALLOWANCE                ═
;═                                                                            ═
;═════════════════════════════════════════════════════════════════════════════
; Health insurance: flat premium deducted (only if employee opts in).
; Medical allowance: additive benefit calculated from grade level.
;═════════════════════════════════════════════════════════════════════════════

; ----------------------------------------------------------------------------
;  long calc_health_insurance(long has_insurance)
;      Returns insurance_base if has_insurance != 0, else returns 0.
;      Demonstrates: conditional with TEST instruction.
; ----------------------------------------------------------------------------
calc_health_insurance:
    test    rcx, rcx                  ; is has_insurance zero?
    jz      .no_insurance
    mov     rax, [rel insurance_base] ; return 2500
    ret
.no_insurance:
    xor     rax, rax                  ; return 0
    ret


; ----------------------------------------------------------------------------
;  long calc_medical_allowance(long grade_level)
;      Returns medical_base + (grade_level * medical_per_grade)
;      Demonstrates: arithmetic combination with memory variables.
; ----------------------------------------------------------------------------
calc_medical_allowance:
    push    rbx

    mov     rax, rcx                  ; rax = grade_level
    imul    rax, [rel medical_per_grade]  ; * 150
    mov     rbx, [rel medical_base]   ; rbx = 1000
    add     rax, rbx                  ; rax = 1000 + (grade * 150)

    pop     rbx
    ret


;═════════════════════════════════════════════════════════════════════════════
;═                                                                            ═
;═          MODULE 4  ::  LOAN REPAYMENT  (installment + remaining)           ═
;═                                                                            ═
;═════════════════════════════════════════════════════════════════════════════
; If employee has an outstanding loan, monthly installment is calculated as
;   installment = loan_balance / months_to_repay
; where months_to_repay depends on the loan size (looked up in loan_table).
; Installment is capped at 35% of gross salary (max_loan_pct).
;═════════════════════════════════════════════════════════════════════════════

; ----------------------------------------------------------------------------
;  long calc_loan_installment(long loan_balance, long gross_salary)
;      Looks up months_to_repay from loan_table ARRAY (LOOP + conditional).
;      Computes installment = loan_balance / months.
;      Caps it at 35% of gross_salary if installment is too high.
; ----------------------------------------------------------------------------
calc_loan_installment:
    push    rbx
    push    r12
    push    r13
    push    r14

    mov     r12, rcx                  ; r12 = loan_balance
    mov     r13, rdx                  ; r13 = gross_salary

    ; If loan balance is 0, return 0 immediately
    test    r12, r12
    jz      .no_loan

    ; -- Step 1: walk loan_table to find months_to_repay
    lea     rbx, [rel loan_table]
    mov     rcx, loan_table_count

.find_loan_slab:
    mov     rax, [rbx]                ; threshold
    mov     r14, [rbx + 8]            ; months for this slab

    test    rax, rax
    jz      .loan_matched             ; sentinel

    cmp     r12, rax
    jle     .loan_matched

    add     rbx, 16
    loop    .find_loan_slab

.loan_matched:
    ; -- Step 2: installment = loan_balance / months
    mov     rax, r12
    cqo
    idiv    r14                       ; rax = loan / months

    ; -- Step 3: cap at 35% of gross
    mov     rbx, rax                  ; rbx = computed installment

    mov     rax, r13                  ; rax = gross
    imul    rax, [rel max_loan_pct]   ; * 35
    mov     rcx, 100
    cqo
    idiv    rcx                       ; rax = gross * 35 / 100 = max cap

    cmp     rbx, rax                  ; installment > cap?
    jle     .within_cap
    mov     rbx, rax                  ; cap it

.within_cap:
    mov     rax, rbx
    jmp     .done_loan

.no_loan:
    xor     rax, rax                  ; no loan -> 0 installment

.done_loan:
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret


; ----------------------------------------------------------------------------
;  long calc_loan_remaining(long loan_balance, long installment)
;      Returns loan_balance - installment, clamped at 0.
; ----------------------------------------------------------------------------
calc_loan_remaining:
    mov     rax, rcx
    sub     rax, rdx
    cmp     rax, 0
    jge     .ok
    xor     rax, rax
.ok:
    ret


;═════════════════════════════════════════════════════════════════════════════
;═                                                                            ═
;═          FINAL AGGREGATOR  ::  pulls every module together                 ═
;═                                                                            ═
;═════════════════════════════════════════════════════════════════════════════

; ----------------------------------------------------------------------------
;  long calc_final_net(long gross, long total_earnings_extra,
;                      long total_deductions)
;      final = gross + extra_earnings - total_deductions (clamped at 0)
;      Used by the Python bridge to compute the final figure.
; ----------------------------------------------------------------------------
calc_final_net:
    mov     rax, rcx                  ; rax = gross
    add     rax, rdx                  ; + extra earnings (medical, etc.)
    sub     rax, r8                   ; - total deductions
    cmp     rax, 0
    jge     .final_ok
    xor     rax, rax
.final_ok:
    ret
