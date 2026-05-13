export function LandingPage({ onSignIn }: { onSignIn: () => void }) {
  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #0a2e1a 0%, #0d3b22 50%, #0a2e1a 100%)",
      display: "flex",
      flexDirection: "column",
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      color: "#fff"
    }}>
      {/* Header */}
      <header style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "20px 48px",
        borderBottom: "1px solid rgba(255,255,255,0.08)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <img
            src="/brand/think-success-logo.jpg"
            alt="Think Success Consulting"
            style={{ width: 44, height: 44, borderRadius: 8, objectFit: "cover" }}
          />
          <span style={{ fontWeight: 700, fontSize: "1.1rem", letterSpacing: "-0.02em" }}>
            Think Success Consulting
          </span>
        </div>
        <button
          onClick={onSignIn}
          style={{
            background: "#00a651",
            color: "#fff",
            border: "none",
            borderRadius: 8,
            padding: "10px 24px",
            fontWeight: 600,
            fontSize: "0.95rem",
            cursor: "pointer",
            transition: "background 0.2s"
          }}
          onMouseOver={(e) => (e.currentTarget.style.background = "#007a3d")}
          onMouseOut={(e) => (e.currentTarget.style.background = "#00a651")}
        >
          Sign In
        </button>
      </header>

      {/* Hero */}
      <main style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "80px 24px 60px"
      }}>
        <img
          src="/brand/think-success-logo.jpg"
          alt="Think Success Consulting"
          style={{
            width: 120,
            height: 120,
            borderRadius: 24,
            objectFit: "cover",
            marginBottom: 32,
            boxShadow: "0 8px 40px rgba(0,0,0,0.4)"
          }}
        />
        <h1 style={{
          fontSize: "clamp(2rem, 5vw, 3.2rem)",
          fontWeight: 800,
          letterSpacing: "-0.03em",
          lineHeight: 1.1,
          marginBottom: 20,
          maxWidth: 720
        }}>
          IT Staffing &amp; Recruitment,<br />
          <span style={{ color: "#00a651" }}>Done Right.</span>
        </h1>
        <p style={{
          fontSize: "1.15rem",
          color: "rgba(255,255,255,0.7)",
          maxWidth: 560,
          lineHeight: 1.7,
          marginBottom: 48
        }}>
          Think Success Consulting connects top IT talent with the right opportunities.
          Smarter matching, faster placements, better outcomes.
        </p>
        <div style={{ display: "flex", gap: 16, flexWrap: "wrap", justifyContent: "center" }}>
          <button
            onClick={onSignIn}
            style={{
              background: "#00a651",
              color: "#fff",
              border: "none",
              borderRadius: 10,
              padding: "14px 36px",
              fontWeight: 700,
              fontSize: "1rem",
              cursor: "pointer",
              transition: "background 0.2s"
            }}
            onMouseOver={(e) => (e.currentTarget.style.background = "#007a3d")}
            onMouseOut={(e) => (e.currentTarget.style.background = "#00a651")}
          >
            Sign In to Portal →
          </button>
        </div>
      </main>

      {/* Features */}
      <section style={{
        display: "flex",
        justifyContent: "center",
        gap: 24,
        padding: "40px 48px",
        flexWrap: "wrap",
        borderTop: "1px solid rgba(255,255,255,0.08)"
      }}>
        {[
          { icon: "🎯", title: "Smart Matching", desc: "AI-powered candidate-job fit scoring" },
          { icon: "⚡", title: "Fast Placements", desc: "Streamlined operations dashboard" },
          { icon: "📊", title: "Full Visibility", desc: "Analytics across every placement" },
        ].map((f) => (
          <div key={f.title} style={{
            background: "rgba(255,255,255,0.05)",
            borderRadius: 12,
            padding: "24px 28px",
            minWidth: 200,
            maxWidth: 260,
            flex: "1 1 200px",
            border: "1px solid rgba(255,255,255,0.08)"
          }}>
            <div style={{ fontSize: "1.8rem", marginBottom: 10 }}>{f.icon}</div>
            <div style={{ fontWeight: 700, marginBottom: 6 }}>{f.title}</div>
            <div style={{ color: "rgba(255,255,255,0.6)", fontSize: "0.9rem" }}>{f.desc}</div>
          </div>
        ))}
      </section>

      {/* Footer */}
      <footer style={{
        textAlign: "center",
        padding: "20px 48px",
        color: "rgba(255,255,255,0.35)",
        fontSize: "0.85rem",
        borderTop: "1px solid rgba(255,255,255,0.06)"
      }}>
        © {new Date().getFullYear()} Think Success Consulting. All rights reserved.
      </footer>
    </div>
  );
}
