# /workstack:create-from-plan - Examples

This document provides concrete examples of how the `/workstack:create-from-plan` command works in practice.

## Example 1: Simple Plan with Clear Structure

### User Interaction

**User presents plan:**

```markdown
## Implementation Plan: Add User Authentication

### Steps

1. Create authentication middleware in `src/middleware/auth.py`
2. Add JWT token validation using PyJWT library
3. Update routes in `src/api/routes.py` to use authentication
4. Add unit tests in `tests/test_auth.py`
5. Add integration tests in `tests/test_api.py`
```

**User runs:** `/workstack:create-from-plan`

### Command Execution

**Assistant:** I'll create a worktree from your authentication implementation plan. Let me analyze it and ask any clarifying questions.

The plan looks clear with explicit file paths and structured steps. Let me clarify a few details:

**Using AskUserQuestion tool:**

- Question: "Which JWT library version should we use?"
  - Options: PyJWT latest (2.8.0), PyJWT 2.7.0 (stable), Other
- Question: "What should happen when authentication fails?"
  - Options: Return 401 Unauthorized, Redirect to login, Raise exception

**User selects:** PyJWT latest, Return 401 Unauthorized

**Assistant enhances plan:**

```markdown
## Implementation Plan: Add User Authentication

### Context & Understanding

- Using PyJWT 2.8.0 for token validation
- Authentication failures return 401 Unauthorized status

### Steps

1. Create authentication middleware in `src/middleware/auth.py`
   - Success: Middleware validates JWT tokens
   - On failure: Returns 401 status
2. Add JWT token validation using PyJWT library (v2.8.0)
   - Success: Valid tokens are decoded
   - On failure: Invalid tokens rejected
3. Update routes in `src/api/routes.py` to use authentication
   - Success: Protected routes require valid token
4. Add unit tests in `tests/test_auth.py`
   - Success: All auth scenarios covered
5. Add integration tests in `tests/test_api.py`
   - Success: End-to-end auth flow works
```

**Creates worktree:**

```
✅ Worktree created: **add-user-authentication**

Plan: `add-user-authentication-plan.md`
Branch: `add-user-authentication`
Location: `/Users/dev/workstacks/add-user-authentication`

**Next step:**
`workstack switch add-user-authentication && claude --permission-mode acceptEdits "/workstack:implement-plan"`
```

## Example 2: Complex Plan Requiring Phase Decomposition

### User Interaction

**User presents plan:**

```markdown
## Refactor Database Layer

Need to:

- Replace SQLAlchemy with asyncpg for better performance
- Migrate all models to new schema
- Update all API endpoints to use async
- Add caching layer with Redis
- Update tests
```

**User runs:** `/workstack:create-from-plan`

### Command Execution

**Assistant:** I'll create a worktree from your database refactoring plan. Let me analyze it for improvements.

I notice this plan involves multiple significant changes. Let me ask some clarifying questions:

**Using AskUserQuestion tool:**

- Question: "Which specific models need migration?"
  - Header: "Models"
  - Options: All models in src/models/, Only User and Post models, Let me specify
- Question: "What Redis configuration will you use?"
  - Header: "Redis"
  - Options: Local Redis (localhost:6379), Redis Cloud, Docker Redis, Other
- Question: "Should we break this into phases?"
  - Header: "Phases"
  - Options: Yes - separate branches, No - single branch

**User selects:** All models, Docker Redis, Yes - separate branches

**Assistant suggests phase structure:**

This refactoring would benefit from phase-based implementation. Here's a suggested breakdown:

**Phase 1: Database Migration** [branch: refactor-db-layer]

- Replace SQLAlchemy with asyncpg
- Migrate models in `src/models/`
- Add unit tests
- Deliverable: Working async database layer

**Phase 2: API Updates** [branch: refactor-api-async]

- Update all endpoints in `src/api/` to use async
- Add integration tests
- Deliverable: Fully async API

**Phase 3: Caching Layer** [branch: add-redis-cache]

- Integrate Redis caching with Docker
- Update queries to check cache first
- Add cache tests
- Deliverable: Complete caching solution

Would you like to structure the plan this way?

**User confirms:** Yes

**Assistant creates enhanced plan:**

```markdown
## Refactor Database Layer

### Context & Understanding

- Migrating from SQLAlchemy to asyncpg for performance
- Using Docker Redis for caching
- All models in src/models/ will be migrated

### Phase 1: Database Migration

**Branch**: refactor-db-layer (base: main)
**Goal**: Replace SQLAlchemy with asyncpg

**Steps:**

1. Install asyncpg and remove SQLAlchemy from requirements
2. Create new database connection in `src/db/connection.py`
3. Migrate all models in `src/models/`:
   - User model
   - Post model
   - Comment model
4. Add unit tests in `tests/test_models.py`
5. Validate with `/ensure-ci`

### Phase 2: API Updates

**Branch**: refactor-api-async (stacks on: refactor-db-layer)
**Goal**: Make all endpoints async

**Steps:**

1. Update endpoints in `src/api/users.py` to async
2. Update endpoints in `src/api/posts.py` to async
3. Update endpoints in `src/api/comments.py` to async
4. Add integration tests in `tests/test_api_async.py`
5. Validate with `/ensure-ci`

### Phase 3: Caching Layer

**Branch**: add-redis-cache (stacks on: refactor-api-async)
**Goal**: Add Redis caching

**Steps:**

1. Add Redis to docker-compose.yml
2. Create cache client in `src/cache/redis_client.py`
3. Add caching decorators in `src/cache/decorators.py`
4. Update API endpoints to use caching
5. Add cache tests in `tests/test_cache.py`
6. Final validation with `/ensure-ci`
```

