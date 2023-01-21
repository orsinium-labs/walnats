---
# Alloy requires frontmatter, and myst-parser requires it to be non-empty
layout: default
---
# Verification

Formal verification usually means that you describe the same algorithm twice (declaratively and imperatively), and then the computer checks that both implementations are equivalent. And when it comes to distributed systems, you need not only to describe your system but also how it changes over time. There are currently 2 usable languages that can effectively describe changing systems: [TLA+](https://en.wikipedia.org/wiki/TLA%2B) and [Alloy 6](https://en.wikipedia.org/wiki/Alloy_(specification_language)). On this page, I use Alloy 6 because it's simpler, looks more like a programming language, is great for describing relations, and has a nice visualizer.

This page provides a declarative model for a walnats-based system. You can use this model to generate possible failure scenarios or build on top of it verification of your business-specific logic.

## Learn Alloy

The good news is that there are tons of articles and publications about Alloy. Disproportionally more than this tool is actually used by sane people. The bad news is that Alloy 6 (released in 2021) was a huge release introducing great support for working with time. Before the release, working with the time required a lot of dirty hacks and workarounds, and it all was far from pretty. And most of the models and tutorials using Alloy relied on time. Hence if you see a tutorial for Alloy using time and not updated after 2021, you can safely discard it, it's useless now.

There are some resources to learn Alloy that are still good:

+ [Alloy Documentation](https://alloy.readthedocs.io/en/latest/index.html) is an unofficial documentation by Hillel Wayne about Alloy. At the moment of writing, it's not updated for Alloy 6, so skip the "time" section. The rest is good.
+ Hillel Wayne also has a great blog about formal verification. Check out the tag [Alloy](https://www.hillelwayne.com/tags/alloy/), it has some good posts. I especially recommend [Formally Modeling Database Migrations](https://www.hillelwayne.com/post/formally-modeling-migrations/) (doesn't use time) and [Alloy 6: it's about time](https://www.hillelwayne.com/post/alloy6/) (covers the new time syntax).
+ [Alloy for TLA+ users](https://www.youtube.com/watch?v=tZywZc04lJg) is a tech talk by Jay Parlar. Again, disregard what he says about alloy being convoluted for time. The rest is good.

## Run this model

Alloy [supports running Markdown files](https://alloy.readthedocs.io/en/latest/tooling/markdown.html). This page that you read right now can be directly executed by Alloy:

1. Clone walnats repository.
1. [Install Alloy Analyzer](https://github.com/AlloyTools/org.alloytools.alloy/releases/)
1. Run Alloy Analyzer: `java -jar org.alloytools.alloy.dist.jar`.
1. Press "Open".
1. Navigate to the walnats repository you cloned, and inside go to `docs/alloy.md` and open it.
1. Press "Execute" to generate a sample of the model and "Show" to open the graph.

Go to these tutorials to learn using the GUI:

+ [How to use the analyzer](https://alloy.readthedocs.io/en/latest/tooling/analyzer.html)
+ [How to use the visualizer](https://alloy.readthedocs.io/en/latest/tooling/visualizer.html)
+ [How to use visualizer for time-based models](https://www.hillelwayne.com/post/alloy6/#the-new-visualizer)

## Message

The first "signature" (something like `class` in Python) we'll have is `Message`. It represents specific messages sent for a single event type. I make a model for only one event type to keep it simple. Whenever possible, you should use the [inductive](https://en.wikipedia.org/wiki/Inductive_reasoning) approach. Prove your assumptions for one event, prove that every event in the system fits the model, and you have proven the whole system. That's why one event type is sufficient.

```alloy
some sig Message {}
```

The `some` quantifier means that there is always at least one message because models without messages are boring. If nothing happens, what's the point?

if there is a Message, it doesn't mean it has been emitted yet. All that means is that it will be emitted on the interval we consider. In other words, each message atom (instance) at the start is a planned message. I find it helpful for verification. We know in advance what messages we expect, so it's easier to check if all expected messages actually happened. Lastly, it will help you if you plan to model producer failures.

## Producer

A producer is a service that emits messages for the event. We can have multiple producers.

```alloy
sig Producer {
    var emitted: set Message
}
```

Here, `set` means, well, that there is a set of messages, and `var` means that this set may change over time.

## Actors

And lastly, let's make some actors:

```alloy
abstract sig Actor {
    var handled: set Message
}

sig Actor1, Actor2 extends Actor {}
```

`Actor1` and `Actor2` are different actor types, such as "send-email" or "generate-report". Each atom (instance) here is a separate instance of that actor. For example, the atom `Actor1$2` will be the 2nd instance of Actor1.

The `abstract` means that there are no atoms of `Actor` type, it must be either `Actor1` or `Actor2`.

## Init

Time to write some "predicates". A predicate is a function that returns a boolean. If there are multiple conditions on multiple lines, they are implicitly connected with `and`.

The first predicate we'll have describes the initial state of the system:

```alloy
pred init {
    no Producer.emitted
    no Actor.handled
}
```

No messages we have should be emitted or handled at the start. If it is already handled, it's the same for us that it doesn't exist.

## Safety

[Safety and liveness properties](https://en.wikipedia.org/wiki/Safety_and_liveness_properties) are fundamental to how distributed systems are verified. We'll start with safety. It describes invariants that must be **always** true in the system whatever happens, "that bad things never happen".

```alloy
pred safety {
    all m: Message {
        // Every message is either isn't emitted yet
        // or emitted by a single producer.
        lone p: Producer | m in p.emitted
        // Every message is either isn't handled yet
        // or handled by a single instance of actor.
        lone a: Actor1 | m in a.handled
        lone a: Actor2 | m in a.handled
    }
    // Emitted message cannot be unemitted.
    all p: Producer |
        all m: p.emitted |
            m in p.emitted'
    // Handled message cannot be unhandled.
    all a: Actor |
        all m: a.handled |
            m in a.handled'
    // Message can be handled only if it has been emitted earlier.
    all m: Actor.handled' |
        m in Producer.emitted
}
```

Whatever happens, a message can be emitted at most by one actor, handled by at most one instance of each actor, and so on. Always.

## Liveness

Liveness properties are the ones that **eventually** will be true, that "good things happen".

```alloy
pred liveness {
    // Every message is eventually emitted.
    Message = Producer.emitted
    // Every emitted message is eventually processed.
    Producer.emitted = Actor1.handled
    Producer.emitted = Actor2.handled
}
```

## Step algorithm

A common approach to verification of an algorithm is to write an [imperative](https://en.wikipedia.org/wiki/Imperative_programming) implementation of the algorithm, then describe [declarative](https://en.wikipedia.org/wiki/Declarative_programming) properties, and then prove that the described properties are true for the algorithm. For distributed systems that means to describe how the system state changes on each step and then prove safety and liveness properties.

We won't do that. Our system is complex by nature, and there is no simple imperative algorithm describing it all. Instead, we'll let Alloy to change anything in our system: emit and handle any events and all. Safety properties will make sure that such changes are always legal and make sense, and liveness properties will make sure that our system always moves forward.

So, the last thing we do is specify [run](https://alloy.readthedocs.io/en/latest/language/commands.html#run) command where we put together everything we described above:

```alloy
run {
    init
    always safety
    always eventually liveness
}
```

We start with `init` and let the system evolve such that `safety` always holds true and `liveness` is eventually true. The rest is up to Alloy.

## Stuttering

Since we require `liveness` properties to be eventually true, on each step the system will progress towards that goal. There are a few things to keep in mind, though:

+ One step of the spec can take any amount of time in the real world, from nanoseconds to days. The system may die and be dead for days until an engineer comes and fixes a critical bug. All we say is that *eventually* messages will be processed.
+ Individual actors or even all of them still can [stutter](https://www.learntla.com/core/temporal-logic.html?highlight=stutter#anything-can-crash) for any duration of steps. Again, all we say is that they will *eventually* move on.
