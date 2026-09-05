# Local upstream skill overlays

These patches maintain the personal `.agents/skills` instruction changes made on 2026-09-05. They are overlays on an existing upstream installation, not complete installable skills. Keep the distribution's scripts and framework references.

`manifest.json` pins every changed file before and after the patch. Before applying, require every existing file to match `before_sha256` and every new path to be absent, then run `git apply --check` in a disposable copy. Apply only within the owner's requested update scope, verify all `after_sha256` values, and validate skill frontmatter and references. Already matching all after hashes means no action is needed. A partial match or upstream version change requires reconciliation; never force a patch or overwrite it silently.

The upstream skill lock remains untouched because these are local overlays, not a claim that the package manager installed a new upstream revision. After an explicit upstream update, review/rebase these patches and their manifest. The dated local activation manifest contains backup locations and a guarded rollback recipe.

Most upstream product examples remain reference material and still rely on the global dependency, authentication, secret, resource-mutation, and production authorization floors. Commands such as Agents SDK package installation or Cloudflare Email Service enablement do not grant authority to execute them. The Wrangler router states these boundaries before dispatching to examples; retained examples are not current CLI validation evidence.
