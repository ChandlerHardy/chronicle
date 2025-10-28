#!/bin/bash

# Demo: Transient Import-Summarize System
# Shows how sessions are temporarily created and cleaned up

echo "🎭 Chronicle Transient Import-Summarize Demo"
echo "=========================================="

# Create a test session JSON
cat > /tmp/demo_session.json << 'EOF'
{
  "version": "1.0",
  "session": {
    "original_id": 42,
    "timestamp": "2025-01-01T12:00:00",
    "ai_tool": "claude-code",
    "is_session": true,
    "session_transcript": "User: What's the weather like?\nAssistant: I don't have access to real-time weather data, but I can help you understand weather patterns or suggest weather apps you could use!",
    "duration_ms": 15000,
    "title": "Weather Question",
    "tags": "weather,question",
    "keywords": "weather,question,apps",
    "response_summary": null,
    "summary_generated": false,
    "files_mentioned": null,
    "parent_session_id": null,
    "related_session_ids": null
  }
}
EOF

echo "📝 Created demo session JSON"

echo ""
echo "1️⃣ Regular import-session (permanent):"
echo "---------------------------------------"
cat /tmp/demo_session.json | python3 -m backend.main import-session

echo ""
echo "2️⃣ import-and-summarize (transient):"
echo "------------------------------------"
echo "👀 Watch for:"
echo "   - Negative session ID"
echo "   - '[TEMP]' prefix in title"
echo "   - Cleanup process at the end"
echo ""

cat /tmp/demo_session.json | python3 -m backend.main import-and-summarize

echo ""
echo "✅ Demo completed! Check that no negative ID sessions remain in the database."

# Cleanup
rm /tmp/demo_session.json