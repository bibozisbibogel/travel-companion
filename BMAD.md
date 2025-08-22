BMAD - Breakthrough Method of Agile AI-Driven Development

The Official BMad-Method Masterclass
https://www.youtube.com/watch?v=LorEJPrALcg

BMad Github: https://github.com/bmad-code-org/BMAD-METHOD

# install
npx bmad-method install

# The Planning Workflow
1. Analyst
    - Does research, brainstorming, market research, competitor analysis.
    - Creates project brief.
2. Project Manager
    - Creates PRD from brief.
3. UX Expert
    - Creates UX (frontend) specification.
4. Architect
    - Creates Architecture from PRD + UX Spec
5. Project Owner
    - Ensures all documents are consistent and complete
    - Shards large documents for development consumption
      - Shard Epics
      - Shard Architecture

# The Core Development Cycle
1. Scrum Master
    - Drafts Next Story from Sharded Epic + Architecture
    - User Approves the draft
2. Developer
    - Implements story (Tasks + Tests)
3. Quality Advisor
    - Reviews story
    - Creates test scenarios

# PRD (Product Requirement Document)
- A PRD describes what the product should do.
- It’s usually written by product managers.
- Example: “The system shall allow users to reset their password via email.”

# PRP = Product Release Plan
- While the PRD defines what the product/feature is, the PRP defines how and when it will be released.
- It’s essentially a translation of the PRD into an execution plan.

/generate-prp docs/stories/story.md