# Contributing to Puzzly

Thanks for your interest in improving Puzzly! This guide covers how to get set
up, the conventions we follow, and what we look for in a pull request.

## Getting started

1. **Fork** the repository and clone your fork.
2. Install Python 3.10 or newer.
3. Install the dev dependencies (this includes the runtime ones):
   ```bash
   pip install -r requirements-dev.txt
   ```
4. Create your local config:
   ```bash
   cp .env.example .env
   python -c "import secrets; print(secrets.token_hex(32))"   # -> SECRET_KEY
   ```
   Set `FLASK_DEBUG=1` for local development. Optionally set `ADMIN_TOKEN` to
   work on the admin dashboard.
5. Run the app:
   ```bash
   python app.py
   ```
   and open http://127.0.0.1:5000.

## Running the tests

Please run the suite before opening a PR, and add tests for new behavior:

```bash
pytest
```

The tests live in `tests/` and exercise the HTTP routes with Flask's test
client (uploads, previews, PDF generation, admin auth, and CSRF).

## Working on the UI

- The design follows the **Vintage Puzzle Studio** palette. Use the CSS custom
  properties / Tailwind theme colors (`cream`, `paper`, `mahogany`, `sage`,
  `charcoal`, `gold`) rather than hard-coded hex values.
- Fonts: **Playfair Display** for headings, **Inter** for body text.
- Components follow shadcn/ui-style conventions (see `static/components.js` and
  the component classes in `static/style.css`).
- The compiled Tailwind stylesheet is committed. If you change Tailwind classes
  in templates or JS, rebuild it:
  ```bash
  npx tailwindcss -i static/tailwind.input.css -o static/tailwind.build.css --minify
  ```
  Commit the regenerated `static/tailwind.build.css` with your change.

## Coding conventions

- **Python:** follow PEP 8. The project is formatted/linted with
  [Ruff](https://docs.astral.sh/ruff/); run `ruff check .` and `ruff format .`
  if you have it installed. Keep functions small and prefer standard-library
  solutions.
- **JavaScript:** vanilla ES (no framework/build). Match the existing style —
  `"use strict"`, small focused functions, no new dependencies.
- Validate and sanitize any new user input on the server (see `is_valid_image`,
  `_clamp`, and `secure_filename` for existing patterns).
- Any admin mutation (state-changing POST) must be CSRF-protected via the
  `require_admin` decorator and send the `X-CSRF-Token` header from the client.

## Security & secrets

- **Never commit secrets.** `.env`, `wsgi.py`, `DEPLOY.md`, the `data/` folder,
  and the `library/` images are git-ignored on purpose.
- If you add a new configuration value, read it from an environment variable and
  document it in `.env.example` and the README's Configuration table.

## Submitting a pull request

1. Create a feature branch off `main`.
2. Keep commits focused and write clear, imperative commit messages
   (e.g. "Add per-day chart to admin dashboard").
3. Make sure `pytest` passes and the app runs.
4. Describe **what** changed and **why** in the PR description; include
   screenshots for any UI change.

## Reporting bugs / requesting features

Open a GitHub issue with clear reproduction steps (for bugs) or a short
description of the use case (for features). Screenshots and sample images help.

Made with ♥ — happy puzzling!
