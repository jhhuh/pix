# MkDocs Dual-Config i18n Without Plugin

## The Problem

`mkdocs-static-i18n` may not be available in your package manager (e.g., not in nixpkgs). You need multi-language docs with a language switcher.

## The Approach

Use two separate MkDocs config files with Material theme's `extra.alternate` for language switching.

### Config structure

```
mkdocs.yml        # English (docs_dir: docs, site_dir: site)
mkdocs-ko.yml     # Korean  (docs_dir: docs/ko, site_dir: site/ko)
docs/
  index.md
  ...
  ko/
    index.md
    ...
```

### Language switcher (in both configs)

```yaml
extra:
  alternate:
    - name: English
      link: /pix/
      lang: en
    - name: 한국어
      link: /pix/ko/
      lang: ko
```

### Build & deploy

```bash
mkdocs build -f mkdocs.yml
mkdocs build -f mkdocs-ko.yml
ghp-import -n -p -f site
```

## Gotcha: mkdocs gh-deploy wipes subdirectories

`mkdocs gh-deploy` runs its own `mkdocs build` which cleans `site/` and only builds one config. This wipes the other language's output.

**Fix:** Always build both configs separately, then deploy with `ghp-import -n -p -f site` directly.
