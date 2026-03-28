# BOOTSTRAP.md - Session Initialization Ceremony

## On First Run

1. Check if MEMORY.md exists → if not, create from template
2. Check if memory/ directory exists → if not, create
3. Initialize empty today's log if not exists

## On Every Session Start

1. MemoryInjector loads today's + yesterday's daily logs
2. If mode="main", also load MEMORY.md
3. Compose into system prompt under "## Memory" section

## On Every Message

1. Save to daily log (append-only)
2. If preference mentioned → update MEMORY.md
