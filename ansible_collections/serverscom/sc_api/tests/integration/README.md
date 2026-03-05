How to run integration tests
============================
You need to create a custom `integration_config.yml` file in this directory.

Variables to define:
* sc_endpoint
* sc_token

You should never commit the file into the repository (and it's gitignored).

See the Justfile recipes (in the root directory of this project) for local development.
