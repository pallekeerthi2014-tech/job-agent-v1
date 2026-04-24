const navToggle = document.querySelector(".nav-toggle");
const siteNav = document.querySelector(".site-nav");

if (navToggle && siteNav) {
  navToggle.addEventListener("click", () => {
    const isOpen = siteNav.classList.toggle("is-open");
    navToggle.setAttribute("aria-expanded", String(isOpen));
  });

  siteNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      siteNav.classList.remove("is-open");
      navToggle.setAttribute("aria-expanded", "false");
    });
  });
}

const revealItems = document.querySelectorAll("[data-reveal]");

const revealObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        revealObserver.unobserve(entry.target);
      }
    });
  },
  {
    threshold: 0.15,
  }
);

revealItems.forEach((item) => revealObserver.observe(item));

const counters = document.querySelectorAll(".stat-number");

const animateCounter = (element) => {
  const target = Number(element.dataset.target || 0);
  const duration = 1600;
  const start = performance.now();

  const tick = (timestamp) => {
    const progress = Math.min((timestamp - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    element.textContent = Math.round(target * eased);

    if (progress < 1) {
      requestAnimationFrame(tick);
    } else if (target === 45) {
      element.textContent = "45+";
    } else if (target === 100) {
      element.textContent = "100%";
    }
  };

  requestAnimationFrame(tick);
};

const statsObserver = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        statsObserver.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.65 }
);

counters.forEach((counter) => statsObserver.observe(counter));

const filterButtons = document.querySelectorAll(".filter-button");
const fruitCards = document.querySelectorAll(".fruit-card");
const orchardNoteTitle = document.querySelector("#orchard-note-title");
const orchardNoteCopy = document.querySelector("#orchard-note-copy");

const filterSummaries = {
  all: {
    title: "45+ mango varieties with a mix of classics, regional favourites, and rare cultivars.",
    copy: "The orchard brings together familiar favourites, Andhra-rooted gems, and uncommon finds that make each walk feel more discoverable.",
  },
  classic: {
    title: "Classic mangoes that families instantly recognise and enjoy.",
    copy: "This set highlights dependable favourites like Beneshan, Totapuri, Neelam, Dasheri, Alphonso, and Kesar that connect guests to well-loved flavour traditions.",
  },
  rare: {
    title: "Rare finds that make the orchard feel special and conversation-worthy.",
    copy: "These cultivars add surprise to the stay, giving guests a chance to encounter names and flavour stories that are not commonly found together.",
  },
  regional: {
    title: "Regional gems that keep the orchard rooted in local identity.",
    copy: "These mangoes carry Andhra and regional character into the experience, helping children and families connect farming with place, culture, and biodiversity.",
  },
};

filterButtons.forEach((button) => {
  button.setAttribute("aria-selected", String(button.classList.contains("is-active")));

  button.addEventListener("click", () => {
    const selected = button.dataset.filter;

    filterButtons.forEach((item) => {
      item.classList.remove("is-active");
      item.setAttribute("aria-selected", "false");
    });
    button.classList.add("is-active");
    button.setAttribute("aria-selected", "true");

    fruitCards.forEach((card) => {
      const group = card.dataset.group;
      const shouldShow = selected === "all" || group === selected;
      card.classList.toggle("is-hidden", !shouldShow);
      card.toggleAttribute("hidden", !shouldShow);
    });

    const summary = filterSummaries[selected];

    if (summary && orchardNoteTitle && orchardNoteCopy) {
      orchardNoteTitle.textContent = summary.title;
      orchardNoteCopy.textContent = summary.copy;
    }
  });
});

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

const setupImageMotion = () => {
  if (prefersReducedMotion.matches) {
    return;
  }

  const motionTargets = [
    ...document.querySelectorAll(".hero-image"),
    ...document.querySelectorAll(".layer-back img"),
    ...document.querySelectorAll(".layer-front img"),
    ...document.querySelectorAll(".story-photo-card img"),
    ...document.querySelectorAll(".photo-ribbon-item img"),
    ...document.querySelectorAll(".gallery-item img"),
  ];

  if (!motionTargets.length) {
    return;
  }

  const resolveDepth = (element) => {
    if (element.classList.contains("hero-image")) {
      return 28;
    }

    if (element.closest(".layer-front")) {
      return 18;
    }

    if (element.closest(".layer-back")) {
      return 30;
    }

    if (element.closest(".gallery-item-large")) {
      return 22;
    }

    if (element.closest(".gallery-item") || element.closest(".photo-ribbon-item")) {
      return 16;
    }

    return 12;
  };

  const updateMotion = () => {
    const viewportCenter = window.innerHeight / 2;

    motionTargets.forEach((element) => {
      if (element.closest("[hidden]")) {
        return;
      }

      const rect = element.getBoundingClientRect();
      const elementCenter = rect.top + rect.height / 2;
      const progress = Math.max(-1, Math.min(1, (elementCenter - viewportCenter) / viewportCenter));
      const depth = resolveDepth(element);
      const translateY = progress * -depth;
      const scale = 1.03 + (1 - Math.abs(progress)) * 0.03;

      element.style.setProperty("--parallax-y", `${translateY.toFixed(2)}px`);
      element.style.setProperty("--image-scale", scale.toFixed(3));
    });
  };

  let ticking = false;

  const requestUpdate = () => {
    if (ticking) {
      return;
    }

    ticking = true;

    requestAnimationFrame(() => {
      updateMotion();
      ticking = false;
    });
  };

  updateMotion();
  window.addEventListener("scroll", requestUpdate, { passive: true });
  window.addEventListener("resize", requestUpdate);
};

setupImageMotion();
