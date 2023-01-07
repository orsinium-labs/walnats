# Linter

Walnats ships with a [flake8](https://flake8.pycqa.org/en/latest/) linter to make sure you use correct arguments and follow good code style. It runs automatically when you run flake8 in the environment with walnats installed.

Since walnats is 100% type annotated and built with type safety in mind, linter doesn't check things that should be detected by [mypy](https://mypy.readthedocs.io/en/stable/).

## Violations

### walnats.Event

| code   | message                              |
| ------ | ------------------------------------ |
| WNS001 | event name is empty                  |
| WNS002 | event name is too long               |
| WNS003 | event name has invalid symbols       |
| WNS004 | event name should use kebab-case     |
| WNS005 | event description is empty           |
| WNS006 | event description is too long        |

### walnats.Limits

| code   | message                              |
| ------ | ------------------------------------ |
| WNS011 | limit must be positive               |
| WNS012 | age must be in seconds               |

### walnats.Actor

| code   | message                              |
| ------ | ------------------------------------ |
| WNS021 | actor name is empty                  |
| WNS022 | actor name is too long               |
| WNS023 | actor name has invalid symbols       |
| WNS024 | actor name should use kebab-case     |
| WNS025 | actor description is empty           |
| WNS026 | actor description is too long        |
