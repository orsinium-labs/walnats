---
# Alloy requires frontmatter, and myst-parser requires it to be non-empty
layout: default
---
# Verification

Formal verification usually means that you describe the same algoithm twice (declaratively and imperatively), and then computer checks that both implementations are equivalent. And when it comes to distributed systems, you need not only to describe your system but also how it changes over time. There are currently 2 usable languages that can effectively describe changing systems: [TLA+](https://en.wikipedia.org/wiki/TLA%2B) and [Alloy 6](https://en.wikipedia.org/wiki/Alloy_(specification_language)). On this page, I use Alloy 6 because it's  simpler, looks more like a programming language, great for describing relations, and has a nice visualizer.

This page provides a declarative model for a walnats-based system. You can use this model to generate possible failure scenarios or built on top of it verification of your business-specific logic.

## Learn Alloy

The good news is that there are tons of articles and publications about Alloy. Disproportinally more than this tool is actually used by sane people. The bad news is that Alloy 6 (released in 2021) was a huge release introducing a great support for working with time. Before the release, working with time required a lot of dirty hacks and workarounds, and it all was far from pretty. And most of models and tutorials using Alloy relied on time. Hence if you see a tutorial for Alloy using time and not updated after 2021, you can safely dicard it, it's useless now.

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
1. Navigate to the walnats repository you clonned, and inside go to `docs/alloy.md` and open it.
1. Press "Execute" to generate a sample of the model and "Show" to open the graph.

Go to these tutorials to learn using the GUI:

+ [How to use the analyzer](https://alloy.readthedocs.io/en/latest/tooling/analyzer.html)
+ [How to use the visualizer](https://alloy.readthedocs.io/en/latest/tooling/visualizer.html)
+ [How to use visualizer for time-based models](https://www.hillelwayne.com/post/alloy6/#the-new-visualizer)

## Message

The first "signature" (something like `class` in Python) we'll have is `Message`. It represents specific messages sent for a single event type. I make a model for only one event type to keep it simple. Whenever possible, you should use [inductive](https://en.wikipedia.org/wiki/Inductive_reasoning) approach. Prove your assumptions for one event, prove that every event in the system fits the model, and you have proven the whole system. That's why one event type is sufficient.

```alloy
some sig Message {}
```

The `some` quantifier means that there is always at least one message because models without messages are boring. If nothing happens, what's the point?

if there is a Message, it doesn't mean it has been emitted yet. All that means is that it will be emitted on the interval we consider. In other words, each message atom (instance) at the start is a planned message. I find it helpful for verification. We know in advance what messages we expect, and so it's easier to check if all expected messages actually happened. Lastly, it will help you if you plan to model producer failures.

## Producer

...

```alloy
sig Producer {
    var emitted: set Message
}
```

## Actors

...

```alloy
abstract sig Actor {
    var handled: set Message
}

// Different actor types, such as "send-email"
// or "generate-report". Each atom here
// is a separate instance of that actor.
sig Actor1, Actor2 extends Actor {}
```

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

[Safety and liveness properties](https://en.wikipedia.org/wiki/Safety_and_liveness_properties) are fundamental to how distributed systems are verified. We'll start with safety. It describes invariants that must be always true in the system whatever happens, "that bad things never happen".

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

## Liveness

...

```alloy
// Properties that will eventually hold true.
pred liveness {
    // Every message is eventaully emitted.
    Message = Producer.emitted
    // Every emitted message is eventaully processed.
    Producer.emitted = Actor1.handled
    Producer.emitted = Actor2.handled
}
```

## Step algorithm

...

## Running

Lastly, we specify [run](https://alloy.readthedocs.io/en/latest/language/commands.html#run) command where we put together everything we described above:

```alloy
run {
    init
    always safety
    always eventually liveness
}
```
