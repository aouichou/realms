#!/bin/bash
# Jira API Helper Script for Mistral Realms Project
# Usage: ./jira-helper.sh <command> [args]

# Configuration - Set these via environment variables or edit directly
JIRA_HOST="${JIRA_HOST:-aouichou.atlassian.net}"
JIRA_EMAIL="${JIRA_EMAIL:-}"
JIRA_API_TOKEN="${JIRA_API_TOKEN:-}"
PROJECT_KEY="RL"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper function to make Jira API calls
jira_api() {
    local method="$1"
    local endpoint="$2"
    local data="$3"

    if [ -z "$JIRA_EMAIL" ] || [ -z "$JIRA_API_TOKEN" ]; then
        echo -e "${RED}Error: JIRA_EMAIL and JIRA_API_TOKEN must be set${NC}"
        echo "Export them as environment variables or edit this script"
        exit 1
    fi

    local url="https://${JIRA_HOST}/rest/api/3/${endpoint}"

    if [ "$method" = "GET" ]; then
        curl -s -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
            -H "Content-Type: application/json" \
            "$url"
    else
        curl -s -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
            -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$url"
    fi
}

# Command: List Projects
cmd_list_projects() {
    echo -e "${BLUE}Fetching projects...${NC}"
    jira_api "GET" "project" | jq -r '.[] | "\(.key)\t\(.name)"'
}

# Command: Create Epic
cmd_create_epic() {
    local summary="$1"
    local description="$2"

    if [ -z "$summary" ]; then
        echo -e "${RED}Usage: $0 create-epic <summary> [description]${NC}"
        exit 1
    fi

    local data=$(cat <<EOF
{
    "fields": {
        "project": {
            "key": "${PROJECT_KEY}"
        },
        "summary": "${summary}",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "text": "${description:-No description provided}",
                            "type": "text"
                        }
                    ]
                }
            ]
        },
        "issuetype": {
            "name": "Epic"
        }
    }
}
EOF
)

    echo -e "${BLUE}Creating epic: ${summary}${NC}"
    local response=$(jira_api "POST" "issue" "$data")
    local key=$(echo "$response" | jq -r '.key // empty')

    if [ -n "$key" ]; then
        echo -e "${GREEN}✓ Created epic: ${key}${NC}"
        echo "$key"
    else
        echo -e "${RED}✗ Failed to create epic${NC}"
        echo "$response" | jq '.'
        exit 1
    fi
}

# Command: Create Story
cmd_create_story() {
    local summary="$1"
    local description="$2"
    local epic_key="$3"
    local story_points="$4"

    if [ -z "$summary" ]; then
        echo -e "${RED}Usage: $0 create-story <summary> [description] [epic_key] [story_points]${NC}"
        exit 1
    fi

    local epic_field=""
    if [ -n "$epic_key" ]; then
        epic_field=",\"parent\": {\"key\": \"${epic_key}\"}"
    fi

    local data=$(cat <<EOF
{
    "fields": {
        "project": {
            "key": "${PROJECT_KEY}"
        },
        "summary": "${summary}",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "text": "${description:-No description provided}",
                            "type": "text"
                        }
                    ]
                }
            ]
        },
        "issuetype": {
            "name": "Story"
        }${epic_field}
    }
}
EOF
)

    echo -e "${BLUE}Creating story: ${summary}${NC}"
    local response=$(jira_api "POST" "issue" "$data")
    local key=$(echo "$response" | jq -r '.key // empty')

    if [ -n "$key" ]; then
        echo -e "${GREEN}✓ Created story: ${key}${NC}"
        echo "$key"
    else
        echo -e "${RED}✗ Failed to create story${NC}"
        echo "$response" | jq '.'
        exit 1
    fi
}

# Command: Get Issue
cmd_get_issue() {
    local issue_key="$1"

    if [ -z "$issue_key" ]; then
        echo -e "${RED}Usage: $0 get-issue <issue_key>${NC}"
        exit 1
    fi

    jira_api "GET" "issue/${issue_key}" | jq '.'
}

# Command: Get Transitions for an Issue
cmd_get_transitions() {
    local issue_key="$1"

    if [ -z "$issue_key" ]; then
        echo -e "${RED}Usage: $0 get-transitions <issue_key>${NC}"
        exit 1
    fi

    echo -e "${BLUE}Fetching available transitions for ${issue_key}...${NC}"
    jira_api "GET" "issue/${issue_key}/transitions" | jq -r '.transitions[] | "\(.id)\t\(.name)"'
}

# Command: Transition Issue to Done
cmd_mark_done() {
    local issue_key="$1"

    if [ -z "$issue_key" ]; then
        echo -e "${RED}Usage: $0 mark-done <issue_key>${NC}"
        exit 1
    fi

    # First, get available transitions to find the "Done" transition ID
    local transitions=$(jira_api "GET" "issue/${issue_key}/transitions")
    local done_id=$(echo "$transitions" | jq -r '.transitions[] | select(.name == "Done") | .id')

    if [ -z "$done_id" ]; then
        echo -e "${RED}✗ Could not find 'Done' transition for ${issue_key}${NC}"
        echo -e "${BLUE}Available transitions:${NC}"
        echo "$transitions" | jq -r '.transitions[] | "\(.id)\t\(.name)"'
        exit 1
    fi

    local data=$(cat <<EOF
{
    "transition": {
        "id": "${done_id}"
    }
}
EOF
)

    echo -e "${BLUE}Marking ${issue_key} as Done...${NC}"
    local response=$(jira_api "POST" "issue/${issue_key}/transitions" "$data")

    # If response is empty, transition was successful
    if [ -z "$response" ] || [ "$response" = "{}" ]; then
        echo -e "${GREEN}✓ Successfully marked ${issue_key} as Done${NC}"
    else
        echo -e "${RED}✗ Failed to mark ${issue_key} as Done${NC}"
        echo "$response" | jq '.'
        exit 1
    fi
}

