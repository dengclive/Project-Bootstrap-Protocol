**THE UI / UX DESIGN GUIDE**

*Validated Principles for Interfaces People Trust and Enjoy*

A formalized reference synthesizing five practitioner sources,

cross-checked against current (2025–2026) UX research.

**Draft v1.1  ·  July 2026  ·  Bootstrap Protocol v2.4.0–aligned**

# **How to Read This Guide**

This guide consolidates the design advice from the five source transcripts into a single, non-overlapping reference. Overlapping tips were merged: for example, *visual cues* and *visual hierarchy* appeared in multiple sources and are unified here under one section; *anchoring* appeared in both the A/B-test source and the psychology source and is treated once.

Every principle was checked against recent UX literature before inclusion. Each carries a status banner:

| **VALIDATED —  **confirmed by current research and still standard practice. |
| --- |

| **VALIDATED WITH CAVEAT —  **still useful, but recent evidence narrows when or how it applies. |
| --- |

A short **Ethical use** note accompanies the persuasion principles, because several of them now sit close to the line regulators call "deceptive design." Under current enforcement (e.g. the FTC's US $2.5B Amazon settlement in September 2025), persuasion that conceals information or manufactures false urgency is a legal and reputational risk, not just an ethical one.

# **Contents**

# **Part 1 · Visual Foundations**

How information is weighted, layered, and lit on the screen. These are the base-layer skills every other section assumes.

## **1.1 Establish a Clear Visual Hierarchy**

| **VALIDATED —  **core, uncontested principle of interface design. |
| --- |

Presenting every element with the same size, weight, and color creates a flat, monotonous surface that forces users to read everything to find anything. Before designing, list the elements the screen must contain and rank them by importance to the user. Then use **size, weight, color, contrast, and position** to make the ranking visible at a glance.

A frequent mistake is emphasizing the wrong element — giving a metric's label ("Sales") more visual weight than its value ("591"). Emphasize the information the user actually came for; de-emphasize the supporting labels.

| **Weak hierarchy** | **Strong hierarchy** |
| --- | --- |
| Labels and values share one size and weight | Key value is largest / boldest |
| Everything competes for attention | Supporting labels are smaller and muted |
| User scans line-by-line to orient | Eye lands on what matters in ~1 second |

## **1.2 Reinforce Meaning with Visual Cues**

| **VALIDATED —  **icons and imagery measurably speed comprehension. |
| --- |

Icons, images, and small graphic markers are not decoration; they let users grasp meaning faster than text alone. Two practical applications from the sources:

- In lists and menus, pair each item with a relevant icon so the row is scannable rather than a wall of words.

- For identity (email senders, contacts), real photos and company logos beat generic colored initials — users recognize the sender and the message context instantly.

Caution: cues must clarify, not clutter. An icon that doesn't map to a well-understood meaning adds noise. When in doubt, pair the icon with a short label.

## **1.3 Use Soft, Color-Matched Shadows**

| **VALIDATED —  **consistent with current soft-UI / depth conventions. |
| --- |

Harsh, high-contrast shadows read as unprofessional. Prefer soft, diffuse shadows that add just enough depth to separate a surface from its background. Two rules:

- Keep the shadow soft and low-opacity so it blends rather than announces itself.

- Tint the shadow toward the background color. A pure-gray or black shadow on a colored (e.g. light-purple) background clashes; a background-tinted shadow preserves visual harmony.

## **1.4 Optimize and Test Presentation to Convert**

| **VALIDATED —  **A/B testing remains the backbone of conversion work. |
| --- |

How something is presented can matter as much as what it is. The source's own experiment moved a product's conversion rate from ~22% to ~48% simply by changing the presentation — swapping a plain backdrop for one that showed the product's value proposition, then adding a genuine "look inside" preview that built trust and transparency.

The durable lesson is the discipline, not the number: **form a hypothesis, test it, measure, and iterate.** Treat every high-stakes screen as testable rather than final.

## **1.5 Design to a Perceivable, Operable Floor**

| **VALIDATED —  **WCAG 2.2 AA is the current, stable benchmark (W3C Rec.; ISO/IEC 40500:2025); WCAG 3.0 remains a Working Draft with no settled contrast algorithm. The design-time subset below is uncontested practice. |
| --- |

The principles above rank elements by *importance*. This one sets the floor under them: a hierarchy no one can perceive, and a control no one can hit, has failed regardless of how well it is ranked. Four checks belong to design time, not to a later audit — each is cheap while a screen is still a mockup and expensive afterward:

- **Text contrast.** Body text ≥ 4.5:1 against its background; large text (≥ 18pt, or 14pt bold) and non-text UI — icons, input borders, focus rings — ≥ 3:1. The muted supporting labels 1.1 asks for are the usual casualty; mute by *weight and size*, not by fading toward the background.

- **Target size.** Interactive targets ≥ 24×24 CSS px, or spaced so a 24px circle centred on each does not overlap its neighbour. That is the *web pointer* floor (Level AA) and the absolute minimum anywhere. Native platform guidance is higher and expressed in its own units — iOS 44pt, Material 48dp — which are density-independent rather than convertible to CSS px; on touch surfaces design to the platform figure, not the 24px one. Primary actions in the thumb zone (2.1) should clear all of these comfortably.

- **Never color alone.** Any state, error, required field, or selection carries a second signal: an icon, a label, an underline, a shape. Test with a red-green (deutan/protan) simulator rather than by desaturating: red-green deficiency affects roughly 8% of men — mostly deuteranomaly (~5–6%), with deuteranopia and protanopia around 1% each — and it collapses red and green *toward each other*, not into gray. Grayscale approximates achromatopsia instead (~1 in 30,000), so a red/green pairing can pass a desaturation check and still fail the people the rule exists for.

- **Visible focus.** Every interactive element is reachable by keyboard and shows an obvious focus indicator when it is. Removing the browser default without replacing it is the common failure; a 2px offset outline that contrasts with both the component and its background is the safe replacement.

Two things this floor is *not*. It is not a conformance claim — meeting these four does not make a product WCAG-conformant, which requires testing this guide does not cover. And it is not a constraint on ambition: soft shadows (1.3), emotional imagery (4.3), and card layouts (2.3) all survive it intact. Only the choices that were illegible to begin with do not.

*Principle: the floor is checked while the screen is still a mockup, because that is the only point at which it is free.*

*(Where this section is the numbers behind an obligation stated elsewhere — the accessibility invariant in the Part 6 steering doc and the one-line check in the design-review skill — those name the four checks; this section is where their values live. Set the project's own baseline once, in the steering doc's Project-specifics block, and let both cite it.)*

# **Part 2 · Layout ****&**** Interaction**

How the interface is arranged for the body holding the device and the effort required to act.

## **2.1 Design for the Thumb Zone**

| **VALIDATED WITH CAVEAT —  **more critical than ever on large phones; adjust for screen size and foldables. |
| --- |

Most phones are operated one-handed with the thumb. The screen divides into an easy zone (bottom and center), a stretch zone (reachable but uncomfortable), and a hard zone (top and far corners). Place primary actions — CTAs, navigation, key buttons — in the easy zone.

Research update: as phones now routinely exceed 6.5 inches, the hard zone has grown to roughly the top third of the screen, which is exactly why bottom navigation bars and bottom-anchored primary buttons have become the dominant pattern. Two current refinements the original tip didn't cover:

- Center positions are reachable from either hand — good for the single most important action.

- On foldables and tablets over ~7 inches, single-thumb reach breaks down; plan a two-handed or split layout rather than assuming one reach model. Validate with real-device testing, not simulators.

## **2.2 Reduce Interaction Cost — Expose Value Directly**

| **VALIDATED —  **aligns with modern "show value before the ask" onboarding. |
| --- |

Interaction cost is the cognitive, physical, and time effort a user spends to reach their goal. Hiding content behind a banner ("Discover 100+ recipes →") adds a tap and a decision before any value is felt. New or uncertain users often won't pay that cost.

Instead, surface the value immediately — show a curated list of top recommendations on arrival. This delivers instant value, reduces friction, and lets you lead with your most relevant or popular content. The same instinct underlies the modern paywall guidance in Part 4: prove usefulness *before* you ask for anything.

## **2.3 Experiment with Card-Based Layouts**

| **VALIDATED —  **cards remain a standard, flexible pattern. |
| --- |

A plain vertical list of text options is clear but bland and offers little room for differentiation. Reimagining options as selectable cards adds a layer of interaction and visual richness: each card can carry a label, color, icon, or image, giving more context and making choices more digestible. Use cards when options benefit from imagery or grouping; keep simple lists when density and speed matter more (see 3.3 on category screens for the trade-offs).

## **2.4 Turn Empty States into Opportunities**

| **VALIDATED —  **empty-state design remains a recognized best practice. |
| --- |

An empty screen that only says "You have no projects" is a dead end that leaves users stuck. A well-designed empty state instead educates and activates. Combine four elements:

- A solution-oriented headline ("Start managing your projects and stay organized").

- A friendly illustration to make the screen approachable rather than barren.

- One or two actionable tips that hint at what's possible (invite teammates, set deadlines).

- A single clear CTA ("Create new project") giving a direct way to act.

## **2.5 Match the Input Method to the Moment**

| **VALIDATED —  **context-appropriate input is standard mobile-form guidance. |
| --- |

The right control depends on how often and how precisely a value is entered, not on which component looks nicer.

| **One-time / low-precision setup** | **Frequent / high-precision entry** |
| --- | --- |
| Entering weight, height, age at signup | Logging food quantity (e.g. 350 g) daily |
| Values fall in a known range | Needs speed and exact control |
| Sliders and scroll wheels feel effortless | Text fields, steppers, number inputs win |

Rule of thumb: sliders and scroll wheels for casual one-time inputs; text fields or steppers for frequent, precise, or repetitive tasks. The goal is reducing friction for the actual context of use.

# **Part 3 · Adapting to the User**

Meeting people where they are — by journey stage and by intent.

## **3.1 Personalize by User Behavior and Journey Stage**

| **VALIDATED —  **behavior-based adaptation is central to modern product design. |
| --- |

Showing every user the same screen wastes an opportunity. Adapt the experience to where the user is in their journey. Using a fitness app as an example:

- New user: keep it simple — a welcome, a prompt to set weekly goals, and a few trending programs. Enough to explore, not enough to overwhelm.

- Returning user: skip onboarding; show today's workout plan with useful details like duration and calories.

- Power user: surface advanced stats (steps, calories, heart rate), the day's plan, and personalized suggestions — the goal shifts from getting started to optimizing.

Small adaptations — personalized messages, tailored content, progress tracking — make a product feel more human and more valuable.

## **3.2 Design Search as an Act of Intent**

| **VALIDATED —  **guided / suggestion-rich search is current best practice. |
| --- |

The moment a user taps into a search bar is a moment of intent — they want something but may not know exactly what. A blank search screen puts all the work on them. A smarter screen offers subtle, ignorable support beneath the field:

- Recent searches, so users resume where they left off.

- Popular items, signalling what others find useful.

- Personalized recommendations based on past behavior.

These hints reduce friction and give unsure users a starting point, while users who know what they want can simply type past them.

## **3.3 Design Category Screens for Effortless Scanning**

| **VALIDATED —  **cohesion and scannability over decoration is standard guidance. |
| --- |

Category screens look trivial but shape how users move through a product. The source contrasts three versions and the lesson is that neither extreme wins:

- A plain text list is clean but puts all the effort on the user — every line looks the same, with no rhythm or hierarchy to guide the eye.

- A heavily image-driven version can look impressive yet fail on usability: low text contrast even with overlays, and mismatched photos (one bright, one moody, one magazine-style) that feel like random stock rather than one brand.

- The strongest version uses color-coded cards with soft solid backgrounds and clean, stylistically unified imagery, so the whole screen feels cohesive and branded and can be scanned in seconds.

The principle: visual consistency and scan-ability beat decoration. Unified imagery and balanced background colors let users understand the options at a glance — the payoff of the card pattern from 2.3 done well.

# **Part 4 · Persuasion, Pricing ****&**** Trust**

The highest-leverage — and highest-risk — section. Each principle here is validated by behavioral research, but each can be used to help users decide or to manipulate them. The line matters legally now, so an **Ethical use** note follows each.

## **4.1 Ask an Easy Question, Not a Hard One (Framing)**

| **VALIDATED —  **reframing the decision is confirmed by paywall research; timing matters most. |
| --- |

A paywall that opens with price and feature bullets forces a hard question — "Is this worth $19/month?" — on someone who has felt no value yet. Reframing to "How your free trial works" shifts the user to an easy question — "Can I try this free?" — whose answer is obviously yes.

Supporting techniques from the source: a clear trial **timeline** (today → day 5 reminder → day 7 charge); light verbs ("Start," not "Subscribe"); possessive framing ("my free trial"); and specificity that kills uncertainty ("Start in 2 taps," not "quick setup"). Show the actual product (real game characters, real screens) rather than decorative art — users can't commit to what they can't visualize.

Research refinement: recent paywall analysis finds **timing outranks visual design** — a paywall shown after a user experiences a value moment converts far better than the same paywall shown cold. Keep early paywalls dismissible.

**Ethical use: **This one is a model of ethical persuasion — the "day 5 reminder" line works precisely because it is a real, honoured promise (transparency bias). Do not borrow the framing while removing the reminder; that inverts trust into a trap.

## **4.2 Present Numbers to Reduce Doubt (Anchoring ****&**** Evaluative Ease)**

| **VALIDATED —  **anchoring and contrast are robust, well-replicated effects. |
| --- |

This section merges anchoring as it appeared in both the A/B-test and psychology sources.

Price *ranges* ($13–$17) backfire: the brain anchors on the high number and multiplies uncertainty across every option, so the easiest decision becomes no decision. Showing **one clear number per option** lets users compare in seconds (evaluative ease).

The **contrast effect** shows the same $50 protection plan feels expensive in isolation but trivial (*"**just 2.6%**"*) right after a $1,900 laptop. The first number a user sees becomes the ruler for everything after it — so control what they see first. Anchoring can also work in the user's favor: showing €129 struck through beside €89 with a −31% badge makes a fair price feel like a deal.

**Ethical use: **Anchor against real reference prices and show genuine discounts. Fabricated "was" prices and fake original values are deceptive and are actively enforced against.

## **4.3 Design for Feeling, Not Just Information (Emotional Design)**

| **VALIDATED —  **emotional/sensory design and trust signals are well supported. |
| --- |

Two screens can carry identical facts yet perform very differently. A booking screen that squeezes the villa into a thumbnail and lists fields reads like a form; the same screen with a large immersive photo, sensory copy ("Beachside escape, steps from the sand"), day-named dates with a "5 nights" badge, an all-in total on the button, and a "free cancellation" line *transports* the user instead of merely informing them.

Two reusable moves: (1) answer the user's biggest objection before they voice it — a visible "free cancellation" line defuses the top booking worry; (2) use specific, sensory language and real imagery to let people imagine the outcome. "Free cancellation," all-in pricing, and honoured reminders build trust — the through-line of this entire section.

## **4.4 Smarter Post-Purchase ****&**** Order-Tracking Design**

| **VALIDATED —  **post-purchase experience is a recognized retention lever. |
| --- |

The gap between payment and delivery is full of uncertainty, and design either reduces or amplifies that anxiety. A bare order screen dumps an order number, a plain item list, and dates, leaving the user to interpret it all. An upgraded screen opens with a confident status ("Your order is on the way"), uses icons for time window and address, humanizes the courier (photo, name, call/message buttons), and turns order history into a **visual timeline** so the current stage is obvious at a glance. Good design answers questions before they're asked.

# **Part 5 · Behavioral Psychology Principles**

Six cognitive principles that explain *why* many of the tactics above work. All were confirmed against current research; two carry important caveats.

## **5.1 Smart Defaults**

| **VALIDATED —  **default bias is robust; pair with the choice-overload caveat below. |
| --- |

Most users never change default values, and they read a sensible default as a recommendation. Replace blank forms with fields pre-filled to the most common choices, and make the outcome visible (a search button that already shows results waiting). The user's task shifts from "fill this from scratch" to "scan and adjust" — a fundamentally easier job.

**Related idea — choice overload: **the source cites the classic jam study (6 flavors outsold 24) to argue fewer choices convert better. Treat this as context-dependent, not a law.

| **CAVEAT —  **a meta-analysis of ~50 studies found the average choice-overload effect near zero. It appears mainly when options are comparable, stakes feel high, and users are non-experts; it weakens when users know the domain or options are clearly differentiated. Reduce or filter choices deliberately, and A/B test rather than assuming less is always more. |
| --- |

## **5.2 The Goal-Gradient Effect**

| **VALIDATED —  **well-established; motivation rises with proximity to a goal. |
| --- |

People move faster toward a goal as they get closer to it — and you get to choose where the starting line sits. A car-wash study found cards showing 2 of 10 stamps pre-filled were completed at nearly double the rate of blank 8-stamp cards, despite requiring the same effort.

In practice: never start a progress meter at 0%. Count something the user has already done — completing signup can be "step 1" at 20% rather than a separate event. LinkedIn's profile-strength meter is never at zero. Momentum, even a modest head start, is what separates users who finish onboarding from those who drop off.

## **5.3 Reciprocity**

| **VALIDATED —  **one of the most durable findings in persuasion research. |
| --- |

When you give first, people feel a pull to give back. Asking for signup before delivering any value ("Create an account to see your results," results blurred behind a lock) reads like holding the user's outcome hostage. Instead, deliver something genuinely useful first — a real partial report showing their score and top issues — then invite them to save the full breakdown. The signup stops feeling like a wall because value already arrived. This is the psychology beneath "expose value directly" (2.2) and modern paywall timing (4.1).

## **5.4 The IKEA ****&**** Endowment Effects**

| **VALIDATED —  **2025 meta-analyses confirm a moderate, reliable effect (Cohen's d ≈ 0.57). |
| --- |

People value things more when they've built or customized them (IKEA effect), and merely feeling ownership raises perceived value (endowment effect). A bare "email / password / signup" screen contains nothing that belongs to the user, so leaving costs nothing. Letting users build first — choose a name, palette, card style — makes the result feel theirs, and a "Continue" button reframes leaving as abandoning something they made. Duolingo has users pick a language, set a goal, and finish a first lesson before any account exists.

Boundary condition from the research: the effect depends on *successful completion*. If the build step is confusing or frustrating, attachment doesn't form — keep the effort meaningful but achievable.

## **5.5 Loss Aversion ****&**** Status-Quo Bias**

| **VALIDATED WITH CAVEAT —  **the effect is real; the aggressive "threat" execution now risks deceptive-design enforcement. |
| --- |

Losing something is felt about twice as strongly as gaining the equivalent (Kahneman), and people are wired to protect what they already have (status-quo bias). So framing an upgrade around what the user stands to *lose* tends to motivate more than framing it around what they'd gain. The source's example replaces "Upgrade now / Maybe later" with a named list of the user's own files, a countdown, and a dismiss button reading "I'll risk it."

**Ethical use — read carefully: **This is the single most abusable tactic in the guide. Loss framing is legitimate when the loss is *true* (a real trial genuinely ending, real files genuinely affected). It becomes a **dark pattern** — and a regulatory liability — the moment the countdown is fake, the "loss" is manufactured, or the dismiss option is worded to shame or confuse. Countdown timers implying false scarcity are named explicitly in FTC guidance, and confusing/guilt-worded dismiss buttons are the exact conduct penalized in recent multi-million-dollar cases. Prefer honest loss framing; never invent the loss.

## **5.6 The Contrast Effect**

| **VALIDATED —  **covered under 4.2; robust and widely applied. |
| --- |

The brain evaluates each piece of information relative to what it saw just before, which is why $50 registers as large alone but negligible after $1,900. This principle is applied in detail in 4.2 (Anchoring); it is listed here only to complete the psychology set. Rule: don't show cost in isolation — control the first number the user sees, and make sure any reference price is real.

# **The Through-Line**

Across all five sources and every validated principle, one idea recurs: **every element on the screen asks the user a question, and the question determines whether they act or hesitate.** Good design asks easy questions — by clarifying hierarchy, cutting interaction cost, meeting users where they are, and framing decisions honestly.

The persuasion principles in Parts 4 and 5 are genuinely powerful, and that is exactly why the ethical line matters. Current regulation (the FTC's 2022 dark-patterns report and enforcement through 2025–2026) has made the distinction concrete: persuasion that *helps a user decide* — clear numbers, honest reminders, real previews, true trials — builds the trust that drives lasting conversion. Persuasion that *conceals or coerces* — fake urgency, hidden information, manufactured loss — is now a measurable legal and reputational risk. Design for the safety net, not the sales pitch.

## **Sources Synthesized**

- Top 5 UX/UI Design Tips, Part 1 — hierarchy, prioritization, soft shadows, presentation testing.

- Top 5 UX/UI Design Tips, Part 2 — card layouts, interaction cost, thumb zone, empty states, visual cues.

- Top 5 UX/UI Design Tips, Part 3 — personalization, search, order tracking, category screens, input methods.

- Top 3 UX/UI A/B Tests — paywall framing, price presentation, emotional booking design.

- 6 UX Psychology Principles — smart defaults, goal gradient, reciprocity, IKEA/endowment, loss aversion, contrast.

*Research validation drew on current (2025–2026) sources including Laws of UX, Nielsen-tradition thumb-zone research (Hoober), 2025 IKEA-effect meta-analyses, the Scheibehenne choice-overload meta-analysis, and FTC dark-patterns guidance and enforcement records. Promotional content in the source transcripts (product discounts, sponsor mentions) was filtered out and excluded.*

*One section is **not** transcript-derived. §1.5 has no basis in the five sources — none of them offers accessibility guidance (the two closest moments are a passing note in the thumb-zone source that hard-to-reach controls penalize users on the go or with limited mobility, and a complaint that one category-screen mockup's text stays hard to read even behind a dark overlay — the latter is a text-contrast failure observed on a single mockup, not a stated rule, and it is captured as a scannability point in §3.3). It was written directly against W3C WCAG 2.2 (W3C Recommendation, 5 October 2023; editorial update 12 December 2024; the October 2023 text is also ISO/IEC 40500:2025), specifically SC 1.4.1 Use of Color, 1.4.3 Contrast (Minimum), 1.4.11 Non-text Contrast, 2.1.1 Keyboard, 2.4.7 Focus Visible, and 2.5.8 Target Size (Minimum). Note that SC 2.4.13 Focus Appearance and SC 2.5.5 Target Size (Enhanced) — the sources of the widely-quoted focus-indicator and 44×44 figures — are Level AAA, not AA; several secondary sources report them wrongly, which is why §1.5 frames focus through 2.1.1/2.4.7 and offers the outline spec as advice. It is included because the guide's Part 6 steering doc obligates projects to an accessibility floor, and an obligation with no stated content is not actionable.*

# **Part 6 · Bootstrap Protocol Integration**

This part lets a **Bootstrap Protocol**–certified project (v2.4.0) adopt everything above with minimal friction. It maps each part of the guide onto the protocol's existing artifact hierarchy, tells you where in the wizard it attaches, and ends with a ready-to-commit steering doc you can drop straight into *.claude/steering/*. Nothing here changes the protocol or its conformance surface — the guide composes as a project-level design reference, filling a gap the protocol leaves open (UI/UX appears today only as a few Phase 2 *tech.md* questions, and accessibility audit is explicitly out of scope).

> **Status — shipped in v2.5.0 (DS-01).** The integration described in this Part is no longer a proposal: when `design_steering_enabled` is set, the wizard emits `.claude/steering/design.md` (sourced from the protocol's frozen `docs/design.md`), and that emitted file is canonical. The guide text below is unchanged as a v2.4.0-authored record; where it reads as a proposal (“a steering doc you can drop straight into…”), read it as documentation of what now ships. See 6.6.

## **6.1 Where the Guide Lives: It****'****s a Steering Doc**

The protocol's mental model has three governing artifact types. This guide maps cleanly onto the first:

| **Artifact type** | **Bootstrap meaning** | **Does the guide fit?** |
| --- | --- | --- |
| Steering doc | What's true about the project always; read on every task; lives in .claude/steering/ | Yes — this is the right home. Design conventions are project-wide invariants, exactly what steering is for. |
| Skill | Advisory instructions the AI loads when relevant; lives in .claude/skills/ | Optional add-on — a design-review skill can cite this doc at review time (see 6.4). |
| Hook | Deterministic gate the model cannot violate; lives in .claude/hooks/ | No — design taste is guidance, not a fail-closed gate (see 6.5). |

Per your decision, the whole guide is treated as **guidance**, not enforcement. Under the protocol's own framing, CLAUDE.md-style guidance lands around 70% compliance in practice — which is the right bar for design taste. The one place that bar feels uncomfortable is the ethical guardrails in Parts 4–5; those stay as strong, unambiguous prose in the steering doc, and 6.5 explains why they're deliberately not wired as hooks.

## **6.2 Per-Archetype Applicability**

The protocol classifies every project into an archetype in Phase 0 and uses that to decide what runs. Below, each archetype gets an applicability note so the guidance never fires where it doesn't belong. "Core" means adopt the whole guide; "Partial" means the visual/interaction parts apply but persuasion/pricing may not; "Minimal" means only a small slice is relevant.

| **Archetype** | **Applies?** | **What to adopt** |
| --- | --- | --- |
| Full-stack app | Core | The entire guide. This is the primary target — all five parts apply. |
| Mobile app | Core | Entire guide; thumb-zone (2.1) and input-method (2.5) sections are especially load-bearing. Mind the foldable caveat. |
| AI / agent system | Core | Full guide wherever there's a user-facing surface (chat UI, dashboards). Onboarding, empty states, and reciprocity map directly to first-run agent UX. |
| Platform / multi-component | Core (per unit) | Apply per deployable unit that has a UI; skip for headless components. Cohesion (3.3) matters most across units. |
| Service / API | Partial | Parts 1–3 apply to any admin panel, docs site, or status page. Skip 4–5 unless there's a paywall or pricing surface. Pure backend: Minimal. |
| Library / SDK | Minimal | Visual hierarchy (1.1) applies to docs and README presentation only. Most of the guide is N/A. |
| CLI tool | Minimal | Hierarchy and clarity ideas apply to help text and output formatting; thumb-zone, cards, paywalls are N/A. |
| Data / ML pipeline | Minimal | Applies only to a dashboard or report UI if one exists; otherwise N/A. |
| Other | Depends | Use the Phase 0 synthetic profile: if the 'distribution' dimension is app-store / hosted-service / browser-store, treat as Core; if binary/embedded, treat as Minimal. |

Rule of thumb matching the protocol's own style: if the archetype has a human-facing surface, the guide is Core or Partial; if it's headless, it's Minimal or N/A. The steering doc in 6.6 states its own applicability at the top so a subagent reading it on an unrelated task knows to skip it.

## **6.3 Where It Attaches in the Wizard**

Two clean insertion points, no new phase required:

- Phase 2 (tech.md), for Full-stack and Mobile, already asks about "styling approach" and "accessibility baseline." When the operator is on a Core/Partial archetype, the wizard offers to also generate the design steering doc from this guide. This is the lowest-friction path — it rides an existing question.

- Phase 4 (principles.md) ranks 3–5 project-specific principles. A design-led project can promote one guide principle into its ranked set (e.g. "honest persuasion over short-term conversion") with a tiebreaker, so it carries principle-level weight rather than sitting only in the design doc.

For an already-certified project not re-running the wizard, adoption is a single committed file plus one CLAUDE.md pointer — see 6.5. Because the protocol commits all steering docs, the design doc is version-controlled and reviewed like code by default.

## **6.4 Optional: A Design-Review Skill**

If the project wants design checked at task time the way *code-review* checks code, add a lightweight skill under *.claude/skills/design-review/*. It stays advisory (the protocol reserves must-run gates for hooks) and simply points the reviewer at the steering doc:

---

name: design-review

description: Use when a task changes a user-facing surface —

  screens, components, onboarding, pricing, or copy. Checks the

  diff against .claude/steering/design.md.

---

 

Read .claude/steering/design.md. For each changed user-facing

surface, check: visual hierarchy, thumb-zone reachability,

empty/loading states, and — if the change touches pricing,

paywalls, or persuasive copy — the Ethical-use rules. Flag,

do not block. Recommended: invoke from an Opus session.

Wire it through Phase 7 exactly like the other skills (a *SKILL.md* plus a */design-review* command). It reads the steering doc rather than restating it — the protocol's **compose-do-not-fork** discipline applied to our own artifacts, so there's a single source of truth.

## **6.5 Guidance, Not Hooks — and Why**

The protocol's central test for any constraint: "if the model ignores this 30% of the time, is that catastrophic or annoying?" Catastrophic ⇒ hook; annoying ⇒ guidance. Applied to this guide:

- Visual and interaction principles (Parts 1–3) are aesthetic judgment. A missed soft-shadow or a sub-optimal empty state is annoying, not catastrophic. Guidance is correct; a hook would produce false positives and train operators to bypass gates — a failure mode the protocol names explicitly.

- The ethical guardrails (fake countdowns, manufactured loss, concealed information) are genuinely high-stakes — they carry legal exposure. It's tempting to make them hooks. But they can't be reliably detected by a deterministic script: whether a countdown is "fake" or a loss is "manufactured" is a semantic judgment, and the protocol is explicit that a check the model has to interpret is not a real gate. So they stay as unambiguous steering prose plus (optionally) the advisory design-review skill, which is the honest place for a semantic check.

If a project later wants a deterministic slice, the only defensible hook-able rules are narrow and literal — e.g. "no *<**meta**>* countdown element whose target timestamp is generated client-side per session" — and even those belong in the project's own CI, not the protocol's gate set. Recommended default: keep it all guidance.

## **6.6 The Design Steering Doc (Emitted)**

As of Bootstrap **v2.5.0** (DS-01), a certified project does not hand-write this doc. When `design_steering_enabled` is set, the wizard emits `.claude/steering/design.md` for you — the Phase-2 offer on Core/Partial archetypes (6.3). That emitted file is the canonical, always-current steering doc; its source of truth is the protocol's frozen `docs/design.md`, embedded byte-for-byte in the installer. The block below is an **illustrative excerpt** — it shows the doc's shape and its load-bearing invariants, not a copy to maintain in parallel with the emitter. A certified project *not* re-running the wizard adopts by copying the emitted body from `docs/design.md` (plus the one-line CLAUDE.md pointer at the end of this section); it should not copy this excerpt in its place.

# Design Steering (design.md) — *illustrative excerpt; the emitted doc is canonical*

> Applicability: user-facing surfaces only. If this task touches no UI (backend, migration, CLI-internal), skip this doc. Archetype applicability: see the guide, Part 6.2.

Source of truth for detailed rationale: The UI/UX Design Guide (docs/UIUX-Design-Guide.md). This distilled doc is always-read; the guide is the reference.

## Invariants (apply to every user-facing change)

The emitted doc states a one-paragraph rule under each heading; the eight are:

1. **Visual hierarchy** · 2. **Cut interaction cost** · 3. **Mobile reach** · 4. **No bare empty or loading states** · 5. **Match input to context** · 6. **Adapt to journey stage** · 7. **Design for scanning** · 8. **Accessible by default** — the §1.5 perceivable-and-operable floor.

## Persuasion & pricing — HONEST USE ONLY (highest within this doc)

Keep every promise you imply; show one real price per option with no fabricated 'was' prices; use loss framing only when the loss is true — fake countdowns and manufactured scarcity are FTC-enforced dark patterns. Cross-domain ties resolve in principles.md, which remains the sole ranking surface. **Tiebreaker:** honest persuasion over short-term conversion — trust is the conversion strategy.

## Project specifics  [fill during Phase 2 / at adoption]

- Styling approach: [e.g. Tailwind + design tokens]
- Component library: [e.g. shadcn/ui]
- Accessibility baseline: [e.g. WCAG 2.2 AA]
- Brand palette / shadow-tint rules: [link or values]

A matching CLAUDE.md pointer keeps the thin-invariants file honest — one line, no restatement: *"**Design: user-facing work follows .claude/steering/design.md.**"* That single pointer plus the committed doc is the entire adoption cost for a project that isn't re-running the wizard.

**Alignment summary: **the standalone guide (Parts 1–5) is unchanged; Part 6 makes it a first-class, per-archetype-aware steering doc that the wizard **emits** into any Bootstrap workspace (v2.5.0+) as one committed file plus a one-line pointer, treated as guidance throughout, with the ethical rules preserved as ranked steering prose rather than unenforceable hooks.