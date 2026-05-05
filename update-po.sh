#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

POT_FILE="po/akizip.pot"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

ITS_FILE="/usr/share/gettext/its/metainfo.its"

# ========== 自动分类 POTFILES.in ==========
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
        *.gschema.xml) SKIP_FILES+=("$f") ;;  # 运行时翻译，跳过提取
        *) echo "警告: 未知文件类型，跳过: $f" >&2 ;;
    esac
done < po/POTFILES.in

# ========== 按类型分别提取 ==========
[[ ${#PY_FILES[@]} -gt 0 ]] && \
    xgettext --from-code=UTF-8 --language=Python \
        --keyword=_ --keyword=N_ --keyword=C_:1c,2 --keyword=NC_:1c,2 \
        --package-name=akizip --package-version=0.1.0 \
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

# ========== 合并 ==========
msgcat "$TMPDIR/"*.pot -o "$POT_FILE"
echo "已更新 $POT_FILE"

# ========== 初始化 / 合并 zh_CN zh_HK ==========
for lang in zh_CN zh_HK; do
    PO_FILE="po/$lang.po"
    if [[ -f "$PO_FILE" ]]; then
        echo "合并 $lang.po ..."
        msgmerge --update --previous "$PO_FILE" "$POT_FILE"
    else
        echo "创建 $lang.po ..."
        msginit --input="$POT_FILE" --locale="$lang" \
                --output="$PO_FILE" --no-translator
    fi
    # 确保字符集为 UTF-8，避免中文翻译报错
    sed -i 's/charset=ASCII/charset=UTF-8/' "$PO_FILE"
done

# ========== 更新 LINGUAS ==========
cat > po/LINGUAS <<'EOF'
# Please keep this file sorted alphabetically.
zh_CN
zh_HK
EOF

echo "完成。请编辑 po/zh_CN.po 和 po/zh_HK.po 填入翻译。"
