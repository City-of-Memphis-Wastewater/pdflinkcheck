# justfile # for including the rust core
analyze FILE:
    @echo "Running analysis on {{FILE}}..."
    LD_LIBRARY_PATH="{{invocation_directory()}}/rust_pdflinkcheck/target/release:$$LD_LIBRARY_PATH" \
    uv run pdflinkcheck analyze {{FILE}} -p rust
