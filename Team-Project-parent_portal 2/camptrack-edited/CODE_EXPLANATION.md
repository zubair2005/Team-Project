# CampTrack - Code Explanation Guide

This document explains the key programming constructs and patterns used in CampTrack, from simple to advanced.

## Basic Python Constructs

### 1. Variables and Type Hints

```python
username: str = "admin"           # String variable
user_id: int = 42                 # Integer variable
enabled: bool = True              # Boolean variable
rate: Optional[str] = None        # Can be string or None
```

**Why**: Type hints make code clearer and help catch errors early.

### 2. String Methods

```python
username.strip()                  # Remove leading/trailing whitespace
username.lower()                  # Convert to lowercase
f"Hello {username}"              # Format string (f-string)
```

**Where used**: Input validation, case-insensitive matching, user messages

### 3. Dictionaries

```python
user = {"id": 1, "username": "admin", "role": "admin"}
user["id"]                        # Access value: 1
user.get("role", "unknown")       # Safe access with default
```

**Where used**: Storing database rows, passing user data between functions

### 4. Lists and List Comprehensions

```python
users = [{"id": 1}, {"id": 2}]    # List of dictionaries
[u["id"] for u in users]          # List comprehension: [1, 2]
```

**Where used**: Collecting query results, transforming data for display

## Intermediate Constructs

### 5. Functions with Optional Returns

```python
def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    # Returns user dict if valid, None if invalid
```

**Why**: Allows functions to signal "not found" or "failed" gracefully

### 6. Context Managers (with statements)

```python
with _connect() as conn:
    conn.execute("INSERT...")
# Connection auto-closes even if error occurs
```

**Where used**: All database operations to ensure proper cleanup

### 7. Try-Except Blocks

```python
try:
    conn.execute("INSERT...")
    return True
except sqlite3.IntegrityError:
    return False  # Unique constraint violated
```

**Where used**: Handling unique constraints, file operations, validation

### 8. Lambda Functions

```python
tk.Button(text="Logout", command=lambda: do_logout())
# Creates anonymous function for button callback
```

**Where used**: Tkinter button commands, event handlers

### 9. Generator Expressions

```python
total = sum(row["value"] for row in data)
# More memory-efficient than [row["value"] for row in data]
```

**Where used**: Calculating totals, filtering data

### 10. next() with Generator

```python
leader = next(u for u in users if u["role"] == "leader")
# Finds first matching item
```

**Where used**: Finding specific records in lists

## Advanced Constructs

### 11. Partial UNIQUE Indexes (SQLite)

```sql
CREATE UNIQUE INDEX one_admin ON users(role) WHERE role='admin';
CREATE UNIQUE INDEX one_coordinator ON users(role) WHERE role='coordinator';
```

**Purpose**: Enforce "exactly one admin, one coordinator" per brief (Page 1)

**How it works**:

- Regular UNIQUE index would allow only one of each role total
- Partial index (WHERE clause) only applies to specific role values
- Leaders can be unlimited, but admin/coordinator limited to one

**Why it's important**: Database-level enforcement prevents bugs even if UI code fails

### 12. Foreign Key Constraints with CASCADE/RESTRICT

```sql
FOREIGN KEY (camp_id) REFERENCES camps(id) ON DELETE CASCADE
FOREIGN KEY (leader_user_id) REFERENCES users(id) ON DELETE RESTRICT
```

**CASCADE**: When parent is deleted, children auto-delete (e.g., delete camp → delete its activities)

