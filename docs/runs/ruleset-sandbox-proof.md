# Ruleset sandbox proof (Q-K4-101, SPEC-0013 rule 21)

Date: 2026-10-18 (from `date -u`). Q-K4-101 was ruled "accepted with the `(verify)`": before relying on phase detection, prove on the sandbox what
GitHub does for a required status check that has never run. The maintainers' ruling (corrected, 2026-10-18): the sandbox is the existing
`gbvraju/agk-sandbox` (the repository of `docs/runs/doctor-live-proof.md`); build and test on recorded fixtures and a dry run first; before any
write, GET the repository and its rulesets and record both here; the only writes allowed are added rulesets on `gbvraju/agk-sandbox`, each naming
it; never edit or delete its existing ruleset; never write to `gbvraju/agk`, `gbvraju/cors` or any upstream; afterwards GET the rulesets again and
list what was added; if the `gh` login lacks admin there, stop and report; never ask for or handle a token.

## Result

**Not proven yet.** The first write was refused by the session's proxy, not by GitHub's permissions on the account:

```
gh api --method POST repos/gbvraju/agk-sandbox/rulesets --input proof-ruleset.json     (2026-10-18T19:27:58Z)
HTTP 403
{
  "message": "Write access to this GitHub API path is not permitted through this proxy.",
  "documentation_url": "https://docs.anthropic.com/en/docs/claude-code/github-actions"
}
```

The login can read with admin rights (`permissions.admin` is `true` in the first record below) but this environment does not allow a write to
that API path. No retry and no other route was tried, and no token was read or used. Nothing on `gbvraju/agk-sandbox` was changed: the second
GET of the rulesets (below) is the same as the first. What GitHub does for a required check that has never run is therefore **still `(verify)`**;
the plan's phase detection (phase 1 until `governance.yml` has succeeded on the default branch) is the conservative reading and is what the code
builds. The pilot's first day reported that a never-run required check blocks the first merge (SPEC-0013 rule 21); that is the only evidence so far.

## What the maintainers can run to finish the proof

From a login of the maintainers' own, on `gbvraju/agk-sandbox` only. This adds one inert ruleset (it targets a branch name that does not exist,
so `main` is unaffected; the existing ruleset `Main` is untouched):

```
cat > proof-ruleset.json <<'EOF2'
{
  "name": "agk-proof-never-run",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {"ref_name": {"include": ["refs/heads/agk-proof-never-run"], "exclude": []}},
  "rules": [
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [{"context": "agk-never-run"}]
      }
    }
  ]
}
EOF2
gh api --method GET repos/gbvraju/agk-sandbox          # admin: true
gh api --method POST repos/gbvraju/agk-sandbox/rulesets --input proof-ruleset.json
```

Then observe what a pull request into a branch named `agk-proof-never-run` shows while no check named `agk-never-run` has ever reported (create
that branch from `main`, push a change on another branch, open the pull request against it): the merge state (`mergeable_state`, the
"Expected — Waiting for status to be reported" line, whether the merge button is blocked). Record the API responses here, delete the branch and the
ruleset `agk-proof-never-run`, and GET the rulesets again to show only `Main` remains. The request to the maintainers: either run these steps and
record them, or allow the session to push the one branch and open the one pull request on the sandbox (a write the ruling does not cover).

## Records (all GET, read-only)

First GET of the repository, 2026-10-18T19:27:27Z (`gh api --method GET repos/gbvraju/agk-sandbox`):

