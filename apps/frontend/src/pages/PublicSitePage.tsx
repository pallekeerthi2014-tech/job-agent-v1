import { useEffect, useState } from "react";
import {
  ArrowRight,
  Award,
  BarChart3,
  Building,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  FileText,
  Instagram,
  Linkedin,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  ShieldCheck,
  Star,
  TrendingUp,
  Twitter,
  Users
} from "lucide-react";

import { PublicChatbot } from "./PublicChatbot";

type PublicPage = "home" | "success-stories" | "contact";

type PublicSitePageProps = {
  page: PublicPage;
  onNavigate: (path: string) => void;
};

const services = [
  {
    title: "Business Analyst & Data Analyst Training",
    copy: "Hands-on BA/DA programs covering SDLC, Agile, SQL, dashboards, domain knowledge, case studies, and interview preparation.",
    bullets: [
      "Comprehensive training programs designed for BA/DA roles",
      "Hands-on project work, case studies, and interview prep",
      "Focus on SDLC, Agile, SQL, Data Visualization, and domain knowledge"
    ]
  },
  {
    title: "Career Placement Support",
    copy: "Resume building, LinkedIn optimization, recruiter visibility, mock interviews, and guided application strategy.",
    bullets: [
      "Resume building and profile optimization",
      "LinkedIn branding and recruiter visibility tips",
      "Mock interviews and proxy interview support",
      "Connecting candidates with 50+ partner companies"
    ]
  },
  {
    title: "Certification Guidance",
    copy: "Support choosing and preparing for credentials across CBAP, CCBA, Tableau, Power BI, SQL, Agile, and Scrum.",
    bullets: [
      "Support choosing relevant certifications",
      "Assistance with preparation resources and timelines"
    ]
  },
  {
    title: "End-to-End Job Support",
    copy: "Guidance from applications through onboarding, background check readiness, and first-project transition support.",
    bullets: [
      "Guidance from job applications to onboarding",
      "Assistance during the first month of the project",
      "Background check readiness and compliance support"
    ]
  }
];

const expertise = [
  {
    icon: FileText,
    title: "Application Strategy",
    description: "Smart, targeted applications to roles that align with your BA/DA skills using data-driven insights."
  },
  {
    icon: Users,
    title: "Resume & LinkedIn Makeover",
    description: "Build a professional brand that gets noticed through tailored resumes and optimized LinkedIn profiles."
  },
  {
    icon: MessageCircle,
    title: "Interview Assistance",
    description: "Prepare with real-world BA/DA case studies, mock interviews, and role-specific prep sessions."
  },
  {
    icon: ShieldCheck,
    title: "Verification Support",
    description: "Guidance for background checks and smooth onboarding with employers."
  }
];

const stories = [
  {
    role: "Senior Business Analyst",
    company: "JPMorgan Chase & Co.",
    industry: "Financial Services",
    quote: "Strategic guidance helped me secure a Senior BA role with a major salary increase."
  },
  {
    role: "Data Analyst",
    company: "Johnson & Johnson",
    industry: "Healthcare",
    quote: "The interview preparation helped me move from reporting work into deeper data analysis."
  },
  {
    role: "Business Intelligence Analyst",
    company: "McKinsey & Company",
    industry: "Consulting",
    quote: "The LinkedIn and resume work helped recruiters understand my value much faster."
  },
  {
    role: "Senior Data Analyst",
    company: "Google",
    industry: "Technology",
    quote: "Technical interview preparation made complex data conversations feel natural."
  },
  {
    role: "Business Analyst",
    company: "Amazon",
    industry: "E-commerce",
    quote: "The support was comprehensive from application strategy to offer stage."
  },
  {
    role: "Data Scientist",
    company: "Pfizer",
    industry: "Pharmaceuticals",
    quote: "They helped me translate analytics experience into a stronger data science profile."
  }
];

