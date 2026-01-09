#!/bin/bash
# Setup Jira tickets for Days 9-18 reorganization
# Run this after setting JIRA_EMAIL and JIRA_API_TOKEN

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JIRA_HELPER="${SCRIPT_DIR}/jira-helper.sh"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Jira Ticket Setup - Days 9-18 Reorganization${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Step 1: Fix existing ticket titles (remove RL-XX: prefix)
echo -e "${GREEN}Step 1: Fixing existing ticket titles...${NC}"

"$JIRA_HELPER" update-issue RL-74 title "(Day 9): Browser compatibility testing"
"$JIRA_HELPER" update-issue RL-68 title "(Day 13): Performance profiling and optimization"
"$JIRA_HELPER" update-issue RL-66 title "(Day 9): End-to-end testing with Playwright"
"$JIRA_HELPER" update-issue RL-65 title "(Day 9): Comprehensive integration test suite"
"$JIRA_HELPER" update-issue RL-49 title "(Day 9): Complete integration test suite"
"$JIRA_HELPER" update-issue RL-39 title "(Day 9): Integration testing suite"

echo ""
echo -e "${GREEN}Step 2: Creating new tickets from reorganization plan...${NC}"

# Day 9 tickets
"$JIRA_HELPER" create-story "(Day 9): Vector Memory Integration" "Add capture hooks to gameplay APIs for memory system. Tasks: Add capture in conversations.py, combat.py, quests.py, spells.py, loot.py. Test end-to-end memory capture and retrieval."

"$JIRA_HELPER" create-story "(Day 9): Save/Load UI Integration" "Add save/load buttons and UI. Tasks: SaveGameButton component, SaveSlotsModal component, Load Game in menu, auto-save every 5 minutes."

"$JIRA_HELPER" create-story "(Day 9): Bug Fixes & Stability" "Fix critical bugs only. Reduced scope from 8 SP to 1 SP."

# Day 10 tickets
"$JIRA_HELPER" create-story "(Day 10): Roll Tag Parser" "Create roll tag parser service to parse DM output for dice roll requests. Parse [ROLL:...] tags."

"$JIRA_HELPER" create-story "(Day 10): Roll Executor" "Create roll executor service to execute dice rolls (d20, advantage, modifiers)."

"$JIRA_HELPER" create-story "(Day 10): DM System Prompt Enhancement" "Update DM system prompt to request rolls via tags. Add dice roll guidelines."

"$JIRA_HELPER" create-story "(Day 10): Roll Integration in Conversation" "Integrate roll system into conversation flow. Parse tags, execute rolls, inject results."

"$JIRA_HELPER" create-story "(Day 10): Frontend Roll UI" "Create DiceRollResult component. Display roll results in chat with animation."

# Day 12 tickets
"$JIRA_HELPER" create-story "(Day 12): Context Builder with Spell Slots" "Add spell slot tracking to character context sent to DM. Include slots remaining."

"$JIRA_HELPER" create-story "(Day 12): Spell Slot Awareness in DM" "Update DM to acknowledge spell slots in narration. Warn on last slots."

"$JIRA_HELPER" create-story "(Day 12): Active Effects Database" "Create effects table and service. Track buffs/debuffs/conditions duration."

# Day 13 tickets
"$JIRA_HELPER" create-story "(Day 13): Image Generation Integration" "Connect ImageService to DM responses. Scene detection logic, image display component, cache management."

"$JIRA_HELPER" create-story "(Day 13): Frontend Spell Slot & Effects UI" "Display spell slots and active effects in UI. Slot indicators, effect badges."

"$JIRA_HELPER" create-story "(Day 13): Message Summarization - Part 1" "Basic message summarization to condense conversation history. Reduced scope 1 SP."

# Day 14 tickets
"$JIRA_HELPER" create-story "(Day 14): Message Summarization - Part 2" "Complete message summarization with summary injection into context."

"$JIRA_HELPER" create-story "(Day 14): Context Window Management" "Implement context pruning to stay within token limits. Keep recent + summaries."

"$JIRA_HELPER" create-story "(Day 14): AI Companion UI Integration - Part 1" "Create companion panel and speech in chat. Companion visibility. 8 SP reduced scope."

# Day 15 tickets
"$JIRA_HELPER" create-story "(Day 15): AI Companion UI Integration - Part 2" "Complete companion UI with trigger logic and DM integration."

"$JIRA_HELPER" create-story "(Day 15): Demo Video Creation" "Record 5-minute demo video showing all features. Character creation to combat."

"$JIRA_HELPER" create-story "(Day 15): README & Documentation" "Complete README with setup instructions, features, screenshots, roadmap."

# Day 16 tickets
"$JIRA_HELPER" create-story "(Day 16): ARCHITECTURE.md" "Document system architecture with diagrams. Service layer, API structure, data flow."

"$JIRA_HELPER" create-story "(Day 16): Final Bug Fixes & Polish" "Fix remaining bugs and polish UI/UX. Final testing pass."

"$JIRA_HELPER" create-story "(Day 16): Rate Limiting & DDoS" "Add basic rate limiting to API endpoints. 2 SP reduced scope."

# Day 17 tickets
"$JIRA_HELPER" create-story "(Day 17): Docker Multi-Stage Builds" "Optimize Docker builds with multi-stage pattern. Reduce image size."

"$JIRA_HELPER" create-story "(Day 17): Environment Config Management" "Implement proper environment variable management for production."

"$JIRA_HELPER" create-story "(Day 17): Database Migration Strategy" "Setup database migration system with Alembic. Migration workflow."

"$JIRA_HELPER" create-story "(Day 17): Security Audit" "Basic security audit - SQL injection, XSS, CORS. 4 SP reduced scope."

# Deferred tickets (for reference, not creating)
echo ""
echo -e "${BLUE}Deferred tickets (P3 - Post-Internship):${NC}"
echo "- Character Creation Steps 3-6 (27 SP)"
echo "- Adventure System (16 SP)"
echo "- Testing Suite (21 SP)"
echo "- Advanced D&D Features (31 SP)"
echo "- Observability Stack (34 SP)"
echo "- CI/CD & Deployment (21 SP)"
echo "- Advanced Features (11 SP)"
echo ""
echo -e "${GREEN}✓ Ticket setup complete!${NC}"
echo -e "${BLUE}Total new tickets created: 26${NC}"
echo -e "${BLUE}Total SP for Days 9-18: 90 SP${NC}"
echo ""
echo -e "${GREEN}Next: Run './jira-helper.sh list-tickets' to verify${NC}"
