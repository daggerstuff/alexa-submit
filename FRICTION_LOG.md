# Friction Log — Clinical Conversation Coach (Alexa+ track)

A record of what we hit while building and shipping this project on Amazon
tools, and the workarounds that got us unblocked. Tools touched: AWS App Runner,
Amazon ECR, AWS IAM, the `aws login` console-session CLI, and (as the LLM
inference backend) Cloudflare Workers AI reached through an OpenAI-compatible
endpoint.

---

## 1. `aws login` console session silently dies mid-build

- **Tried:** authenticate the CLI with the console session (`aws login
  --region us-east-2`) and rely on its automatic token refresh during a deploy.
- **What happened:** the session worked for a while, then every command started
  failing with `CreateOAuth2Token … authorization grant is invalid, expired,
  revoked, or malformed`. The refresh token is tied to the browser session, so
  the moment that lapses, the CLI credentials are dead and every AWS call fails.
- **Workaround:** stopped using the console session for automation and created a
  long-lived IAM user with a static access key in `~/.aws/credentials`.
- **Suggestion:** make the console-session CLI surface *when* it can no longer
  refresh (and why), and document that it is not intended for unattended or
  long-running builds. A one-line "session expired — re-run `aws login`" would
  have saved us a lot of head-scratching.

## 2. App Runner `update-service` rejects `Port` as a number

- **Tried:** `aws apprunner update-service --cli-input-json` with
  `SourceConfiguration.ImageRepository.ImageConfiguration.Port` set to the
  integer `8001`.
- **What happened:** `ParamValidation: Invalid type for parameter
  SourceConfiguration.ImageRepository.ImageConfiguration.Port, value: 8001,
  type: <class 'int'>, valid types: <class 'str'>`. A port is naturally an
  integer, and nothing in the console or docs calls out that this field must be
  a *string* in the API model.
- **Workaround:** emit `"Port": "8001"` (a string) in the JSON.
- **Suggestion:** accept the integer and coerce it, or document the string
  requirement next to the field. This one cost us a full deploy cycle to find.

## 3. App Runner rolls back a failed deploy with no signal

- **Tried:** deploy a new container image and poll
  `describe-service` for `Status == RUNNING` before declaring success.
- **What happened:** the new image crashed on startup, App Runner rolled back to
  the previous image, and the service still reported `RUNNING`. Our deploy
  script (and the GitHub Actions job) showed **success** while the *old* image
  kept serving. The only place the failure surfaced was `list-operations`
  (`Status: ROLLBACK_SUCCEEDED`) plus the instance logs in CloudWatch.
- **Workaround:** poll `list-operations` in addition to `describe-service`, and
  fail the deploy if the latest operation is `FAILED` or `ROLLBACK_*`.
- **Suggestion:** expose a deployment's rollback in `describe-service` (or a
  dedicated "last deployment health" field), so a client doesn't have to know to
  cross-check operations + logs to detect a reverted deploy.

## 4. GitHub OIDC → IAM trust policy broke in two independent ways

- **Tried:** the standard GitHub Actions OIDC setup — a federated role trusting
  `token.actions.githubusercontent.com` with `sub: repo:owner/repo:*` and
  `aud: sts.amazonaws.com`.
- **What happened (a):** `sts:AssumeRoleWithWebIdentity` was denied even though
  the trust policy looked right. Decoding the actual token showed the `sub`
  claim is now `repo:owner@<owner-id>/repo@<repo-id>:ref:…` — owner and repo
  IDs are embedded, so a `repo:owner/repo:*` condition silently stops matching.
- **What happened (b):** the IAM OIDC provider's thumbprint was stale — GitHub
  had rotated `token.actions.githubusercontent.com` to a Let's Encrypt chain,
  so the stored thumbprint no longer matched the served certificate.
- **Workaround:** read the live token's `sub`/`aud` claims directly, write the
  trust-policy condition against the real (ID-suffixed) format, and recompute
  the TLS chain thumbprint (root + intermediate + leaf) for the provider.
- **Suggestion:** a clearer, distinguishable error for "token issuer/subject
  didn't match the trust policy" versus "couldn't fetch/verify the JWKS" would
  have cut this from a multi-hour hunt to minutes.

---

**Net:** none of these blocked us for good, but three of the four (Port type,
silent rollback, OIDC subject format) each cost a full build-deploy-observe
cycle to diagnose because the failure surfaced far from its cause. The single
highest-leverage fix across the board is *better, earlier error visibility*.