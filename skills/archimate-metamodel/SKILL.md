---
name: archimate-metamodel
description: Authoritative ArchiMate 3.2 metamodel reference (Motivation, Strategy, Business, Application, Technology layers) — valid element types per layer and the relationship-validity matrix. Use this skill before creating, validating, or reviewing any ArchiMate model element or relationship, to prevent inventing element types or illegal relationships that don't exist in the ArchiMate 3.2 specification.
version: 0.1.0-draft
source: "ArchiMate® 3.2 Specification – Reference Cards (The Open Group), N221 Personal PDF Edition, © 2022 The Open Group. ArchiMate is a registered trademark of The Open Group."
status: DRAFT — element tables complete; relationship-validity matrix pending upload; NOT YET REVIEWED by ArchiMate/EA expert. Do not treat as final.
layers_covered: [Motivation, Strategy, Business, Application, Technology]
layers_out_of_scope: [Implementation and Migration, Composite Elements]
---

# ArchiMate 3.2 Metamodel Reference

## Purpose

This skill is the ground truth for valid ArchiMate 3.2 elements and relationships. Any agent creating, editing, or validating an ArchiMate model **must** check this file before:
- Introducing a new element into a model (must appear in the Element Type Tables below).
- Drawing a relationship between two elements (must appear in the Relationship-Validity Matrix — see Section 3, pending).

If an element type or relationship is not listed here, treat it as **invalid** and do not invent one — flag it for human review instead.

## Scope note

- Covers only the 5 layers required by this task: **Motivation, Strategy, Business, Application, Technology**.
- ArchiMate 3.2 also defines an **Implementation & Migration layer** (Work Package, Deliverable, Implementation Event, Plateau, Gap) and **Composite/Generic elements** (Grouping, Location). These are **intentionally excluded** from this version — out of scope per the Epic C1 task definition, not an oversight. Add a follow-up task if the MVP later needs them.
- "Physical" elements (Equipment, Facility, Distribution Network, Material) are **not** a separate layer. Per the official Open Group reference card, they are part of the **Technology layer** and are listed there below.

---

## 1. Element Type Tables

Columns:
- **Aspect** — ArchiMate's structural classification (Active Structure / Behavior / Passive Structure for the core layers; Motivation and Strategy layers use their own aspect labels). Useful for reasoning about which relationship types are even plausible before checking the matrix.
- **Definition** — adapted from the official ArchiMate 3.2 Specification Reference Cards (The Open Group).
- **Distinguishing notes** — supplementary disambiguation (not verbatim spec text) to stop agents confusing near-identical element types (e.g., Function vs. Process, Node vs. Device).

> ⚠️ Aspect classification note for reviewer: Aspect labels for Business/Application/Technology are drawn from the ArchiMate Core Framework (Active Structure / Behavior / Passive Structure grid) and partially corroborated by row labels in the supplied course material. Please double-check these during expert review — they are structurally standard but were not individually re-verified against a specific spec page/section number for every row.

### 1.1 Motivation Layer (10 elements)

Aspect for this layer: all elements below belong to the **Motivation extension** and are not classified under Active Structure/Behavior/Passive Structure — they describe the "why" behind an architecture.

| Element | Definition | Distinguishing notes |
|---|---|---|
| Stakeholder | Represents the role of an individual, team, or organization (or classes thereof) that represents their interests in the effects of the architecture. | Stakeholder = who cares. Driver = why they care. |
| Driver | Represents an external or internal condition that motivates an organization to define its goals and implement the changes necessary to achieve them. | Driver = source of motivation. Goal = desired future state. |
| Assessment | Represents the result of an analysis of the state of affairs of the enterprise with respect to some driver. | Assessment = interpretation of a driver. Driver = the raw motivating factor. |
| Goal | Represents a high-level statement of intent, direction, or desired end state for an organization and its stakeholders. | Goal = what we want. Outcome = the measurable result of achieving it. |
| Outcome | Represents an end result, effect, or consequence of a certain state of affairs. | Outcome = measured effect. Goal = intended direction. |
| Principle | Represents a statement of intent defining a general property that applies to any system in a certain context in the architecture. | Principle = guiding rule (general, normative). Requirement = a mandatory, specific condition. |
| Requirement | Represents a statement of need defining a property that applies to a specific system as described by the architecture. | Requirement = what must be implemented. Principle = how decisions are guided. |
| Constraint | Represents a limitation on aspects of the architecture, its implementation process, or its realization. | Constraint = a limitation. Requirement = an expectation to be fulfilled. |
| Meaning | Represents the knowledge or expertise present in, or the interpretation given to, a concept in a particular context. | Meaning = interpretation. Value = benefit/importance. |
| Value | Represents the relative worth, utility, or importance of a concept. | Value = why outcomes matter. Outcome = what was achieved. |

