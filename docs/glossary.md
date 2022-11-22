# Glossary

We do our best not to use too many technical terms, or at least not to rely on them too much. But if you encountered in the documentation some term that you don't understand, check this page, it may be explained there. These aren't technical 100% correct explanations but rather informal ones that should be sufficient to use and understand walnats.

+ **Actor** is a piece of code in a subscriber service that acts on a specific event. For example, "notifications" service can have "send-email" and "send-sms" actors that act on the same "user-registered" event (or on different unrelated events).
+ **Consumer** is how Nats calls an Actor. If you run multiple copies of the same Actor, event on different machines, they all will be considered one consumer. Consumers are "the same" if they have the same name. That's why an Actor name must be unique accross the whole system.
+ **Event** is information about something happening in your system. Services in microservice architecture emit events into a message broker, so that other services can act upon them. For example, "users" service may emit event "user-registered", so that "email" can send a email confirmation message to the user and "audit-log" service can write an audit record that a new user has registered.
+ **Handler** is a function that implements the core logic for an actor. For example, "send-sms" actor can call "send_sms" Python function that accepts the event payload and sends an SMS.
+ **Message broker** is a service that takes care of delivering messages over the network. The most famous message brokers are RabbitMQ, Kafka, and Redis. Walnats uses Nats as the message broker.
+ **Nats** is a message broker that we use for delivering messages. It's cloud-native, written on Go, and initially was just a Pub.Sub solution, meaning that messages are delivered to only the subscribers that are currently online and are never retried. Now, it also has Nats JetStream for streams, and that's what makes walnats possible.
+ **Payload** is the content of the event serialized into binary, so it can be transfered over the network. In other words, it's the raw body of Nats message.
+ **Polling** is periodically requesting and receiving messages from a message broker. It's like "pull" but in a loop. That's how Actors consume Events.
+ **Publisher** is a service that emits events.
+ **Registry** is a collection of related things that can be managed together. For example, `walnats.Actors` is a collection of `walnats.Actor` instances.
+ **Schema** is a Python type of the data inside of the event. It can be a Pydantic model, a protobuf message, a dataclass, or a built-in type. Walnats transfers raw bytes over the network, and the schema is a Pytohn representation of the data that you can work with.
+ **Serializer** is a class that can take your data in Python types and convert it into bytes to be transfered over the network. For example, if your schema is `dict` and and your data is `{'hello': 1}`, walnats will (by default) convert it on the publisher side into `{"hello":1}` binary JSON payload, transfer it through the network, and turn back into `{'hello': 1}` on the receiving side.
+ **Stream** is a peristency layer on top of a subject in Nats JetStream. This is how Nats JetStream makes sure that messages are delivered to the right Actors and don't get lost.
+ **Subject** is how Nats calls queues. This is how different subscribers can receive from Nats only specific messages they are interested in instead of everything that gets put in it. Walnats uses the Event name as the subject name when emitting events.
+ **Subscriber** is a service that consumes events and acts on them.
