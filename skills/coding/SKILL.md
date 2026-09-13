---
name: coding
description: >-
  Use this skill when writing, editing, or reviewing code — across any language (Python, TypeScript, Kotlin, Go, Rust, Java, YAML, shell, Gherkin, and more). Covers repo discovery (reading CLAUDE.md, README, CONTRIBUTING/ARCHITECTURE, CI workflows, and formatter/linter config to learn a repo's specific rules before touching anything), code review for design flaws (SOLID, Clean Code, Naming, Constants, Localization, Error Handling, separation of concerns), reviewing AI-generated diffs for hallucinated APIs and silent scope creep, proposing edits with justification, writing or fixing tests, authoring new code, refactoring, assessing style violations, and safe git workflow (branch + PR, never push to main). Discovers and runs the repo's own pinned formatters and linters rather than assuming a toolchain. Do NOT use for creating or editing skills — use skill-creator for that.
user-invocable: false
metadata:
  domain: >-
    Writing, editing, and reviewing production code in any language, grounded in
    each repo's own discovered conventions.
---

# Coding

Language-agnostic engineering discipline. It applies to whatever the repo under
your hands actually uses — the first job is always to discover that, not to assume it.

---

## Repo Discovery — do this first in any unfamiliar repo

Before writing or reviewing any code, learn what the specific repo is about. Every
repo has its own toolchain, conventions, and constraints that override general
defaults. Never assume — discover.

Read in this order (all can be done in parallel):

1. **CLAUDE.md files** — highest priority; explicit human-authored rules that override everything else
   ```bash
   find . -name "CLAUDE.md" -not -path "*/node_modules/*" | xargs cat 2>/dev/null
   ```
2. **README.md** — purpose, architecture overview, quick-start, known constraints
3. **CONTRIBUTING.md / ARCHITECTURE.md / docs/architecture.md** — coding standards, layering rules, PR checklists, naming conventions
4. **CI workflows** — the authoritative list of what must pass before merge
   ```bash
   ls .github/workflows/ 2>/dev/null && grep -h "run:\|uses:" .github/workflows/*.yml 2>/dev/null | head -40
   ```
5. **Formatter/linter config** — `pyproject.toml`, `ruff.toml`, `.eslintrc*`, `.prettierrc*`, `Makefile`, `go.mod`, `Cargo.toml` — tells you the exact flags and rules the repo enforces
6. **`package.json` scripts / `Makefile` targets** — often a single `make lint` or `npm run ci` wraps everything; prefer running that over reconstructing individual commands

From this, build a mental model: *What does this repo do? What language/framework?
What formatter and with what flags? What test runner? What CI jobs must pass? Are
there repo-specific patterns or forbidden practices?*

A rule found in CLAUDE.md or CI beats a general best practice. When a repo pins a
formatter version or line length, use exactly that — never a global default.

---

## Edit Workflow

Follow this sequence for any code change, regardless of repo or language.

1. **Run Repo Discovery above** if you haven't already this session — binding rules from CLAUDE.md, CONTRIBUTING.md, and CI override general defaults. Don't skip even if you think you know the codebase.
2. **Read** the file(s) to change — never propose edits blind.
3. **Read** the associated tests — if none exist, plan to create them.
4. **Propose** the implementation change — show a clear before/after, explain *why* it's correct.
5. **Propose** the test change — every implementation change ships with a test change; no exceptions.
6. **Confirm** with the user — wait for explicit approval before touching anything.
7. **Branch + push** — create a feature branch, push commits there (see Git Workflow below).
8. **Open a PR** targeting the default branch with a summary and test plan (see the `finalize-and-open-pr` skill).

---

## Reviewing AI-generated code

The bottleneck has shifted from *writing* code to *reviewing* it. When the diff under
review was produced by an AI — your own first draft, or another agent's — apply the
same rigor you'd give a human PR, plus the failure modes specific to generated code:

- **Hallucinated APIs** — a function, flag, import, or config key that reads plausibly but doesn't exist. Grep the repo for it before trusting it.
- **Silent scope creep** — edits beyond the task (a "helpful" refactor, a renamed symbol, an unrelated touched file). Confirm every hunk maps to the stated requirement; drop the rest.
- **Tests that assert nothing** — a test green because it never exercises the change.
- **Fixture-vs-production mismatch** — mock/sample data drifted from the real data shape, so the test passes but validates nothing.
- **Plausible-but-wrong reasoning** — a confident comment or commit message that misdescribes what the code does. Read the code, not the narration.

A fluent diff is not a correct one. Reviewing is the work — do not rubber-stamp
generated output.

---

## SOLID

### S — Single Responsibility
One function / class / module does exactly one thing. If you need "and" to describe it, split it.

```python
# Bad
def fetch_and_save_results(run_id, output_path): ...
# Good
def fetch_results(run_id): ...
def save_results(results, output_path): ...
```

### O — Open/Closed
Extend by adding new code, not by editing existing code. Add a new handler/plugin
rather than growing an existing function with more `if:` branches.

### L — Liskov Substitution
Any subclass must be usable in place of its parent without breaking the caller.
Practically: avoid subclassing unless the IS-A relationship is obvious. Prefer composition.

### I — Interface Segregation
Callers should not depend on interfaces they don't use. Don't pass a large config
dict to a function that only needs two keys — pass those two keys.

### D — Dependency Inversion
High-level logic should not instantiate its own dependencies. Pass them in.

```python
# Bad — hardwired dependency
def run():
    client = ApiClient(token=os.getenv("API_TOKEN"))

# Good — injected; main() owns os.getenv, nothing else does
def run(client: ApiClient): ...
def main():
    run(client=ApiClient(token=os.getenv("API_TOKEN")))
```

---

## Universal Principles

### DRY — Don't Repeat Yourself
Every piece of knowledge has one authoritative source. Extract repeated logic into
helpers, repeated test setup into fixtures, repeated build steps into shared actions.

### KISS — Keep It Simple
The simplest solution that handles the real cases is the right one. Complexity must justify itself.

### YAGNI — You Aren't Gonna Need It
No "might want later" abstractions, no optional parameters with no current caller,
no framework-style base classes for a single concrete use case.

### Law of Demeter
A function should only call methods on its own arguments, objects it created, or its
direct instance variables. Long chains (`a.b.c.d.method()`) are a fragility smell.

### Separation of Concerns
I/O, business logic, and configuration belong in separate layers.

### Command-Query Separation
A function either **does something** (command — side effects, no return value) or
**returns something** (query — no side effects). Not both.

### Fail Fast
Validate at entry points. Raise early with a clear message.

```python
def process(run_id: str):
    if not run_id:
        raise ValueError("run_id is required")
```

### No Inline Literals
Magic numbers, magic strings, and user-facing text must never appear as inline
literals in logic. See the detailed treatment under **Clean Code & Craftsmanship**
below (Constants & Magic Value Discipline, String Externalization, Centralized
Utilities).

### Verifiable Success Criteria
Before writing code, state concrete checkable outcomes and how you'll verify them.
If you can't describe how to verify the change is correct, you don't yet understand the problem.

### Don't Abort on Already-Effective Side Effects
Once a step has produced a visible external effect (PR opened, branch pushed, file
written), a later failure should warn and continue — not abort as if nothing happened.

```python
# Bad — PR is live on the remote but run goes red
create_pr(...)
enable_auto_merge(...)  # raises → caller thinks nothing was created

# Good
create_pr(...)
try:
    enable_auto_merge(...)
except RuntimeError as exc:
    log.warning("auto-merge could not be enabled: %s — PR is live, merge manually", exc)
```

---

## Clean Code & Craftsmanship

These standards apply to every language and every repo. They complement SOLID and
the universal principles above with the concrete, day-to-day discipline that
prevents the most common quality erosions.

### 1. Naming — Reveal Intent, Not Implementation

Names are the primary documentation. A reader should understand a symbol's purpose
without reading its body.

- **Say what it does, not how it's typed**: `remainingAttempts` not `retryInt`;
  `activeUsers` not `userList`. No Hungarian notation, no type prefixes.
- **Booleans read as questions**: `isVisible`, `hasPermission`, `canRetry`. No
  double negations (`isNotDisabled` → `isEnabled`).
- **Searchable and pronounceable**: no cryptic abbreviations (`ctx`, `tmp_calc_v2`,
  `hdlr`). If you can't say it in a code review, rename it.
- **Domain-aligned (Ubiquitous Language)**: use the domain's vocabulary in class and
  method names. If the business says "Order" don't call it `PurchaseRequest`; if the
  domain says "approve" don't name the method `setStatusToActive`.

```java
// Bad
public List<User> getUL(boolean f) {
    if (f) return repo.findAll().stream().filter(u -> u.a).toList();
    return repo.findAll();
}

// Good
public List<User> findActiveUsers() {
    return userRepository.findByActiveTrue();
}

public List<User> findAllUsers() {
    return userRepository.findAll();
}
```

```python
# Bad
def proc(d, f=True):
    r = [x for x in d if x["s"] == 1] if f else d
    return r

# Good
def filter_active_records(records):
    return [r for r in records if r["status"] == ACTIVE]
```

### 2. Function Design — Small, Flat, Focused

#### Single Level of Abstraction (SLAP)
A function must not mix high-level intent with low-level mechanics. If a function
orchestrates business steps, each step is a call — not an inline block of regex
parsing or byte manipulation.

```java
// Bad — mixes orchestration with parsing detail
public Report generateReport(String input) {
    String[] lines = input.split("\n");
    List<String[]> rows = new ArrayList<>();
    for (String line : lines) {
        rows.add(line.split(","));
    }
    var summary = computeSummary(rows);
    return new Report(summary);
}

// Good — each call is at the same abstraction level
public Report generateReport(String input) {
    List<Record> records = parseCsv(input);
    Summary summary = computeSummary(records);
    return new Report(summary);
}
```

```python
# Bad — mixes orchestration with I/O detail
def generate_report(path):
    with open(path) as f:
        lines = f.readlines()
    rows = [line.strip().split(",") for line in lines[1:]]
    summary = compute_summary(rows)
    return format_report(summary)

# Good
def generate_report(path):
    records = read_csv(path)
    summary = compute_summary(records)
    return format_report(summary)
```

#### Parameter Count (Arity)
- **0–2 parameters**: ideal.
- **3 parameters**: justify each one.
- **4+ parameters**: anti-pattern — group into a parameter object / value object.

```java
// Bad — 5 loose parameters
public void sendEmail(String to, String from, String subject, String body, boolean isHtml) { ... }

// Good — parameter object
public void sendEmail(EmailMessage message) { ... }
```

```python
# Bad
def create_user(name, email, role, department, notify, locale):
    ...

# Good
def create_user(user_data: UserCreationRequest):
    ...
```

#### Flag Arguments — Split Instead
A boolean parameter that switches behavior means the function does two things.

```java
// Bad
public String render(boolean isPrintMode) { ... }

// Good
public String renderForScreen() { ... }
public String renderForPrint() { ... }
```

#### Guard Clauses — Keep It Flat
Deep nesting (the "arrow anti-pattern") obscures logic. Use early returns to handle
edge cases at the top; keep the happy path unindented. Maximum 2 nesting levels.

```java
// Bad — deep nesting
public double calculateDiscount(Order order) {
    if (order != null) {
        if (order.getCustomer() != null) {
            if (order.getCustomer().isMember()) {
                return order.getTotal() * 0.1;
            }
        }
    }
    return 0;
}

// Good — guard clauses
public double calculateDiscount(Order order) {
    if (order == null) return 0;
    if (order.getCustomer() == null) return 0;
    if (!order.getCustomer().isMember()) return 0;
    return order.getTotal() * 0.1;
}
```

```python
# Bad
def calculate_discount(order):
    if order:
        if order.customer:
            if order.customer.is_member:
                return order.total * 0.1
    return 0

# Good
def calculate_discount(order):
    if not order:
        return 0
    if not order.customer:
        return 0
    if not order.customer.is_member:
        return 0
    return order.total * 0.1
```

### 3. Error Handling — First-Class Concern

Fail Fast (validate early, raise clearly) is the starting point. These rules
complete the picture.

- **Never return null/None for errors**: use exceptions, Result types, Optional, or
  the language's error idiom. A null return forces every caller to remember to check;
  an exception is impossible to silently ignore.
- **Never swallow exceptions**: no empty `catch {}`, no `except: pass`, no
  `catch (e) { /* TODO */ }`. If you catch, either handle meaningfully, wrap and
  re-throw, or log with full context.
- **Context-rich error messages**: include what was attempted, the offending value,
  and the expected condition.

```java
// Bad — swallowed exception, zero context
catch (IOException e) { }

// Good — wrapped with context, original cause preserved
catch (IOException e) {
    throw new ReportGenerationException(
        "Failed to read input file '" + filePath + "': expected UTF-8 CSV", e);
}
```

```python
# Bad
except Exception:
    pass

# Good
except FileNotFoundError as e:
    raise ReportError(f"Input file not found: {file_path}") from e
```

- **Boundary exception wrapping**: errors from third-party libraries or external
  APIs must be caught at the integration boundary and re-thrown as domain
  exceptions. The rest of the code should never depend on a library's exception
  hierarchy — so that swapping or upgrading the library doesn't break callers.

```java
// Bad — library exception leaks into domain
public User fetchUser(String id) throws HttpClientException { // ← library type in signature
    return httpClient.get("/users/" + id);
}

// Good — wrapped at the boundary
public User fetchUser(String id) {
    try {
        return httpClient.get("/users/" + id);
    } catch (HttpClientException e) {
        throw new UserServiceException("Failed to fetch user " + id, e);
    }
}
```

```python
# Bad — library exception leaks
def fetch_user(user_id: str) -> dict:
    return requests.get(f"/users/{user_id}").json()  # raises requests.ConnectionError

# Good — wrapped at boundary
def fetch_user(user_id: str) -> dict:
    try:
        return requests.get(f"/users/{user_id}").json()
    except requests.RequestException as e:
        raise UserServiceError(f"Failed to fetch user {user_id}") from e
```

### 4. Code Smells — Recognize and Refactor

Train yourself to spot these recurring structural weaknesses and refactor on sight:

- **Primitive Obsession**: passing raw `String`, `int`, `float` for domain concepts
  (email, price, currency, duration). Wrap in a value object that validates on
  construction.

```java
// Bad — raw String passed everywhere, no validation
public void createAccount(String email, String iban) { ... }

// Good — value objects that enforce invariants
public void createAccount(Email email, Iban iban) { ... }

public record Email(String value) {
    public Email { if (!value.contains("@")) throw new IllegalArgumentException("Invalid email"); }
}
```

```python
# Bad
def create_account(email: str, iban: str): ...

# Good
@dataclass(frozen=True)
class Email:
    value: str
    def __post_init__(self):
        if "@" not in self.value:
            raise ValueError(f"Invalid email: {self.value}")

def create_account(email: Email, iban: Iban): ...
```

- **Feature Envy**: a method that reads more data from another class than its own →
  move the method to the class whose data it uses.
- **Switch/If-Else chains on type**: branching over a type field or enum to select
  behavior → replace with polymorphism or strategy pattern.
- **Dead Code & Commented-out Code**: unreachable branches, unused imports, unused
  private methods, and commented-out blocks → delete immediately. Git preserves
  history.
- **Shotgun Surgery**: one logical change requires editing many unrelated files →
  the concept is scattered; consolidate into a single module or class.

### 5. Comments — Why, Never What

- **Don't comment bad code — rewrite it.** A comment explaining confusing code is a
  signal the code should be clearer, not that it needs annotation.
- **Good comments explain *why***: business rules, performance trade-offs, workarounds
  for external bugs, regulatory constraints. *What* and *how* are the code's job.
- **No redundant comments**: `getUser()  // gets the user` adds noise.
- **No commented-out code**: delete it. Git preserves history. Commented-out blocks
  rot, confuse, and never get cleaned up.

```java
// Bad — states the obvious
/** Gets the user ID. */
public String getUserId() { return userId; }

// Bad — excuses unclear code
// We multiply by 1000 and divide by 24 and then add 7 because of the timezone offset
long result = (input * 1000 / 24) + 7;

// Good — explains a non-obvious business rule
// Grace period: payment processing can lag by up to 48h on weekends,
// per agreement with the payment provider (ref: CONTRACT-2024-§4.3).
Instant deadline = dueDate.plus(Duration.ofHours(48));
```

```python
# Bad — redundant
# increment counter
counter += 1

# Good — explains why, not what
# Skip the first row: vendor CSV exports include a metadata header
# that is not part of the actual data (confirmed with vendor 2024-06).
records = rows[1:]
```

### 6. Boundary Protection — Isolate External Dependencies

Dependency Inversion says "pass dependencies in." This section says "wrap them so
they can't contaminate your domain."

- **Anti-Corruption Layer / Adapter**: external third-party SDKs, API payloads, and
  database result shapes must not flow raw into core services. Create adapter or
  mapper classes at the boundary that translate external types into your domain
  model — so that library upgrades, API changes, or vendor swaps don't break
  business logic.

```java
// Bad — third-party SDK type used deep in business logic
public InvoiceTotal calculate(StripePaymentIntent intent) {
    return new InvoiceTotal(intent.getAmountReceived());
}

// Good — adapter at the boundary, domain model in core
// adapter layer
public Payment toPayment(StripePaymentIntent intent) {
    return new Payment(Money.ofCents(intent.getAmountReceived()), intent.getCurrency());
}
// core layer — knows nothing about Stripe
public InvoiceTotal calculate(Payment payment) {
    return new InvoiceTotal(payment.amount());
}
```

```python
# Bad — external API shape leaks into business logic
def calculate_total(stripe_intent: dict) -> float:
    return stripe_intent["amount_received"] / 100

# Good — adapter at the boundary
def to_payment(stripe_intent: dict) -> Payment:
    return Payment(
        amount=Money(cents=stripe_intent["amount_received"]),
        currency=stripe_intent["currency"],
    )

def calculate_total(payment: Payment) -> Money:
    return payment.amount
```

### 7. Boy Scout Rule — Bounded Cleanup

*Leave the code cleaner than you found it* — but scope the cleanup:
- **In scope**: rename unclear variables, extract a repeated block, remove dead code
  *in the files you already touch for the task*.
- **Out of scope**: large refactors of untouched files, changing architectural
  patterns, reformatting entire modules. File those as separate tasks/PRs.

The balance: improve what you touch, don't use a bug fix as a Trojan horse for a
rewrite.

---

### Constants & Magic Value Discipline

A literal value appearing inline in logic is a maintenance trap — its meaning is
invisible, and changing it requires hunting every occurrence.

**What must be extracted:**
- Numeric thresholds, timeouts, limits, retry counts
- API endpoints, header names, query parameters
- Status codes, sentinel values, feature flags
- Regex patterns used in more than one place
- Default values for configuration

**Where to put constants — scoping rules:**
1. **Class/module scope**: used only within one class/module → private constant.
2. **Feature/package scope**: shared across a feature → constants object/module in
   that feature package.
3. **Application scope**: used across features → centralized constants file/module
   (e.g. `AppConstants`, `config.py`, `constants.ts`).

```java
// Bad — magic numbers and strings scattered in logic
if (retries > 3) { ... }
if (response.getStatus() == 429) { ... }
String url = "https://api.example.com/v2/users";

// Good — named constants with clear intent
private static final int MAX_RETRIES = 3;
private static final int HTTP_TOO_MANY_REQUESTS = 429;
private static final String USERS_API_ENDPOINT = "https://api.example.com/v2/users";

if (retries > MAX_RETRIES) { ... }
if (response.getStatus() == HTTP_TOO_MANY_REQUESTS) { ... }
```

```python
# Bad
if len(results) > 100:
    results = results[:100]
time.sleep(2.5)

# Good
MAX_RESULTS = 100
RETRY_DELAY_SECONDS = 2.5

if len(results) > MAX_RESULTS:
    results = results[:MAX_RESULTS]
time.sleep(RETRY_DELAY_SECONDS)
```

### String Externalization & Localization

Never hardcode human-readable, user-facing text (labels, messages, error messages,
fallbacks, placeholders, button text, default titles) directly in source code —
whether in UI components, view models, controllers, services, or handlers.

- **Always extract** all user-facing text into the repo's dedicated
  localization/resource system (resource files, i18n catalogs, message bundles — the
  format depends on the platform).
- **No hardcoded fallbacks in logic**: do not write `value ?? "Default Text"` or
  `if val is None: return "Fallback"` in business/presentation code. Emit resource
  keys or resolve via a localized resource provider.
- **Distinguish user-facing vs. technical strings**: log messages and internal debug
  output for developers may remain inline. The bar is: *would an end user see this
  text?* If yes, externalize it.
- **Enforce with tooling**: add linter rules or static-analysis checks that flag
  string literals in UI/presentation layers. A rule that CI enforces cannot regress.

```java
// Bad — user-facing text inline
button.setText("Submit Order");
showError("Something went wrong. Please try again.");

// Good — externalized via resource system
button.setText(resources.getString(R.string.submit_order));
showError(resources.getString(R.string.generic_error));
```

```python
# Bad — user-facing text inline
flash("Your session has expired. Please log in again.")

# Good — externalized via message catalog
flash(get_message("session_expired"))
```

### Centralized Utilities & Shared Logic

When the same formatting, validation, conversion, or helper logic appears in two or
more files, it must be extracted into a shared utility. DRY states the principle;
this section makes it operational.

**Extraction rules:**
1. **Two occurrences = extract**: the second time you write the same logic, stop and
   move it into a shared location.
2. **Utility location**: place shared helpers in a dedicated utilities
   package/module (`utils/`, `common/`, `shared/`, `helpers/`) — not scattered next
   to random feature code.
3. **Naming**: utility modules are named after *what they do*, not `Utils` or
   `Helpers` as a catch-all. Prefer `CurrencyFormatter`, `date_formatting`,
   `string_sanitization` over a monolithic `Utils` class.
4. **Prefer language idioms**: in languages with extension functions, mixins, or
   traits, use those over static utility classes — they keep the call site readable.

```java
// Bad — same formatting logic in 3 different services
String display = "$" + String.format("%.2f", amount);

// Good — centralized, reusable
public final class CurrencyFormatter {
    private CurrencyFormatter() {}
    public static String formatUsd(double amount) {
        return "$" + String.format("%.2f", amount);
    }
}
// Call site
String display = CurrencyFormatter.formatUsd(amount);
```

```python
# Bad — same sanitization copy-pasted in 4 views
username = raw_input.strip().lower().replace(" ", "_")

# Good — shared utility
# utils/string_sanitization.py
def sanitize_username(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_")

# Call site
username = sanitize_username(raw_input)
```

---

## Git Workflow

### Never push directly to the default branch
All changes go through a branch + PR, regardless of how small or obvious the fix is.
Direct pushes bypass CI and peer review — including follow-up chores identified during
a review.

1. Create a branch from the default branch → feature/fix branch name
2. Commit changes to that branch
3. Open a PR against the default branch (see the `finalize-and-open-pr` skill)

---

## Per-language style

Discover the repo's pinned config first; the notes below are defaults for when the
repo says nothing.

### Python
- `snake_case` functions/variables, `PascalCase` classes, `UPPER_CASE` module constants; two blank lines between top-level defs (PEP 8).
- Explicit over implicit: no `from module import *`, no silent `except: pass`.
- Type hints on all signatures (`def fetch(run_id: str, top: int = 10) -> list[dict]: ...`).
- Prefer pure functions — output depends only on inputs; move `os.getenv` to `main()` and pass resolved values down.
- Composition over inheritance.
- **Run the repo's pinned formatter/linter** (black/ruff/isort/autoflake, etc.) with the repo's flags before committing. If the repo pins a line length or version, use exactly that — never a global default (a wrong line length reformats files in a way CI rejects).

### Python test style (pytest-native)
When the repo uses pytest, write **pytest-native** tests, not `unittest.TestCase`:
- Plain `class TestX:` or module-level `test_*` functions — no `TestCase` base. Keep a class grouping when a module reuses `test_*` method names across classes.
- Plain `assert` (`assert a == b`, `assert x in y`, `assert x is None`), never `self.assertEqual/assertIn/...`.
- `with pytest.raises(E) as e:` instead of `self.assertRaises`; the bound var's `.exception` becomes `.value`.
- `setUp`/`tearDown` → `@pytest.fixture(autouse=True)` that `yield`s. Prefer built-in fixtures: `tmp_path` over `tempfile.mkdtemp()`, `monkeypatch` over manual env save/restore, `capsys` over redirecting `sys.stdout`.
- `@pytest.mark.parametrize` over `subTest(...)` loops.
- Shared fixtures + factory helpers in `conftest.py`.
- `from unittest.mock import patch, MagicMock` is fine — that's the mock library, unrelated to runner style.

### YAML
- Run the repo's `yamllint` config if present. Typical relaxations: allow `on:` as a key (`truthy: {check-keys: false}`), disable `document-start`, generous `line-length` for CI-expression lines.

### TypeScript / Playwright
- Prefer `async/await` over Promise chains.
- Keep selector logic in Page Object classes — no inline `page.locator()` in specs.
- No hardcoded waits (`waitForTimeout`); use `waitForSelector`, `waitForResponse`, or auto-waiting.

### Gherkin / Cucumber
- One behavior per scenario — a title containing "and" is likely two scenarios.
- Steps describe intent, not implementation (`When I submit the form`, not `When I click the submit button`).
- No `if`/`for`/`switch` in step definitions — logic belongs in helpers or Page Objects.

### Shell
- Quote variables (`"$VAR"`, not `$VAR`); `set -euo pipefail` or explicit error handling; never `rm -rf` on an unquoted path.