**Creates worktree:**

```
✅ Worktree created: **refactor-database-layer**

Plan: `refactor-database-layer-plan.md` (structured in 3 phases)
Branch: `refactor-db-layer`
Location: `/Users/dev/workstacks/refactor-database-layer`

**Phases to be implemented:**
- Phase 1: Database Migration (branch: refactor-db-layer)
- Phase 2: API Updates (stacks on: refactor-db-layer)
- Phase 3: Caching Layer (stacks on: refactor-api-async)

Each phase will be implemented as a separate branch with CI verification.

**Next step:**
`workstack switch refactor-database-layer && claude --permission-mode acceptEdits "/workstack:implement-plan"`
```

## Example 3: Plan with Guidance

### User Interaction

**User presents plan:**

```markdown
## Add Error Handling

1. Add try/catch blocks to all API endpoints
2. Create custom exception classes
3. Add logging for errors
```

**User runs:** `/workstack:create-from-plan "Fix: Use LBYL pattern instead of try/except per coding standards"`

### Command Execution

**Assistant:** I'll create a worktree from your error handling plan, applying the guidance about LBYL patterns.

**Applies guidance to modify plan:**

```markdown
## Add Error Handling

1. Add LBYL validation to all API endpoints (check conditions before operations)
2. Create custom exception classes for error boundaries only
3. Add logging for errors at CLI boundaries
```

**Assistant asks clarifying questions:**

Let me clarify some details about the error handling approach:

**Using AskUserQuestion tool:**

- Question: "Which API endpoints need error handling?"
  - Options: All endpoints in src/api/, Only public-facing endpoints, Let me specify
- Question: "Where should custom exceptions be defined?"
  - Options: src/exceptions.py, src/api/exceptions.py, src/core/errors.py

**User selects:** All endpoints, src/exceptions.py

**Final enhanced plan:**

```markdown
## Add Error Handling

### Context & Understanding

- Following LBYL (Look Before You Leap) pattern per coding standards
- Exceptions only at error boundaries (CLI level)
- No try/except for control flow

### Implementation Steps

1. Add LBYL validation to all API endpoints in `src/api/`
   - Check preconditions before operations
   - Validate input parameters explicitly
   - Success: All endpoints validate inputs before processing

2. Create custom exception classes in `src/exceptions.py`
   - Only for error boundary handling
   - Will be caught at CLI level only
   - Success: Exception hierarchy defined

3. Add logging for errors at CLI boundaries in `src/cli/main.py`
   - Log errors before displaying to user
   - Include context and stack traces
   - Success: All errors logged appropriately

4. Add tests in `tests/test_error_handling.py`
   - Test LBYL validation paths
   - Test error boundary behavior
   - Success: Coverage for all error scenarios
```

**Creates worktree:**

```
✅ Worktree created: **add-error-handling**

Plan: `add-error-handling-plan.md`
Branch: `add-error-handling`
Location: `/Users/dev/workstacks/add-error-handling`

**Next step:**
`workstack switch add-error-handling && claude --permission-mode acceptEdits "/workstack:implement-plan"`
```

## Example 4: Plan Review with Issues

### User Interaction

**User presents vague plan:**

```markdown
## Improve Performance

- Optimize database queries
- Fix slow endpoints
- Add caching where needed
- Improve frontend rendering
```

### Command Execution

**Assistant:** I'll create a worktree from your performance improvement plan. Let me analyze it and ask clarifying questions.

This plan needs more specific details for clear implementation. Let me ask about the key areas:

**Using AskUserQuestion tool:**

- Question: "Which database queries need optimization?"
  - Options: User listing queries, Search queries, Analytics queries, All queries
- Question: "Which endpoints are slow?"
  - Options: GET /api/users, POST /api/search, GET /api/reports, Need profiling first
- Question: "What type of caching should be added?"
  - Options: Redis for API responses, Browser caching, CDN caching, Database query cache

**User selects:** Search queries, POST /api/search, Redis for API responses

**Assistant presents review:**

## Plan Review - Potential Execution Issues

🟡 **Vague reference: "improve frontend rendering"**
Impact: No specific optimization target identified
Suggested fix: Specify which components or pages need optimization

🟡 **Missing performance metrics**
Impact: Can't measure if optimizations are successful
Suggested fix: Add target response times or performance goals

Would you like to address these issues or continue with the current plan?

**User:** Continue with current plan

**Final plan created:**

```markdown
## Improve Performance

### Steps

1. Optimize search queries in database layer
   - Focus on POST /api/search endpoint
2. Add Redis caching for API responses
3. Improve frontend rendering (specific targets TBD)
```

## Key Patterns Demonstrated

1. **Simple plans** - Minimal questions, quick enhancement
2. **Complex plans** - Phase decomposition for manageable implementation
3. **Plans with guidance** - Corrections applied before enhancement
4. **Vague plans** - Clarifying questions and issue flagging
5. **User control** - All enhancements optional, can skip or dismiss

## Common Question Types

- **File locations** - Where specific code should go
- **Dependencies** - Which versions or services to use
- **Error handling** - How failures should be managed
- **Phase structure** - Whether to break into multiple branches
- **Success criteria** - How to verify implementation works

## Tips for Users

1. **More detail = fewer questions** - Specific plans need less clarification
2. **Guidance is powerful** - Use it to apply corrections before enhancement
3. **Phases help** - Complex work is easier in smaller chunks
4. **Skip when ready** - If your plan is already clear, skip enhancement
5. **Review warnings** - The final review catches potential issues
