#!/bin/sh
# Install with: curl -fsSL https://raw.githubusercontent.com/andrew0928/deep-sleep/main/install.sh | sh
set -eu

main() {
    if [ "$(uname -s)" != Darwin ]; then
        echo 'deep-sleep: installation requires macOS.' >&2
        return 1
    fi
    : "${HOME:?HOME must be set}"
    base_url='https://raw.githubusercontent.com/andrew0928/deep-sleep/main'
    bin_dir="$HOME/.local/bin"
    config_dir="$HOME/.deep-sleep"
    work_dir=$(mktemp -d "${TMPDIR:-/tmp}/deep-sleep-install.XXXXXX")
    staged_binary=''
    trap 'rm -rf "$work_dir"; if [ -n "$staged_binary" ]; then rm -f "$staged_binary"; fi' EXIT
    trap 'exit 1' HUP INT TERM

    curl -fsSL "$base_url/deep-sleep" -o "$work_dir/deep-sleep"
    curl -fsSL "$base_url/examples/config.env" -o "$work_dir/config.env"
    [ -s "$work_dir/deep-sleep" ] && [ -s "$work_dir/config.env" ]
    /bin/bash -n "$work_dir/deep-sleep"

    mkdir -p "$bin_dir" "$config_dir"
    if [ -e "$config_dir/.env" ] || [ -L "$config_dir/.env" ]; then
        echo "Preserved existing configuration: $config_dir/.env"
    else
        # Never overwrite configuration created by another installer.
        (umask 077; set -C; cat "$work_dir/config.env" > "$config_dir/.env")
        echo "Created configuration template: $config_dir/.env"
    fi
    staged_binary=$(mktemp "$bin_dir/.deep-sleep-install.XXXXXX")
    install -m 755 "$work_dir/deep-sleep" "$staged_binary"
    mv -f "$staged_binary" "$bin_dir/deep-sleep"
    staged_binary=''

    printf '\nInstalled: %s/deep-sleep\n' "$bin_dir"
    echo 'Edit ~/.deep-sleep/.env to select your volumes, then verify with:'
    printf '  "%s/deep-sleep" --dry-run\n' "$bin_dir"
    case ":${PATH:-}:" in
        *":$bin_dir:"*) ;;
        *) printf '\nAdd this line to your shell configuration (for example ~/.zshrc):\n  export PATH="$HOME/.local/bin:$PATH"\n' ;;
    esac
}

main
