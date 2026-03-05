encrypted_file := justfile_directory() / ".secrets/integration_config.sops.yaml"
integration_config := justfile_directory() / "ansible_collections/serverscom/sc_api/tests/integration/integration_config.yml"

@_list:
  just --list

# Generate secrets placeholder and .sops.yaml config
init-secrets gpg_fingerprint:
    @test ! -f {{ encrypted_file }} || (echo "Error: {{ encrypted_file }} already exists." && exit 1)
    mkdir -p {{ justfile_directory() / ".secrets" }}
    printf 'creation_rules:\n  - pgp: "%s"\n' "{{ gpg_fingerprint }}" > {{ justfile_directory() / ".secrets/.sops.yaml" }}
    cp {{ justfile_directory() / "integration_config.yml.template" }} {{ encrypted_file }}
    cd {{ justfile_directory() / ".secrets" }} && sops -e -i {{ encrypted_file }}
    echo Done

# Run a command with decrypted integration config
run *args:
    sops --config {{ justfile_directory() / ".secrets/.sops.yaml" }} exec-file --no-fifo {{ encrypted_file }} 'just _run {} {{ args }}'

[working-directory: "ansible_collections/serverscom/sc_api"]dd
_run tmpfile *args:
    ln -sf {{ tmpfile }} {{ integration_config }}
    {{ args }}
    rm -f {{ integration_config }}