**RESTRICT**: Prevents deletion if children exist (e.g., can't delete leader with assignments)

**Where used**:

- CASCADE: camp → campers, activities, reports
- RESTRICT: user → assignments, reports (prevents orphaned data)

### 13. Pandas DataFrame Operations

```python
df = pd.read_sql_query("""SELECT...""", conn)
df["campers_count"] = df["campers_count"].fillna(0).astype(int)
df["effective"] = df["base"] + df["delta"]
```

**Purpose**: Load SQL data into DataFrame for analysis

**Operations**:

- `fillna(0)`: Replace NULL with 0
- `astype(int)`: Convert to integer type
- Computed columns: Create new columns from existing ones

**Where used**: Camp summaries, analytics dashboard

### 14. Pandas Groupby Aggregations

```python
area_counts = df.groupby("area")["id"].count()
# Groups camps by area, counts IDs per group
# Result: {"North": 3, "South": 2}
```

**Purpose**: Aggregate data for charts (per brief: "visualisations using NumPy and Pandas")

**Where used**:

- Camps by geographic area
- Per-camp statistics
- Leader allocation summaries

### 15. NumPy where() Conditional Selection

```python
df["required"] = np.where(
    df["campers_food"] > 0,
    df["campers_food"],              # If true: use actual
    df["default"] * df["count"]      # If false: use default × count
)
```

**Purpose**: Conditional logic on entire DataFrame columns at once

**Where used**: Calculating required food (use per-camper overrides if set, else default)

### 16. CSV DictReader

```python
with open(file, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    # Each row is a dict: {"first_name": "Ada", "last_name": "Lovelace", ...}
    for row in reader:
        process(row["first_name"])
```

**Purpose**: Parse CSV files into dictionaries (easier than indexed lists)

**Where used**: Bulk camper import with header validation

### 17. Tkinter Callback Closures

```python
def build_dashboard(user):
    leader_id = user.get("id")

    def refresh_assignments():
        # Can access leader_id from outer scope
        assignments = list_leader_assignments(leader_id)
```

**Purpose**: Button/event handlers that need access to outer scope variables

**Where used**: All dashboard refresh functions, form submissions

### 18. Tkinter Notebook (Tabs)

```python
notebook = ttk.Notebook(container)
tab1 = tk.Frame(notebook)
notebook.add(tab1, text="Tab Name")
notebook.pack(fill=tk.BOTH, expand=True)
```

**Purpose**: Organize related functions into tabs instead of scrolling

**Where used**: All three role dashboards for clean navigation

### 19. Custom Tkinter Widgets (Classes)

```python
class BarChart(tk.Canvas):
    def __init__(self, master, width=400, height=240):
        super().__init__(master, width=width, height=height)

    def draw(self, data, title=""):
        # Custom drawing logic
```

**Purpose**: Reusable chart components

**Where used**: BarChart (single bars), DualBarChart (comparison), MessageBoard, Table

### 20. Tkinter Canvas Drawing

```python
self.create_rectangle(x0, y0, x1, y1, fill="#3498db")
self.create_text(x, y, text="Label", font=("Helvetica", 10))
self.create_line(x1, y1, x2, y2, fill="#ccc")
```

**Purpose**: Draw charts directly on Canvas (no Matplotlib per brief)

**Where used**: All analytics charts - bars, gridlines, labels, legends

### 21. Date Range Generation with Pandas

```python
dates = pd.date_range(start_date, end_date, freq="D")
# Generates all dates from start to end (inclusive)
```

**Purpose**: Day-by-day food shortage evaluation (per brief requirement)

**Where used**: `compute_day_by_day_food_usage()` for per-day alerts

### 22. SQL Common Table Expressions (CTEs)

```python
WITH camp_totals AS (
    SELECT camp_id, COUNT(*) AS count FROM campers GROUP BY camp_id
),
topups AS (
    SELECT camp_id, SUM(delta) AS total FROM stock_topups GROUP BY camp_id
)
SELECT c.*, ct.count, tp.total FROM camps c LEFT JOIN...
```

**Purpose**: Break complex queries into readable parts, compute aggregates

**Where used**: `get_camp_summary_df()` to gather all camp statistics

### 23. Tkinter Multi-Select Listbox

```python
listbox = tk.Listbox(dialog, selectmode=tk.MULTIPLE)
sel_indices = listbox.curselection()  # Returns tuple of selected indices
selected_ids = [items[idx]["id"] for idx in sel_indices]
```

**Purpose**: Bulk-assign campers to activities (per brief: "Bulk assign campers")

**Where used**: Activity assignment dialog

### 24. Dictionary Unpacking in Function Calls

```python
args = (name, location, area, camp_type, start, end, food, default)
create_camp(*args)  # Unpacks tuple as separate arguments
```

**Purpose**: Cleaner code when passing many parameters

**Where used**: Camp create/update operations

### 25. Nonlocal Variables in Closures

```python
def outer():
    selected_id = None

    def inner():
        nonlocal selected_id  # Modify outer scope variable
        selected_id = 42
```

**Purpose**: Allow inner functions to modify outer scope state

**Where used**: Form selection tracking (selected_camp_id in coordinator)

## Database Patterns

### 26. Row Factory for Dictionary Results

```python
def _dict_cursor(conn):
    conn.row_factory = sqlite3.Row
    return conn

row = conn.execute("SELECT...").fetchone()
row["username"]  # Access by column name instead of index
```

**Purpose**: Readable database access (names instead of row[0], row[1])

**Where used**: All database queries in services.py

### 27. INSERT OR IGNORE

```python
conn.execute("""
    INSERT OR IGNORE INTO camp_campers(camp_id, camper_id, food)
    VALUES (?, ?, ?)
""")
```

**Purpose**: Skip insertion if unique constraint would fail (no error)

**Where used**: CSV import (prevents duplicate camp-camper links)

### 28. INSERT ... ON CONFLICT DO UPDATE (Upsert)

```python
conn.execute("""
    INSERT INTO settings(key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
""")
```

**Purpose**: Insert if new, update if exists (atomic operation)

**Where used**: Settings storage, daily report updates

### 29. GROUP_CONCAT Aggregation

```python
SELECT camp_id, GROUP_CONCAT(username, ', ') AS leader_list
FROM assignments JOIN users...
GROUP BY camp_id
```

**Purpose**: Combine multiple rows into comma-separated string

**Where used**: Show all leader names per camp in coordinator dashboard

## Performance Optimizations

### 30. Caching Computed Values

```python
# BAD: Query inside loop
for day in days:
    sum = sum(query_topups())  # Repeated queries!

# GOOD: Cache once
topup_sum = sum(query_topups())
for day in days:
    planned = base + topup_sum  # Reuse cached value
```

**Where used**: `compute_day_by_day_food_usage()` optimization

### 31. Batch Database Operations

```python
conn.executemany(
    "INSERT INTO camper_activity VALUES (?, ?)",
    [(activity_id, camper_id) for camper_id in camper_ids]
)
```

**Purpose**: Insert many rows in one database round-trip

**Where used**: Bulk activity assignments

## UI Patterns

### 32. Refresh Callbacks

```python
def refresh_data():
    table.delete(*table.get_children())  # Clear all rows
    for row in fetch_data():
        table.insert("", tk.END, values=row)  # Re-populate
```

**Purpose**: Update UI when data changes

**Where used**: After create/update/delete operations

### 33. Toplevel Dialogs

```python
dialog = tk.Toplevel(parent)
dialog.title("Edit Item")
dialog.geometry("400x300")
# Add widgets...
tk.Button(dialog, text="Save", command=save_and_close)
```

**Purpose**: Pop-up forms without blocking main window

**Where used**: CSV import preview, activity creation, food adjustment

### 34. Table Row Selection

```python
selection = table.selection()  # Get selected IIDs
if selection:
    row_id = int(selection[0])  # Convert IID to integer
```

**Purpose**: Get user's selected table row

**Where used**: Enable/disable/delete users, select camps for editing

## Why These Patterns Matter

1. **Partial UNIQUE indexes**: Elegant database-level constraint enforcement
2. **CASCADE/RESTRICT**: Prevents orphaned data automatically
3. **Pandas groupby**: Powers all analytics per brief requirement
4. **NumPy where()**: Efficient vectorized conditionals
5. **Tkinter Canvas**: Allows custom charts without external libraries
6. **CTEs**: Makes complex SQL readable and maintainable
7. **Context managers**: Ensures resources are properly cleaned up
8. **Type hints**: Self-documenting code, easier debugging

## Testing Patterns

### 35. Assertion-Based Validation

```python
assert len(users) == 5, "Should have 5 seeded users"
assert result is not None, "Operation failed"
```

**Purpose**: Verify expected behavior in tests

**Where used**: Smoke test scripts

### 36. Fresh State Testing

```python
rm -f data/camptrack.db  # Delete database
init_db()                # Recreate from schema
seed_initial_data()      # Re-seed baseline
```

**Purpose**: Test from known clean state

**Where used**: Comprehensive test scripts

## Architecture Patterns

### 37. Separation of Concerns

- **database.py**: Schema and connection
- **services.py**: Business logic and data access
- **ui/\*.py**: Presentation layer only

**Why**: Changes to UI don't affect business logic; easier testing

### 38. Dependency Injection

```python
def build_dashboard(root, user, logout_callback):
    # Passed dependencies instead of global state
```

**Why**: Testable, reusable components

### 39. Single Source of Truth

- User data: users table
- Settings: settings table (not hardcoded)
- Stock levels: base + computed sum(topups)

**Why**: Changes propagate automatically, no sync issues

## Common Pitfalls Avoided

### 40. SQL Injection Prevention

```python
# UNSAFE:
conn.execute(f"SELECT * FROM users WHERE id = {user_id}")

# SAFE:
conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

**All queries use parameterized statements (?).**

### 41. CSV Encoding Issues

```python
with open(file, newline="", encoding="utf-8") as csvfile:
    # Explicit UTF-8 prevents encoding errors
```

### 42. Closure Variable Scope

```python
# BAD:
for i in range(3):
    tk.Button(text=f"Click {i}", command=lambda: print(i))
    # All buttons print "2" (last value)

# GOOD:
for i in range(3):
    tk.Button(text=f"Click {i}", command=lambda val=i: print(val))
    # Each button captures its own i value
```

## Key Algorithms

### 43. Date Overlap Detection

```python
def overlaps(start1, end1, start2, end2):
    return not (end1 < start2 or start1 > end2)
```

**Purpose**: Prevent leader assignment conflicts

**Logic**: Two ranges overlap unless one ends before the other starts

### 44. Duplicate Detection (Case-Insensitive)

```python
key = (first_name.lower(), last_name.lower(), dob)
if key in seen:
    duplicates += 1
else:
    seen[key] = row
```

**Purpose**: CSV import deduplication

**Features**: Case-insensitive names, exact DOB match

### 45. Day-by-Day Shortage Evaluation

```python
for each day in camp_duration:
    required = sum(food for campers present that day)
    planned = base + sum(topups)
    if required > planned:
        alert(day, shortage_amount)
```

**Purpose**: Detect food shortages "for the whole duration of the camp" (Page 2)

**Precision**: Per-day instead of average (catches single-day spikes)

## Summary

- **Simple**: Variables, strings, lists, dicts
- **Intermediate**: Functions, context managers, try-except, lambdas
- **Advanced**: Partial indexes, Pandas groupby, NumPy operations, date ranges
- **Patterns**: Separation of concerns, dependency injection, single source of truth
- **Safety**: Parameterized queries, encoding specification, proper cleanup

All constructs are **standard Python** with **no custom frameworks** - exactly as required by the coursework brief!
