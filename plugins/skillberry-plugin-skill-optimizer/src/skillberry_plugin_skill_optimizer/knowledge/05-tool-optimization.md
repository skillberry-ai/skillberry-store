# Optimizing Tools

Tools in the SkillBerry Store are Python functions. Every top-level `def` in a
`.py` file becomes a callable tool. Quality has three independent dimensions —
**correctness**, **discoverability**, and **usability** — and a tool that scores
poorly on any one of them underperforms even if the others are excellent.

---

## Three Quality Dimensions

### 1. Correctness
The function does what it says it does. It handles edge cases, validates inputs,
and fails loudly with informative errors rather than silently returning wrong results.

### 2. Discoverability (docstring clarity)
An agent reading only the function name and docstring can determine whether this
is the right tool for a task. Poor discoverability means agents call the wrong tool
or miss the tool entirely.

### 3. Usability (parameter documentation)
An agent can call the function correctly on the first attempt without guessing
parameter types, formats, or constraints. Poor parameter documentation means
agents pass wrong types, out-of-range values, or missing required fields.

Treat all three as separate problems. A function with excellent logic but a vague
docstring is not a good tool.

---

## Diagnosing Which Dimension Fails

Before editing, identify which dimension is actually broken:

| Symptom in execution traces | Dimension | Fix |
|---|---|---|
| Agent calls a different tool for a task this one handles | Discoverability | Rewrite the docstring description |
| Agent calls this tool but with wrong arguments | Usability | Improve parameter documentation |
| Agent calls tool correctly but result is wrong | Correctness | Fix the logic |
| Agent tries tool, gets an exception, gives up | All three | Improve error messages AND parameter docs |
| Tool works for common case but fails on edge inputs | Correctness | Add validation and edge-case handling |

---

## Correctness

### Input validation
Validate at the boundary. Don't assume callers provide clean inputs.

```python
def calculate_discount(price: float, discount_pct: float) -> float:
    """..."""
    if price < 0:
        raise ValueError(f"price must be non-negative, got {price}")
    if not 0 <= discount_pct <= 100:
        raise ValueError(f"discount_pct must be 0-100, got {discount_pct}")
    return price * (1 - discount_pct / 100)
```

### Informative error messages
Error messages are part of the tool's interface. Agents read them when a call
fails. A good error message tells the agent exactly what was wrong and what to
provide instead.

**Poor:**
```python
raise ValueError("invalid input")
```

**Good:**
```python
raise ValueError(
    f"status must be one of ['active', 'inactive', 'pending'], got {status!r}"
)
```

### Self-contained code
Every `.py` file executes as a flat script. Cross-file imports **do not work**:

```python
# FORBIDDEN — causes "No module named 'scripts'" at runtime
from scripts.utils import call_api
import scripts.helpers
```

Use only stdlib imports. Runtime helpers provided by the store (e.g. `call_api`,
`store_result`) are injected into scope automatically — call them directly without
importing.

### Simple, serialisable types
All parameters and return values must be simple JSON-serialisable types. The store
cannot pass complex objects between tools.

| Use | Avoid |
|---|---|
| `str`, `int`, `float`, `bool` | `datetime`, `Path`, custom objects |
| `list[str]`, `dict[str, int]` | `pd.DataFrame`, `np.ndarray` |
| `Optional[str]` | `Any`, bare `Dict`, bare `List` |

If you need to work with complex types internally, convert at the boundary:
```python
def analyse_data(rows: list[dict]) -> dict:
    """..."""
    import json
    # work internally however you like
    return {"result": "..."}
```

### Security
Never introduce:
- `eval()`, `exec()`, `__import__()`
- `os.system()`, `subprocess.run()` with user-controlled strings
- `pickle.loads()`, `yaml.load()` (use `yaml.safe_load()`)
- Hardcoded credentials, API keys, passwords, tokens

---

## Discoverability

The docstring's **first line** (the one-line summary) is the primary signal agents
use to decide whether to call a tool. It must:

- State what the function **does**, not how it works
- Use action verbs: "Fetch", "Calculate", "Extract", "Convert", "Validate"
- Include the domain nouns that appear in user requests: "invoice", "order",
  "customer", "repository"
