# askquill.to/roam

Public garden. Two nodes to start. Private operating copies stay in-house.

Pointer: https://askquill.to/roam

## Emacs

Your Emacs does **not** visit this directory. This tree is the send copy.

`ikoamu/publish-org-roam-ui` **consumes** `org-roam.db`. It does not mint it.
After you drop a new `__public_*` org file here, run:

```bash
python3 mint-public-roam-db.py
```

Commit the org file **and** `org-roam.db`. Then the Action builds org-roam-ui
and deploys GitHub Pages.

Do not copy `/srv/org/roam.db` here. That db is the House.

## Filenames

Denote stems carry the publish flags:

- `public` / `private`
- `external` / `internal`
- `seed` / `law` / `live` / `draft`

Only `public` + `external` files belong in this repo.

## IDs

UUIDs come from `org-id-get-create` on the House file. Never stamp `:ID:` by hand.
