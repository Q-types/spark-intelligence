# Vibe Project - Claude Code Guide

## Mind MCP - Long-Term Memory System

Mind MCP provides persistent semantic memory with cosine similarity retrieval. Use it to store and retrieve knowledge across sessions.

### Core Tools

#### `mind_remember` - Store a Memory
```
mind_remember(
  content: str,           # The memory content (will be embedded for semantic search)
  memory_type?: str,      # episodic | semantic | procedural | preference
  content_type?: str,     # Legacy: fact | preference | event | goal | observation | decision
  temporal_level?: int,   # 1=hours, 2=days, 3=months, 4=years
  importance?: float,     # 0.0-1.0 (defaults by type)
  user_id?: str           # Defaults to MIND_DEFAULT_USER
)
```

**Memory Types (cognitive classification):**
- `episodic` - Events, tasks, what happened (decay: 30%/month)
- `semantic` - Facts, knowledge, domain expertise (decay: 10%/month)
- `procedural` - Workflows, how-to patterns, best practices (decay: 5%/month)
- `preference` - User/project style, communication preferences (decay: 2%/month)

**When to use:**
- Store important decisions and their rationale
- Record learned patterns and best practices
- Save project-specific knowledge
- Track user preferences and communication style

#### `mind_retrieve` - Retrieve Relevant Memories
```
mind_retrieve(
  query: str,             # Natural language query
  limit?: int,            # Max results (default: 10, max: 100)
  min_salience?: float,   # Threshold 0.0-1.0
  memory_types?: list,    # Filter: ["episodic", "semantic", etc.]
  include_reflections?: bool,  # Include meta-insights (default: true)
  user_id?: str
)
```

**Scoring Formula:**
```
S_i = α·sim(q,m_i) + β·I_i + γ·R_i - δ·A_i
```
- `sim` = Semantic similarity (cosine) + keyword (BM25) via RRF fusion
- `I` = Importance score (static + dynamic salience)
- `R` = Recency boost (last accessed)
- `A` = Age decay penalty (type-specific)

**When to use:**
- Before starting a task: retrieve relevant context
- When making decisions: recall past outcomes
- To check for contradictions or prior knowledge

#### `mind_decide` - Track Decision Outcomes
```
mind_decide(
  memory_ids: list,       # Memory IDs that influenced the decision
  decision_summary: str,  # What was decided (no PII)
  outcome_quality: float, # -1.0 (bad) to 1.0 (good)
  outcome_signal?: str,   # user_accepted | user_rejected | task_completed | agent_feedback
  memory_scores?: dict,   # Optional: memory_id -> retrieval score for weighted attribution
  user_id?: str
)
```

**Learning Loop:**
- Good outcomes (+quality) increase memory salience
- Bad outcomes (-quality) decrease salience
- Memories that lead to good decisions get retrieved more often

**When to use:**
- After a user accepts/rejects a suggestion
- When a task completes successfully or fails
- To reinforce or penalize memory patterns

#### `mind_reflect` - Generate Meta-Insights
```
mind_reflect(
  force?: bool,           # Run even if trigger count not reached (default: false)
  user_id?: str
)
```

**Reflection process:**
- Triggers automatically every 50 memories
- Analyzes patterns, unresolved goals, decisions, contradictions
- Generates "compressed gradients through experience"
- Stores reflection as high-importance memory (0.9 salience)

**When to use:**
- At end of significant work sessions
- When explicitly requested
- To synthesize learnings from recent work

#### `mind_conflicts` - Get Memory Conflicts
```
mind_conflicts(
  limit?: int,            # Max conflicts (default: 10)
  include_resolved?: bool,# Include resolved conflicts (default: false)
  user_id?: str
)
```

**Conflict detection:**
- Cosine similarity threshold: 0.85
- Negation pattern matching
- Auto-resolution based on confidence delta and time

**When to use:**
- To maintain memory consistency
- When information seems contradictory
- Before making decisions based on potentially outdated info

#### `mind_health` - Check System Status
```
mind_health()
```

Returns: model info, database stats, total memories, users

### Best Practices

1. **Session Start**: Retrieve relevant context before beginning work
   ```
   mind_retrieve(query="[project/task description]", limit=5)
   ```

2. **Important Decisions**: Store with rationale
   ```
   mind_remember(
     content="Chose X over Y because Z. Trade-offs: ...",
     memory_type="episodic",
     temporal_level=3
   )
   ```

