# UMLFrame – Project Specification & Implementation Plan

> **Purpose:**  
Build a bidirectional UML ↔ Code Engineering platform that allows users to visually create UML Class Diagrams, generate source code from them, and reverse engineer existing source code back into UML diagrams.

This document serves as the master project specification for Claude Code to generate the actual `CLAUDE.md` and guide implementation.

---

# Project Vision

The project consists of **two complete pipelines** sharing a common intermediate representation.

```
                    FORWARD PIPELINE

          UML Canvas (Frontend)
                    │
                    ▼
           Export Diagram Image
                    │
                    ▼
        Computer Vision + OCR Pipeline
                    │
                    ▼
             Unified UML JSON
                    │
                    ▼
            Template Code Generator
                    │
                    ▼
        Python / Java / JavaScript Code



                    REVERSE PIPELINE

        User Selected Source Files
                    │
                    ▼
             Language AST Parser
                    │
                    ▼
             Unified UML JSON
                    │
                    ▼
          Mermaid Diagram Generator
                    │
                    ▼
            UML Class Diagram
```

The most important architectural decision is:

> **Everything revolves around one unified UML JSON schema.**

Every module either produces this JSON or consumes it.

---

# Overall Goals

The system should allow users to:

- Draw UML class diagrams
- Add classes
- Add attributes
- Add methods
- Create relationships
- Export diagrams
- Convert diagrams into source code
- Reverse engineer existing projects
- Generate UML from source code

---

# High Level Architecture

```
Frontend (React)

├── UML Canvas
├── Shape Library
├── Property Inspector
├── Toolbar
├── Export Module
└── Diagram Viewer


Backend (Python)

├── Image Processing
├── OCR
├── Diagram Parser
├── UML JSON Generator
├── Code Generator
├── AST Parser
├── Mermaid Generator
└── API Layer
```

---

# Core Principle

The application should never directly convert:

Diagram → Code

or

Code → Diagram

Instead every transformation must go through:

```
Unified UML JSON
```

because it becomes the single source of truth.

---

# Forward Pipeline

---

## Phase 1 — UML Editor

### Goal

Build an interactive diagram editor.

The editor should function similarly to tools such as:

- Draw.io
- Excalidraw
- Visual Paradigm
- StarUML (basic subset)

---

## Features

### Infinite Canvas

Support:

- pan
- zoom
- grid
- snapping

---

### Shape Library

Initial supported objects:

- Rectangle
- Circle
- Diamond
- Line
- Arrow

Although the primary focus is UML Class Diagrams, designing generic shapes makes the editor extensible.

---

### UML Class Component

Each UML class consists of three compartments.

```
+----------------------+
| User                 |
+----------------------+
| - email : String     |
| - age : int          |
+----------------------+
| + login()            |
| + logout()           |
+----------------------+
```

Each compartment should be editable independently.

---

### Text Editing

Support:

- class name
- attributes
- methods

Examples

```
User

email : String

login()

logout()
```

---

### Relationship Tools

Support drawing:

Association

```
User -------- Order
```

Aggregation

```
User ◇------ Address
```

Composition

```
User ◆------ Address
```

Inheritance

```
User △------ Person
```

Dependency

```
User -----> Logger
```

Relationships should store metadata rather than only visual lines.

---

### Selection

Support:

- single select
- multi select
- drag
- resize
- delete
- duplicate

---

### Export

Support exporting the canvas as:

- PNG
- JPEG (optional)

The exported image becomes the input for the computer vision pipeline.

---

# Phase 2 — Image Processing Pipeline

Goal:

Convert exported UML image into structured information.

Pipeline:

```
Image

↓

Preprocessing

↓

Shape Detection

↓

OCR

↓

Object Matching

↓

JSON
```

---

## Image Preprocessing

Tasks

- grayscale conversion
- thresholding
- denoising
- edge enhancement
- contour extraction

Purpose

Produce clean binary images for reliable OCR and rectangle detection.

---

## Shape Detection

Detect:

- class rectangles
- relationship arrows
- arrow heads
- diamonds
- circles
- connectors

Output:

Coordinates of every detected object.

Example

```
Rectangle

x
y
width
height
```

---

## OCR

Run OCR only inside detected class boxes.

Extract:

- class names
- attributes
- methods

Expected OCR output

```
User

email : String

login()
```

---

## Parsing OCR

Convert raw OCR text into structured components.

Example

Input

```
User
email:String
password:String
login()
logout()
```

Output

```
Class

Attributes

Methods
```

---

## Relationship Matching

Using detected lines:

Determine

- source class
- destination class
- relationship type

---

## Output

Produce Unified UML JSON.

---

# Phase 3 — Unified UML JSON

This is the most important component.

Every module must use exactly the same schema.

Suggested structure

```json
{
  "classes": [
    {
      "id": "class_1",
      "name": "User",
      "attributes": [],
      "methods": [],
      "position": {},
      "size": {}
    }
  ],
  "relationships": []
}
```

---

## Class Object

Contains

- id
- name
- attributes
- methods
- coordinates
- dimensions

---

## Attribute Object

Contains

- name
- datatype
- visibility
- default value
- static
- final

---

## Method Object

