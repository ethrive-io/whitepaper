# ethrive — Whitepaper

Two companion documents introducing the **ethrive protocol** — a
peer-to-peer system where every participant (a person, a device, a
group, or a program) owns a signed, append-only log of operations
called a _space_. Spaces replicate between peers and converge
eventually. No servers. No central authority.

> **⚠️ Experimental software.** ethrive is pre-1.0 and under active
> development. APIs, wire formats, and on-disk layouts will change
> without notice, and the protocol has not been independently
> security-audited. Do not use it with real funds, production data,
> or anything you can't afford to lose. Provided **as-is**, with no
> warranties of any kind — see [LICENSE](LICENSE).

## Podcast

If you'd like a softer entry point before reading either document,
start here.

> 🎙️ **[Evicting digital landlords with ethrive](https://ethrive-io.github.io/whitepaper/Evicting_digital_landlords_with_ethrive.mp3)** (54 min) — a podcast-style conversation about the protocol, generated with Google NotebookLM.

## Read or listen

Same story, two altitudes. Pick whichever fits the reader in front of
you:

| | Audience | Length | Tone | Audio |
| --- | --- | --- | --- | :-- |
| **[TECHNICAL.md](TECHNICAL.md)** | engineers, protocol implementers, architects | ~7,300 words / ~35 min read | formal, cites prior art, covers the protocol's structure and security model | [🎧 Listen](https://ethrive-io.github.io/whitepaper/WHITEPAPER.mp3) |
| **[NON_TECHNICAL.md](NON_TECHNICAL.md)** | everyone else | ~4,100 words / ~20 min read | plain language, no jargon, no code, starts from "where are your photos, really?" | [🎧 Listen](https://ethrive-io.github.io/whitepaper/WHITEPAPER_NON_TECHNICAL.mp3) |

Both documents stand on their own. Readers new to distributed systems
should start with the non-technical version; readers who want to
implement ethrive or evaluate it as a protocol should read the
technical one. Reading both is ~55 minutes and gives you the most
complete picture.

## What ethrive is, in one paragraph

A _space_ is a signed, append-only log of operations, owned and
replicated by a set of members. A single person is a one-member space.
A chat group is a multi-member space. A DAO is a space whose members
jointly sign with threshold cryptography. An application's data lives
in a space the user controls. Replication happens directly between
members through a vector-clock diff; there is no global ledger, no
consensus round, no central authority, and no server. Every feature
beyond membership and governance — chat, files, collaborative
documents, RPC, profiles, settings, on-chain signing — plugs in
through a single extension point called a _handler_. The result is a
substrate on which applications can be built that are offline-tolerant
by construction, user-sovereign by default, and composable across
categories that earlier systems treat as unrelated problems.

## Status

These documents are the **living whitepaper** for the ethrive
protocol. They describe the design intent; the normative protocol
specification lives in a separate repository
(`ethrive-spec` — coming online alongside this one). If the
whitepaper and the spec ever disagree, the spec wins — the whitepaper
is an invitation, not a contract.

## Citing

Please cite either document as:

> ethrive whitepaper (`<TECHNICAL.md | NON_TECHNICAL.md>`),
> ethrive contributors, 2026.
> Licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
> https://github.com/ethrive-io/whitepaper

## License

Both whitepapers are licensed under **Creative Commons Attribution 4.0
International** (CC BY 4.0). You may copy, translate, excerpt, remix,
or redistribute them — commercial or non-commercial — as long as you
credit the source. Full license text: [LICENSE.md](LICENSE.md).

## Contributing

Typo fixes, clarifications, and translations are welcome via pull
request. Protocol-level changes belong in the spec repository, not
here — the whitepaper's job is to explain the shape of the protocol,
not to define it. If you're unsure which side of that line a change
falls on, open an issue and we'll figure it out together.