3. **Learned Patterns**: Store as procedural
   ```
   mind_remember(
     content="When doing X, always Y first to avoid Z",
     memory_type="procedural",
     temporal_level=4
   )
   ```

4. **Feedback Loop**: Track outcomes
   ```
   # After successful task
   mind_decide(
     memory_ids=["id1", "id2"],
     decision_summary="Used approach X for Y",
     outcome_quality=0.8,
     outcome_signal="task_completed"
   )
   ```

5. **Session End**: Trigger reflection if significant work done
   ```
   mind_reflect(force=true)
   ```

### Technical Details

- **Embedding Model**: nomic-ai/nomic-embed-text-v1.5 (768 dimensions)
- **Similarity**: L2-normalized embeddings, cosine = dot product
- **Search**: Hybrid semantic + BM25 keyword with RRF fusion (k=60)
- **Database**: SQLite with FTS5 at `~/.mind/v2/memories.db`

---

## Spark Intelligence - Self-Evolving AI Companion

Spark Intelligence is a self-evolving AI companion that turns past work into future-ready behavior. It runs 100% locally and continuously converts experience into adaptive operational behavior.

### What Spark Is

- **NOT a chatbot** - A living intelligence runtime
- **NOT a fixed rule set** - Adapts through use
- A system that keeps context, patterns, and practical lessons in a form that agents can use at the right moment

### Intelligence Operating Flow

```
You do work → Spark captures memory → Spark distills and transforms it
→ Spark delivers advisory context → You act with better context
→ Outcomes re-enter the loop
```

**12-Stage Pipeline:**
1. **Event Capture** - Hooks capture events from agent sessions
2. **Queue** - Events queued for processing
3. **Pipeline** - Processing orchestration
4. **Memory Capture** - Importance scoring and categorization
5. **Meta-Ralph** - Quality gate (6-dimension scoring)
6. **Cognitive Learner** - Insight extraction and reliability tracking
7. **EIDOS** - Prediction → Outcome → Evaluation loop
8. **Distillation** - Compress noisy data into reliable insights
9. **Transformation** - Shape for practical reuse
10. **Advisory** - Package and deliver at right workflow point
11. **Promotion** - High-value items promoted to CLAUDE.md
12. **Chips** - Domain-specific expertise modules

### Installation & Setup

**Prerequisites:** Python 3.10+, pip, Git

**Quick Install (Mac/Linux):**
```bash
curl -fsSL https://raw.githubusercontent.com/vibeforge1111/vibeship-spark-intelligence/main/install.sh | bash
```

**Quick Install (Windows):**
```powershell
irm https://raw.githubusercontent.com/vibeforge1111/vibeship-spark-intelligence/main/install.ps1 | iex
```

**Start Services:**
```bash
spark up              # Full mode (all services)
spark up --lite       # Lightweight mode (core only)
```

**Verify Health:**
```bash
spark health
spark status
spark services
```

### CLI Commands

| Command | Description |
|---------|-------------|
| `spark up` | Start all services |
| `spark up --lite` | Start core services only |
| `spark down` | Stop all services |
| `spark status` | Show system status |
| `spark health` | Health check |
| `spark services` | List running services |
| `spark learnings` | View what Spark has learned |
| `spark promote` | Promote insights to CLAUDE.md |

### Claude Code Integration

Spark integrates with Claude Code via hooks. Install hooks:

```bash
./scripts/install_claude_hooks.sh  # Mac/Linux
powershell -File scripts\install_claude_hooks.ps1  # Windows
```

This creates `~/.claude/spark-hooks.json`. Merge the `hooks` object into your `~/.claude/settings.json`.

**Hook Events Captured:**
- `PreToolUse` → pre_tool advisory
- `PostToolUse` → post_tool learning
- `PostToolUseFailure` → failure patterns
- `UserPromptSubmit` → user prompt context

### Configuration (Tuneables)

Edit `~/.spark/tuneables.json` for runtime config:

```json
{
  "advisory": {
    "enabled": true,
    "cooldown_s": 300,
    "max_per_session": 20
  },
  "meta_ralph": {
    "min_quality_score": 0.6
  },
  "observatory": {
    "enabled": true,
    "auto_sync": true,
    "vault_dir": "~/Documents/Obsidian Vault/Spark-Intelligence-Observatory"
  }
}
```

