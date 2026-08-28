# MQL5 Parser Budget Analysis

## Root Cause: O(n²) Complexity in Parser

### Problem Summary

The MQL5 parser fails on large files (>10,000 lines) with `analysis_budget_exceeded` error even when using the maximum budget of 10,000,000 units.

### Test File Statistics

- **File**: `tests/fixtures/large_test_file.mq5`
- **Lines**: 10,364
- **Tokens**: 58,893
- **Functions detected**: ~4,970
- **Classes/Structs/Enums**: 61

### Budget Consumption Breakdown

#### Lexing Phase
- Budget consumed: ~58,894 units (one per token + whitespace)
- Status: ✅ Completes successfully within budget

#### Parsing Phase - The Bottleneck

The parser has several O(n*m) complexity issues:

1. **`inside_function()` function (CRITICAL)**
   - Called once for EVERY token (~58,893 times)
   - Each call iterates through ALL functions (~4,970)
   - **Total operations: ~292,698,210**
   - This alone exceeds the 10M budget by 29x

2. **Type range detection**
   - For each class/struct/enum keyword (61)
   - Iterates up to 20 tokens ahead
   - Total: ~1,220 operations ✅

3. **Call site detection**
   - For each token inside function bodies
   - Iterates through function body tokens
   - Estimated: 50M+ operations ❌

4. **Binding resolution**
   - Multiple passes through parameter/local/member/global bindings
   - Each pass consumes budget per binding lookup
   - Estimated: 10M+ operations ❌

### Code Locations

#### Primary Bottleneck: `parser.py` lines 302-317

```python
def inside_function(index: int) -> bool:
    for item in functions:  # O(m) - iterates ALL functions
        active_budget.consume("parsing")
        if item.open_paren < index < item.close_paren:
            return True
        # ... more checks
    return False

# Called from line 322:
for index in range(len(tokens)):  # O(n) - for EVERY token
    active_budget.consume("parsing")
    if inside_function(index):  # O(m) - catastrophic!
        continue
```

**Complexity**: O(n × m) where n=tokens, m=functions
**For our test file**: 58,893 × 4,970 = **292,698,210 operations**

#### Secondary Bottleneck: Call Detection (lines 362-407)

```python
cursor = function.body_start + 1
while cursor < end:  # Iterates through entire function body
    active_budget.consume("parsing")
    # ... complex nested logic with more budget consumption
    cursor += 1
```

This loop runs for every function, scanning its entire body, with nested budget-consuming operations for binding lookups.

### Budget Math

| Phase | Estimated Operations | Budget Limit |
|-------|---------------------|--------------|
| Lexing | 58,894 | ✅ Pass |
| Paren/Brace pairing | 117,786 | ✅ Pass |
| Include detection | 58,893 | ✅ Pass |
| Type detection | 1,220 | ✅ Pass |
| Depth calculation | 58,893 | ✅ Pass |
| Function detection | 58,893 | ✅ Pass |
| **inside_function calls** | **292,698,210** | ❌ FAIL |
| Call site detection | 50,000,000+ | ❌ FAIL |
| Binding resolution | 10,000,000+ | ❌ FAIL |
| **Total** | **~353M** | **10M limit** |

### Solutions Required

1. **Eliminate `inside_function()` bottleneck**
   - Pre-compute a token-to-function mapping array
   - Use interval tree or simple array lookup
   - Reduce from O(n×m) to O(1) per token

2. **Optimize call site detection**
   - Reduce redundant budget consumption in inner loops
   - Cache binding lookups
   - Skip budget consumption for trivial operations

3. **Increase default budget**
   - Current: 1,000,000 (too low)
   - Recommended: 5,000,000 (reasonable default)
   - Maximum: Consider increasing from 10M to 50M

4. **Make budget configurable via CLI**
   - Already exists via `--max-work` flag
   - Document recommended values for different file sizes

### Recommended Implementation Priority

1. **Immediate fix**: Optimize `inside_function()` to use pre-computed lookup table
2. **Secondary**: Reduce budget consumption in call detection loops  
3. **Configuration**: Increase DEFAULT_MAX_WORK to 5,000,000
4. **Documentation**: Add LARGE_FILE_HANDLING.md guide

### Expected Improvement

With optimized `inside_function()`:
- Reduce from 292M to ~59K operations (5000x improvement)
- Total parsing operations: ~60M → should fit within increased budget
- With DEFAULT_MAX_WORK = 5M and MAX_MAX_WORK = 50M, large files should parse successfully
