# Repository Guidelines

## Project Structure & Module Organization

This directory is currently empty: no source code, tests, assets, dependency manifests, or Git metadata are present. Establish the layout when adding the first implementation. Prefer `src/` for application code, `tests/` for automated tests, and `assets/` for static resources when appropriate. Keep modules focused and document the actual layout in `README.md`.

## Build, Test, and Development Commands

No build, test, or local development commands are configured yet. When selecting a toolchain, provide reproducible commands for installing dependencies, running locally, building, and testing. Record those commands in `README.md` and keep them consistent with package scripts or build configuration. Do not assume commands such as `npm test` or `make build` exist until configured.

## Coding Style & Naming Conventions

Follow the chosen language's standard conventions and configure its formatter and linter early. Keep indentation consistent within each file; avoid mixing tabs and spaces. Use descriptive names for files, functions, and variables. Match established naming patterns as the project grows, and keep formatting changes separate from behavioral changes.

## Testing Guidelines

No testing framework or coverage threshold is established. Add automated tests alongside new behavior and bug fixes once a framework is selected. Use descriptive test names that identify the scenario and expected result. Include normal cases, boundary conditions, and failure paths. Document the test command and required setup before expecting contributors to run it.

## Commit & Pull Request Guidelines

No Git history is available to infer existing commit conventions. Use short, imperative commit subjects, such as `Add initial project configuration`, and keep commits focused. Pull requests should explain the change, its purpose, and validation performed. Link related issues when available, include screenshots for visual changes, and state any setup requirements or untested behavior.

## Security & Configuration

Keep credentials and local secrets out of version control. Provide placeholder configuration examples and document required environment variables when configuration is introduced.
