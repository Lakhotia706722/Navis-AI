# RBAC Permission Matrix — Phase 11

## Roles

Four roles exist in a workspace. Each user has exactly one role per workspace.

| Role    | Description |
|---------|-------------|
| **owner**  | The user who created the workspace (or received ownership transfer). Full control. |
| **admin**  | Trusted team member. Can do everything except delete the workspace or transfer ownership. |
| **member** | Regular collaborator. Can create and edit projects and start renders but cannot manage team. |
| **viewer** | Read-only. Can browse projects and view render status but cannot modify anything. |

---

## Permission Matrix

| Action                              | owner | admin | member | viewer |
|-------------------------------------|:-----:|:-----:|:------:|:------:|
| **Projects**                        |       |       |        |        |
| Create project                      | ✅    | ✅    | ✅     | ❌     |
| View project list                   | ✅    | ✅    | ✅     | ✅     |
| View project detail                 | ✅    | ✅    | ✅     | ✅     |
| Edit project (title, prompt, etc.)  | ✅    | ✅    | ✅     | ❌     |
| Delete project                      | ✅    | ✅    | ❌     | ❌     |
| **Renders**                         |       |       |        |        |
| Start render job                    | ✅    | ✅    | ✅     | ❌     |
| View render status                  | ✅    | ✅    | ✅     | ✅     |
| Cancel render job                   | ✅    | ✅    | ✅     | ❌     |
| **Assets**                          |       |       |        |        |
| View asset library                  | ✅    | ✅    | ✅     | ✅     |
| Upload asset                        | ✅    | ✅    | ✅     | ❌     |
| Delete asset                        | ✅    | ✅    | ❌     | ❌     |
| **Usage & Cost**                    |       |       |        |        |
| View project-level usage            | ✅    | ✅    | ✅     | ✅     |
| View workspace-level cost rollup    | ✅    | ✅    | ❌     | ❌     |
| Set project cost threshold          | ✅    | ✅    | ❌     | ❌     |
| **Workspace Members**               |       |       |        |        |
| View member list                    | ✅    | ✅    | ✅     | ✅     |
| Invite member (any role ≤ own role) | ✅    | ✅    | ❌     | ❌     |
| Revoke pending invite               | ✅    | ✅    | ❌     | ❌     |
| Remove member                       | ✅    | ✅    | ❌     | ❌     |
| Change member role                  | ✅    | ✅*   | ❌     | ❌     |
| **Workspace Settings**              |       |       |        |        |
| View workspace settings             | ✅    | ✅    | ✅     | ✅     |
| Edit workspace name                 | ✅    | ✅    | ❌     | ❌     |
| View plan_tier stub                 | ✅    | ✅    | ❌     | ❌     |
| Transfer workspace ownership        | ✅    | ❌    | ❌     | ❌     |
| Delete workspace                    | ✅    | ❌    | ❌     | ❌     |

\* Admin can change roles but cannot promote anyone to **owner** or demote/remove an **owner**.

---

## Enforcement Rules

### Backend (authoritative)
All permission checks are enforced at the **route level via FastAPI dependency injection**. The middleware:
1. Validates the JWT and extracts `user_id`
2. Reads `workspace_id` from the request (path param, query param, or JWT claim for active workspace)
3. Looks up the user's `WorkspaceMember` row to get their `role`
4. Calls `require_role(minimum_role)` which raises HTTP 403 if insufficient

### Frontend (UX only)
The UI hides or disables buttons the user cannot use (e.g., viewers see no "Delete Project"). This is for UX convenience only — the backend is the real enforcement boundary.

### 403 vs 404
- **Non-member accessing any workspace resource** → **403 Forbidden** (not 404). Rationale: returning 404 would reveal whether workspace/project IDs exist, which aids enumeration. Consistent 403 for non-members is the chosen balance between security-through-obscurity and debuggability.
- **Resource genuinely not found** → **404 Not Found**.
- **Insufficient role for action** → **403 Forbidden**.

---

## Role Hierarchy (for invite constraints)

```
owner > admin > member > viewer
```

A user may only invite someone to a role **equal to or lower than their own**:
- An admin can invite admins, members, and viewers.
- A member cannot invite anyone.

---

## Invite Flow

```
Inviter (admin+)
  → POST /api/workspaces/{id}/invites  { email, role }
  → Server creates workspace_invites row (token, 7-day expiry, status=pending)
  → Email sent via Phase 9 notification hooks
Invitee
  → Receives email with link: /invite/{token}
  → Clicks link → POST /api/workspaces/invites/{token}/accept
  → If user exists: logged in and added to workspace
  → If new user: directed to register first, then auto-accepted
  → workspace_members row created, invite status → accepted
```

---

## Workspace Switching

A user may belong to multiple workspaces. The active workspace is determined by:
1. `X-Workspace-ID` header on individual requests (for API consumers)
2. A stored `activeWorkspaceId` in frontend localStorage (for the web UI)
3. Default: the workspace where the user is **owner** (created first)

The JWT itself does **not** encode workspace — this keeps tokens stateless and avoids re-issuing tokens on workspace switch.

---

## Migration Behaviour for Existing Data

Every existing project was created under `projects.user_id`. During migration 003:
1. For each distinct `user_id` in `projects`, a new `workspace` is created named `"{user.full_name or user.email}'s Workspace"`.
2. A `workspace_members` row is created with `role = owner`.
3. All projects for that user get `workspace_id` set to the new workspace.
4. `projects.user_id` is **kept** (not dropped) in Phase 11 for backward compatibility; it becomes a denormalised convenience field. Authoritative ownership is `workspace_members`.

The migration is **reversible**: downgrade drops the new columns and tables.