**Mental model (motivation chain):** Stakeholders are motivated by Drivers → Drivers are analyzed via Assessments → Goals define direction → Outcomes measure success → Principles guide design → Requirements demand implementation → Constraints limit choices → Value and Meaning explain why results matter.

### 1.2 Strategy Layer (4 elements)

| Element | Aspect | Definition | Distinguishing notes |
|---|---|---|---|
| Resource | Structure | Represents an asset owned or controlled by an individual or organization. | Answers "what do we rely on?" (people, information, assets, budget). |
| Capability | Behavior | Represents an ability that an active structure element, such as an organization, person, or system, possesses. | Answers "what must we be good at?" — stable, long-term ability, independent of org structure/systems. |
| Course of Action | Behavior | Represents an approach or plan for configuring some capabilities and resources of the enterprise, undertaken to achieve a goal. | The plan/approach itself, not the ability (Capability) or the asset (Resource). |
| Value Stream | Behavior | Represents a sequence of activities that create an overall result for a customer, stakeholder, or end user. | Answers "how is value realized end-to-end?" (e.g., Apply → Verify → Approve → Deliver). |

### 1.3 Business Layer (13 elements)

| Element | Aspect | Definition | Distinguishing notes |
|---|---|---|---|
| Business Actor | Active Structure | Represents a business entity that is capable of performing behavior. | Actor = who performs work. Role = the responsibility, not the entity. |
| Business Role | Active Structure | Represents the responsibility for performing specific behavior, to which an actor can be assigned, or the part an actor plays in a particular action or event. | Role is abstract; one Actor can play multiple Roles. |
| Business Collaboration | Active Structure | Represents an aggregate of two or more business internal active structure elements that work together to perform collective behavior. | Collaboration = structural grouping. Interaction = the behavior they jointly perform. |
| Business Interface | Active Structure | Represents a point of access where a business service is made available to the environment. | Interface = access point. Service = the value delivered through it. |
| Business Process | Behavior | Represents a sequence of business behaviors that achieves a specific result such as a defined set of products or business services. | Process = flow & sequence. Function = capability grouping, not a flow. |
| Business Function | Behavior | Represents a collection of business behavior based on a chosen set of criteria (typically required business resources and/or competencies), closely aligned to an organization, but not necessarily explicitly governed by the organization. | Function = what is done (grouped by purpose). Process = how it's sequenced. |
| Business Interaction | Behavior | Represents a unit of collective business behavior performed by (a collaboration of) two or more business actors, business roles, or business collaborations. | Interaction = shared behavior. Collaboration = the shared structure performing it. |
| Business Event | Behavior | Represents a business-related state change. | Event = a trigger/instant. Process = ongoing execution. |
| Business Service | Behavior | Represents explicitly defined behavior that a business role, business actor, or business collaboration exposes to its environment. | Service = value outcome exposed externally. Process = internal execution. |
| Business Object | Passive Structure | Represents a concept used within a particular business domain. | Object = information/meaning. Representation = the format that information takes. |
| Contract | Passive Structure | Represents a formal or informal specification of an agreement between a provider and a consumer that specifies the rights and obligations associated with a product and establishes functional and non-functional parameters for interaction. | Contract = legal/business commitment; a specialization of Business Object. |
| Representation | Passive Structure | Represents a perceptible form of the information carried by a business object. | Representation = format (e.g., PDF, printed form). Business Object = the underlying meaning/content. |
| Product | Composite (passive-structure-adjacent) | Represents a coherent collection of services and/or passive structure elements, accompanied by a contract, which is offered as a whole to (internal or external) customers. | Product bundles services + objects + a contract — not a single-aspect element. |

### 1.4 Application Layer (9 elements)

| Element | Aspect | Definition | Distinguishing notes |
|---|---|---|---|
| Application Component | Active Structure | Represents an encapsulation of application functionality aligned to implementation structure, which is modular and replaceable. | Component = the system itself. Service = what it exposes. Function/Process = its internal behavior. |
| Application Collaboration | Active Structure | Represents an aggregate of two or more application internal active structure elements that work together to perform collective application behavior. | Collaboration = structural grouping. Interaction = the joint behavior performed. |
| Application Interface | Active Structure | Represents a point of access where application services are made available to a user, another application component, or a node. | Interface = access mechanism. Service = the value/functionality provided. |
| Application Function | Behavior | Represents automated behavior that can be performed by an application component. | Function = what the application can do. Process = how steps are sequenced. |
| Application Interaction | Behavior | Represents a unit of collective application behavior performed by (a collaboration of) two or more application components. | Interaction = shared behavior. Collaboration = shared structure. |
| Application Process | Behavior | Represents a sequence of application behaviors that achieves a specific result. | Process = flow & order. Function = capability, not sequence. |
| Application Event | Behavior | Represents an application state change. | Event = trigger/instant. Process = continuous execution. |
| Application Service | Behavior | Represents an explicitly defined exposed behavior. | Service = what others consume. Function = internal behavior. |
| Data Object | Passive Structure | Represents data structured for automated processing. | Data Object = logical data. Artifact (Technology layer) = the deployable file. |

