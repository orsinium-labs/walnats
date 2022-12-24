from __future__ import annotations

from textwrap import dedent

import walnats


def noop(_: str) -> None:
    pass


def test_d2():
    s = walnats.Services()
    e = walnats.Event('user-created', str)
    s.add('users', emits=walnats.Events(e))
    s.add('emails', defines=walnats.Actors(walnats.Actor('send-email', e, noop)))

    assert s.get_d2().strip() == dedent("""
        direction: right
        users.style: {stroke: "#f39c12"; fill: "#fef4e6"}
        user-created.shape: oval
        user-created.style: {stroke: "#e74c3c"; fill: "#fcebea"}
        users -> user-created: str
        emails.style: {stroke: "#f39c12"; fill: "#fef4e6"}
        user-created -> emails.send-email: {style: {stroke: "#2c3e50"}}
        emails.send-email.style: {stroke: "#2980b9"; fill: "#e9f2fb"}
    """).strip()


def test_d2__no_colors():
    s = walnats.Services()
    e = walnats.Event('user-created', str)
    s.add('users', emits=walnats.Events(e))
    s.add('emails', defines=walnats.Actors(walnats.Actor('send-email', e, noop)))

    assert s.get_d2(colors=False).strip() == dedent("""
        direction: right
        user-created.shape: oval
        users -> user-created: str
        user-created -> emails.send-email
    """).strip()
