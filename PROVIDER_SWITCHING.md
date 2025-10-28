# Claude Code Provider Switching

Chronicle now includes built-in support for easily switching between Anthropic's official Claude Code and Z.AI's proxy service.

## Why Switch Providers?

**Anthropic (Default):**
- Official Claude Code with OAuth authentication
- Full feature support
- Standard usage limits

**Z.AI:**
- 3x the usage at lower cost
- Same Claude models via proxy
- Requires Z.AI API key

## Quick Start

### View Available Providers

```bash
chronicle claude-provider list
```

Shows all configured providers and which one is currently active.

### Check Current Provider

```bash
chronicle claude-provider current
```

Displays detailed information about your active provider.

## Switching to Z.AI

### 1. Get Z.AI API Key

1. Visit [https://platform.z.ai](https://platform.z.ai)
2. Sign up and navigate to API Keys
3. Create a new API key
4. Copy the key

### 2. Configure Z.AI Provider

```bash
chronicle claude-provider setup zai
```

This will:
- Prompt for your Z.AI API key (securely hidden)
- Save the key to Chronicle's config
- Configure Z.AI endpoint settings

### 3. Switch to Z.AI

```bash
chronicle claude-provider use zai
```

This will:
- Backup your current Claude settings
- Configure Claude Code to use Z.AI proxy
- Update Chronicle's active provider

**Important:** Restart Claude Code after switching!

## Switching Back to Anthropic

```bash
chronicle claude-provider use anthropic
```

This will:
- Backup your current settings
- Remove Z.AI configuration
- Restore Claude to use OAuth

**Important:** Restart Claude Code after switching!

## Backup Management

### List Backups

```bash
chronicle claude-provider backups
```

Every time you switch providers, your previous settings are automatically backed up.

### Restore from Backup

```bash
chronicle claude-provider restore settings_20251028_143022.json
```

Restores Claude settings from a specific backup file.

## How It Works

Chronicle modifies `~/.claude/settings.json` to switch providers:

**Anthropic (OAuth):**
```json
{
  "enabledPlugins": { ... }
}
```

**Z.AI (API Key):**
```json
{
  "enabledPlugins": { ... },
  "ANTHROPIC_AUTH_TOKEN": "your-zai-api-key",
  "ANTHROPIC_BASE_URL": "https://api.z.ai/api/anthropic",
  "API_TIMEOUT_MS": "3000000"
}
```

## Configuration Storage

Provider settings are stored in Chronicle's config: `~/.ai-session/config.yaml`

```yaml
claude_code:
  current_provider: anthropic  # or zai
  providers:
    anthropic:
      type: oauth
      description: Official Anthropic Claude Code (OAuth)
    zai:
      type: api_key
      description: Z.AI proxy (3x usage at lower cost)
      api_key: your-key-here  # Set via 'chronicle claude-provider setup zai'
      base_url: https://api.z.ai/api/anthropic
      timeout_ms: 3000000
```

## Troubleshooting

### "Z.AI API key not configured"

Run `chronicle claude-provider setup zai` to configure your API key.

### Changes Not Taking Effect

Make sure to **restart Claude Code** after switching providers.

### Provider Detection Wrong

Check `~/.claude/settings.json` to see actual configuration:

```bash
cat ~/.claude/settings.json
```

If it looks wrong, use `chronicle claude-provider restore` to restore from a backup.

## Tips

1. **Quick Switching**: Create shell aliases for fast switching:
   ```bash
   alias claude-anthropic='chronicle claude-provider use anthropic'
   alias claude-zai='chronicle claude-provider use zai'
   ```

2. **Check Before Switching**: Always run `chronicle claude-provider current` to see your active provider.

3. **Backups are Automatic**: Every switch creates a timestamped backup, so you can always roll back.

4. **Track Usage**: Chronicle sessions record which provider was active, helping you track costs.

## Example Workflow

```bash
# Start with Anthropic
chronicle claude-provider current
# Output: Current Provider: anthropic

# Hit usage limit, switch to Z.AI
chronicle claude-provider setup zai  # First time only
chronicle claude-provider use zai
# Restart Claude Code

# Later, switch back
chronicle claude-provider use anthropic
# Restart Claude Code
```

## Security Notes

- API keys are stored in `~/.ai-session/config.yaml` (file permissions: 600)
- Keys are masked when displayed (shows first 8 + last 4 chars)
- Backups are stored in `~/.claude/backups/` with timestamps
- Never commit config files to git

## Future Enhancements

- Auto-detect when hitting rate limits and suggest switching
- Track usage costs per provider
- Support for additional providers (OpenRouter, etc.)
- Provider-specific session tagging

---

**Need Help?**

```bash
chronicle claude-provider --help
```

Each subcommand has detailed help:
```bash
chronicle claude-provider use --help
chronicle claude-provider setup --help
```