### 1.5 Technology Layer (17 elements, including physical elements)

| Element | Aspect | Definition | Distinguishing notes |
|---|---|---|---|
| Node | Active Structure | Represents a computational or physical resource that hosts, manipulates, or interacts with other computational or physical resources. | Node = where things run (execution environment, physical or virtual). Device = the physical hardware itself. |
| Device | Active Structure | Represents a physical IT resource upon which system software and artifacts may be stored or deployed for execution. | Device = hardware. Node = execution environment (logical or virtual). |
| System Software | Active Structure | Represents software that provides or contributes to an environment for storing, executing, and using software or data deployed within it. | System Software = enabler software (OS, container runtime). Technology Service = the capability it exposes. |
| Technology Collaboration | Active Structure | Represents an aggregate of two or more technology internal active structure elements that work together to perform collective technology behavior. | Collaboration = structural grouping. Interaction = the joint behavior performed. |
| Technology Interface | Active Structure | Represents a point of access where technology services offered by a technology internal active structure element can be accessed. | Interface = access point. Service = the capability delivered. |
| Path | Active Structure | Represents a link between two or more technology internal active structure elements, through which these elements can exchange data, energy, or material. | A logical/physical connection distinct from a full Communication Network. |
| Communication Network | Active Structure | Represents a set of structures and behaviors that connects devices or system software for transmission, routing, and reception of data. | Network = connectivity. Node/Device = the endpoints it connects. |
| Technology Function | Behavior | Represents a collection of technology behavior that can be performed by a technology internal active structure element. | Function = what the tech can do. Process = how steps are sequenced. |
| Technology Process | Behavior | Represents a sequence of technology behaviors that achieves a specific result. | Process = flow & order. Function = capability without flow. |
| Technology Interaction | Behavior | Represents a unit of collective technology behavior performed by (a collaboration of) two or more technology internal active structure elements. | Interaction = shared behavior. Collaboration = shared structure. |
| Technology Event | Behavior | Represents a technology state change. | Event = trigger/instant. Process = ongoing execution. |
| Technology Service | Behavior | Represents an explicitly defined exposed technology behavior. | Service = what is consumed externally. Function = internal capability. |
| Artifact | Passive Structure | Represents a piece of data that is used or produced in a software development process, or by deployment and operation of an IT system. | Artifact = deployable item (binary, image, config file). Data Object (Application layer) = logical data. |
| Equipment | Active Structure | Represents one or more physical machines, tools, or instruments that can create, use, store, move, or transform materials. | Movable/operational hardware, not a location (cf. Facility) and not consumed (cf. Material). |
| Facility | Active Structure | Represents a physical structure or environment. | A fixed location/structure that hosts Equipment, people, or activity — not a device itself. |
| Distribution Network | Active Structure | Represents a physical network used to transport materials or energy. | Connects multiple locations/facilities; transports rather than performing a function itself. |
| Material | Passive Structure | Represents tangible physical matter or energy. | Consumed/transformed physical substance — not structural (cf. Equipment/Facility) and not a connector (cf. Distribution Network). |

---

## 2. Relationship Types (generic definitions)

General ArchiMate 3.2 relationship semantics (source: Open Group Reference Card, "Relationships and Relationship Connectors"). These are layer-agnostic definitions; **Section 3 below (pending) will define which element-type pairs each relationship is legal between.**

| Category | Relationship | Definition |
|---|---|---|
| Structural | Composition | Represents that an element consists of one or more other concepts. |
| Structural | Aggregation | Represents that an element combines one or more other concepts. |
| Structural | Assignment | Represents the allocation of responsibility, performance of behavior, storage, or execution. |
| Structural | Realization | Represents that an element plays a critical role in the creation, achievement, sustenance, or operation of a more abstract element. |
| Dependency | Serving | Represents that an element provides its functionality to another element. |
| Dependency | Access | Represents the ability of behavior and active structure elements to observe or act upon passive structure elements. |
| Dependency | Influence | Represents that an element affects the implementation or achievement of some motivation element. |
| Dependency | Association | Represents an unspecified relationship, or one that is not represented by another ArchiMate relationship. |
| Dynamic | Triggering | Represents a temporal or causal relationship between elements. |
| Dynamic | Flow | Represents transfer from one element to another. |
| Other | Specialization | Represents that an element is a particular kind of another element. |

