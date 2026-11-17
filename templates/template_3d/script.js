/**
 * The Scholars Hub & SiteAI Business Website Engine
 * Manages page load entrance, 3D scroll tilt reveals, hero parallax,
 * structured data binding, navigation, gallery modal/filter, FAQs, and inquiry forms.
 */

// ============================================================
// 1. Structured Data Hydration (SiteAI Engine)
// Populates text, links, and attributes from window.SITE_DATA
// ============================================================

function getNestedValue(obj, path) {
  return path.split('.').reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : null), obj);
}

function hydrateSiteData() {
  if (typeof window.SITE_DATA === 'undefined') return;

  const data = window.SITE_DATA;

  // Text content binding: [data-bind="path.to.value"]
  document.querySelectorAll('[data-bind]').forEach((el) => {
    const path = el.getAttribute('data-bind');
    const value = getNestedValue(data, path);
    if (value !== null && value !== undefined) {
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
        el.value = value;
      } else {
        el.innerHTML = value;
      }
    }
  });

  // Href binding: [data-bind-href="path.to.value"]
  document.querySelectorAll('[data-bind-href]').forEach((el) => {
    const path = el.getAttribute('data-bind-href');
    const value = getNestedValue(data, path);
    if (value) {
      el.setAttribute('href', value);
    } else {
      el.style.display = 'none'; // no value for this business: hide the link
    }
  });

  // Attribute binding: [data-bind-attr="title:path.to.value"]
  document.querySelectorAll('[data-bind-attr]').forEach((el) => {
    const bindings = el.getAttribute('data-bind-attr').split(';');
    bindings.forEach((binding) => {
      const [attr, path] = binding.split(':').map((s) => s.trim());
      if (attr && path) {
        const value = getNestedValue(data, path);
        if (value !== null && value !== undefined) {
          el.setAttribute(attr, value);
        }
      }
    });
  });
}

// ============================================================
// 2. Active Page Navigation & Mobile Menu
// ============================================================

function initNavigation() {
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  const navLinks = document.querySelectorAll('.site-nav .nav-link');

  navLinks.forEach((link) => {
    const href = link.getAttribute('href');
    // Match exact page, or root URL to index.html
    if (
      href === currentPath ||
      (currentPath === '' && href === 'index.html') ||
      (currentPath === '/' && href === 'index.html')
    ) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // Mobile menu toggle
  const navToggle = document.getElementById('navToggle');
  const siteNav = document.getElementById('siteNav');

  if (navToggle && siteNav) {
    navToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      const isOpen = siteNav.classList.toggle('open');
      navToggle.classList.toggle('open', isOpen);
      navToggle.setAttribute('aria-expanded', String(isOpen));
    });

    // Close mobile nav when clicking a link
    navLinks.forEach((link) => {
      link.addEventListener('click', () => {
        siteNav.classList.remove('open');
        navToggle.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
      });
    });

    // Close when clicking outside
    document.addEventListener('click', (e) => {
      if (!siteNav.contains(e.target) && !navToggle.contains(e.target) && siteNav.classList.contains('open')) {
        siteNav.classList.remove('open');
        navToggle.classList.remove('open');
        navToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }
}

// ============================================================
// 3. Page-Load Entrance Animation
// ============================================================

window.addEventListener('DOMContentLoaded', () => {
  hydrateSiteData();
  initNavigation();
  initGallery();
  initFAQs();
  initContactForm();

  requestAnimationFrame(() => {
    setTimeout(() => {
      document.body.classList.add('loaded');
    }, 60);
  });
});

// ============================================================
// 4. Scroll-Triggered 3D Tilt Reveals
// ============================================================

const revealSelector = [
  '.facility-card',
  '.catalog-card',
  '.section-title',
  '.section-sub',
  '.contact-inner',
  '.contact-preview-inner',
  '.reveal',
  '.editorial-title',
  '.editorial-lead',
  '.editorial-narrative',
  '.editorial-pullquote',
  '.editorial-blueprint-card',
  '.editorial-metric-card',
  '.editorial-pillar-card',
  '.charter-card',
  '.service-plan-card',
  '.matrix-table-wrap',
  '.amenity-card',
  '.step-card',
  '.faq-item',
  '.gallery-card',
  '.contact-form-card',
  '.info-card',
  '.cta-banner-inner'
].join(', ');

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('in-view');
      revealObserver.unobserve(entry.target);
    }
  });
}, {
  threshold: 0.12,
  rootMargin: '0px 0px -40px 0px'
});

document.addEventListener('DOMContentLoaded', () => {
  const targets = document.querySelectorAll(revealSelector);
  targets.forEach((el) => revealObserver.observe(el));
});

// ============================================================
// 5. Hero Parallax (Lamp Glow)
// ============================================================

{
  const heroSection = document.querySelector('.hero');
  const lampGlow = document.querySelector('.lamp-glow');
  let ticking = false;

  function updateParallax() {
    const scrollY = window.scrollY;
    const heroHeight = heroSection ? heroSection.offsetHeight : 0;

    if (scrollY < heroHeight && lampGlow) {
      lampGlow.style.transform = `translateY(${scrollY * 0.22}px)`;
    }
    ticking = false;
  }

  window.addEventListener('scroll', () => {
    if (!ticking) {
      requestAnimationFrame(updateParallax);
      ticking = true;
    }
  }, { passive: true });
}

// ============================================================
// 6. Gallery Filtering & Lightbox Modal
// ============================================================

