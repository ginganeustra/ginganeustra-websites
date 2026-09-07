(() => {
  'use strict';

  const forms = document.querySelectorAll('form.submission-form[data-rustler-form]');

  forms.forEach((form) => {
    const button = form.querySelector('button[type="submit"]');
    const status = form.querySelector('[data-form-status]');
    if (!button) return;

    const idleText = button.textContent;

    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      if (!form.reportValidity()) return;

      button.disabled = true;
      button.setAttribute('aria-disabled', 'true');
      button.textContent = 'Sending…';
      if (status) {
        status.textContent = 'Sending your submission to The Rustler…';
        status.removeAttribute('data-error');
      }

      try {
        const payload = {};
        const formData = new FormData(form);
        formData.forEach((value, key) => {
          if (key !== '_next' && key !== '_honey') payload[key] = value;
        });

        payload._url = form.dataset.sourceUrl || window.location.href.split('#')[0].split('?')[0];

        const endpoint = form.action.replace('https://formsubmit.co/', 'https://formsubmit.co/ajax/');
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          },
          body: JSON.stringify(payload)
        });

        let result = {};
        try {
          result = await response.json();
        } catch (_) {
          result = {};
        }

        const explicitlyFailed = result.success === false || result.success === 'false';
        if (!response.ok || explicitlyFailed) {
          throw new Error(result.message || `Submission service returned ${response.status}`);
        }

        if (status) status.textContent = 'Sent. Thank you — taking you to the confirmation page…';
        window.location.assign(form.dataset.successUrl || 'thank-you.html');
      } catch (error) {
        console.error('Rustler form submission failed:', error);
        if (status) {
          status.textContent = 'Your submission did not go through. Please try again. If the problem continues, email dadabuddanews@gmail.com.';
          status.setAttribute('data-error', 'true');
        }
        button.disabled = false;
        button.removeAttribute('aria-disabled');
        button.textContent = idleText;
      }
    });
  });
})();