- Be specific enough to distinguish this tool from similar ones

**Poor (too vague):**
```python
def process_data(data: dict) -> dict:
    """Process the input data."""
```

**Poor (describes implementation):**
```python
def get_discount(price: float, pct: float) -> float:
    """Apply percentage-based reduction using multiplication."""
```

**Good:**
```python
def calculate_order_discount(order_total: float, discount_pct: float) -> float:
    """Calculate the final price after applying a percentage discount to an order total."""
```

When optimizing discoverability, ask: "If an agent sees only this one line, would
it know exactly when to reach for this tool?" If the answer is no, rewrite it.

---

## Usability — Parameter Documentation

Each parameter needs enough documentation that an agent can call the tool correctly
without guessing.

### Required per parameter

1. **Type** — in the function signature AND in the docstring
2. **What it is** — brief description (one line)
3. **Constraints** — range, format, allowed values, or units if relevant
4. **Default behaviour** — what happens if optional and omitted

### Google-style docstring format

```python
def fetch_orders(
    customer_id: str,
    status: str = "active",
    limit: int = 50,
) -> list[dict]:
    """Fetch orders for a customer, filtered by status.

    Args:
        customer_id: UUID string identifying the customer. Must be a valid UUID v4.
        status: Filter orders by status. One of: 'active', 'completed', 'cancelled'.
            Defaults to 'active'.
        limit: Maximum number of orders to return. Must be 1-200. Defaults to 50.

    Returns:
        List of order dicts, each with keys: id, status, total, created_at.

    Raises:
        ValueError: If customer_id is not a valid UUID or status is not recognised.
        RuntimeError: If the orders service is unreachable.
    """
```

### Use Literal types for fixed value sets

When a parameter accepts only specific values, declare them explicitly:

```python
from typing import Literal

def set_order_status(
    order_id: str,
    status: Literal["active", "completed", "cancelled"],
) -> bool:
    """Update the status of an order."""
```

This lets agents pass the correct value on the first attempt without guessing.

### Return value documentation

Document what the return value contains. If it's a dict, list the keys:

```python
Returns:
    Dict with keys:
        - 'success' (bool): Whether the operation completed.
        - 'id' (str): The new record's UUID.
        - 'errors' (list[str]): Validation errors, empty if success is True.
```

---

## When to Split vs. Consolidate Functions

**Split** a function when:
- It does two distinct things that agents might need independently
- The docstring requires "and" to describe what it does
- Different callers need only part of its behaviour

**Consolidate** functions when:
- Two functions always get called together
- One function is only ever a helper for another (and can't be a cross-file import)
- Two functions have nearly identical signatures and logic

When optimizing, err toward splitting. A tool with a narrow, clear purpose is
more likely to be called correctly than one that does multiple things.

---

## Naming

Function names become tool names in the store. They must be:

- **Verb-first**: `calculate_`, `fetch_`, `extract_`, `validate_`, `convert_`
- **Domain-specific**: include the entity the function acts on (`order`, `invoice`, `user`)
- **Distinguishable**: if the skill has `get_order` and `get_invoice`, the names must
  make the difference immediately obvious
- **Snake_case** only

**Poor names:** `process`, `handle`, `do_thing`, `run`, `execute`
**Good names:** `calculate_invoice_total`, `fetch_customer_orders`, `validate_iban`

---

## Checklist Before Finalising a Tool

**Correctness:**
- [ ] All parameters validated with informative error messages
- [ ] Edge cases handled (empty input, None, out-of-range values)
- [ ] No cross-file imports (`from scripts.x import y`)
- [ ] No `eval`, `exec`, hardcoded credentials, or unsafe calls
- [ ] All types are simple and JSON-serialisable

**Discoverability:**
- [ ] First docstring line uses an action verb and names the domain entity
- [ ] One-line summary distinguishes this tool from similar ones in the skill
- [ ] Name is verb-first and domain-specific

**Usability:**
- [ ] Every parameter has type annotation in signature AND docstring
- [ ] Constraints documented (range, format, allowed values)
- [ ] Return value documents its structure if it's a dict or list
- [ ] `Literal[...]` used for parameters with a fixed set of allowed values
- [ ] Exceptions documented with the conditions that trigger them
