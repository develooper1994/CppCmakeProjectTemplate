# AGENTS.md

## Agent Execution Contract

### Workflow (MANDATORY)

1. ANALYZE
- Identify affected area:
  libs / apps / tests / external / docs / cmake

2. IMPACT
- New target?
- CMake change?
- Tests needed?
- Docs needed?
- Build impact?

3. PLAN
- Choose minimal safe change
- Avoid unrelated edits

4. IMPLEMENT
- Complete code only
- No placeholders
- Respect structure

5. INTEGRATE
If target added:
- use `python3 scripts/libtool.py add <n>` for new libraries
- or manually: update CMake, link deps, apply warnings, add docs + README + tests
- libtool commands: add / remove / rename / move / deps / list / tree / doctor

6. VALIDATE
- build integrity
- presets intact
- external isolation respected
- warnings correct

7. OUTPUT
- full, working result
- no partial code

---

## Fail-Safe Rule

If uncertain:
→ do minimal safe change  
→ NEVER break build  

---

## Forbidden Actions

- editing external/
- removing presets
- disabling compile_commands
- global CMake hacks
- large blind refactors

---

## Priority

1. Build integrity
2. Correctness
3. Isolation
4. Maintainability