---

## 3. Relationship-Validity Matrix

This matrix defines all valid relationships between source (From) and target (To) element types according to the official **ArchiMate 3.2 Specification (Appendix B.5 - Relationship Tables)**.

### Legend & Relationship Type Key
* **a** — Access
* **c** — Composition
* **f** — Flow
* **g** — Aggregation
* **i** — Assignment
* **n** — Influence
* **o** — Association (Valid between virtually all concepts)
* **r** — Realization
* **s** — Specialization
* **t** — Triggering
* **v** — Serving

---

### 3.1 Structural & Dependency Relationship Rules Summary

| Relationship | Abbr | Allowed Source Types (From) | Allowed Target Types (To) | Primary Semantics / Specification Rules |
| :--- | :---: | :--- | :--- | :--- |
| **Composition** | `c` | Any element within same layer/concept | Same concept type / structural subtype | Whole-part structural relation (e.g., Process → Sub-process, Node → Sub-node). |
| **Aggregation** | `g` | Any element within same layer/concept | Same concept type / structural subtype | Logical grouping without ownership/lifecycle linkage. |
| **Assignment** | `i` | Active Structure / Node / Behavior / Device | Behavior / Role / Active Structure | Allocation of responsibility or execution (e.g., Actor → Role, Component → App Function). |
| **Realization** | `r` | Lower Layer Element / Realizing Structure / Behavior | Abstract Concept / Service / Requirement / Goal | Fulfillment of a requirement, goal, capability, or higher-layer service. |
| **Serving** | `v` | Service / Internal Behavior / Lower Layer Structure | Active Structure / Behavior / Higher Layer Concept | Provides functionality to another element (e.g., App Service → Business Process). |
| **Access** | `a` | Behavior / Active Structure | Passive Structure (Business Object, Data Object, Artifact, Material) | Ability to create, read, write, or delete passive structure elements. |
| **Influence** | `n` | Core Concepts / Behavior / Motivation Elements | Motivation Elements (Goal, Requirement, Driver, etc.) | Describes positive (+) or negative (-) impact on motivational goals or drivers. |
| **Triggering** | `t` | Behavior Elements / Events | Behavior Elements / Events | Temporal or causal sequence between behavior elements or events. |
| **Flow** | `f` | Behavior / Active Structure Elements | Behavior / Active Structure Elements | Exchange/transfer of data, information, energy, or material between elements. |
| **Specialization**| `s` | Any Element Type | Same Element Type | Represents "is-a" taxonomy/specialization hierarchy. |
| **Association** | `o` | Any Element Type | Any Element Type | Unspecified generic relationship; valid between almost all concepts. |

---

### 3.2 Layer Permitted Pairs Matrix Lookup

#### 1. Motivation Layer Sources
* **Assessment**:
  * Motivation: Assessment (`scg, n, o`), Constraint (`n, o`), Driver (`n, o`), Goal (`n, o`), Meaning (`scg, n, o`), Outcome (`n, o`), Principle (`n, o`), Requirement (`n, o`), Stakeholder (`n, o`), Value (`n, o`).
  * All Other Layers: Association (`o`).
* **Constraint / Requirement**:
  * Motivation: Assessment (`n, o`), Constraint (`scg, n, o`), Driver (`n, o`), Goal (`r, n, o`), Meaning (`n, o`), Outcome (`r, n, o`), Principle (`r, n, o`), Requirement (`scg, n, o`), Stakeholder (`n, o`), Value (`n, o`).
  * Core Layers (Strategy / Business / App / Tech): Realizes, Influences, Associates (`r, n, o`).
* **Driver**:
  * Motivation: Assessment (`n, o`), Constraint (`n, o`), Driver (`scg, n, o`), Goal (`n, o`), Meaning (`n, o`), Outcome (`n, o`), Principle (`n, o`), Requirement (`n, o`), Stakeholder (`n, o`), Value (`n, o`).
* **Goal / Outcome / Principle / Value / Meaning**:
  * Motivation & Strategy: Realizes higher motivational targets, Influences (`r, n, o`).
* **Stakeholder**:
  * Motivation & Strategy: Assignment, Influence, Association (`i, n, o`).

