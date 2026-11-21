# Commercial rights, once the node is AGPL

**Raised 21 November 2026 by Tomas. Drafted the same day. Nothing here is decided until Tomas strikes a row in
§10.**

Tomas asked whether being open source stops the Fab City Foundation from licensing a version of the node
commercially, or from turning one into a product. The code is Apache-2.0 today and becomes AGPL-3.0-or-later once
every contributor has consented ([2026-09-25-licence.md](2026-09-25-licence.md)). The 18 September record
([2026-09-18-licence.md](2026-09-18-licence.md)) touched this twice. In §2 it called an exception licence sold by
the Foundation "a business decision this record does not make", and in §3 it said a closed product is possible
"not without the Foundation's permission". This record asks what that permission rests on.

The public licence does not stop the Foundation. Whoever holds the copyright in a piece of code is not bound by
the licence they give everybody else, so the Foundation can publish the node under AGPL and license the same code
on other terms, for the code it holds. **Today no document says it holds any.** `NOTICE` reads "Copyright 2026 Fab
City Foundation and contributors", and nothing in the repository records a contributor, Tomas included, giving the
Foundation more than the Apache-2.0 licence everybody already has.

Nobody who worked on this record is a lawyer. §11 lists what counsel has to answer before anything is signed or
sold.

---

## §1 · What the repository says today, checked

Counted on 21 November 2026 at `6b32461`, the v0.92.0 release commit.

| | |
|---|---|
| commits on `main`, excluding merges | **1,136** (1,525 with merges) |
| by Tomas, under five author identities | **1,124** |
| by Lucas Marangoni, under two identities | **2**, and one merge commit |
| by Lars Petrova Taylor | **2** |
| authored as Claude | **8**, all on 7 September, 104 lines added |
| carrying a `Co-Authored-By` trailer for a model | **952** (84%) |
| carrying a `Signed-off-by` line | **1** |
| releases tagged, v0.4.3 to v0.92.0 | **121**, every one Apache-2.0 |

What the files say:

- `LICENSE` is Apache-2.0 and has not changed since the first commit on 3 September.
- `CONTRIBUTING.md` says "Code Apache 2.0, docs CC-BY 4.0. By opening a PR you agree to those terms." The sign-off
  it asks for is the Developer Certificate of Origin, which it describes as "Not a CLA: nothing is assigned to
  anybody, and there is no form."
- No source file carries a copyright line or a licence header.
- No consent to the AGPL relicence is recorded anywhere in the repository.
- `GOVERNANCE.md` leaves "the licence, the trademark" to the Fab City Foundation, and says of the things the
  Foundation would pass on if it dissolved that "today it holds none of them".
- 372 pull requests have merged: 368 from Tomas, 2 from Lucas, 2 from Lars. #152 and #176, from Saad Chinoy, closed
  without merging, and no commit on `main` names him or either pull request. His work is in four wild packs (§7).

---

## §2 · What the Foundation can already do

None of this needs a new right, a consent or a form.

- It can sell services: installing nodes, the Node kit, and the Kept Alive tier as `PRODUCT.md` describes it. The
  18 September record (§3) found all of it unaffected by AGPL, because the node belongs to the household and is
  not offered to them over a network.
- It can sell the software as it is. AGPL allows charging for a copy, for support and for a warranty. A box sold
  with the node installed is fine as long as the source comes with it or is offered.
- It can host the node for other people if it publishes the source. AGPL §13 asks whoever runs a modified version
  for other people over a network to offer those people its source, and a hosted service that publishes what it
  runs meets that.
- It can write a separate program that talks to nodes. Something that reads a node's API or its MCP tools from
  outside, and contains no node code, is its own work and can carry any licence. Where "separate" ends is a
  question for counsel (§11).
- It can use everything released so far on Apache-2.0 terms. A licence change does not reach back. All 121
  releases stay Apache-2.0 for anyone who has them, so the Foundation could build a closed product on v0.92.0
  tomorrow.

