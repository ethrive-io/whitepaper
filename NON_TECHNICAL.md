# ethrive

## A Plain-Language Introduction

---

### A simple question to start with

Where, right now, are the photos you took last weekend?

If you're like most people, the answer is some version of "in the cloud." They might be on your phone, but they're also on a server somewhere — in Oregon, in Ireland, in Singapore — owned by Apple or Google or Amazon or whoever else makes the app you used. The same is true of your messages. Your documents. Your notes. Your calendar. Your contacts. Your medical records, increasingly. The pictures of your kids. The plans for your wedding. The drafts of the novel you've been writing since college.

You don't think about this most days, and there's no particular reason you should. The cloud works. It works very well. It backs things up. It syncs them between your devices. It surfaces them when you search. It just _exists_, like the electrical grid or the postal service, and you get on with your life.

But every now and then something happens that briefly tears the curtain back. A company you trusted with years of your work goes bankrupt or gets acquired and shuts down. A platform you've used for a decade changes its terms of service in a way that means your work is now training material for a model you don't want to train. A government somewhere decides that a particular kind of speech is illegal and the platform complies. An account gets suspended over a misunderstanding and you spend three weeks trying to reach a human being. A breach happens and your data is in some Russian forum.

What all of these have in common is that they're consequences of one specific architectural fact: your data isn't really yours. It's on someone else's computer. You're a tenant.

This document is about what it would take for things to be different.

---

### What we mean by "ownership"

Imagine you're renting an apartment. You hang your photos on the walls. You arrange your books on the shelves. You cook in the kitchen and sleep in the bedroom and have friends over for dinner. In every meaningful day-to-day sense, the apartment is _yours_.

But it isn't, really. The landlord can raise the rent. They can decline to renew the lease. They can sell the building to someone who has different ideas. If the landlord goes bankrupt, the building enters receivership and the new owner can do whatever the old contracts allow. If you stop paying rent, you have to leave. If the building burns down, you're out of luck unless you bought your own insurance.

This is approximately the relationship most of us have with our digital lives. We've decorated the apartment beautifully. We've arranged it just so. But we don't own it. We own the things inside it, in some legal sense, but we have no power over the building.

The consequences of that arrangement get clearer with each passing year. A note-taking company called Evernote was, for a long time, the way millions of people kept their personal records. When it changed hands and changed strategy, many of those people lost meaningful access. A photo service called Picnik shut down. A bookmark service called Delicious shut down. Google Reader shut down, taking with it years of personal curation. Friendster shut down. MySpace lost twelve years of user uploads in a single botched migration. The full list, if anyone bothered to keep it, would be in the thousands.

When we say a piece of software "owns" your data, we don't mean it in a sinister way. We mean it in a literal, structural way: the bytes that make up your messages and photos and notes are sitting on hard drives in data centres that the software's vendor controls. If the vendor stops operating, the bytes stop being available. The arrangement isn't anyone's fault — it's just how the software you use happens to be built.

The question is whether it has to be that way.

---

### A different idea

Suppose, instead, that your data lived on your own devices — your phone, your laptop, the spare computer in the closet — and on the devices of the people you actually share things with: your spouse, your colleagues, your family, the friends in your group chat. Suppose there was no central server in the middle. When you send a message, it goes directly from your device to the devices of the people you're sending it to. When you write a note, it lives on your devices, and on the devices of anyone you've explicitly chosen to share it with, and nowhere else.

This is roughly the picture of how the world _used_ to work before the cloud era — letters, phone calls, photo albums on the bookshelf — and roughly the picture that some peer-to-peer projects have been trying to restore for the past two decades. The trouble has always been that the old peer-to-peer ideas didn't quite work for ordinary use. Messages got lost when one party was offline. Apps were hard to build. Groups were hard to manage. Anything more sophisticated than file-sharing was a research project.

ethrive is a fresh attempt at that picture, with a few specific ingredients that earlier attempts didn't have.

The first ingredient is a single underlying idea, which the rest of the system is built from. Imagine a shared notebook. Several people own copies of the notebook, all of them identical. When one person writes something in their copy, the notebook eventually shows up the same in everyone else's. Each entry is signed, so you can always see who wrote what. Nothing ever gets erased — only crossed out — so the history is always there. Anyone with a copy can read it; only people with permission can write in it.

In ethrive, this shared notebook is called a _space_. Spaces are the only thing that exist. Your personal account is a space — one with just you in it. A conversation between you and your sister is a space — one with two people in it. A team's shared project is a space — one with your colleagues in it. A neighbourhood association is a space. A family treasury is a space. A photo album you've shared with your in-laws is a space.

