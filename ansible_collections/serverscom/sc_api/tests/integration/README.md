How to run integration tests
============================
You need to create custom `integration_config.yaml` file in this directory.

Variables to define:
* sc_endpoint
* sc_token

You should never commit the file into repository (and it's gitignored).

Run `ansible-test integration --requirements --docker --python=3.8` to run
tests.
