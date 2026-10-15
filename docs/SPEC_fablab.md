# SPEC: a fab lab node

*Asked, 15 October 2026, by Tomas, answering the pre-launch audit: "We should add a node type: fab lab." Then:
"machines, services, courses, repair, optional to be a parent node (depends on compute capacity), it should for sure
take 7 cells by default."*

**Status: decided 15 October 2026 (Tomas: "A: ok, B: yes, and with possibilities of expanding to the next contiguous cells, expanded limit, minimum 7. C: not yet"). Nothing built.** Each step below is its own pull request, run on node #1 before it merges.

## 1 · What is there today

- **The kind.** `NODE_KIND` is `home`, `business`, `community` or `district` (`app/settings.py:46`). Apart from the
  installer's question 3, nothing reads it: `/health` echoes it and no route changes on it. The installer files a
  lab under "A community or lab node", together with a neighbourhood.
- **Labs a node can see.** The `make` pack lists the nearest labs from the fablabs.io directory, as display only. That
  data is not openly licensed: AGPL covers the app, not the 2,864 records. A node can say where a lab is, but must not
  republish the lab's description.
- **What a house offers.** `things` (SPEC_inventory) with `offer = lend | give` become public lines at the res-8
  cell (`GET /offers`), answered through the node's bot.
- **Seven cells.** A private node maps its own res-8 cell and the six that touch it (SPEC_eyes §5). Mapping past them
  means asking to become a community node, and a lab registered on fablabs.io qualifies (§6).
- **Parents.** Any node with `AGGREGATE_TOKEN` set takes hourly means and alert timestamps from children. Since #258
  that token pushes and reads nothing.

## 2 · The kind

`NODE_KIND=fablab` is a fifth kind. A lab is not a neighbourhood: it has an offer of its own, and it is the place the
other nodes send people to ("the nearest place to make or fix something").

- **Installer, question 3.** "A fab lab: machines, courses and repair for the people around it." It sets
  `NODE_KIND=fablab` and `NODE_SCALE=community`. It also asks for the lab's fablabs.io slug, if it has one. The slug
  links the node to its own directory entry, so the lab can import its own record (§3).
- **The seven cells by default.** A fab lab node maps and counts its seven cells from the first boot, as a private
  node may. The slug is what a lab later shows when it asks to map past them (SPEC_eyes §6).
- **Listed as a lab.** `planetai hello` carries `kind: fablab` into `registry.json`, so every node's map draws it as a
  lab rather than a house. The registry schema gains `kind`, which is optional and defaults to the scale's word.

## 3 · What a lab offers

Four kinds of offer, all of them the lab's own words about itself, published CC BY by the lab:

| offer | what it says | built on |
|---|---|---|
| **machines** | a laser cutter, a 3D printer, a CNC mill: name, kind, state (working, down) | `things` with `class=tool`/`appliance` and `offer=lend` |
| **services** | "we cut your file", "we print parts": what, and whether it costs | a new `offers` kind, `service` |
| **courses** | a title, the next date, how to join | a new `offers` kind, `course`, with a date |
| **repair** | repair café days, what they fix | a new `offers` kind, `repair`, with a date |

- **One list, one route.** These ride the same rails as a house's lend and give: `GET /offers`, at the res-8 cell,
  in the open daily export, and answered through the lab's bot. A house's node already reads the labs nearby (the
  `make` pack). Once a lab runs a node, the house reads that lab's own `/offers` in place of the directory. Then
  "the nearest place to fix something" says what the lab can actually do this week.
- **Importing its own record.** A lab may copy its machines and its description from its own fablabs.io entry once,
  by its slug. Importing your own record is the lab republishing itself, which the licence question does not touch.

## 4 · Optional parent, by compute

A lab can be the parent of the homes around it, and becomes one only when its machine can carry it.

- The installer reads what `planetai preflight` already measures (memory, cores, disk). It offers "Let homes nearby
  report to this lab" only above a floor.
- Proposed floor: 8 GB and 4 cores.
- Saying yes sets `AGGREGATE_TOKEN` and prints it to hand out. Saying no, or a machine below the floor, leaves the lab
  a leaf like any home.

## 5 · Steps

1. **The kind.** `fablab` goes into settings, the installer question with the slug, `/health`, `planetai hello` and
   the registry's `kind`. The seven cells are on by default for this kind.
2. **Offers.** Add `service`, `course` and `repair` to offers, with a date where one belongs. A lab's machines come
   from things. The Data door gets a "This lab offers" table. The `make` pack prefers a lab node's `/offers` to the
   directory.
3. **Import from fablabs.io** by the lab's own slug, once, on the lab's word.
4. **Parent by compute.** The installer question and the floor.

## 6 · Decided (Tomas, 15 October 2026)

- **A. The floor for parent: 8 GB and 4 cores.**
- **B. Seven cells is the minimum, mapped like a private node.** A lab may grow into the next contiguous cells. The
  next ring around the seven makes 19 at res 8. It grows ring by ring, up to a larger limit than a home's. The seven
  are never fewer. The limit itself is set when step 1 is built.
- **C. Not yet.** Node #1 will move to Fab Lab Bali later; for now it stays at Tomas's place, a home. The first lab
  node waits for that move.