Members of a space carry copies of the space's notebook on their own devices. When two members' devices come into contact — over the internet, over a local network, even directly over Bluetooth in the same room — they compare notes and fill in each other's gaps. After a few seconds, both copies are identical again.

That's the whole picture. Everything else in this document is a consequence of it.

---

### How devices stay in sync

The "comparing notes" part deserves a moment of attention, because it's how peer-to-peer systems mostly used to fall apart, and ethrive's answer is what makes it actually usable.

When you and a friend get back from separate trips and you're catching up over coffee, neither of you has to recount your entire trip from the beginning. You don't say "first I woke up, then I had breakfast, then I went to the airport…" Instead, you ask each other questions: where did you go on Tuesday? What was that restaurant you mentioned? Each of you already knows what _you_ did; you only need to learn the parts the other person did that you don't already know.

ethrive's devices do something similar when they meet. Each one quickly explains, "I have these entries in our shared notebook," and then each side fills in whatever the other is missing. The exchange is fast and efficient because most of the time, most of the notebook is already shared — only a few new entries need to move.

The result is that you never have to think about syncing. You write a message; it appears on your friend's phone, eventually. You add a card to the team board; your colleagues see it, eventually. The "eventually" can be milliseconds, when you're both online and connected. It can also be hours, when one of you is on a flight or in a tunnel. The system handles both cases the same way.

Critically, the system also handles the case where the recipient is _completely_ offline. As long as _some_ member of a shared space is online, your message can reach them — and from there, eventually, the offline party. The space's notebook is the inbox; it lives on every member's device; the message will arrive when the recipient's device next sees a peer who has the message. There's no central server that can be down, no email account that can be full, no special "delivery infrastructure" to maintain. The members of the conversation are the delivery infrastructure.

---

### Different shapes of spaces

Spaces come in different sizes and serve different purposes, but underneath they're all the same thing.

The simplest is a space with just you in it. This is your _personal_ space — your account, in the language of the apps you use today. It holds your private notes, your settings, your contacts, your personal files. Only you can write to it. Only your devices have copies of it. If you want a backup, you set up another device of your own.

The next-simplest is a space with two people in it. When you pair up with a friend or a family member or a colleague — through a one-time introduction ceremony where each of you confirms the other's identity — ethrive automatically creates a shared two-person space for the two of you. This is where your messages with that person live. Both of you can read it; both of you can write to it; both of your devices carry copies.

After that, spaces can have any number of people. A team. A neighbourhood. A small business. A family. A book club. A working group. The mechanics are the same; the only thing that changes is who's allowed to read and who's allowed to write.

There's one more variation that's worth singling out, because it's the most surprising. Some spaces are set up so that _no single member_ can sign on the space's behalf — instead, a _quorum_ of members has to agree. Think of a safe with multiple keys, where no one key opens it but any three out of five do. This is how you'd set up something like a family treasury, a small organization's funds, or any decision-making body where no one person should have unilateral power.

The remarkable thing is that, for these multi-key spaces, ethrive can also act as a real bank account on the existing financial system. The "signature" produced by three people agreeing is a perfectly ordinary signature from the outside world's point of view — banks and exchanges and online services see a single account, with a single signature, and have no idea that several people had to agree behind the scenes. The governance is invisible to everyone but the people doing it.

That's the kind of arrangement that traditionally required either trust in a custodian (a bank, a lawyer, a treasurer) or expensive special infrastructure. With ethrive, it's a setting on a space.

---

### Apps as lenses, not vaults

Here's the reframing that does most of the work in understanding why ethrive is interesting.

Today, most apps are _vaults_. The note-taking app stores your notes. The photo app stores your photos. The chat app stores your messages. Switching apps means somehow getting your data out of one vault and into another, which is famously difficult and often impossible.

In ethrive, apps are _lenses_. Your notes are in your own space; the note-taking app just shows them to you and lets you edit them. Your photos are in your own space; the photo app just displays them. Your messages are in your shared spaces with your friends; the messaging app just renders them as bubbles.

When you install an app, you're granting it specific, limited permission to read and write to specific parts of your space. Not a master key — a narrowly-scoped, time-limited permission. The app can do exactly what you've allowed it to do, and nothing else. If you change your mind, you revoke that permission and the app stops being able to act on your behalf, with no help required from the app's vendor.

The consequences are large.

