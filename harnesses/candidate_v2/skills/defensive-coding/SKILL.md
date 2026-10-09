---
name: defensive-coding
description: Guidelines and patterns for robust defensive programming, concurrency control, and encoding.
---

# Defensive Coding Skill

## Thread Safety Patterns
When implementing stateful classes accessed by multiple concurrent callers:
- Initialize `self._lock = threading.Lock()` in `__init__`.
- Wrap mutating state operations within `with self._lock:`.

## Boundary Validation
- Validate numeric ranges immediately: `if limit <= 0 or limit > 100: raise ValueError(...)`.
- Sanitize and safely decode tokens using `base64.urlsafe_b64encode` and `base64.urlsafe_b64decode`.