const testimonials = [
  {
    quote: "With their comprehensive prep, I landed my first Business Analyst role in finance within 45 days.",
    role: "Business Analyst at Goldman Sachs",
    rating: 5
  },
  {
    quote: "They helped me transition from reporting to a Data Analyst role in healthcare seamlessly.",
    role: "Data Analyst at Kaiser Permanente",
    rating: 4.5
  },
  {
    quote: "The interview preparation was game-changing. I felt confident in every technical discussion.",
    role: "Senior BA at McKinsey & Company",
    rating: 5
  }
];

const industryHighlights = [
  { icon: Users, title: "Business Analytics", description: "Placing analysts in top business roles worldwide." },
  { icon: TrendingUp, title: "Data Science", description: "Empowering data professionals to scale their careers." },
  { icon: Award, title: "Consulting", description: "Connecting consultants to high-impact opportunities." },
  { icon: Building, title: "Technology", description: "Helping tech analysts achieve their dream roles." }
];

function CounterAnimation({ end, suffix = "", duration = 2000 }: { end: number; suffix?: string; duration?: number }) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime = 0;
    let animationFrame = 0;
    const animate = (currentTime: number) => {
      if (startTime === 0) startTime = currentTime;
      const progress = Math.min((currentTime - startTime) / duration, 1);
      setCount(Math.floor(progress * end));
      if (progress < 1) animationFrame = requestAnimationFrame(animate);
    };
    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [duration, end]);

  return <>{count}{suffix}</>;
}

function PublicHeader({ activePage, onNavigate }: { activePage: PublicPage; onNavigate: (path: string) => void }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const navItems = [
    { path: "/", label: "Home", page: "home" as const },
    { path: "/success-stories", label: "Success Stories", page: "success-stories" as const },
    { path: "/contact", label: "Contact", page: "contact" as const }
  ];

  function go(path: string) {
    setMenuOpen(false);
    onNavigate(path);
  }

  return (
    <header className={`public-header ${scrolled ? "public-header-scrolled" : ""}`}>
      <div className="public-nav">
        <button className="public-brand" onClick={() => go("/")} type="button">
          <img src="/brand/think-success-logo.png" alt="Think Success Consulting" />
          <span>Think Success Consulting</span>
        </button>

        <nav className="public-nav-links">
          {navItems.map((item) => (
            <button
              key={item.path}
              className={activePage === item.page ? "public-nav-active" : ""}
              onClick={() => go(item.path)}
              type="button"
            >
              {item.label}
            </button>
          ))}
          <button className="public-login-button" onClick={() => go("/login")} type="button">
            Portal Login
          </button>
        </nav>

        <button className="public-menu-button" onClick={() => setMenuOpen((value) => !value)} type="button">
          {menuOpen ? "Close" : "Menu"}
        </button>
      </div>

      {menuOpen ? (
        <nav className="public-mobile-nav">
          {navItems.map((item) => (
            <button key={item.path} onClick={() => go(item.path)} type="button">
              {item.label}
            </button>
          ))}
          <button className="public-login-button" onClick={() => go("/login")} type="button">
            Portal Login
          </button>
        </nav>
      ) : null}
    </header>
  );
}

