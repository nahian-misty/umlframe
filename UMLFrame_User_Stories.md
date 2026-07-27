# 2. User Story

## 2.1 Diagram Creation

A user can create a UML class diagram on an infinite canvas by drawing shapes
such as rectangles, circles, diamonds, lines, and arrows. The canvas supports
pan, zoom, and snap-to-grid so that shapes align cleanly as they are placed.
A user can add a UML class box to the canvas and edit its three
compartments — name, attributes, and methods — directly inline. For each
attribute, the user specifies a name, data type, and visibility (public,
private, protected, or package); for each method, the user specifies a name,
visibility, parameter list, and return type. The user can select shapes
individually or in groups, drag them to reposition, resize them, duplicate
them, or delete them from the canvas.

## 2.2 Relationship Modeling

A user can connect two class boxes with a relationship by selecting a
relationship tool from the toolbar — association, aggregation, composition,
inheritance, or dependency. When a relationship is drawn between a source and
destination class, the user can specify multiplicity (e.g., "1", "*",
"0..1") on each end and an optional label describing the relationship. If a
user attempts to draw a relationship without a valid source or destination
class, the system does not create the relationship and the canvas remains
unchanged.

## 2.3 Diagram Export and Image Recognition

A user can export the current canvas as a PNG image. If a user instead
uploads a hand-drawn or previously exported UML diagram image, the system
preprocesses the image (grayscale, threshold, denoise, edge detection),
detects rectangles and shape outlines, and runs OCR scoped to each detected
bounding box to extract class names, attributes, and methods. The system also
detects relationship lines and arrow/diamond markers and matches them to
their source and destination shapes. The extracted structure is converted
into the Unified UML JSON representation and returned to the user; if OCR
text is ambiguous or noisy (e.g., "l" mistaken for "1"), the parser tolerates
common OCR errors rather than failing outright.

## 2.4 Code Generation

A user can select a Unified UML JSON diagram and choose a target
language — Python, Java, or JavaScript — to generate source code. The system
maps each language-neutral attribute and method type to the target
language's equivalent type, then renders one output file per class using the
language's code template. If the diagram is invalid (e.g., a relationship
references a class ID that doesn't exist), the system rejects the request
with a structured validation error rather than generating incomplete code.
The user receives a response mapping each generated filename to its file
content; the generated code contains method stubs, not full implementations,
since it is intended as a scaffold rather than production-ready code.

## 2.5 Reverse Engineering

A user can select existing source files in a supported language and submit
them for reverse engineering. The system parses the selected files' abstract
syntax tree, extracts classes, attributes, and methods, and infers
relationships (association, aggregation, composition, inheritance,
dependency) wherever they can be proven directly from the code. Constructs
with no UML equivalent are discarded rather than approximated. The result is
returned to the user as Unified UML JSON, ready to be rendered or further
edited.

## 2.6 Diagram Rendering

A user can convert a Unified UML JSON document into a Mermaid class diagram.
The system translates every class, attribute, method, and relationship type
into valid Mermaid `classDiagram` syntax. The user can preview the rendered
diagram directly in the frontend's diagram preview panel, allowing them to
visually confirm that reverse-engineered code matches their expectations
before making further edits.