```json
{
  "id": 1419626386,
  "node_id": "R_kgDOVJ3Hkg",
  "name": "agk-sandbox",
  "full_name": "gbvraju/agk-sandbox",
  "private": false,
  "owner": {
    "login": "gbvraju",
    "id": 6429652,
    "node_id": "MDQ6VXNlcjY0Mjk2NTI=",
    "avatar_url": "https://avatars.githubusercontent.com/u/6429652?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/gbvraju",
    "html_url": "https://github.com/gbvraju",
    "followers_url": "https://api.github.com/users/gbvraju/followers",
    "following_url": "https://api.github.com/users/gbvraju/following{/other_user}",
    "gists_url": "https://api.github.com/users/gbvraju/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/gbvraju/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/gbvraju/subscriptions",
    "organizations_url": "https://api.github.com/users/gbvraju/orgs",
    "repos_url": "https://api.github.com/users/gbvraju/repos",
    "events_url": "https://api.github.com/users/gbvraju/events{/privacy}",
    "received_events_url": "https://api.github.com/users/gbvraju/received_events",
    "type": "User",
    "user_view_type": "public",
    "site_admin": false
  },
  "html_url": "https://github.com/gbvraju/agk-sandbox",
  "description": null,
  "fork": false,
  "url": "https://api.github.com/repos/gbvraju/agk-sandbox",
  "forks_url": "https://api.github.com/repos/gbvraju/agk-sandbox/forks",
  "keys_url": "https://api.github.com/repos/gbvraju/agk-sandbox/keys{/key_id}",
  "collaborators_url": "https://api.github.com/repos/gbvraju/agk-sandbox/collaborators{/collaborator}",
  "teams_url": "https://api.github.com/repos/gbvraju/agk-sandbox/teams",
  "hooks_url": "https://api.github.com/repos/gbvraju/agk-sandbox/hooks",
  "issue_events_url": "https://api.github.com/repos/gbvraju/agk-sandbox/issues/events{/number}",
  "events_url": "https://api.github.com/repos/gbvraju/agk-sandbox/events",
  "assignees_url": "https://api.github.com/repos/gbvraju/agk-sandbox/assignees{/user}",
  "branches_url": "https://api.github.com/repos/gbvraju/agk-sandbox/branches{/branch}",
  "tags_url": "https://api.github.com/repos/gbvraju/agk-sandbox/tags",
  "blobs_url": "https://api.github.com/repos/gbvraju/agk-sandbox/git/blobs{/sha}",
  "git_tags_url": "https://api.github.com/repos/gbvraju/agk-sandbox/git/tags{/sha}",
  "git_refs_url": "https://api.github.com/repos/gbvraju/agk-sandbox/git/refs{/sha}",
  "trees_url": "https://api.github.com/repos/gbvraju/agk-sandbox/git/trees{/sha}",
  "statuses_url": "https://api.github.com/repos/gbvraju/agk-sandbox/statuses/{sha}",
  "languages_url": "https://api.github.com/repos/gbvraju/agk-sandbox/languages",
  "stargazers_url": "https://api.github.com/repos/gbvraju/agk-sandbox/stargazers",
  "contributors_url": "https://api.github.com/repos/gbvraju/agk-sandbox/contributors",
  "subscribers_url": "https://api.github.com/repos/gbvraju/agk-sandbox/subscribers",
  "subscription_url": "https://api.github.com/repos/gbvraju/agk-sandbox/subscription",
  "commits_url": "https://api.github.com/repos/gbvraju/agk-sandbox/commits{/sha}",
  "git_commits_url": "https://api.github.com/repos/gbvraju/agk-sandbox/git/commits{/sha}",
  "comments_url": "https://api.github.com/repos/gbvraju/agk-sandbox/comments{/number}",
  "issue_comment_url": "https://api.github.com/repos/gbvraju/agk-sandbox/issues/comments{/number}",
  "contents_url": "https://api.github.com/repos/gbvraju/agk-sandbox/contents/{+path}",
  "compare_url": "https://api.github.com/repos/gbvraju/agk-sandbox/compare/{base}...{head}",
  "merges_url": "https://api.github.com/repos/gbvraju/agk-sandbox/merges",
  "archive_url": "https://api.github.com/repos/gbvraju/agk-sandbox/{archive_format}{/ref}",
  "downloads_url": "https://api.github.com/repos/gbvraju/agk-sandbox/downloads",
  "issues_url": "https://api.github.com/repos/gbvraju/agk-sandbox/issues{/number}",
  "pulls_url": "https://api.github.com/repos/gbvraju/agk-sandbox/pulls{/number}",
  "milestones_url": "https://api.github.com/repos/gbvraju/agk-sandbox/milestones{/number}",
  "notifications_url": "https://api.github.com/repos/gbvraju/agk-sandbox/notifications{?since,all,participating}",
  "labels_url": "https://api.github.com/repos/gbvraju/agk-sandbox/labels{/name}",
  "releases_url": "https://api.github.com/repos/gbvraju/agk-sandbox/releases{/id}",
  "deployments_url": "https://api.github.com/repos/gbvraju/agk-sandbox/deployments",
  "created_at": "2026-10-14T18:07:58Z",
  "updated_at": "2026-10-16T10:32:14Z",
  "pushed_at": "2026-10-16T10:32:12Z",
  "git_url": "git://github.com/gbvraju/agk-sandbox.git",
  "ssh_url": "git@github.com:gbvraju/agk-sandbox.git",
  "clone_url": "https://github.com/gbvraju/agk-sandbox.git",
  "svn_url": "https://github.com/gbvraju/agk-sandbox",
  "homepage": null,
  "size": 144,
  "stargazers_count": 0,
  "watchers_count": 0,
  "language": "Python",
  "has_issues": true,
  "has_projects": true,
  "has_downloads": false,
  "has_wiki": true,
  "has_pages": false,
  "has_discussions": false,
  "forks_count": 0,
  "mirror_url": null,
  "archived": false,
  "disabled": false,
  "open_issues_count": 0,
  "license": null,
  "allow_forking": true,
  "is_template": false,
  "web_commit_signoff_required": false,
  "has_pull_requests": true,
  "pull_request_creation_policy": "all",
  "topics": [],
  "visibility": "public",
  "forks": 0,
  "open_issues": 0,
  "watchers": 0,
  "default_branch": "main",
  "permissions": {
    "admin": true,
    "maintain": true,
    "push": true,
    "triage": true,
    "pull": true
  },
  "allow_squash_merge": true,
  "allow_merge_commit": true,
  "allow_rebase_merge": true,
  "allow_auto_merge": true,
  "delete_branch_on_merge": true,
  "allow_update_branch": false,
  "use_squash_pr_title_as_default": false,
  "squash_merge_commit_message": "COMMIT_MESSAGES",
  "squash_merge_commit_title": "COMMIT_OR_PR_TITLE",
  "merge_commit_message": "PR_TITLE",
  "merge_commit_title": "MERGE_MESSAGE",
  "security_and_analysis": {
    "secret_scanning": {
      "status": "enabled"
    },
    "secret_scanning_push_protection": {
      "status": "enabled"
    },
    "dependabot_security_updates": {
      "status": "disabled"
    },
    "secret_scanning_non_provider_patterns": {
      "status": "disabled"
    },
    "secret_scanning_validity_checks": {
      "status": "disabled"
    }
  },
  "network_count": 0,
  "subscribers_count": 0
}
```