Contains

- name
- visibility
- parameters
- return type
- static
- abstract

---

## Relationship Object

Contains

- source
- destination
- type
- multiplicity
- label

---

# Phase 4 — Code Generation

Input

```
Unified UML JSON
```

Output

Language source code.

Supported languages

- Python
- Java
- JavaScript (ES6 classes)

Future

- TypeScript
- C#
- C++
- Go

---

## Architecture

```
JSON

↓

Language Mapper

↓

Template Engine

↓

Generated Code
```

---

## Template Engine

Each language has its own templates.

Example

```
templates/

python/

class.j2

java/

class.j2

javascript/

class.j2
```

---

## Language Mapping

Datatype mapping

```
String

↓

Python

str

↓

Java

String

↓

JavaScript

string
```

---

## Generated Files

One file per class.

Example

```
User.py

Order.py

Product.py
```

---

# Reverse Engineering Pipeline

---

# Phase 5 — Source Code Parsing

Goal

Convert existing projects into UML JSON.

Supported languages

- Python
- Java
- JavaScript

---

## User Workflow

User selects:

- file
- folder
- project

Backend parses only selected files.

---

## Parsing

Python

↓

Python AST

Java

↓

JavaParser

JavaScript

↓

Babel / Acorn / Esprima

---

## Extract

For every class

Extract

- class name
- attributes
- methods
- inheritance
- interfaces
- imports
- relationships

---

## Relationship Detection

Infer

Association

Composition

Aggregation

Inheritance

Dependency

---

## Output

Unified UML JSON

---

# Phase 6 — Diagram Generation

Input

Unified UML JSON

Output

Mermaid Class Diagram

Pipeline

```
JSON

↓

Mermaid Generator

↓

Mermaid Text

↓

Diagram Renderer
```

---

## Mermaid Output

Example

```
classDiagram

class User{
String email
login()
}

User --> Order
```

---

## Rendering

Use MermaidJS to render diagrams.

---

# API Design

Suggested backend endpoints

```
POST /api/export-image

POST /api/image-to-json

POST /api/generate-code

POST /api/reverse

POST /api/json-to-mermaid

GET /api/templates

GET /api/languages
```

---

# Suggested Project Structure

```
umlframe/

frontend/

components/

canvas/

toolbar/

uml/

hooks/

pages/

backend/

api/

cv/

ocr/

parser/

json/

generator/

templates/

python/

java/

javascript/

reverse/

python/

java/

javascript/

mermaid/

shared/

schema/

tests/

docs/
```

---

# Development Roadmap

## Milestone 1

Frontend UML editor

Deliverables

- Canvas
- Shapes
- UML Class boxes
- Relationships
- Export image

---

## Milestone 2

Image processing

Deliverables

- OpenCV preprocessing
- Shape detection
- OCR
- JSON generation

---

## Milestone 3

Unified UML JSON

Deliverables

- Stable schema
- Validation
- Serialization

---

## Milestone 4

Code generation

Deliverables

- Jinja2 templates
- Python generation
- Java generation
- JavaScript generation

---

## Milestone 5

Reverse engineering

Deliverables

- Python parser
- Java parser
- JavaScript parser
- Relationship inference

---

## Milestone 6

Diagram generation

Deliverables

- Mermaid generator
- Mermaid rendering
- Diagram preview

---

## Milestone 7

Full integration

Pipeline A

```
Canvas

↓

Export Image

↓

OpenCV

↓

OCR

↓

Unified UML JSON

↓

Template Engine

↓

Python / Java / JavaScript Code
```

Pipeline B

```
Source Code

↓

AST

↓

Unified UML JSON

↓

Mermaid Generator

↓

UML Diagram
```

---

# Non-Functional Requirements

## Modularity

Each module should be independently testable.

No module should depend directly on another except through defined interfaces.

---

## Extensibility

Adding a new language should require only:

- AST parser
- Language mapping
- Templates

The rest of the pipeline should remain unchanged.

---

## Maintainability

- Strong separation of concerns
- Clear folder organization
- Typed interfaces where possible
- Shared JSON schema
- Reusable components

---

## Future Enhancements (Out of Scope for Initial Version)

- Plugin architecture
- Real-time collaboration
- Authentication and user accounts
- Project persistence
- Database storage
- Spring Boot generation
- FastAPI generation
- NestJS generation
- TypeScript support
- C# support
- C++ support
- AI-assisted UML recognition
- AI-assisted code generation
- CI/CD pipeline
- Celery workers
- Redis task queue
- ResNet-based object detection
- Deployment and containerization

---

# Definition of Done

The MVP is considered complete when both pipelines work end-to-end.

### Forward Pipeline

```
User Draws Diagram
        ↓
Export Image
        ↓
Image Processing
        ↓
Unified UML JSON
        ↓
Generate Python / Java / JavaScript
```

### Reverse Pipeline

```
User Selects Code Files
        ↓
AST Parsing
        ↓
Unified UML JSON
        ↓
Mermaid Generation
        ↓
Rendered UML Diagram
```

The Unified UML JSON must be the canonical representation shared by every subsystem, ensuring that any frontend, parser, generator, or future extension can interoperate without direct coupling.