**Anybody else can do the same with those releases.** A competitor keeps Apache-2.0 on every release up to the
relicence tag, for good, and may close it and host it without publishing anything. So an exception licence from
the Foundation is only worth paying for where the code exists under AGPL alone, which means code written after
the relicence. Every release that ships before the relicence adds to what a competitor may close.

---

## §3 · What needs rights the Foundation does not hold yet

Three things, and all three need the same right, which is to license AGPL code on terms other than AGPL. That
right sits with the copyright holders, or with somebody they have given a licence broad enough to pass on.

| | what it is | what it needs |
|---|---|---|
| **a closed edition** | a version shipped without its source, or with closed parts built in | the right to distribute every AGPL-only line in it on other terms, and no third-party copyleft inside (§7) |
| **a hosted multi-tenant service, source unpublished** | `PRODUCT.md`'s Community tier grown into something a district logs into, the two "§13 fires" rows of the 18 September record | the same right. Without it §13 binds the Foundation like any operator, for the parts it does not hold. Publishing the source needs nothing (§2). |
| **an exception licence sold to a vendor** | a signed licence that lets one company ship or host without AGPL's duties | the same right, and being able to say in a contract that the Foundation holds what it is licensing (§6, §11) |

Where that right would come from, slice by slice:

| code | written by | what the Foundation holds today |
|---|---|---|
| released, to v0.92.0 | Tomas, 1,124 commits | Apache-2.0, the same as everybody. Nothing records more (§6). |
| | Lucas and Lars, 4 commits | Apache-2.0 through `CONTRIBUTING.md`'s line. Apache-2.0 lets a recipient sublicense and ship closed derivative works, so for these contributions that is already enough. |
| | the 8 commits authored as Claude, and the model-assisted share of the rest | a question for counsel (§11) |
| written after the relicence | Tomas | whatever the document in §6 says. Without one, AGPL, the same as everybody. |
| | anyone else | whatever `CONTRIBUTING.md` says on the day they open the pull request (§4) |

**The relicence pull request decides the last row, whether anybody means it to or not.** It will edit the line
"Code Apache 2.0". If it changes that line to say AGPL, which is the obvious edit, every later contribution
reaches the Foundation under AGPL only, and each one adds a person whose permission a closed edition would need.
GitHub's terms of service set the same default: a contribution to a repository comes in under that repository's
licence unless a separate agreement says otherwise (section D.6).

An exception licence also has a cost that no document fixes. AGPL was chosen because "The sovereignty claim is the
product" (the 18 September record, §6). An exception that lifts §13 for a vendor lifts that protection for the
households on the vendor's servers. If one is ever sold, the refusals in `ARCHITECTURE.md §7` belong in the
contract, and the same goes for a hosted service the Foundation runs itself.

---

## §4 · Inbound contributions, three options

### (a) Contributions come in under Apache-2.0, the node goes out under AGPL

`CONTRIBUTING.md` keeps its line for what comes in, and says in so many words that the node as a whole is
published under AGPL-3.0-or-later. A contributor keeps their copyright and gives everybody Apache-2.0 on their
contribution, which is what they give today.

**What it gives the Foundation:** Apache-2.0 §2 lets a recipient sublicense and distribute derivative works on
other terms, and §3 adds a patent licence. The Foundation can carry every contribution into a closed edition or an
exception licence, with the notices kept.

**Cost:**

- It is lopsided, and it has to be said in the open. A contributor gives more than they get back, and the
  Foundation is the only party holding enough of the rest to use it. Some people contribute to copyleft projects
  so their work cannot be closed.
- Apache-2.0 is given to everybody, so anyone may take a contribution on its own under those terms. A patch
  against AGPL files is of little use without the files, so this is small in practice.
- Nobody can contribute code that is itself GPL or AGPL from somewhere else. It stays out of core, or it comes in
  marked, and a marked part is one a closed edition leaves out (§7).
- The Foundation does not become the holder of that code. It can enforce the AGPL only over the parts it holds.
- The wording needs counsel. The DCO certifies a contribution "under the open source license indicated in the
  file", and after the relicence the file will indicate AGPL.

### (b) A contributor licence agreement with a relicensing grant