#### 2. Strategy Layer Sources
* **Capability**:
  * Strategy: Capability (`scg, v, t, f, o`), Value Stream (`v, t, f, o`), Course of Action (`v, t, f, o`), Resource (`v, t, f, o`).
  * Motivation: Realizes Goal, Requirement, Outcome (`r, n, o`).
  * Business: Serves Business Function, Process, Service (`r, v, t, f, o`).
* **Resource**:
  * Strategy: Capability (`i, v, t, f, o`), Value Stream (`i, v, t, f, o`), Course of Action (`r, v, t, f, o`), Resource (`scg, v, t, f, o`).
  * Motivation: Realizes Requirement, Goal (`r, n, o`).

#### 3. Business Layer Sources
* **Business Actor / Business Role**:
  * Business: Actor/Role (`scg, v, t, f, o`), Business Process/Function (`i, v, t, f, o`), Business Interface (`c, g, i, v, t, f, o`), Business Service (`i, r, v, t, f, o`).
  * Strategy: Realizes/Assigned to Capability & Resource (`r, o`).
  * Application: Serves App Component, App Service (`v, t, f, o`).
* **Business Process / Business Function / Business Interaction**:
  * Business: Process/Function (`scg, v, t, f, o`), Business Service (`r, v, t, f, o`), Business Object (`a, o`).
  * Application/Technology: Accesses Data Objects & Artifacts (`a, o`); Served by App/Tech Services (`v, t, f, o`).
* **Business Service**:
  * Business: Business Process, Role, Actor (`v, t, f, o`).
  * Strategy: Realizes Capability, Value Stream (`r, o`).
  * Motivation: Realizes Requirement, Goal (`r, n, o`).
* **Business Object / Contract / Product / Representation**:
  * Business: Contract, Product, Representation (`scg, o`). Accesses/Realizes Business Objects (`a, r, o`).

#### 4. Application Layer Sources
* **Application Component / Application Collaboration**:
  * Application: Component/Collaboration (`scg, v, t, f, o`), App Function/Process (`i, v, t, f, o`), App Interface (`c, g, i, v, t, f, o`), App Service (`i, r, v, t, f, o`), Data Object (`a, o`).
  * Business: Serves Business Actor, Role, Process, Function, Service (`v, t, f, o`).
  * Technology: Realized by / Deployed on Node, Device, System Software (`r, o`).
* **Application Process / Application Function**:
  * Application: Function/Process (`scg, v, t, f, o`), App Service (`r, v, t, f, o`), Data Object (`a, o`).
  * Business: Serves Business Process, Function (`v, t, f, o`).
* **Application Service**:
  * Application: App Process, Function (`v, t, f, o`).
  * Business: Serves Business Process, Business Role, Business Actor (`v, t, f, o`).
* **Data Object**:
  * Application: Data Object (`scg, o`).
  * Business: Realizes Business Object, Contract (`r, o`).

#### 5. Technology & Physical Layer Sources
* **Node / Device / System Software / Path / Communication Network**:
  * Technology: Node/Device/Software (`scg, i, r, v, t, f, o`), Tech Function/Process (`i, v, t, f, o`), Tech Interface (`c, g, i, v, t, f, o`), Tech Service (`i, r, v, t, f, o`), Artifact (`a, o`).
  * Application: Hosts / Serves App Component, App Process, App Service (`v, t, f, o`).
  * Business: Serves Business Actor, Role, Process (`v, t, f, o`).
* **Technology Process / Technology Function / Technology Interaction**:
  * Technology: Process/Function (`scg, v, t, f, o`), Tech Service (`r, v, t, f, o`), Artifact (`a, o`).
  * Application: Serves App Function, Process (`v, t, f, o`).
* **Technology Service**:
  * Technology & Application: Serves Tech/App Functions, Processes, Components (`v, t, f, o`).
* **Artifact**:
  * Technology: Artifact (`scg, r, o`).
  * Application: Realizes Data Object (`r, o`).
* **Equipment / Facility / Distribution Network**:
  * Physical: Equipment/Facility/Distribution Network (`scg, i, r, v, t, f, o`), Material (`a, o`).
  * Business & Technology: Serves Node, Device, Business Actor, Business Process (`v, t, f, o`).
* **Material**:
  * Physical: Material (`scg, r, o`). Realizes/Accesses passive physical elements (`a, r, o`).




## 4. Review status

- [ ] Element tables checked against official ArchiMate 3.2 spec (traceability)
- [ ] Relationship-validity matrix added
- [ ] Relationship-validity matrix checked against official spec
- [ ] Signed off by ArchiMate/EA expert — **name/date TBD**