### Custom Modifications (qtypes Setup)

**LLM Routing:**
- Chat/memory → Codex (gpt-5.5)
- Builder/mission → Claude (sonnet)

**Claude Execution Bridge:**
- `SPARK_CLAUDE_AGENT_MODE=true`
- `DEFAULT_MISSION_PROVIDER=claude`
- `--permission-mode acceptEdits`

**Quality Gates Implemented:**
| Gate | Threshold | Blocking |
|------|-----------|----------|
| `test_pass_rate` | 100% | Yes |
| `lint_critical_errors` | 0 | Yes |
| `scope_coverage` | 80% | No |

**Enhanced Review Pipeline:**
- `verificationService.ts` - Git diff capture, file verification, lint/type/test
- `scopeEnforcement.ts` - Context re-injection for long tasks
- `driftDetection.ts` - Scope adherence checking
- `reviewLoopController.ts` - Quality gate cycles

**Architect MCP Integration:**
- `architect_enforce_scope` - Supervisor drift checking
- `architect_review_loop` - Iterative quality improvement
- `architect_project_manager_review` - Sprint go/no-go decisions

### Observability

**Spark Pulse Dashboard:** http://localhost:8765

**Obsidian Observatory:**
```bash
python scripts/generate_observatory.py --force --verbose
```
Opens at `~/Documents/Obsidian Vault/Spark-Intelligence-Observatory`

---

## SPARK Mission System

The mission system executes complex multi-step tasks with skill loading, verification, and review loops.

### Mission Prompt Template

Use this template for well-structured missions:

```
spark-mission run "
PROJECT: <Project Name> - <Sprint/Phase>: <Title>
GOAL: <One-line goal statement>

LOAD SKILLS:
- <skill-name> (<what it provides>)
- <skill-name> (<what it provides>)
- ...

TASKS:
1. <Task title>
   - <Subtask details>
   - <Subtask details>

2. <Task title>
   - <Subtask details>
   - <Subtask details>

CONSTRAINTS:
- <Hard rule that must not be violated>
- <Security constraint>
- <Pattern to follow>

EXIT CRITERIA:
- [ ] <Verifiable outcome>
- [ ] <Verifiable outcome>
- [ ] <Verifiable outcome>
"
```

### Complete Mission Example

```
spark-mission run "
PROJECT: QSol Data Project Finder - Sprint 2: Core Diagnostic Engine
GOAL: Build /api/diagnose endpoint with LLM classification, scoring, and roadmap generation

LOAD SKILLS:
- LLM Architect (structured output, prompting, RAG integration)
- Prompt Engineer (system prompts, few-shot, chain-of-thought)
- API Designer (REST patterns, validation, rate limiting)
- TypeScript Strict Mode (Zod schemas, type inference)
- Test Architect (unit tests, integration tests, fixtures)
- Security Hardening (input validation, injection prevention)
- Supabase Backend (database operations, RLS compliance)

TASKS:
1. Create LLM prompt with classification taxonomy:
   - 8 categories: reporting_automation, spreadsheet_to_system, forecasting_early_warning,
     customer_intelligence, ai_knowledge_assistant, workflow_automation, data_readiness,
     not_enough_information
   - Scoring rubric: value_potential, feasibility, urgency, data_readiness, repeatability
   - Formula: S = 0.25V + 0.25F + 0.15U + 0.15D + 0.15R - 0.05C

2. Build POST /api/diagnose endpoint:
   - Validate input (20-3000 chars)
   - Call OpenAI with structured output schema
   - Retrieve relevant playbook by classification
   - Store in Supabase diagnoses table
   - Return diagnosis_id, instant_result, roadmap_preview

3. Connect frontend to API:
   - Wire component to POST /api/diagnose
   - Handle loading, success, error states
   - Display classification, confidence, project fit score

4. Create test suite with 20+ example problems:
   - Cover all 8 classification types
   - Test edge cases: vague inputs, mixed problems
   - Target >80% classification accuracy

CONSTRAINTS:
- LLM must classify conservatively
- Prefer automation/reporting before recommending AI
- Handle low-confidence with follow-up question
- No guaranteed ROI claims in output

EXIT CRITERIA:
- [ ] /api/diagnose returns valid classification for all test cases
- [ ] Scoring formula correctly implemented
- [ ] Test suite passes with >80% accuracy
- [ ] All inputs validated server-side
"
```

