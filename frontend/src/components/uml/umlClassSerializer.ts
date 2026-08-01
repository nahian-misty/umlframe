import type { Attribute, Method, UmlClass } from '../../types/uml';
import type { AttributeState, MethodState, UmlClassState } from '../../types/diagram';

/**
 * Per-class mapping between internal editor state and the Unified UML JSON
 * wire format. Pure, no network access — matches the uml/ folder's rule that
 * this module never talks to the backend directly.
 */

function attributeToWire(a: AttributeState): Attribute {
  return {
    name: a.name,
    datatype: a.datatype,
    visibility: a.visibility,
    default_value: a.defaultValue,
    static: a.static,
    final: a.final,
  };
}

function attributeFromWire(a: Attribute, id: string): AttributeState {
  return {
    id,
    name: a.name,
    datatype: a.datatype,
    visibility: a.visibility,
    defaultValue: a.default_value,
    static: a.static,
    final: a.final,
  };
}

function methodToWire(m: MethodState): Method {
  return {
    name: m.name,
    visibility: m.visibility,
    parameters: m.parameters,
    return_type: m.returnType,
    static: m.static,
    abstract: m.abstract,
  };
}

function methodFromWire(m: Method, id: string): MethodState {
  return {
    id,
    name: m.name,
    visibility: m.visibility,
    parameters: m.parameters,
    returnType: m.return_type,
    static: m.static,
    abstract: m.abstract,
  };
}

export function classToWire(c: UmlClassState): UmlClass {
  return {
    id: c.id,
    name: c.name,
    attributes: c.attributes.map(attributeToWire),
    methods: c.methods.map(methodToWire),
    position: c.position,
    size: c.size,
  };
}

export function classFromWire(c: UmlClass): UmlClassState {
  return {
    id: c.id,
    name: c.name,
    attributes: c.attributes.map((a, i) => attributeFromWire(a, `${c.id}_attr_${i}`)),
    methods: c.methods.map((m, i) => methodFromWire(m, `${c.id}_method_${i}`)),
    position: c.position,
    size: c.size,
  };
}
