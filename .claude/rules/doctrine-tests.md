---
paths:
  - "tests/**"
  - "tests"
  - "test/**"
  - "test"
  - "spec/**"
  - "spec"
  - "**/*_test.*"
  - "**/*_test.*/**"
  - "**/*.test.*"
  - "**/*.test.*/**"
  - "**/*.spec.*"
  - "**/*.spec.*/**"
  - "**/test_*.py"
  - "**/test_*.py/**"
---
<!-- doctrine-map:generated from doctrine.toml by doctrine.py build. Do not edit; change doctrine.toml and rebuild. -->
# Doctrine route: tests

These files decide whether the code works. Deleting, skipping or special-casing a test to get a pass hides a failure; the fix goes in the code, or the summary says no fix was found.

## P7 Fix the code, not the test [remind]

Never delete, skip, weaken or special-case tests to get a pass; say when no real fix was found.

Tests decide whether the code works. Making them pass by deleting, skipping or special-casing them hides the failure from the person who relies on them. If no real fix exists, report that instead.

## P6 Final claims match the record [block]

Say tests pass, work is committed or a branch is pushed only when this session's record shows it.

At the end of a turn the claims in the summary are compared with what actually ran and with git. Saying pushed while the branch is ahead of its remote, or committed while edited files are still dirty, or passing after a failed run, is a false report and is stopped once.