function PublicFooter({ onNavigate }: { onNavigate: (path: string) => void }) {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="public-footer">
      <div className="public-footer-grid">
        <div className="public-footer-brand">
          <button onClick={() => onNavigate("/")} type="button">
            <img src="/brand/think-success-logo.png" alt="Think Success Logo" />
            <strong>Think Success Consulting</strong>
          </button>
          <span>Empowering Analysts to Excel</span>
          <p>Specialized consultancy helping Business and Data Analysts secure their dream careers through comprehensive support and expert guidance.</p>
        </div>

        <div>
          <h3>Quick Links</h3>
          <div className="public-footer-stack">
            <button onClick={() => onNavigate("/")} type="button">Home</button>
            <button onClick={() => onNavigate("/success-stories")} type="button">Success Stories</button>
            <button onClick={() => onNavigate("/contact")} type="button">Contact Us</button>
            <button onClick={() => onNavigate("/login")} type="button">Portal Login</button>
          </div>
        </div>

        <div>
          <h3>Our Services</h3>
          <ul className="public-footer-list">
            <li>Application Strategy</li>
            <li>Resume & LinkedIn Makeover</li>
            <li>Interview Assistance</li>
            <li>Verification Support</li>
          </ul>
        </div>

        <div>
          <h3>Get in Touch</h3>
          <div className="public-footer-contact">
            <span><Mail size={16} /> thinksuccessITconsultants@gmail.com</span>
            <span><Phone size={16} /> +91 80084 38080</span>
            <span><MapPin size={16} /> North Carolina, Chicago, Hyderabad</span>
            <span><Clock size={16} /> Mon-Fri, 9:00 AM-6:00 PM IST</span>
          </div>
        </div>
      </div>

      <div className="public-footer-bottom">
        <p>© {currentYear} Think Success Consulting. All rights reserved.</p>
        <div className="public-social-row">
          <a href="#" aria-label="LinkedIn"><Linkedin size={20} /></a>
          <a href="#" aria-label="Twitter"><Twitter size={20} /></a>
          <a href="#" aria-label="Instagram"><Instagram size={20} /></a>
        </div>
      </div>
    </footer>
  );
}

