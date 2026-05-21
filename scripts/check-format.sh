#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

ERRORS=0

echo "==> Checking .po files..."
PO_FILES=$(find . -name "*.po" -not -path "./.flatpak-builder/*" -not -path "./build*" || true)

if [ -z "${PO_FILES}" ]; then
    echo "No .po files found."
else
    for f in ${PO_FILES}; do
        if ! msgfmt -c "${f}" -o /dev/null 2>&1; then
            echo "ERROR: Invalid .po file: ${f}"
            ERRORS=$((ERRORS + 1))
        else
            echo "OK: ${f}"
        fi
    done
fi

echo ""
echo "==> Checking .xml and .xml.in files..."
XML_FILES=$(find . \( -name "*.xml" -o -name "*.xml.in" \) -not -path "./.flatpak-builder/*" -not -path "./build*" || true)

if [ -z "${XML_FILES}" ]; then
    echo "No .xml files found."
else
    for f in ${XML_FILES}; do
        if ! xmllint --noout "${f}" 2>&1; then
            echo "ERROR: Invalid XML file: ${f}"
            ERRORS=$((ERRORS + 1))
        else
            echo "OK: ${f}"
        fi
    done
fi

echo ""
if [ "${ERRORS}" -gt 0 ]; then
    echo "==> FAILED: ${ERRORS} file(s) with format errors."
    exit 1
else
    echo "==> SUCCESS: All files passed format checks."
    exit 0
fi
