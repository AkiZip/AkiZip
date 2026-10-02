# Security Policy

## Supported Versions

Akizip is distributed as a Flatpak, with releases cut from GitHub tags.
Security fixes are always applied on top of the **latest tagged release**;
older releases do not receive backports.

| Version               | Supported |
| --------------------- | --------- |
| Latest tagged release | ✅        |
| Any older release     | ❌        |

Please make sure you are running the newest release before reporting an
issue — a vulnerability that only affects an outdated build is generally
not considered actionable.

## Reporting a Vulnerability

If you discover a security vulnerability in Akizip, please report it
responsibly using **GitHub's private vulnerability reporting** feature:

1. Go to the [Security](https://github.com/AkiZip/AkiZip/security) tab of the
   Akizip repository.
2. Click **"Report a vulnerability"**.
3. Fill in the advisory form with as much detail as possible, including steps
   to reproduce, affected versions (e.g. the Git tag or the version shown in
   the About dialog), and potential impact.

This creates a private advisory visible only to you and our security team,
allowing us to discuss and address the issue before any public disclosure.
**Please do not open a public issue for security reports.**

You can expect an acknowledgement within **72 hours** and an initial assessment
within **14 days**. We will keep you informed about the progress of a fix.

For more information on this process, see
[GitHub's documentation on private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability).

## Scope

**In scope:**

- Akizip's own code (Python/GTK application, plugin system, job queue)
- Flatpak packaging and sandbox permissions
- The way Akizip invokes the bundled `7zz` binary (e.g. command-line
  construction, path handling, archive extraction safeguards)

**Reported upstream instead:**

- Vulnerabilities in the 7-Zip engine itself (the bundled `7zz` binary) should
  be reported to the [7-Zip project](https://www.7-zip.org/). If the issue is
  in how Akizip packages or calls `7zz`, report it to us.

**Out of scope:**

- Attacks requiring physical access to the machine
- Social engineering
- Denial-of-service attacks against infrastructure we do not operate

## Disclosure Policy

We follow coordinated disclosure: please give us reasonable time to prepare
and ship a fix before any public disclosure. Once the fix is released, we will
publish a GitHub Security Advisory describing the issue and crediting the
reporter (unless you prefer to remain anonymous).