First GET of the rulesets (`gh api --method GET repos/gbvraju/agk-sandbox/rulesets`):

```json
[
  {
    "id": 25107038,
    "name": "Main",
    "target": "branch",
    "source_type": "Repository",
    "source": "gbvraju/agk-sandbox",
    "enforcement": "active",
    "node_id": "RRS_lACqUmVwb3NpdG9yec5UnceSzgF_Gl4",
    "_links": {
      "self": {
        "href": "https://api.github.com/repos/gbvraju/agk-sandbox/rulesets/25107038"
      },
      "html": {
        "href": "https://github.com/gbvraju/agk-sandbox/rules/25107038"
      }
    },
    "created_at": "2026-10-14T18:41:41.821Z",
    "updated_at": "2026-10-16T07:56:47.194Z"
  }
]
```

The existing ruleset, read for the plan (`.../rulesets/25107038`); it was not and will not be edited:

```json
{
  "id": 25107038,
  "name": "Main",
  "target": "branch",
  "source_type": "Repository",
  "source": "gbvraju/agk-sandbox",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "exclude": [],
      "include": [
        "~DEFAULT_BRANCH"
      ]
    }
  },
  "rules": [
    {
      "type": "deletion"
    },
    {
      "type": "non_fast_forward"
    },
    {
      "type": "required_linear_history"
    },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "required_reviewers": [],
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "require_extra_approval_for_unattributed_changes": false,
        "allowed_merge_methods": [
          "squash"
        ]
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": true,
        "required_status_checks": [
          {
            "context": "governance",
            "integration_id": 15368
          }
        ]
      }
    }
  ],
  "node_id": "RRS_lACqUmVwb3NpdG9yec5UnceSzgF_Gl4",
  "created_at": "2026-10-14T18:41:41.821Z",
  "updated_at": "2026-10-16T07:56:47.194Z",
  "bypass_actors": [],
  "current_user_can_bypass": "never",
  "_links": {
    "self": {
      "href": "https://api.github.com/repos/gbvraju/agk-sandbox/rulesets/25107038"
    },
    "html": {
      "href": "https://github.com/gbvraju/agk-sandbox/rules/25107038"
    }
  }
}
```

`governance.yml` on `main`: `GET .../actions/workflows/governance.yml/runs?branch=main&status=success&per_page=1` returned `total_count` 4 (run 17,
`push`, `success`, on `main`), so `--phase auto` reads phase 2.

The dry run, `python3 scripts/agk/ruleset.py plan --repo gbvraju/agk-sandbox` (reads only):

```
repo: gbvraju/agk-sandbox (default branch main); phase 2 (auto: governance has succeeded on the default branch)
nothing to do
```

## Second GET of the rulesets, after the refused write

2026-10-18T19:29:25Z, `gh api --method GET repos/gbvraju/agk-sandbox/rulesets`. Compared with the first GET (keys sorted): identical. Nothing was
added, so there is nothing for the maintainers to remove.

```json
[
  {
    "id": 25107038,
    "name": "Main",
    "target": "branch",
    "source_type": "Repository",
    "source": "gbvraju/agk-sandbox",
    "enforcement": "active",
    "node_id": "RRS_lACqUmVwb3NpdG9yec5UnceSzgF_Gl4",
    "_links": {
      "self": {
        "href": "https://api.github.com/repos/gbvraju/agk-sandbox/rulesets/25107038"
      },
      "html": {
        "href": "https://github.com/gbvraju/agk-sandbox/rules/25107038"
      }
    },
    "created_at": "2026-10-14T18:41:41.821Z",
    "updated_at": "2026-10-16T07:56:47.194Z"
  }
]
```
