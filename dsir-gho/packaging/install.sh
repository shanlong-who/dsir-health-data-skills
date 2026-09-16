#!/bin/sh
set -eu

skills_root="${HOME}/.agents/skills"
if [ "$#" -gt 0 ]; then
    if [ "$#" -ne 2 ] || [ "$1" != '--skills-root' ] || [ -z "$2" ]; then
        printf '%s\n' 'Usage: sh packaging/install.sh [--skills-root DIRECTORY]' >&2
        exit 2
    fi
    skills_root=$2
fi

source_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
if [ ! -f "$source_dir/SKILL.md" ] || [ ! -f "$source_dir/scripts/cli.py" ]; then
    printf '%s\n' 'The skill files are missing. Extract the complete dsir-gho package first.' >&2
    exit 1
fi

mkdir -p "$skills_root"
skills_dir=$(CDPATH= cd -- "$skills_root" && pwd -P)
destination="$skills_dir/dsir-gho"
case "$destination" in
    "$source_dir"|"$source_dir"/*)
        printf '%s\n' 'The installation destination must be outside the source skill folder.' >&2
        exit 1
        ;;
esac

if [ -e "$destination" ] || [ -L "$destination" ]; then
    printf 'Installation stopped: %s already exists. No files were overwritten.\n' "$destination" >&2
    exit 1
fi

# Exclusive creation prevents replacing an existing skill.
mkdir "$destination"
if ! cp -R "$source_dir/." "$destination/"; then
    printf 'Installation did not complete. The destination was left for review at %s.\n' "$destination" >&2
    exit 1
fi

printf 'Installed DSIR GHO at %s\n' "$destination"
printf '%s\n' 'Start a new Codex task and use $dsir-gho. Restart Codex if the skill is not visible.'
printf '%s\n' 'Python and network permissions were not changed. Run the doctor command before retrieval.'
