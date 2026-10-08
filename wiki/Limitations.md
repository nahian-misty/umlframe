# Limitations

Known scope limits of v1.

## Image pipelines

- Tuned for clean, programmatically drawn diagrams and the editor's own PNG export. Photographs and hand-drawn sketches are not supported.
- Two connectors that cross are fused into one blob.
- OCR can misread text; the parser repairs common slips but the result should be reviewed after import.

## Reverse engineering

- Nested and local classes are not discovered; layout is a fixed-size grid.
- Java: only the first constructor's top-level statements are scanned for instantiation.
- JavaScript: `esprima` handles ES5 and early ES6 only, with no class fields and no TypeScript. Types are recorded only when provable (JSDoc, literals, `new X()`), otherwise `any`.
- Relationship inference is best-effort and never guesses.

## Activity diagrams

- Not supported by the structuring step: fork/join, non-binary decisions, irreducible loops, multiple back edges into one header, and decisions with no findable convergence point. These return a 422.
- Code → Activity: `match`, nested `def` and `class` become one opaque action. `break` and `continue` appear as plain text without jump semantics. A `return` inside `try` goes straight to END.

## Code generation

- Output is a scaffold with stub bodies. Activity-to-code reproduces control-flow shape only; actions and conditions stay placeholders.

## Platform

- No real-time multi-user editing, and no mobile app (desktop browsers only).
