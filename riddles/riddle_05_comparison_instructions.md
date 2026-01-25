# 2-Bit Comparator Instructions

## Objective
Design a circuit that compares two 2-bit binary numbers, **A** and **B**.
- **A** is represented by bits $A_1$ (MSB) and $A_0$ (LSB).
- **B** is represented by bits $B_1$ (MSB) and $B_0$ (LSB).

## Outputs
Evaluate the magnitude of the binary numbers:
1. **GT** (Greater Than): High (1) if $A > B$.
2. **EQ** (Equal): High (1) if $A = B$.
3. **LT** (Less Than): High (1) if $A < B$.

## Logic Hint
- **Equality**: $A = B$ if ($A_1 = B_1$) AND ($A_0 = B_0$).
- **Greater**: Compare MSBs first. If $A_1 > B_1$, then A > B. If $A_1 = B_1$, check if $A_0 > B_0$.
- **Less**: Similar logic, or can be derived from NOT (GT or EQ).