function HomePage({ onNavigate }: { onNavigate: (path: string) => void }) {
  const [testimonialIndex, setTestimonialIndex] = useState(0);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setTestimonialIndex((index) => (index + 1) % testimonials.length);
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <>
      <section className="public-hero">
        <div className="public-hero-copy">
          <p className="eyebrow">Career consulting for analysts</p>
          <h1>Shaping careers in Business and Data Analysis</h1>
          <p>
            From applications to interviews to background checks, we guide analysts at every step of their career journey.
          </p>
          <div className="public-hero-actions">
            <button className="public-primary-cta" onClick={() => onNavigate("/contact")} type="button">
              Start My Career Journey
              <ArrowRight size={18} />
            </button>
            <button className="public-secondary-cta" onClick={() => onNavigate("/success-stories")} type="button">
              View Success Stories
            </button>
          </div>
        </div>

        <div className="public-hero-card" aria-label="Think Success results">
          <div>
            <strong>90%</strong>
            <span>Success Rate</span>
          </div>
          <div className="public-stat-grid">
            <span><b>200+</b> Analysts Placed</span>
            <span><b>50+</b> Partner Companies</span>
            <span><b>45</b> Avg. Days to Hire</span>
            <span><b>24h</b> Response Time</span>
          </div>
        </div>
      </section>

      <section className="public-section">
        <div className="public-section-heading">
          <p className="eyebrow">Our Services</p>
          <h2>Support for every step of the analyst career path</h2>
        </div>
        <div className="public-service-grid">
          {services.map((service) => (
            <article className="public-service-card" key={service.title}>
              <h3>{service.title}</h3>
              <ul>
                {service.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="public-section public-muted-section" id="expertise">
        <div className="public-section-heading">
          <p className="eyebrow">Our Expertise</p>
          <h2>Comprehensive support designed for analyst careers</h2>
        </div>
        <div className="public-expertise-grid">
          {expertise.map((item) => {
            const Icon = item.icon;
            return (
              <article className="public-expertise-card" key={item.title}>
                <Icon size={34} />
                <h3>{item.title}</h3>
                <p>{item.description}</p>
              </article>
            );
          })}
        </div>
        <div className="public-mini-grid">
          <article>
            <h3>Training & Upskilling</h3>
            <p>Hands-on BA/DA training with real project scenarios to strengthen practical experience.</p>
          </article>
          <article>
            <h3>Certification Guidance</h3>
            <p>Support in completing industry-recognized certifications like CBAP, Tableau, Power BI, and SQL.</p>
          </article>
          <article>
            <h3>On-Project Support</h3>
            <p>Guidance during your first month on the job to ensure a confident and successful start.</p>
          </article>
        </div>
      </section>

      <section className="public-track-record">
        <div>
          <h2>Our Track Record</h2>
          <p>Measurable results that speak for themselves</p>
        </div>
        <div className="public-track-grid">
          <article>
            <strong><CounterAnimation end={90} suffix="%" /></strong>
            <h3>Clients secured interviews within 60 days</h3>
            <p>Success rate for our comprehensive career support program</p>
          </article>
          <article>
            <strong><CounterAnimation end={200} suffix="+" /></strong>
            <h3>Business & Data Analysts placed</h3>
            <p>Professionals successfully placed in top organizations</p>
          </article>
          <article>
            <strong><CounterAnimation end={50} suffix="+" /></strong>
            <h3>Companies trust our candidates</h3>
            <p>Organizations that regularly hire our trained analysts</p>
          </article>
        </div>
      </section>

      <section className="public-section">
        <div className="public-section-heading">
          <p className="eyebrow">Testimonials</p>
          <h2>Analysts Who Trusted Us</h2>
          <p>Real success stories from our professional community</p>
        </div>
        <div className="public-testimonial-card">
          <div className="public-stars">
            {Array.from({ length: Math.floor(testimonials[testimonialIndex].rating) }).map((_, index) => (
              <Star key={index} size={24} />
            ))}
            {testimonials[testimonialIndex].rating % 1 !== 0 ? <Star size={24} className="public-half-star" /> : null}
          </div>
          <blockquote>"{testimonials[testimonialIndex].quote}"</blockquote>
          <strong>{testimonials[testimonialIndex].role}</strong>
          <div className="public-testimonial-controls">
            <button
              onClick={() => setTestimonialIndex((testimonialIndex + testimonials.length - 1) % testimonials.length)}
              type="button"
              aria-label="Previous testimonial"
            >
              <ChevronLeft size={22} />
            </button>
            <button
              onClick={() => setTestimonialIndex((testimonialIndex + 1) % testimonials.length)}
              type="button"
              aria-label="Next testimonial"
            >
              <ChevronRight size={22} />
            </button>
          </div>
        </div>
      </section>

      <section className="public-cta-band public-green-cta">
        <h2>Ready to Accelerate Your Analytics Career?</h2>
        <p>Join hundreds of successful Business and Data Analysts who transformed their careers with our expert guidance.</p>
        <button className="public-light-cta" onClick={() => onNavigate("/contact")} type="button">
          Start Your Journey Today
          <ArrowRight size={18} />
        </button>
      </section>

      <PublicChatbot />
    </>
  );
}

function SuccessStoriesPage({ onNavigate }: { onNavigate: (path: string) => void }) {
  return (
    <>
      <section className="public-page-hero">
        <p className="eyebrow">Success Stories</p>
        <h1>Analysts who moved into stronger roles</h1>
        <p>Real career transformations across finance, healthcare, consulting, technology, and analytics teams.</p>
        <div className="public-page-stats">
          <span><b>90%</b> Average Success Rate</span>
          <span><b>45</b> Average Days to Hire</span>
          <span><b>45%</b> Average Salary Increase</span>
        </div>
      </section>

      <section className="public-section">
        <div className="public-section-heading">
          <p className="eyebrow">Recent Outcomes</p>
          <h2>Representative placements and transitions</h2>
        </div>
        <div className="public-story-grid">
          {stories.map((story) => (
            <article className="public-story-card" key={`${story.company}-${story.role}`}>
              <span>{story.industry}</span>
              <h3>{story.role}</h3>
              <strong><Building size={16} /> {story.company}</strong>
              <p>"{story.quote}"</p>
            </article>
          ))}
        </div>
      </section>

      <section className="public-section public-muted-section">
        <div className="public-section-heading">
          <p className="eyebrow">Industry Impact</p>
          <h2>Our reach spans multiple industries and career levels</h2>
        </div>
        <div className="public-industry-grid">
          {industryHighlights.map((highlight) => {
            const Icon = highlight.icon;
            return (
              <article key={highlight.title}>
                <Icon size={26} />
                <h3>{highlight.title}</h3>
                <p>{highlight.description}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="public-cta-band">
        <h2>Ready to write your success story?</h2>
        <p>Start with a conversation about your current profile, target roles, and next best move.</p>
        <button className="public-primary-cta" onClick={() => onNavigate("/contact")} type="button">
          Get Started Today
          <ArrowRight size={18} />
        </button>
      </section>
    </>
  );
}

function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  return (
    <>
      <section className="public-page-hero">
        <p className="eyebrow">Contact</p>
        <h1>Talk to a career expert in analytics</h1>
        <p>Ready to accelerate your BA/DA career? Tell us where you are now and where you want to go next.</p>
      </section>

      <section className="public-contact-section">
        <div className="public-contact-form-shell">
          {submitted ? (
            <div className="public-submit-state">
              <h2>Thank you.</h2>
              <p>We received your message. The team will follow up as soon as possible.</p>
            </div>
          ) : (
            <form
              className="public-contact-form"
              onSubmit={(event) => {
                event.preventDefault();
                setSubmitted(true);
              }}
            >
              <h2>Start your career transformation</h2>
              <label>
                <span>Name</span>
                <input name="name" required placeholder="Enter your full name" />
              </label>
              <label>
                <span>Email</span>
                <input name="email" type="email" required placeholder="your.email@example.com" />
              </label>
              <label>
                <span>Phone</span>
                <input name="phone" type="tel" placeholder="+1 555 000 0000" />
              </label>
              <label>
                <span>Message</span>
                <textarea name="message" rows={6} required placeholder="Tell us about your career goals and how we can help." />
              </label>
              <button className="public-primary-cta" type="submit">
                Send Message
                <ArrowRight size={18} />
              </button>
              <small>We respond to inquiries within 24 hours during business days.</small>
            </form>
          )}
        </div>

        <aside className="public-contact-card">
          <h2>Get in Touch</h2>
          <dl>
            <div>
              <dt><Mail size={18} /> Email</dt>
              <dd>thinksuccessITconsultants@gmail.com</dd>
              <dd>We respond within 24 hours</dd>
            </div>
            <div>
              <dt><Phone size={18} /> Phone</dt>
              <dd>+91 80084 38080</dd>
              <dd>Mon-Fri, 9:00 AM-6:00 PM IST</dd>
            </div>
            <div>
              <dt><MapPin size={18} /> Offices</dt>
              <dd>North Carolina, Chicago, Hyderabad</dd>
              <dd>By appointment only</dd>
            </div>
            <div>
              <dt><Clock size={18} /> Business Hours</dt>
              <dd>Monday-Friday, 9:00 AM-6:00 PM IST. US availability by appointment.</dd>
            </div>
          </dl>

          <div className="public-why-card">
            <h3>Why Work With Us?</h3>
            <ul>
              <li><CheckCircle size={16} /> Specialized BA/DA expertise</li>
              <li><CheckCircle size={16} /> 90% success rate</li>
              <li><CheckCircle size={16} /> Personalized career strategy</li>
              <li><CheckCircle size={16} /> End-to-end support</li>
            </ul>
          </div>

          <div className="public-follow-card">
            <h3>Follow Our Journey</h3>
            <div className="public-social-row">
              <a href="#" aria-label="LinkedIn"><Linkedin size={20} /></a>
              <a href="#" aria-label="Twitter"><Twitter size={20} /></a>
              <a href="#" aria-label="Instagram"><Instagram size={20} /></a>
            </div>
          </div>
        </aside>
      </section>
    </>
  );
}

export function PublicSitePage({ page, onNavigate }: PublicSitePageProps) {
  return (
    <div className="public-site-shell">
      <PublicHeader activePage={page} onNavigate={onNavigate} />
      <main className="public-main">
        {page === "home" ? <HomePage onNavigate={onNavigate} /> : null}
        {page === "success-stories" ? <SuccessStoriesPage onNavigate={onNavigate} /> : null}
        {page === "contact" ? <ContactPage /> : null}
      </main>
      <PublicFooter onNavigate={onNavigate} />
    </div>
  );
}
