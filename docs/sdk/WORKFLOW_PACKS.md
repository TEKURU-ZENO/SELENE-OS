# Workflow Packs System

## Overview

Workflow Packs are robust, reusable, pre-defined templates in SELENE OS that dictate specific multi-step sequences for common complex tasks. Instead of relying purely on zero-shot LLM reasoning to invent a plan on the fly, Workflow Packs provide the Layer 4 (Planner) with structured blueprints. This ensures deterministic, high-quality execution for specialized domains like code refactoring, data analysis, or deep research.

---

## What are Workflow Packs?

A Workflow Pack is essentially a declarative JSON/YAML manifest coupled with optional Python hooks. It defines:
- **Triggers:** Intent classifications (Layer 1) that should activate the pack.
- **Steps:** The sequential or parallel nodes to execute.
- **Capabilities:** The specific tools (Plugins) required for the pack.
- **Expected Outputs:** Validation schema for the final result.

By utilizing Workflow Packs, SELENE shifts from a generalized reasoning engine to an expert system for targeted tasks.

---

## Pack Structure and Format

Packs are defined in YAML format for readability. Below is an example structure:

```yaml
# packs/code_review.yaml
name: "Code Review Assistant"
id: "pack-code-review-01"
version: "1.0.0"
domain: "coding"

activation:
  intents:
    - "CODE_REVIEW"
    - "SECURITY_AUDIT"
  confidence_threshold: 0.85

capabilities_required:
  - "FILE_OPERATION"
  - "EXECUTE_CODE"

steps:
  - id: "step_1"
    action: "READ_DIFF"
    description: "Extract the git diff of the current working tree."
  - id: "step_2"
    action: "STATIC_ANALYSIS"
    description: "Run pylint and safety checks on modified files."
  - id: "step_3"
    action: "LLM_CRITIQUE"
    description: "Evaluate the logic and architecture of the changes."
    
output:
  format: "markdown"
  schema: "CodeReviewReportSchema"
```

---

## Built-In Packs

SELENE ships with several highly tuned, default workflow packs to bootstrap cognitive capability out-of-the-box.

### 1. Research Pack (`pack-research-core`)
**Goal:** Deep dive into a web topic.
- Executes iterative searches.
- Scrapes and summarizes long-form text.
- Outputs citations and a synthesized markdown report.

### 2. Coding Pack (`pack-coding-dev`)
**Goal:** Scaffold, write, and test code.
- Reads context and workspace architecture.
- Writes code to file.
- Executes unit tests in the Layer 7 Sandbox.
- Iterates based on stderr output until tests pass.

### 3. Analysis Pack (`pack-data-analysis`)
**Goal:** Interpret CSV/JSON data.
- Loads data into pandas dataframe in Sandbox.
- Generates descriptive statistics.
- Creates matplotlib visualizations.
- Explains findings.

---

## Creating Custom Packs

Developers can easily create and inject custom workflow packs.

1. **Create the YAML Definition:** Define your steps and requirements.
2. **Define Schemas:** If your pack outputs structured data, add Pydantic models to `backend/schemas/packs.py`.
3. **Register the Pack:** Place the YAML file in the `workflows/` directory. On backend startup, the Orchestrator will automatically parse and register it.

```python
# To dynamically register a pack via code
from backend.core.planner import register_workflow_pack

register_workflow_pack("path/to/custom_pack.yaml")
```

---

## Pack Validation and Testing

To ensure reliability, SELENE provides a test harness for Workflow Packs.

Run the validation suite via CLI:
```bash
python -m backend.testing.validate_packs
```
This utility will:
- Check YAML syntax.
- Ensure all referenced capabilities exist in the plugin registry.
- Verify that there are no circular dependencies in step execution graphs.

---

## Sharing and Distribution

Workflow packs are fully portable. You can share them by distributing the YAML manifest and any associated custom plugin Python files. In future versions, SELENE will introduce a central package registry (like npm or pip) for community-driven workflow packs.

---

## Integration with the Planner Layer

When a user request arrives, the workflow integration happens in the following sequence:

1. **Layer 1 (Intent Decomposer):** Classifies the user's prompt (e.g., "Review my code").
2. **Layer 4 (Planner):** Before generating an ad-hoc plan via LLM, it queries the Workflow Pack Registry.
3. **Match Found:** If a pack's activation triggers match the intent, the planner adopts the pack's steps directly, substituting variables where necessary.
4. **Execution:** The Orchestrator routes the pre-defined steps to the relevant LangGraph execution nodes.

This bypasses the hallucination-prone step of zero-shot planning, drastically improving speed and reliability.
