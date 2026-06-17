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

      const websiteUrl = document.getElementById('websiteUrl').value.trim();
      const email = document.getElementById('email').value.trim();
      const formAction = auditForm.getAttribute('action');

      // Basic validation
      if (!websiteUrl || !email) {
        showFormMessage('Please fill in all fields.', 'error');
        return;
      }

      if (!isValidUrl(websiteUrl)) {
        showFormMessage('Please enter a valid website URL.', 'error');
        return;
      }

      if (!isValidEmail(email)) {
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
        // If Formspree URL is set, submit to it
        if (formAction && formAction.trim() !== '') {
          const response = await fetch(formAction, {
            method: 'POST',
            headers: {
              Accept: 'application/json',
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              websiteUrl,
              email,
            }),
          });

          if (response.ok) {
            showFormMessage(
              "Thanks! We've received your request. Your free audit report will arrive within 24 hours.",
              'success'
            );
            auditForm.reset();
          } else {
            throw new Error('Form submission failed');
          }
        } else {
          // No Formspree URL yet — simulate submission
          await simulateAsyncOperation(1200);
          showFormMessage(
            "Thanks! Your request has been recorded. (Formspree action not configured yet — connect your endpoint to start receiving submissions.)",
            'success'
          );
          auditForm.reset();
        }
      } catch (error) {
        console.error('Form submission error:', error);
        showFormMessage('Something went wrong. Please try again or email us at hello@intentflow.io', 'error');
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

  function simulateAsyncOperation(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
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
