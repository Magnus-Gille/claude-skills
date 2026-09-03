---
name: cloudflare-private-static-site
description: Create, preview, test, release, verify, or roll back a small static Cloudflare site protected by per-person HTTP Basic Auth. Use for private briefings, reports, one-pagers, document portals, or similar sites that should go from finished content to a custom domain in about ten minutes. Do not use for full applications or when the user requires SSO, identity lifecycle, or Cloudflare Access policy management.
---

# Cloudflare Private Static Site

Use the tested template instead of recreating authentication, DNS polling, credential generation,
or release scripts in the task repository.

## Locate the template

Use `PRIVATE_STATIC_SITE_TEMPLATE_ROOT` when set. Otherwise use:

`/Users/magnus/repos/cloudflare-private-static-site-template`

Stop if the template is missing, has uncommitted changes, or its checks fail. Do not silently build
an ad hoc replacement.

Load the `cloudflare` and `wrangler` skills before Cloudflare work. Load
`workers-best-practices` when changing Worker code. Prefer current primary Cloudflare documentation
for changing CLI or platform behavior.

## Establish the contract

Obtain or infer only values that are required to generate the site:

- absolute target directory;
- lowercase Worker name;
- custom hostname and owning Cloudflare zone;
- exact 32-character account ID;
- page title;
- one lowercase username and display name per authorized person;
- static content to place in `public/`.

Use Basic Auth for the ten-minute path. Stop and propose a separate Cloudflare Access setup if the
user needs SSO, central revocation, identity-provider groups, or identity-level audit policy.

## Generate and author

Run the template generator from the template repository:

```sh
npm ci
npm run new-site -- \
  --target /absolute/path/to/site \
  --name worker-slug \
  --domain private.example.com \
  --zone example.com \
  --account-id 0123456789abcdef0123456789abcdef \
  --users 'anna:Anna Andersson,magnus:Magnus Gille' \
  --title 'Private Briefing'
```

Edit only the generated project's content and presentation unless a requirement truly needs Worker
changes. Never add passwords, hashes, API tokens, `.dev.vars`, `.env*`, or generated credential
files to Git.

Visually inspect the final page at desktop size and at a narrow mobile viewport. Fix clipping,
overflow, unreadable contrast, broken links, and missing assets before release.

## Check and commit

In the generated repository, run:

```sh
npm ci
npm run check
npm run lint:shell
npm run types
npm run deploy:dry-run
```

Initialize Git if needed. Stage only task files, inspect the staged diff, and commit the verified
site. Release only an exact clean 40-character commit SHA.

## Preflight and release

Run the read-only preflight with the exact SHA:

```sh
npm run preflight -- --sha FULL_40_CHARACTER_SHA
```

Then run `npm run release` without `--apply`. Present its exact account, hostname, Worker, SHA,
verification contract, rollback command, and confirmation string to the owner. A production deploy
is a sensitive mutation: obtain just-in-time confirmation before applying it.

After confirmation, set the exact printed `PRIVATE_STATIC_SITE_RELEASE_CONFIRM` value and run the
printed `npm run release -- --apply --sha ...` command. Do not bypass or reproduce the script with
direct Wrangler commands.

The script must finish by verifying:

- anonymous request returns 401;
- invalid credentials return 401;
- every configured account returns 200;
- authenticated responses carry the expected security headers;
- authoritative DNS reaches the claimed Cloudflare edge without relying on recursive DNS caches.

On success, report the URL, immutable SHA, verification result, and local mode-0600 credential-file
path. Never print credential values. Share each person's password only when explicitly requested and
through an appropriate secure channel.

On failure, report the sanitized diagnostic path. The script attempts to remove a partially created
Worker and deletes the incomplete credential file. Confirm external state before any manual cleanup.

## Verify or roll back

Re-verify with:

```sh
npm run verify -- --credentials-file /tmp/WORKER-credentials-SHA.json
```

For rollback, first run the plan-only command and present the exact target, SHA, confirmation, and
effect. Obtain just-in-time confirmation, then use the printed `--apply` command. Rollback deletes
only the named Worker and custom-domain route; it retains local credentials deliberately.

## Ten-minute operating target

For content that is already finished and an authenticated Wrangler account, aim for:

1. 0-2 minutes: confirm the contract and generate the repository.
2. 2-5 minutes: insert content and perform visual QA.
3. 5-8 minutes: run checks, dry-run, commit, and preflight.
4. 8-10 minutes: obtain deployment confirmation, release, and verify.

DNS or certificate propagation can extend elapsed time, but the authoritative polling path should
continue without restarting or debugging recursive negative caches.