# Command: Bulk Mark Issues as Done
cmd_bulk_mark_done() {
    if [ $# -eq 0 ]; then
        echo -e "${RED}Usage: $0 bulk-mark-done <issue_key1> [issue_key2] ...${NC}"
        exit 1
    fi

    local success=0
    local failed=0

    for issue_key in "$@"; do
        echo ""
        if cmd_mark_done "$issue_key" 2>/dev/null; then
            ((success++))
        else
            ((failed++))
        fi
    done

    echo ""
    echo -e "${GREEN}Successfully marked ${success} issues as Done${NC}"
    if [ $failed -gt 0 ]; then
        echo -e "${RED}Failed to mark ${failed} issues${NC}"
    fi
}

# Command: List Open Tickets
cmd_list_tickets() {
    echo -e "${BLUE}Fetching open tickets for project ${PROJECT_KEY}...${NC}"

    # JQL query to get open tickets - status values must be properly quoted
    local jql='project='"${PROJECT_KEY}"' AND status in ("Open","In Progress","To Do") ORDER BY created DESC'

    local data=$(cat <<EOF
{
    "jql": $(echo "$jql" | jq -R .),
    "fields": ["summary", "status", "issuetype", "assignee", "priority"]
}
EOF
)

    local response=$(jira_api "POST" "search/jql" "$data")

    # Check if response is valid
    if echo "$response" | jq -e '.issues' > /dev/null 2>&1; then
        echo "$response" | jq -r '.issues[] | select(.fields.issuetype.name != "Epic") | "\(.key)\t\(.fields.status.name)\t\(.fields.issuetype.name)\t\(.fields.summary)"'

        local total=$(echo "$response" | jq -r '.total // 0')
        echo ""
        echo -e "${GREEN}Total open tickets: ${total}${NC}"
    else
        echo -e "${RED}Error fetching tickets. Check credentials.${NC}"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    fi
}

# Command: List Epics
cmd_list_epics() {
    echo -e "${BLUE}Fetching epics for project ${PROJECT_KEY}...${NC}"

    local jql="project=${PROJECT_KEY} AND issuetype=Epic ORDER BY created DESC"

    local data=$(cat <<EOF
{
    "jql": "${jql}",
    "fields": ["summary", "status"]
}
EOF
)

    local response=$(jira_api "POST" "search/jql" "$data")

    # Check if response is valid
    if echo "$response" | jq -e '.issues' > /dev/null 2>&1; then
        echo "$response" | jq -r '.issues[] | "\(.key)\t\(.fields.status.name)\t\(.fields.summary)"'
    else
        echo -e "${RED}Error fetching epics. Check credentials.${NC}"
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    fi
}

# Main command router
case "${1:-}" in
    list-projects|lp)
        cmd_list_projects
        ;;
    create-epic|ce)
        shift
        cmd_create_epic "$@"
        ;;
    create-story|cs)
        shift
        cmd_create_story "$@"
        ;;
    get-issue|gi)
        shift
        cmd_get_issue "$@"
        ;;
    get-transitions|gt)
        shift
        cmd_get_transitions "$@"
        ;;
    mark-done|md)
        shift
        cmd_mark_done "$@"
        ;;
    bulk-mark-done|bmd)
        shift
        cmd_bulk_mark_done "$@"
        ;;
    list-tickets|lt)
        shift
        cmd_list_tickets "$@"
        ;;
    list-epics|le)
        shift
        cmd_list_epics "$@"
        ;;
    help|--help|-h|"")
        echo "Jira Helper Script for Mistral Realms"
        echo ""
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands:"
        echo "  list-projects (lp)              List all projects"
        echo "  list-epics (le)                 List all epics"
        echo "  list-tickets (lt) [status]      List open tickets (default: Open,In Progress,To Do)"
        echo "  create-epic (ce) <summary> [description]"
        echo "  create-story (cs) <summary> [description] [epic_key] [points]"
        echo "  get-issue (gi) <issue_key>      Get issue details"
        echo "  get-transitions (gt) <issue_key> Get available transitions"
        echo "  mark-done (md) <issue_key>      Mark issue as Done"
        echo "  bulk-mark-done (bmd) <key1> [key2] ... Mark multiple issues as Done"
        echo ""
        echo "Environment Variables:"
        echo "  JIRA_EMAIL      Your Atlassian email"
        echo "  JIRA_API_TOKEN  Your API token"
        echo "  JIRA_HOST       Jira host (default: aouichou.atlassian.net)"
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Run '$0 help' for usage"
        exit 1
        ;;
esac
