#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

ERRORS=0

# Helper: find files by pattern, excluding build dirs
find_files() {
    local pattern="$1"
    find . -name "${pattern}" -not -path "./.flatpak-builder/*" -not -path "./build*" -not -path "./.git/*" || true
}

# Helper: check a single file with a command
check_one() {
    local file="$1"
    local label="$2"
    shift 2
    if ! "$@" 2>&1; then
        echo "ERROR: Invalid ${label}: ${file}"
        ERRORS=$((ERRORS + 1))
    else
        echo "OK: ${file}"
    fi
}

echo "==> Checking .po files..."
PO_FILES=$(find_files "*.po")
if [ -z "${PO_FILES}" ]; then
    echo "No .po files found."
else
    for f in ${PO_FILES}; do
        check_one "${f}" ".po file" msgfmt -c "${f}" -o /dev/null
    done
fi

echo ""
echo "==> Checking .pot files..."
POT_FILES=$(find_files "*.pot")
if [ -z "${POT_FILES}" ]; then
    echo "No .pot files found."
else
    for f in ${POT_FILES}; do
        check_one "${f}" ".pot file" msgfmt -c "${f}" -o /dev/null
    done
fi

echo ""
echo "==> Checking .xml / .xml.in / .ui files..."
XML_FILES=$(find . \( -name "*.xml" -o -name "*.xml.in" -o -name "*.ui" \) -not -path "./.flatpak-builder/*" -not -path "./build*" -not -path "./.git/*" || true)
if [ -z "${XML_FILES}" ]; then
    echo "No XML files found."
else
    for f in ${XML_FILES}; do
        check_one "${f}" "XML file" xmllint --noout "${f}"
    done
fi

echo ""
echo "==> Checking .json files..."
JSON_FILES=$(find_files "*.json")
if [ -z "${JSON_FILES}" ]; then
    echo "No .json files found."
else
    for f in ${JSON_FILES}; do
        check_one "${f}" "JSON file" python3 -c "import json; json.load(open('${f}'))"
    done
fi

echo ""
echo "==> Checking .yml / .yaml files..."
YAML_FILES=$(find . \( -name "*.yml" -o -name "*.yaml" \) -not -path "./.flatpak-builder/*" -not -path "./build*" -not -path "./.git/*" || true)
if [ -z "${YAML_FILES}" ]; then
    echo "No YAML files found."
else
    for f in ${YAML_FILES}; do
        check_one "${f}" "YAML file" python3 -c "import yaml; yaml.safe_load(open('${f}'))"
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
