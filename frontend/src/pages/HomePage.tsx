import { ArrowRight, Boxes, Code2, GitBranch, Image, LayoutGrid, Workflow } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Button } from '../components/common/Button';
import { ThemeToggle } from '../components/common/ThemeToggle';
import { useAuthContext } from '../context/AuthContext';
import { useTheme } from '../hooks/useTheme';
import { useScrollReveal } from '../hooks/useScrollReveal';
import styles from './HomePage.module.css';

interface Feature {
  id: string;
  title: string;
  description: string;
  icon: typeof LayoutGrid;
}

const FEATURES: Feature[] = [
  {
    id: 'canvas',
    title: 'Canvas Editor',
    description:
      'Draw UML class diagrams and activity diagrams directly on an interactive, pannable canvas.',
    icon: LayoutGrid,
  },
  {
    id: 'image',
    title: 'Image Upload → Diagram',
    description:
      'Upload a class or activity diagram image and parse it into the editor via computer vision + OCR.',
    icon: Image,
  },
  {
    id: 'codegen',
    title: 'Code Generation',
    description:
      'Generate Python, Java, or JavaScript source from a class diagram, or a structured function from an activity diagram.',
    icon: Code2,
  },
  {
    id: 'reverse',
    title: 'Reverse Engineering',
    description: 'Reconstruct a class diagram from existing Python, Java, or JavaScript source.',
    icon: GitBranch,
  },
  {
    id: 'activity-draw',
    title: 'Activity Diagram Canvas',
    description:
      'Draw start, action, decision, fork/join and end nodes, label the guards, and let auto-layout tidy diagrams that arrive from code or an image.',
    icon: Workflow,
  },
  {
    id: 'activity-code',
    title: 'Activity ↔ Code',
    description:
      'Turn an activity diagram into a function with real if/else and while structure (action bodies stay TODO placeholders), or render the control flow of any method as an activity diagram.',
    icon: GitBranch,
  },
];

const STEPS = [
  {
    title: 'Draw',
    description:
      'Sketch a class or activity diagram on the infinite canvas - classes, relationships, actions, decisions.',
  },
  {
    title: 'Generate',
    description:
      'Export to code in Python, Java, or JavaScript with one click - or paste source code to reverse it into a diagram.',
  },
  {
    title: 'Iterate',
    description:
      'Save your work as a project, come back any time, and keep both directions in sync.',
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
      </div>
      <p className={styles.featureCardDescription}>{feature.description}</p>
    </div>
  );
}

function StepCard({
  index,
  title,
  description,
}: {
  index: number;
  title: string;
  description: string;
}) {
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
            UMLFrame turns your class and activity diagrams into working Python, Java, or JavaScript
            source — and reconstructs class diagrams and activity flows from code you already have.
            One canonical schema powers every pipeline.
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
            <StepCard
              key={step.title}
              index={i}
              title={step.title}
              description={step.description}
            />
          ))}
        </div>
      </section>

      <footer className={styles.footer}>
        <div className={styles.footerBrand}>
          <Boxes size={16} />
          <span>UMLFrame</span>
        </div>
        <p className={styles.footerCopy}>© {new Date().getFullYear()} UMLFrame.</p>
      </footer>
    </div>
  );
}
