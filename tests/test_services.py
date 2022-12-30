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


def test_async_api() -> None:
    s = walnats.Services()
    e = walnats.Event('user-created', dict, description='event descr')
    s.add('users', emits=walnats.Events(e))
    s.add('emails', defines=walnats.Actors(walnats.Actor('send-email', e, noop)))

    expected = {
        'asyncapi': '2.5.0',
        'info': {
            'title': 'application',
            'version': '0.0.0',
        },
        'channels': {
            'user-created': {
                'description': 'event descr',
                'subscribe': {
                    'message': {
                        'name': 'dict',
                        'payload': {'$ref': '#/components/schemas/dict'}
                    },
                },
            },
        },
        'components': {
            'schemas': {
                'dict': {'type': 'object'},
            },
        },
    }
    assert s.get_async_api() == expected

    expected_users = {
        'asyncapi': '2.5.0',
        'info': {
            'title': 'users',
            'version': '0.0.0',
        },
        'channels': expected['channels'],
        'components': expected['components'],
    }

    expected_emails = {
        'asyncapi': '2.5.0',
        'info': {
            'title': 'emails',
            'version': '0.0.0',
        },
        'channels': {},
        'components': {'schemas': {}},
    }
    specs = s.get_async_apis()
    assert len(specs) == 2
    assert specs[0] == expected_users
    assert specs[1] == expected_emails