function initGallery() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  const galleryCards = document.querySelectorAll('.gallery-card');

  if (filterBtns.length > 0 && galleryCards.length > 0) {
    filterBtns.forEach((btn) => {
      btn.addEventListener('click', () => {
        filterBtns.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');

        const category = btn.getAttribute('data-filter');

        galleryCards.forEach((card) => {
          const cardCat = card.getAttribute('data-category');
          if (category === 'all' || cardCat === category) {
            card.style.display = 'flex';
            requestAnimationFrame(() => {
              card.style.opacity = '1';
              card.style.transform = 'translateY(0)';
            });
          } else {
            card.style.display = 'none';
          }
        });
      });
    });
  }

  // Modal Lightbox
  const modal = document.getElementById('galleryModal');
  const modalClose = document.getElementById('galleryModalClose');
  const modalTitle = document.getElementById('modalTitle');
  const modalTag = document.getElementById('modalTag');
  const modalDesc = document.getElementById('modalDesc');
  const modalArt = document.getElementById('modalArt');

  if (modal && galleryCards.length > 0) {
    galleryCards.forEach((card) => {
      card.addEventListener('click', () => {
        const title = card.querySelector('.gallery-title')?.textContent || '';
        const tag = card.querySelector('.gallery-tag')?.textContent || '';
        const desc = card.querySelector('.gallery-desc')?.textContent || '';
        const artHtml = card.querySelector('.gallery-art')?.innerHTML || '';

        if (modalTitle) modalTitle.textContent = title;
        if (modalTag) modalTag.textContent = tag;
        if (modalDesc) modalDesc.textContent = desc;
        if (modalArt) modalArt.innerHTML = artHtml;

        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
      });
    });

    const closeModal = () => {
      modal.classList.remove('show');
      document.body.style.overflow = '';
    };

    if (modalClose) {
      modalClose.addEventListener('click', closeModal);
    }

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal.classList.contains('show')) {
        closeModal();
      }
    });
  }
}

// ============================================================
// 7. FAQ Accordion Toggle
// ============================================================

function initFAQs() {
  const faqItems = document.querySelectorAll('.faq-item');
  faqItems.forEach((item) => {
    const questionBtn = item.querySelector('.faq-question');
    if (questionBtn) {
      questionBtn.addEventListener('click', () => {
        const isActive = item.classList.contains('active');
        // Close others in same accordion
        faqItems.forEach((other) => other.classList.remove('active'));
        if (!isActive) {
          item.classList.add('active');
        }
      });
    }
  });
}

// ============================================================
// 8. Interactive Reservation & Inquiry Form
// ============================================================

function initContactForm() {
  const form = document.getElementById('reservationForm');
  const feedback = document.getElementById('formFeedback');

  // Pre-select shift from URL query params (e.g. ?shift=Morning)
  if (form) {
    const urlParams = new URLSearchParams(window.location.search);
    const shiftParam = urlParams.get('shift');
    if (shiftParam) {
      const shiftSelect = form.querySelector('[name="shift"]');
      if (shiftSelect) {
        const lower = shiftParam.toLowerCase();
        for (let i = 0; i < shiftSelect.options.length; i++) {
          if (shiftSelect.options[i].value.toLowerCase().includes(lower)) {
            shiftSelect.selectedIndex = i;
            break;
          }
        }
      }
    }
  }

  if (form && feedback) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();

      const name = form.querySelector('[name="name"]')?.value.trim() || 'Aspirant';
      const phone = form.querySelector('[name="phone"]')?.value.trim() || '';
      const shift = form.querySelector('[name="shift"]')?.value || 'Morning Shift';
      const startDate = form.querySelector('[name="startDate"]')?.value || 'Immediately';
      const notes = form.querySelector('[name="notes"]')?.value.trim() || '';

      if (!phone) {
        alert('Please provide your phone number so we can confirm seat availability.');
        return;
      }

      // Format WhatsApp message text
      const biz = (window.SITE_DATA && window.SITE_DATA.business) || {};
      const bizName = biz.name || 'there';
      const waMsg = encodeURIComponent(
        `Hello ${bizName}! My name is ${name}. I would like to reserve a seat for the *${shift}* starting on *${startDate}*. Contact: ${phone}. ${notes ? 'Notes: ' + notes : ''}`
      );
      const waUrl = biz.whatsappLink ? `${biz.whatsappLink}?text=${waMsg}` : '#';

      feedback.innerHTML = `
        <strong>Thank you, ${name}!</strong> Your seat reservation request has been noted.<br>
        We will contact you at <strong>${phone}</strong> shortly.<br><br>
        <a href="${waUrl}" target="_blank" rel="noopener" class="btn btn-whatsapp" style="font-size:0.85rem; padding:0.6rem 1.2rem; display:inline-flex;">
          <svg viewBox="0 0 24 24" class="icon"><path d="M17.5 6.5a7.5 7.5 0 0 0-12.1 8.6L4 21l6-1.4A7.5 7.5 0 0 0 17.5 6.5Z"/><path d="M9 9.3c0 3.5 2.9 6.3 6.3 6.3.5 0 .9-.4.9-.9v-.9l-2.1-.7-.7 1a4.6 4.6 0 0 1-2.9-2.9l1-.7-.7-2.1H9.9c-.5 0-.9.4-.9.9Z"/></svg>
          Confirm instantly on WhatsApp
        </a>
      `;
      feedback.className = 'form-feedback success';

      form.reset();
    });
  }
}