The contributor keeps their copyright and gives the Foundation a broad licence that includes the right to license
under other terms. It is signed once, usually through a bot on the first pull request.

**What it gives the Foundation:** an explicit grant, in the form a buyer's lawyer expects to see before paying for
an exception licence. It can also carry a promise back, that the Foundation keeps publishing the node under an
open licence.

**Cost:** it is a form. The 18 September record (§5) called an inbound licence that permits relicensing "a less
popular one". It slows the same university offices AGPL already slows, somebody has to keep the signatures, and
`CONTRIBUTING.md` would stop saying "there is no form".

### (c) Copyright assignment

The contributor transfers ownership to the Foundation.

**What it gives the Foundation:** one holder for all of the code. That is the simplest position from which to
enforce the licence or sign a warranty.

**Cost:** the heaviest of the three. It takes a signed document per contributor, and sometimes one from their
employer. Some legal systems do not let an author transfer these rights at all, and an exclusive licence stands in
(§11). It contradicts "nothing is assigned to anybody" outright. And contributors will ask what stops the
Foundation closing everything, which today is one paragraph of intent in `GOVERNANCE.md`.

### Which one fits the stance `CONTRIBUTING.md` takes today

**(a).** There is no form and nothing is assigned, and the sentence a contributor reads changes by one clause.
(b) is the fallback if counsel finds (a)'s wording does not hold. (c) fits one person only, Tomas, where it is one
document signed once (§6).

---

## §5 · The consents still to collect

