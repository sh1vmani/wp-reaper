
## Coding Philosophy
Follow principles from docs/karpathy-skills/ when writing code:
- Prefer simple, readable code over clever code
- No unnecessary abstractions
- No premature optimization
- Write code that is obvious to read
- Delete code aggressively -- less code = fewer bugs
- Every function should do one thing well
- No magic numbers, no magic strings -- name everything
- If you have to comment to explain what code does, rewrite it

## Karpathy Guidelines (from docs/karpathy-skills/skills/karpathy-guidelines/SKILL.md)

### 1. Think Before Coding
- State assumptions explicitly before writing any code
- If multiple interpretations exist, present them -- do not pick silently
- If a simpler approach exists, say so
- If something is unclear, stop and ask

### 2. Simplicity First
- Minimum code that solves the problem -- nothing speculative
- No features beyond what was asked
- No abstractions for single-use code
- No flexibility or configurability that was not requested
- If you write 200 lines and it could be 50, rewrite it

### 3. Surgical Changes
- Touch only what you must
- Do not improve adjacent code, comments, or formatting
- Do not refactor things that are not broken
- Match existing style even if you would do it differently
- Every changed line must trace directly to the request

### 4. Goal-Driven Execution
- Define success criteria before starting
- For every task state a brief plan with verify steps:
  1. [Step] -> verify: [check]
  2. [Step] -> verify: [check]
- Do not move to next step until current step is verified