If the company that makes your favourite note-taking app goes out of business tomorrow — gets acquired and shut down, runs out of money, pivots to making dating apps for accountants — your notes are unaffected. They were never on the company's servers. They're in your space, on your devices. You install a different note-taking app from a different vendor, grant it the same permissions, and within minutes you're back to work with all your notes intact.

This means apps have to compete on quality rather than on having captured your data. It means new entrants in any category aren't fighting against years of accumulated lock-in. It means open-source and commercial apps can read and write to the same data side by side. It means switching costs collapse. It means the apocalyptic "Twitter is shutting down" story just doesn't happen — or rather, when it does happen, it's an inconvenience rather than a disaster.

It also means a category of application that's currently very awkward becomes natural: apps that are _shared_ between several people. A team kanban board where everyone is writing to the same set of cards. A co-edited document. A shared calendar. A collaborative shopping list. These work because the data is in a shared space, and the protocol is careful to ensure that when two people edit the same thing at the same time, neither edit gets silently thrown away.

---

### Five things this makes possible

To make all of this concrete, here are five small stories about people using applications built on ethrive. None of them are speculative; each is a direct consequence of the design.

**The conversation that doesn't disappear.** Maria lives in São Paulo; her sister Lucia lives in Lisbon. They text every day. The internet between them is sometimes fast and sometimes terrible. With a normal messaging app, when Lucia sends a message and Maria's phone is offline, the message waits on the company's server. If the company has an outage — or if its servers in Maria's region are unreachable for any reason — the message is delayed. With ethrive, Lucia's message lives on Lucia's devices and any other devices in their shared two-person space. When Maria comes back online, her phone connects to Lucia's directly (or, if that fails, to any other device in the conversation), and the message arrives. There's no third party in the middle, and no third party's infrastructure that has to be working for the conversation to flow.

**The team that never loses an edit.** A small marketing team — Aisha, Ben, and Carlos — uses an ethrive-based tool to plan their campaigns. The tool is a collaborative board where they can move cards around, write notes, assign tasks. One Tuesday they're all working on the same plan at the same time, on different continents, all editing simultaneously. With many traditional collaboration tools, simultaneous edits sometimes lead to one person's work silently disappearing — the kind of bug that surfaces months later when someone says "I'm sure I wrote something here last week." With ethrive, when the right kind of data structure is used for shared editing, no edit is ever silently lost. Both versions of a disputed change are kept, and the application can show the conflict and let a team member resolve it. No work disappears.

**The family savings account that nobody can drain alone.** The Garcia family — two parents and two adult children — set up a shared savings fund. They use ethrive's multi-key arrangement: any three out of the four of them have to agree before any money moves. The fund is a real account on the existing financial system, with a real address, that can receive deposits like any other account. But to send money out, three Garcias have to participate in a brief approval ceremony from their own phones. No one Garcia can drain the account, even if their phone is stolen and the thief somehow gets past the lock screen. No bank, no lawyer, no custodian sits in the middle. The arrangement is a setting on a space.

**The notes app that outlives the company that built it.** Sam keeps their journal in an ethrive-based notes app called, let's say, JournalCo. They use it for three years. Their notes — over a thousand of them by now — accumulate in their own space. One day, JournalCo announces it's shutting down. Sam shrugs, downloads a different ethrive notes app — something called PenAndPad, maybe — grants it the same permissions, and within ten minutes is writing in PenAndPad with all of JournalCo's notes intact. The company shutting down didn't take Sam's journal with it. The journal was Sam's the whole time.

**The neighbourhood that runs on its own infrastructure.** A residents' association in a Cape Town suburb coordinates volunteer schedules, local events, donations to a community kitchen, and a shared list of trusted contractors. They could pay one of the big platforms to host all of this. Instead, they use ethrive. The association is a space with all 47 households as members. Their shared lists, schedules, and discussions live on members' phones — collectively, the neighbourhood is its own infrastructure. There are no monthly fees to anyone, no advertising-based business model demanding their attention, no risk of a platform deciding their kind of community isn't profitable enough to keep supporting. The neighbourhood runs itself.

---

### What this isn't

A few things ethrive is sometimes mistaken for, that it isn't.

It isn't a cryptocurrency. Spaces _can_ be set up to control money, as in the Garcia family example, but most spaces won't. Most spaces are just notebooks for notes, or photo albums, or message threads, or team boards. The protocol can talk to the financial system when that's what you want, and stays out of it otherwise.

