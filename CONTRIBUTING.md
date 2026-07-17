# Contributing to Akizip

Before opening a pull request, please read these rules. PRs that violate them will be closed.

## Rules

1. **No fully AI-generated PRs.** AI assistance is fine, but a human must review, understand, and test every line before submitting. If you can't explain your change during review, the PR will be closed.

2. **Translations go through [Weblate](https://hosted.weblate.org/engage/akizip/).** The only exception: a PR adding a **new language** is accepted only if it translates the **entire** catalog in one commit — add the locale to `po/LINGUAS`, include the complete `.po` file, and make sure `msgfmt --check` passes. Partial translations and updates to existing languages must use Weblate.

3. **The sandbox is non-negotiable.** PRs that add new permissions to `top.akizip.akizip.json` (`finish-args`: sockets, shares, devices, filesystems, D-Bus names, etc.) are not accepted. If a feature can't work within the current sandbox, open an issue to discuss alternatives.

4. **No external Python packages.** Stick to the standard library and PyGObject. A new dependency is allowed only when implementing it yourself is genuinely impossible — open an issue and get maintainer agreement *before* writing any code.

By contributing, you agree your work is licensed under GPLv3-or-later (see [COPYING](COPYING)).
