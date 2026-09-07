import type { Visibility } from '../../types/uml';

const VISIBILITY_SYMBOLS: Record<Visibility, string> = {
  public: '+',
  private: '-',
  protected: '#',
  package: '~',
};

export function visibilitySymbol(visibility: Visibility): string {
  return VISIBILITY_SYMBOLS[visibility];
}