### Skills Reference

Load skills with Spawner:

```bash
# Load essentials pack
spawner_skills action="pack" pack="essentials"

# Load specific skills
spawner_skills action="get" name="supabase-backend"
spawner_skills action="get" name="llm-architect"
spawner_skills action="get" name="security-hardening"
```

**Common Skills by Category:**

| Category | Skills |
|----------|--------|
| **Database** | Supabase Backend, PostgreSQL Wizard, Database Architect |
| **LLM/AI** | LLM Architect, Prompt Engineer, RAG Engineer |
| **Frontend** | Frontend Engineering, Tailwind CSS UI, UI Design, UX Design |
| **Backend** | Backend Engineering, API Designer, Python Craftsman |
| **Security** | Security Hardening, Auth Specialist |
| **Testing** | Test Architect, Testing Automation, Code Reviewer |
| **DevOps** | DevOps Engineering, Docker Specialist, Vercel Deployment |
| **Data Science** | time-series-specialist, graph-ml-specialist, anomaly-detection-specialist |

### Mission Mind MCP Integration

**Before each sprint**, retrieve relevant context:
```
mind_retrieve(user_id: "qtypes", query: "<project> <sprint topic>", limit: 5)
```

**After completing significant work**, store learnings:
```
mind_remember(
  user_id: "qtypes",
  content: "<what was learned or decided>",
  memory_type: "procedural",
  temporal_level: 3,
  importance: 0.8
)
```

### Mission Chaining

Missions can be chained together for multi-sprint projects:

```
# Sprint 1
spark-mission run "PROJECT: MyApp - Sprint 1: Foundation..."

# Sprint 2 (references Sprint 1)
spark-mission run "PROJECT: MyApp - Sprint 2: Core Features
Continue from Sprint 1 (foundation complete).
..."
```

Spark tracks mission IDs (e.g., `spark-1778155166447`) and retrieves past mission context via Mind MCP.

---

## Other MCP Servers

### Spawner MCP
Project skills, validation, and sharp edges. Call `spawner_orchestrate` at session start.

**Key tools:**
- `spawner_skills` - Search and load specialist skills
- `spawner_validate` - Run guardrail checks on code
- `spawner_watch_out` - Get gotchas for your tech stack
- `spawner_unstick` - Get alternative approaches when stuck

### IdeaRalph MCP
Startup idea validation and PMF scoring. Use `idearalph_validate` for idea assessment.

**Key tools:**
- `idearalph_validate` - Score idea on 10 PMF dimensions
- `idearalph_brainstorm` - Generate startup ideas for a topic
- `idearalph_refine` - Iteratively improve an idea
- `idearalph_prd` - Generate Product Requirements Document

### Architect MCP
Project planning with teams and sprints. Use `architect_full_pipeline` for end-to-end planning.

**Key tools:**
- `architect_init` - Initialize project from idea
- `architect_plan` - Create execution plan
- `architect_spawn_teams` - Create team structure
- `architect_smart_assign` - Assign tasks with skill loading
- `architect_enforce_scope` - Supervisor drift checking
- `architect_review_loop` - Quality improvement cycles

### Muse MCP
Creative idea mutation and contradiction finding. Use `muse_expand_prompt` to start.

**Key tools:**
- `muse_expand_prompt` - Expand raw prompt into structured context
- `muse_retrieve_associations` - Multi-mode retrieval for productive associations
- `muse_find_contradictions` - Surface tensions and counter-evidence
- `muse_mutate_ideas` - Apply transformation operators to generate variants

---

## Quick Reference

### Session Start Checklist
1. `spark health` - Verify Spark is running
2. `mind_retrieve(query="<project context>")` - Load relevant memories
3. `spawner_orchestrate(cwd="<project path>")` - Load project skills

### Session End Checklist
1. `mind_remember(content="<session learnings>")` - Store important insights
2. `mind_reflect(force=true)` - Generate meta-insights if significant work done

### Key Paths
| Path | Purpose |
|------|---------|
| `~/.spark/` | Spark data directory |
| `~/.spark/tuneables.json` | Runtime configuration |
| `~/.spark/research_reports/` | Daily research outputs |
| `~/.mind/v2/memories.db` | Mind MCP database |
| `~/.claude/settings.json` | Claude Code settings |