| who | what is on `main` | what to ask |
|---|---|---|
| **Lucas Marangoni** | 2 commits, 12 and 15 September (#35, #64): the Menorca preset, the posidonia pack and the presets mount. The pack moved to the wild repository on 8 October. `presets/menorca.env` (17 lines) and one line of `docker-compose.yml` are still his, and the rest is in every release since. | both questions below |
| **Lars Petrova Taylor** | 2 commits, 18 October and 3 November (#281, #372): two node listings in `registry.json`, 12 lines each | both questions. A listing is facts about a node and may carry no copyright at all. Asking costs one message. |
| **Tomas Diez** | 1,124 commits | his own consent as an author, written into the document in §6 |
| **Saad Chinoy** | nothing | nothing for the node. His four wild packs are his (§7). |
| the 8 commits authored as Claude | 104 lines | nobody to ask (§11) |

Lucas and Lars both commit from fab.city addresses. If their agreements with the Foundation already give it their
work, the consent is a confirmation. Tomas knows that and this record does not.

For the commercial question alone, their past contributions need nothing new, because Apache-2.0 already covers
them (§3). The 25 September record waits for every contributor's consent before `LICENSE` changes, and this record
does not reopen that. They are being asked once anyway, so the message carries both questions.

Draft wording, for Tomas to send once counsel has read it:

> Hi Lucas
>
> the node is moving from Apache-2.0 to AGPL-3.0-or-later. I decided it on 25 September and the record is in
> docs/decisions. Before LICENSE changes I need a yes in writing from everyone who has code in it, and you do: the
> Menorca preset, the posidonia pack and the presets mount, pull requests #35 and #64.
>
> I am asking two things in one message so I do not come back to you later.
>
> 1. Do you agree that what you have contributed to fabcity/planetai-node is published under AGPL-3.0-or-later as
>    part of the node, and can you confirm you wrote it yourself and nobody else has a claim on it?
> 2. Do you agree that the Fab City Foundation may also license it under other terms, commercial ones included?
>    Apache-2.0 already allows that today, I want it said clearly. You keep your copyright and nothing is assigned.
>
> A reply with "yes to both" and your name is enough. If it is yes to the first only, tell me and we talk.
>
> all the best
> Tomas

The Foundation keeps the replies. The relicence pull request names who consented and on which date, and does not
paste anybody's email into a public repository.

---

## §6 · Tomas's own code

**Nothing records it as the Foundation's.** `NOTICE` is the only place that claims it, and a copyright notice
states a claim without transferring anything. The repository holds no assignment, no licence from Tomas to the
Foundation and no term of an agreement between them. This record does not know what Tomas's agreement with the
Foundation says, where the Foundation is registered or which law governs it, and does not guess.

It is 1,124 of 1,136 commits. In practice the Foundation's commercial rights in the node are this one document.

What it would need to say:

1. **Who:** Tomas Diez in his own name, and the Fab City Foundation by its registered name and seat.
2. **What:** everything he has written and will write for the node, under any of the five author identities in
   `git shortlog`. Whether the same document covers the other PLANETAI repositories should be decided at the
   same time. They were not checked for this record.
3. **The grant:** an assignment where the governing law allows one. Where it does not, an exclusive, worldwide,
   perpetual and irrevocable licence, with the right to license on any terms. Counsel picks.
4. **Work made with a model:** he passes on whatever rights he holds in it and says how it was made. That is 952
   of the commits.
5. **Other claims:** a statement that no other organisation he works with has a claim on the code. Three commits
   carry the identity of a Fab Lab Bali machine.
6. **What the Foundation promises back:** that it keeps publishing the node under AGPL-3.0-or-later, and a licence
   back to Tomas for his own use. This is the answer to "what stops the Foundation closing everything", and it is
   what would give the dissolution clause in `GOVERNANCE.md` something to bind. The document should also say
   whether the commercial right passes to a successor or ends with the Foundation.
7. **Who signs for the Foundation:** Tomas is its Founder and Executive Chair, so he is on both sides. Somebody
   else signs for the Foundation, by whatever its statutes say about a transaction with a board member.

---

## §7 · Parts that are not the Foundation's

A closed edition can carry only what the Foundation may license on closed terms. Read off `app/requirements.txt`,
the `pip:` lines of the 28 core packs, `NOTICE`, `docker-compose.yml`, PyPI and GitHub on 21 November 2026.

| part | its terms | in a closed edition |
|---|---|---|
| `psycopg`, the database driver | LGPL-3.0-only | allowed on LGPL's conditions: the user can swap the library, and its notices stay. The binary wheel bundles other libraries (§11). |
| the other Python dependencies read for this record (`mcp`, `pillow`, `pillow-heif`, `python-multipart`, `h3`, `paho-mqtt`, `rasterio`, `earthengine-api`, `pyshp`) | MIT, MIT-CMU, BSD-3-Clause, Apache-2.0, EPL-2.0 or BSD-3-Clause | allowed, notices kept. `pillow-heif`'s wheels bundle codec libraries whose licences were not read. |
| fonts, map libraries, the coastline and esp-web-tools under `app/static/` | OFL 1.1, BSD-3-Clause, MIT, ISC, Apache-2.0 | allowed with their licence texts. An OFL font cannot be sold on its own. esp-web-tools ships with its licence and is missing from `NOTICE`. |
| the containers beside the app: PostGIS, Mosquitto, Kubo, and Grafana when its profile is on | each its own. GitHub reports GPL-2.0 for PostGIS and AGPL-3.0 for Grafana. | separate programs, so a closed app may run beside them. A box sold with them installed conveys them and owes each its own terms. |
| the Reticulum bridge, in fabcity/planetai-reticulum | the bridge is Apache-2.0. `rns` and `lxmf` are under the Reticulum License, which is not an open licence ([2026-10-23-reticulum-licence.md](2026-10-23-reticulum-licence.md)). | may ship. Its two conditions on use pass to the customer. |
| OpenStreetMap geometry held by `packs/place` | ODbL | allowed. Attribution and share-alike on the database travel with it. |
| the data a node reads | each source's own terms, as `NOTICE` says | this is outside the code licence. A paid product is commercial use, and a source open to a household can be closed to a company. Earth Engine (`packs/earth-engine`, `packs/place`) is free for a nonprofit's noncommercial work, excludes fee-for-service work, and charges commercial customers. Each source gets read before a paid product turns it on. |

**After the relicence the core may take in GPL-3.0 and AGPL-3.0 code from other people.** That was one of the
reasons for AGPL (the 18 September record, §1). Each such part is one a closed edition has to leave out or
replace. The core holds none today: `xiaomi-air` and its GPL-3.0-only `python-miio` left on 3 October (#173). If
the option of a closed edition is to stay open, a copyleft dependency coming into core needs its own decision
record.

**The wild packs belong to their authors.** Ten are listed at fabcity/planetai-wild-packs on 21 November, and each
lists Apache-2.0 for its code. Four are by Tomas, four by Saad Chinoy, one by Lucas, and one is listed as "PLANETAI
community". Because they are Apache-2.0, a closed edition may bundle them with their notices, as anybody may. The
Foundation cannot grant more than Apache-2.0 on them, relicense them, or stop an author changing the licence of
the next version. The 18 September record (§4) recommended that pack code follow the core, which would make them
AGPL, and from that day each would need its author's permission. `xiaomi-air` cannot go into a closed edition at
all, because of `python-miio`.

The 28 core packs still declare no `licence:` key. The 18 September record asked for one when there were
seventeen.

---

## §8 · Hardware

There is no hardware in this repository, and the Foundation's GitHub account has no hardware repository for the
node (checked 21 November). The 18 September record recommended CERN-OHL-S and the 25 September record left it
undecided. Here is what the three variants of version 2 mean for somebody selling a box. They were read from the
SPDX copies of the texts, because CERN's own files would not load.

| | a vendor makes and sells our design | a vendor changes it | a vendor builds it into a larger product |
|---|---|---|---|
| **CERN-OHL-S**, strongly reciprocal | allowed, for any price. The complete source goes with the product, or a notice of where it is kept for at least three years. | the changed design is published under -S | the larger design is covered too and goes out under -S, apart from components that are open themselves or that anyone can buy as parts |
| **CERN-OHL-W**, weakly reciprocal | the same | changes to our design are published under -W | allowed. Parts that meet our design only through a documented interface stay closed. Our part and the changes to it stay open. |
| **CERN-OHL-P**, permissive | allowed, notices kept | may stay closed | allowed |

All three allow selling. All three carry a patent licence that ends for a licensee who sues over patents. None
gives the right to use the licensor's name beyond stating facts.

For a hardware product that means:

- **Under -S** a vendor may sell our box, and may not turn it into a better closed one. That matches AGPL on the
  software side.
- **Under -W** a partner can build our enclosure into a product of their own and keep their part closed.
- **Under -P** anybody can do anything, as under Apache-2.0.
- **The Foundation, as holder of the design, is not bound by any of them** and can sell a closed variant or give a
  partner other terms. That holds only if it holds the design, which is the question in §6 again, asked of whoever
  drew the enclosure. `PRODUCT.md` says the outdoor enclosure work is done. It is in no Foundation repository.

Two things limit all of this. Reciprocity in hardware rests on rights in the design files, and the shape of a box
or a circuit often carries no copyright, so somebody who measures a product and redraws it may be outside all
three (§11). And the kit holds other people's hardware, the Smart Citizen Kit, an AirGradient unit, a mini PC or a
Pi, each under its maker's terms, none read here. OSHWA certification works with all three variants and with
selling. It is a mark with rules of its own.

---

## §9 · The trademark policy

It is still unwritten. The 18 September record left a box for Tomas in its §6, and the box is empty.

It matters more after §2 and §3. Under AGPL a competitor who publishes their source may sell the same software,
the same kit and the same Kept Alive service. Under the Apache-2.0 releases they may close it too. In both cases
the name is what they cannot take. Apache-2.0 §6 grants no trademark rights, and AGPL §7 lets a licensor withhold
them. So the name is the one thing the Foundation can license commercially with no contributor's consent, if it
owns the name.

What the policy needs before it can be written is what the 18 September box asked: what is registered, in which
jurisdictions, by which entity, and whether "PLANETAI" is registered at all. For a product, add:

- classes that cover software, hardware and services;
- the household-facing name, which `PRODUCT.md` says is not decided;
- who may call a thing a PLANETAI node. `ARCHITECTURE.md §7`, the refusals, is the conformance test the
  18 September record proposed;
- what a fab lab selling installation and Kept Alive may call what it sells. `PRODUCT.md` makes the labs the
  installers, so that permission should be easy to get;
- names for forks and for wild packs;
- whether the Foundation's own products pass the same test before they carry the name.

---

## §10 · The recommendation, which Tomas can strike

Strike any row. Each stands without the others, except that row 4 waits on rows 2 and 3.

| | row |
|---|---|
| 1 | **Contributions stay inbound Apache-2.0 when `LICENSE` becomes AGPL**, option (a) of §4. The relicence pull request writes that into `CONTRIBUTING.md` in so many words, and says the Foundation may license the node on other terms. |
| 2 | **One message each to Lucas and Lars**, with §5's wording and both questions. |
| 3 | **Tomas and the Foundation sign the document in §6**, with the promise to keep publishing under AGPL in it. |
| 4 | **The relicence lands at the first tag after rows 2 and 3.** Every release before it is one more a competitor may close. |
| 5 | **A hosted service, if one is built, publishes its source.** A closed edition and exception licences wait for counsel's answers to §11, and an exception licence carries the refusals of `ARCHITECTURE.md §7`. |
| 6 | **Hardware goes out under CERN-OHL-S**, as the 18 September record recommended. -W is for a named partner, by its own record. |
| 7 | **Tomas fills the trademark box**, and the policy is written before any product ships under the name. |
| 8 | **A copyleft dependency coming into core needs a decision record** (§7). |

The reasons, in order of weight:

1. **Almost all of the right is one person's to give.** 1,124 of 1,136 commits are Tomas's. Row 3 is one document,
   and without it rows 1 and 2 protect four commits.
2. **Option (a) keeps the promise `CONTRIBUTING.md` makes.** No form, nothing assigned. It asks a contributor for
   what they already give today.
3. **The order matters.** If the relicence lands first and the inbound line changes with it, the door closes by
   default (§3), and reopening it later means finding every contributor again.

**The alternative** is to decide that the Foundation will never ship a closed edition or sell an exception. Then
rows 1 and 5 fall away, contributions come in under AGPL like the node goes out, and the
business is services, the kit, hosting with the source published, and the name. That is a simpler thing to explain
to a contributor. It is also the choice that cannot be undone once outside contributions arrive. Row 3 is still
needed, so the Foundation holds what it publishes.

Rows 1 to 4 give the Foundation the ability. Whether it ever uses it is a product decision this record does not
make.

---

## §11 · For counsel

1. **Tomas and the Foundation.** Assignment or exclusive licence under the Foundation's governing law, moral
   rights, who signs when the author chairs the board, and whether an existing agreement already covers it.
2. **Lucas and Lars.** Whether their agreements with the Foundation already give it their work.
3. **The inbound wording.** Whether "by opening a PR you agree" holds for Apache-2.0 inbound on an AGPL
   repository, against GitHub's default (terms of service, D.6) and the DCO's "license indicated in the file".
4. **Code written with a model.** Eight commits are authored as Claude and 952 carry a model's trailer. Whether
   such code has an author where it matters, how much a person's direction and selection count, what the tool
   provider's terms say about output, and what the Foundation can warrant in an exception licence if part of the
   code has no holder. Code with no holder cannot be held to the AGPL either.
5. **Whether the Foundation may earn licence income at all**, under its statutes and its tax status, or needs
   another vehicle for it.
6. **Where a separate program ends** (§2), for a closed service that only talks to nodes.
7. **Bundled libraries.** `psycopg`'s binary wheel under LGPL in a closed edition, and what `pillow-heif`'s wheels
   bundle.
8. **Hardware.** What CERN-OHL protects beyond the design files, and whether a registered design is worth having.
9. **The trademark.** Registration, classes and jurisdictions (§9).

---

## §12 · What this record does not do

It does not edit `LICENSE`, `NOTICE` or `CONTRIBUTING.md`. It sends no message to anybody and collects no consent.
It does not add a `licence:` key to a pack or list esp-web-tools in `NOTICE`. It does not state the Foundation's
trademark position, its legal form, or what Tomas's agreement with it says. It decides nothing until Tomas strikes
a row in §10.
