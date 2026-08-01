import { Code2, GitBranch, Image, LayoutGrid, Boxes, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { ThemeToggle } from '../components/common/ThemeToggle';
import { useAuthContext } from '../context/AuthContext';
import { useTheme } from '../hooks/useTheme';
import { useScrollReveal } from '../hooks/useScrollReveal';
import styles from './HomePage.module.css';

interface Feature {
  id: string;
  title: string;
  description: string;
  status: 'live' | 'coming-soon';
  icon: typeof LayoutGrid;
}

const FEATURES: Feature[] = [
  {
    id: 'canvas',
    title: 'Canvas Editor',
    description: 'Draw UML class diagrams directly on an interactive, pannable canvas.',
    status: 'live',
    icon: LayoutGrid,
  },
  {
    id: 'image',
    title: 'Image Upload → UML JSON',
    description: 'Upload a diagram image and parse it into the editor via computer vision + OCR.',
    status: 'live',
    icon: Image,
  },
  {
    id: 'codegen',
    title: 'Code Generation',
    description: 'Generate Python, Java, or JavaScript source directly from your diagram.',
    status: 'live',
    icon: Code2,
  },
  {
    id: 'reverse',
    title: 'Reverse Engineering',
    description: 'Reconstruct a class diagram or activity diagram from existing source code.',
    status: 'coming-soon',
    icon: GitBranch,
  },
];

const STEPS = [
  {
    title: 'Draw',
    description: 'Sketch your class diagram on the infinite canvas — classes, attributes, relationships.',
  },
  {
    title: 'Generate',
    description: 'Export to code in Python, Java, or JavaScript with one click — or upload a source file to reverse it.',
  },
  {
    title: 'Iterate',
    description: 'Save your work as a project, come back any time, and keep both directions in sync.',
  },
];

function FeatureCard({ feature, delay }: { feature: Feature; delay: number }) {
  const [ref, isVisible] = useScrollReveal<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={`${styles.featureCard} ${isVisible ? styles.visible : ''}`}
      style={{ transitionDelay: `${delay}ms` }}
    >
      <div className={styles.featureCardHeader}>
        <feature.icon size={18} />
        <span className={styles.featureCardTitle}>{feature.title}</span>
        <Badge tone={feature.status === 'live' ? 'live' : 'planned'}>
          {feature.status === 'live' ? 'Live' : 'Coming Soon'}
        </Badge>
      </div>
      <p className={styles.featureCardDescription}>{feature.description}</p>
    </div>
  );
}

function StepCard({ index, title, description }: { index: number; title: string; description: string }) {
  const [ref, isVisible] = useScrollReveal<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={`${styles.stepCard} ${isVisible ? styles.visible : ''}`}
      style={{ transitionDelay: `${index * 100}ms` }}
    >
      <div className={styles.stepNumber}>{index + 1}</div>
      <h3 className={styles.stepTitle}>{title}</h3>
      <p className={styles.stepDescription}>{description}</p>
    </div>
  );
}

export function HomePage() {
  const { resolvedTheme, toggle } = useTheme();
  const { isAuthenticated } = useAuthContext();

  return (
    <div className={styles.page}>
      <header className={styles.nav}>
        <div className={styles.navBrand}>
          <Boxes size={20} />
          <span>UMLFrame</span>
        </div>
        <div className={styles.navActions}>
          <ThemeToggle resolvedTheme={resolvedTheme} onToggle={toggle} />
          {isAuthenticated ? (
            <Link to="/dashboard">
              <Button variant="primary">Go to Dashboard</Button>
            </Link>
          ) : (
            <>
              <Link to="/login">
                <Button variant="ghost">Log In</Button>
              </Link>
              <Link to="/register">
                <Button variant="primary">Get Started</Button>
              </Link>
            </>
          )}
        </div>
      </header>

      <section className={styles.hero}>
        <div className={styles.heroBackdrop} aria-hidden="true" />
        <div className={styles.heroContent}>
          <h1 className={styles.heroTitle}>
            Design UML diagrams.
            <br />
            Generate real code. <span className={styles.heroAccent}>Both directions.</span>
          </h1>
          <p className={styles.heroSubtitle}>
            UMLFrame turns your class diagrams into working Python, Java, or JavaScript source —
            and reconstructs diagrams from code you already have. One canonical schema powers
            every pipeline.
          </p>
          <div className={styles.heroActions}>
            {isAuthenticated ? (
              <Link to="/dashboard">
                <Button variant="primary" size="md" icon={ArrowRight} iconPosition="right">
                  Open My Projects
                </Button>
              </Link>
            ) : (
              <>
                <Link to="/register">
                  <Button variant="primary" size="md" icon={ArrowRight} iconPosition="right">
                    Get Started Free
                  </Button>
                </Link>
                <Link to="/login">
                  <Button variant="secondary" size="md">
                    Log In
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      <section className={styles.features}>
        <h2 className={styles.sectionTitle}>Everything you need, both ways</h2>
        <div className={styles.featureGrid}>
          {FEATURES.map((feature, i) => (
            <FeatureCard key={feature.id} feature={feature} delay={i * 80} />
          ))}
        </div>
      </section>

      <section className={styles.howItWorks}>
        <h2 className={styles.sectionTitle}>How it works</h2>
        <div className={styles.stepGrid}>
          {STEPS.map((step, i) => (
            <StepCard key={step.title} index={i} title={step.title} description={step.description} />
          ))}
        </div>
      </section>

      <footer className={styles.footer}>
        <div className={styles.footerBrand}>
          <Boxes size={16} />
          <span>UMLFrame</span>
        </div>
        <p className={styles.footerCopy}>© {new Date().getFullYear()} UMLFrame. All rights reserved.</p>
      </footer>
    </div>
  );
}
