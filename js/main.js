/**
 * Intentflow - Main JavaScript
 * Handles navigation, scroll animations, mobile menu, and form interactions.
 */

(function () {
  'use strict';

  // ========================================
  // DOM Elements
  // ========================================
  const navbar = document.getElementById('navbar');
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const mobileMenu = document.getElementById('mobileMenu');
  const overlay = document.getElementById('overlay');
  const auditForm = document.getElementById('auditForm');
  const submitBtn = document.getElementById('submitBtn');
  const formMessage = document.getElementById('formMessage');
  const languageSelector = document.querySelector('.language-selector');

  // ========================================
  // Navbar scroll effect
  // ========================================
  function handleNavbarScroll() {
    if (!navbar) return;

    if (window.scrollY > 20) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
  }

  window.addEventListener('scroll', handleNavbarScroll, { passive: true });
  handleNavbarScroll();

  // ========================================
  // Mobile menu
  // ========================================
  function openMobileMenu() {
    if (!mobileMenu || !overlay) return;
    mobileMenu.classList.add('active');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeMobileMenu() {
    if (!mobileMenu || !overlay) return;
    mobileMenu.classList.remove('active');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', openMobileMenu);
  }

  if (overlay) {
    overlay.addEventListener('click', closeMobileMenu);
  }

  // Close mobile menu when clicking a link
  if (mobileMenu) {
    mobileMenu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', closeMobileMenu);
    });
  }

  // Close on escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeMobileMenu();
    }
  });

  // ========================================
  // Smooth scroll for anchor links
  // ========================================
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;

      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        e.preventDefault();
        const navHeight = navbar ? navbar.offsetHeight : 0;
        const targetPosition = targetElement.getBoundingClientRect().top + window.pageYOffset - navHeight;

        window.scrollTo({
          top: targetPosition,
          behavior: 'smooth',
        });
      }
    });
  });

  // ========================================
  // Scroll reveal animations (Intersection Observer)
  // ========================================
  const revealElements = document.querySelectorAll('.reveal');

  if ('IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('active');
            revealObserver.unobserve(entry.target);
          }
        });
      },
      {
        root: null,
        rootMargin: '0px 0px -50px 0px',
        threshold: 0.1,
      }
    );

    revealElements.forEach((el) => revealObserver.observe(el));
  } else {
    // Fallback for older browsers
    revealElements.forEach((el) => el.classList.add('active'));
  }

  // ========================================
  // Audit form handling
  // ========================================
  if (auditForm) {
    auditForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      if (submitBtn.disabled) return;

      const siteUrl = document.getElementById('websiteUrl').value.trim();
      const userEmail = document.getElementById('email').value.trim();
      const category = document.getElementById('category').value;
      const market = document.getElementById('market').value;

      // Basic validation
      if (!siteUrl || !userEmail) {
        showFormMessage('Please enter your website URL and email.', 'error');
        return;
      }

      if (!isValidUrl(siteUrl)) {
        showFormMessage('Please enter a valid website URL.', 'error');
        return;
      }

      if (!isValidEmail(userEmail)) {
        showFormMessage('Please enter a valid email address.', 'error');
        return;
      }

      // Show loading state
      const originalBtnText = submitBtn.innerHTML;
      submitBtn.disabled = true;
      submitBtn.innerHTML = `
        <span class="spinner"></span>
        Analyzing...
      `;
      hideFormMessage();

      try {
        const response = await fetch('https://api.intentflowapp.com/api/audit/report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ site_url: siteUrl, user_email: userEmail, category, market }),
        });

        if (response.ok) {
          showFormMessage('Thanks! Your audit report is being generated.', 'success');
          auditForm.reset();
        } else {
          let detail = 'Server error';
          try {
            const data = await response.json();
            detail = data.detail || data.message || response.statusText;
          } catch (_) {
            detail = response.statusText || 'Server error';
          }
          showFormMessage('Sorry, something went wrong: ' + detail, 'error');
        }
      } catch (error) {
        console.error('Form submission error:', error);
        showFormMessage('Unable to connect. Please check your network and try again.', 'error');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalBtnText;
      }
    });
  }

  function showFormMessage(message, type) {
    if (!formMessage) return;
    formMessage.textContent = message;
    formMessage.className = 'form-message ' + type;
  }

  function hideFormMessage() {
    if (!formMessage) return;
    formMessage.className = 'form-message';
    formMessage.textContent = '';
  }

  function isValidUrl(string) {
    try {
      const url = new URL(string);
      return url.protocol === 'http:' || url.protocol === 'https:';
    } catch (_) {
      return false;
    }
  }

  function isValidEmail(string) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(string);
  }

  // ========================================
  // Language selector (placeholder)
  // ========================================
  if (languageSelector) {
    languageSelector.addEventListener('click', () => {
      // In production, this would open a language dropdown
      console.log('Language switcher clicked. Multi-language support coming soon.');
    });
  }

  // ========================================
  // Active nav link highlighting on scroll
  // ========================================
  const sections = document.querySelectorAll('section[id]');
  const navLinks = document.querySelectorAll('.nav-link[href^="#"]');

  if ('IntersectionObserver' in window && sections.length > 0 && navLinks.length > 0) {
    const sectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.getAttribute('id');
            navLinks.forEach((link) => {
              link.classList.remove('active');
              if (link.getAttribute('href') === '#' + id) {
                link.classList.add('active');
              }
            });
          }
        });
      },
      {
        rootMargin: '-50% 0px -50% 0px',
        threshold: 0,
      }
    );

    sections.forEach((section) => sectionObserver.observe(section));
  }
})();