It isn't a blockchain in the conventional sense. There's no global ledger that everyone shares; there's no mining; there's no token; there are no transaction fees. Each space is its own little universe, visible only to its members. The cryptographic ideas that blockchains introduced — signed entries, verifiable history, no central authority — are present, but they're applied per-space, not to a single global log that the whole world has to agree on.

It isn't a replacement for the internet. ethrive runs _on top of_ the internet, the same way email and the web do. It uses your existing network connection. When two devices are online and connected, data moves between them; when they're not, it waits.

It isn't anti-business. Apps still get built. App makers still get paid. Subscription apps still subscribe. The relationship between you and the app maker just changes shape: they're no longer holding your data hostage to keep you as a customer; they're earning your continued business by being good at what they do.

And it isn't magic. When all of your devices are off, your data is on those devices and nowhere else, which is great for privacy but means that you, personally, are responsible for backups in a way you weren't before. (The protocol provides ways to make this manageable — extra members, dedicated always-on devices, recovery arrangements — but the responsibility is yours.)

---

### The trade-offs, honestly

Anything you build by removing the central server will give up some of the things the central server provided.

You give up instant search across everyone's stuff, in the sense that big search engines do. You can search within your own spaces and the ones you're a member of, of course; but ethrive doesn't index "the internet" because there is no central place that _is_ the internet of ethrive.

You give up some of the conveniences that depend on a service knowing about lots of users at once. Real-time recommendations based on what "people like you" are doing, for instance, look different in a world where there's no central observer keeping track of everyone.

You give up the option to call customer support and have someone reset your password by looking at your account in their database. Your data is on your devices; if you lose all your devices and have made no recovery arrangements, your data is gone, the same way a house key is gone if you don't have a spare and lock yourself out.

You give up the simplest possible mental model — "it's somewhere in the cloud" — and replace it with one that's a little more involved: "it's on devices I and my collaborators control." That's a real cognitive cost, especially the first time you set things up.

These costs are not theoretical. They're the price of sovereignty. The benefit is that the costs are paid in convenience rather than in control, which most people, asked plainly, would prefer.

---

### A future you can choose

For the past twenty years, the structure of digital life has narrowed. A handful of large companies have come to host most of what we make, share, and remember. We didn't choose this because we wanted to. We chose it because the alternative — running our own servers, syncing between our own devices, managing our own backups — was beyond what ordinary people could be expected to do. The cloud companies offered a deal: give us your data, and we'll handle the hard parts. We took the deal, mostly without thinking about it, because there wasn't really another option.

ethrive is an attempt to offer a different deal. The hard parts are handled by the protocol itself, not by a vendor: your devices know how to find each other, how to sync, how to recover from offline periods, how to manage permissions, how to revoke access when you change your mind. You don't have to run a server. You don't have to know how any of this works. You just install apps and use them, the same way you do now. The difference is what's underneath: the data those apps work with is yours, in a sense that's not just legal but architectural.

Whether this turns out to be the structure of digital life for the next twenty years depends on a lot of things, most of them out of any one person's hands. What's true now is that the technology is built. The specifications are open. There is no company that owns ethrive. Anyone who wants to build something on it can; anyone who wants to use it can.

If the world we have right now is one you're broadly happy with, none of this matters very much. If it isn't, this is one of the places to look.

---

### A plain-language glossary

A few words used in this document, defined plainly. None of these are required to use anything built on ethrive, but they'll help if you read further.

**Space.** A shared notebook that one or more people have copies of. Everything in ethrive happens inside a space.

**Member.** A person, organization, or program that has been admitted to a space and can read or write in it.

**Personal space.** A space with just you in it; the equivalent of your "account" on a service, but living on your own devices.

**Pairing.** The one-time introduction ceremony two people go through to add each other as contacts; afterwards, their devices can find each other and share spaces.

**Multi-key space.** A space where no single member can act alone — a quorum of members has to agree. Useful for treasuries, family funds, group decisions.

**App permission (or "scope").** A specific, narrow capability you grant an app — for example, "read my display name," or "write to my notes." Apps can only do what you've allowed them to do.

**Revocation.** The act of taking back a permission. Once revoked, an app loses its ability to act on your behalf, even if it disagrees.

**Sync.** The process by which two devices that share a space catch each other up on what's happened. Mostly invisible; mostly automatic.

**Sovereignty (in this context).** The property that your data lives in places you control, not in places someone else controls.

**Lens, not a vault (for apps).** A way of describing the new relationship between apps and your data: an app shows you your data and lets you work with it, but the data is yours and stays yours when the app is gone.
