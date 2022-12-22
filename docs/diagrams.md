# Diagrams

The definitions of {py:class}`walnats.Actors` and {py:class}`walnats.Events` can be used to produce architectural diagram of the project. It's especially helpful when the system grows to a crazy size and you still want to have the system overview.

The class `Service` accepts the `name` of the service, events it `emits`, and actors it `defines`. The string representation of the service produces a [d2](https://github.com/terrastruct/d2) diagram definiton:

```python
services = [
    walnats.Service(
        name='users',
        emits=walnats.Events(USER_CREATED, USER_UPDATED),
    ),
    walnats.Service(
        name='notifications',
        defines=walnats.Actors(SEND_EMAIL),
    ),
]
for s in services:
    print(s)
```

1. [Install d2](https://github.com/terrastruct/d2#install): `curl -fsSL https://d2lang.com/install.sh | sh -s --`
1. Pipe output of your script into d2 to produce a diagram: `python3 arch.py | d2 - > arch.svg`

## A bigger example

Here is a big working example of generating diagrams and its output.

```{literalinclude} ../examples/diagram.py
:language: python
```

The produced diagram:

![output](./schemas/arch.svg)
