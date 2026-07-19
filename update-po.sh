#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

POT_FILE="po/akizip.pot"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

ITS_FILE="/usr/share/gettext/its/metainfo.its"

# ========== Auto-classify POTFILES.in ==========
PY_FILES=()
UI_FILES=()
DESKTOP_FILES=()
METAINFO_FILES=()
SKIP_FILES=()

while IFS= read -r f; do
    [[ -z "$f" || "$f" == \#* ]] && continue
    case "$f" in
        *.py)          PY_FILES+=("$f") ;;
        *.ui)          UI_FILES+=("$f") ;;
        *.desktop.in)  DESKTOP_FILES+=("$f") ;;
        *.metainfo.xml.in|*.appdata.xml.in)
                       METAINFO_FILES+=("$f") ;;
        *.gschema.xml) SKIP_FILES+=("$f") ;;  # Runtime translation, skip extraction
        *) echo "Warning: unknown file type, skipping: $f" >&2 ;;
    esac
done < po/POTFILES.in

# ========== Extract by file type ==========
[[ ${#PY_FILES[@]} -gt 0 ]] && \
    xgettext --from-code=UTF-8 --language=Python \
        --add-comments=TRANSLATORS: \
        --keyword=_ --keyword=N_ --keyword=C_:1c,2 --keyword=NC_:1c,2 \
        --package-name=akizip --package-version=0.3.0 \
        -o "$TMPDIR/python.pot" "${PY_FILES[@]}"

[[ ${#UI_FILES[@]} -gt 0 ]] && \
    xgettext --language=Glade --keyword=translatable \
        -o "$TMPDIR/ui.pot" "${UI_FILES[@]}"

[[ ${#DESKTOP_FILES[@]} -gt 0 ]] && \
    xgettext --language=Desktop \
        -o "$TMPDIR/desktop.pot" "${DESKTOP_FILES[@]}"

[[ ${#METAINFO_FILES[@]} -gt 0 && -f "$ITS_FILE" ]] && \
    xgettext --its="$ITS_FILE" --from-code=UTF-8 \
        -o "$TMPDIR/metainfo.pot" "${METAINFO_FILES[@]}"

# ========== Merge ==========
msgcat "$TMPDIR/"*.pot -o "$POT_FILE"
echo "Updated $POT_FILE"

# ========== Read languages from LINGUAS ==========
LANGS=()
while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    LANGS+=("$line")
done < po/LINGUAS

# ========== Init / merge PO files ==========
for lang in "${LANGS[@]}"; do
    PO_FILE="po/$lang.po"
    if [[ -f "$PO_FILE" ]]; then
        echo "Merging $lang.po ..."
        msgmerge --update --previous "$PO_FILE" "$POT_FILE"
    else
        echo "Creating $lang.po ..."
        msginit --input="$POT_FILE" --locale="$lang" \
                --output="$PO_FILE" --no-translator
    fi
    # Ensure charset is UTF-8
    sed -i 's/charset=ASCII/charset=UTF-8/' "$PO_FILE"
done

echo "Done. Please edit the PO files to add translations."
