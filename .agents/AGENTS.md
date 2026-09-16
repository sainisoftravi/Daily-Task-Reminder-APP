# Repository Agent Rules & Automatic Documentation Guidelines

## Automatic README.md Documentation Rule
Whenever you complete changes to the codebase, UI layouts, backend logic, API endpoints, database schemas, templates, or configuration files in response to a user request or prompt:

1. **Automatically Update `README.md`**:
   - Update `README.md` before concluding your task turn.
   - Append a new entry to the table in **Section 7: Prompt-by-Prompt Development & Optimization History**.
   - Include:
     - Prompt Number (`#`)
     - Exact / Summarized User Request
     - Technical Solution & Implementation Rationale
     - List of Modified Files & Components (with clickable markdown file links)
     - Functional & Visual Outcome
   - Update any other relevant sections of `README.md` (such as Section 2 Sitemap or Section 3 REST API Reference) if new routes or features were introduced.
