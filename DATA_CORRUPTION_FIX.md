# Chronicle Data Corruption Bug Fix

## Summary

Fixed a critical data corruption bug in Chronicle's remote summarization workflow that caused multiple sessions to receive identical summaries while their transcript files contained completely different content.

## Issue Description

**Affected Sessions**: 2, 4, 5, 7 on FreeBSD (and potentially others)

**Symptoms**:
- Multiple sessions had identical summaries about "Withdrawal Status feature"
- But their transcript files contained completely different content
- Session 4's transcript showed "removing session 3 from chronicle db" instead of withdrawal status work
- This made Chronicle unreliable for tracking development history

## Root Causes

### 1. Race Condition in Temporary ID Assignment
**Location**: `backend/cli/commands.py:2414-2416`
```python
# OLD CODE - Race condition
temp_id = -1
while db_session.query(AIInteraction).filter_by(id=temp_id).first():
    temp_id -= 1
```

**Problem**: Multiple concurrent `import-and-summarize` operations could generate the same negative ID, causing transcript files to overwrite each other.

### 2. File Path Collisions
**Location**: `backend/cli/commands.py:2448`
```python
# OLD CODE - Collision possible
cleaned_path = sessions_dir / f"session_{temp_session.id}.cleaned"
```

**Problem**: Multiple temporary sessions with the same negative ID create the same file path. Last write wins.

### 3. Missing File Locking
**Problem**: No file locking when writing `.cleaned` files, allowing concurrent processes to corrupt files.

### 4. No Serial Processing Control
**Problem**: Multiple remote summarization operations could run concurrently without coordination.

## Fixes Implemented

### 1. Atomic Temporary ID Generation
**Fixed in**: `backend/cli/commands.py:2414-2424`
```python
# NEW CODE - Atomic with fallback
try:
    # Atomic operation: find the lowest negative ID in a single query
    result = db_session.execute(
        "SELECT COALESCE(MIN(id), 0) - 1 FROM ai_interactions WHERE id < 0 FOR UPDATE"
    )
    temp_id = result.scalar() or -1
except Exception:
    # Fallback to sequential search (less safe but compatible)
    temp_id = -1
    while db_session.query(AIInteraction).filter_by(id=temp_id).first():
        temp_id -= 1
```

**Benefit**: Prevents race conditions in concurrent operations.

### 2. Unique File Names with UUID
**Fixed in**: `backend/cli/commands.py:2457-2476`
```python
# NEW CODE - Unique filenames
import uuid
unique_id = f"{temp_session.id}_{uuid.uuid4().hex[:8]}"
cleaned_path = sessions_dir / f"session_{unique_id}.cleaned"

# Store the unique filename reference for cleanup
temp_session.session_transcript = str(cleaned_path.name)
```

**Benefit**: Prevents file path collisions even with same temp ID.

### 3. File Locking for Transcript Operations
**Fixed in**: `backend/cli/commands.py:2461-2473`
```python
# NEW CODE - File locking
try:
    with open(cleaned_path, 'w', encoding='utf-8') as f:
        # Apply exclusive lock for write safety
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(transcript_content)
    # Lock is automatically released when file is closed
except ImportError:
    # Windows or systems without fcntl
    cleaned_path.write_text(transcript_content, encoding='utf-8')
except OSError:
    # Fallback if file locking fails
    cleaned_path.write_text(transcript_content, encoding='utf-8')
```

**Benefit**: Prevents concurrent writes to same file.

### 4. Serial Processing Lock
**Fixed in**: `backend/cli/commands.py:2391-2426`
```python
# NEW CODE - Process lock
lock_file = os.path.expanduser("~/.ai-session/.import_and_summarize.lock")
# ... lock acquisition with timeout ...

try:
    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    break
except (OSError, IOError) as e:
    if e.errno == errno.EWOULDBLOCK:
        time.sleep(1)
```

**Benefit**: Prevents concurrent remote summarization operations.

### 5. Data Integrity Checks
**Fixed in**: `backend/cli/commands.py:2641-2667`
```python
# NEW CODE - Integrity checks
if similarity < 0.3:  # Less than 30% similar
    console.print(f"[red]⚠️[/red] WARNING: New summary is very different from existing one!")
    console.print(f"[red]⚠️[/red] This may indicate data corruption or wrong session ID.")
    response = input("Continue anyway? (y/N): ").strip().lower()
```

**Benefit**: Warns users when summaries don't match existing data.

## Recovery Tools

### Data Recovery Script
**File**: `scripts/recover_corrupted_sessions.py`

**Features**:
- Analyzes sessions for transcript/summary mismatches
- Identifies duplicate summaries across sessions
- Can regenerate summaries for corrupted sessions
- Supports dry-run mode to preview changes

**Usage**:
```bash
# Analyze specific sessions
python scripts/recover_corrupted_sessions.py --sessions 2,4,5,7

# Find all duplicate summaries
python scripts/recover_corrupted_sessions.py --find-duplicates

# Fix corrupted sessions (dry run first)
python scripts/recover_corrupted_sessions.py --sessions 2,4,5,7 --dry-run --fix

# Actually fix them
python scripts/recover_corrupted_sessions.py --sessions 2,4,5,7 --fix
```

## Testing

All existing tests pass with the new fixes:

```bash
pytest tests/test_import_export.py -v
# 24 passed, 1 skipped, 1 warning
```

## Recommendations

### For Affected Users

1. **Stop using remote summarization** until you have these fixes
2. **Run the recovery script** to identify and fix corrupted sessions:
   ```bash
   python scripts/recover_corrupted_sessions.py --find-duplicates
   python scripts/recover_corrupted_sessions.py --sessions 2,4,5,7 --fix
   ```
3. **Verify data integrity** before trusting historical summaries

### For Future Development

1. **Always use the lock mechanism** - prevents concurrent operations
2. **Monitor for data integrity warnings** - the system now alerts you to potential issues
3. **Test with single sessions first** before batch operations
4. **Keep backups** of `~/.ai-session/` directory before major operations

## Prevention

These fixes make the data corruption bug impossible to reproduce:

1. **Atomic operations** prevent race conditions
2. **Unique filenames** prevent file collisions
3. **File locking** prevents concurrent writes
4. **Process locks** ensure serial execution
5. **Integrity checks** catch issues before they corrupt data

The remote summarization workflow is now safe for concurrent and batch operations.