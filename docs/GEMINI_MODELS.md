# Gemini Model Fallback Strategy

Chronicle automatically selects the best available Gemini model based on **session size** and **quota usage** to optimize for performance, cost, and reliability.

## Model Selection Logic

### Small/Medium Sessions (<50K lines)

**Preference order:**
1. **gemini-2.5-flash** - 250K TPM, 250 RPD - Latest stable features (preferred)
2. **gemini-2.5-flash-preview-09-2025** - 250K TPM, 250 RPD - Preview features
3. **gemini-2.0-flash** - 1M TPM, 200 RPD - Fallback (overkill for small sessions)
4. **gemini-2.0-flash-lite** - 1M TPM, 200 RPD - Additional fallback
5. **gemini-2.5-flash-lite** - 250K TPM, 1000 RPD - High volume fallback

**Why 2.5 models first:**
- 250K TPM is sufficient for 3-5K line chunks
- Latest features and improvements
- Good balance of performance and quota limits

### Large Sessions (>50K lines)

**Preference order:**
1. **gemini-2.0-flash** - 1M TPM, 200 RPD - Primary (handles 10K line chunks)
2. **gemini-2.0-flash-lite** - 1M TPM, 200 RPD - First fallback (same capacity)
3. **gemini-2.5-flash** - 250K TPM, 250 RPD - **Reduces chunks to 5K lines** for 250K TPM
4. **gemini-2.5-flash-preview-09-2025** - 250K TPM, 250 RPD
5. **gemini-2.5-flash-lite** - 250K TPM, 1000 RPD

**Why 2.0 models first:**
- 1M TPM (4x more than 2.5) enables larger 10K line chunks
- Faster processing for large sessions
- Automatic chunk size reduction when falling back to 2.5 models

## Automatic Chunk Size Adjustment

Chronicle intelligently adjusts chunk size based on available model capacity:

- **1M TPM models** (2.0-flash, 2.0-flash-lite): **10,000 lines per chunk**
- **250K TPM models** (2.5-flash variants): **5,000 lines per chunk**

This ensures chunks fit within token limits while maximizing throughput.

## Smart Failover

Chronicle tracks quota usage per model in the database and automatically:
- Detects rate limit errors
- Falls back to next available model
- Resumes from last successful chunk
- Retries with exponential backoff

**Retry delays:**
- Rate limit errors: 15s, 30s, 45s
- Other errors: 5s, 10s, 20s (exponential backoff)
- After 3 failures: Saves partial summary, can resume later

## Configuration

### Default Model

```bash
chronicle config ai.default_model gemini-2.0-flash
```

**Available models:**
- gemini-2.0-flash
- gemini-2.0-flash-lite
- gemini-2.5-flash
- gemini-2.5-flash-preview-09-2025
- gemini-2.5-flash-lite

**Note:** Chronicle auto-selects models based on quota, so you rarely need to change this manually.

### API Key Setup

```bash
chronicle config ai.gemini_api_key YOUR_KEY
# Or: export GEMINI_API_KEY=...
```

## Why This Strategy Works

1. **Session size matters**: Large sessions need high-throughput models (1M TPM)
2. **Latest features for common use**: Most sessions are small, benefit from 2.5 models
3. **Graceful degradation**: Automatic fallback ensures summarization always succeeds
4. **Cost optimization**: Balances performance vs quota consumption
5. **Intelligent recovery**: Partial summaries + resume capability prevents data loss

## Implementation Details

See `backend/services/summarizer.py` for the complete implementation of:
- Model selection logic
- Chunk size calculation
- Quota tracking
- Retry strategies

---

**Related Documentation:**
- [CLAUDE.md](../CLAUDE.md) - Chronicle development guide
- [README.md](../README.md) - User documentation
