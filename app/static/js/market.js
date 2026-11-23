// Dynamic product markup below is trusted same-origin Jinja output. Other
// server-provided values are inserted as text, never constructed as HTML here.
// MM-017: progressive enhancement. Without support, the image is still a link.
(() => {
  const trigger = document.querySelector('#product-image-trigger');
  const dialog = document.querySelector('#product-image-dialog');
  const close = document.querySelector('#product-image-close');
  const photo = document.querySelector('#product-lightbox-image');
  const error = document.querySelector('#product-image-error');
  if (!trigger || !dialog || !close || !photo || !error ||
      typeof dialog.showModal !== 'function' || typeof dialog.close !== 'function') return;

  let restorePage = null;
  let startedOnBackdrop = false;
  // Save individual styles (including priorities), not the entire style attribute.
  const saveStyles = (node, names) => {
    const values = names.map(name => [name, node.style.getPropertyValue(name), node.style.getPropertyPriority(name)]);
    return () => values.forEach(([name, value, priority]) => {
      if (value) node.style.setProperty(name, value, priority);
      else node.style.removeProperty(name);
    });
  };
  const lockPage = () => {
    const body = document.body;
    const root = document.documentElement;
    const x = window.scrollX, y = window.scrollY;
    const resetBody = saveStyles(body, ['position', 'top', 'left', 'width', 'overflow', 'padding-right']);
    const resetRoot = saveStyles(root, ['overflow']);
    const resetScroll = saveStyles(root, ['scroll-behavior']);
    const gap = Math.max(0, window.innerWidth - root.clientWidth);
    const padding = parseFloat(getComputedStyle(body).paddingRight) || 0;
    restorePage = () => {
      resetBody(); resetRoot();
      root.style.setProperty('scroll-behavior', 'auto', 'important');
      window.scrollTo(x, y);
      resetScroll();
    };
    body.style.position = 'fixed'; body.style.top = `-${y}px`; body.style.left = `-${x}px`;
    body.style.width = '100%'; body.style.overflow = 'hidden';
    body.style.paddingRight = `${padding + gap}px`;
    root.style.overflow = 'hidden';
  };
  const cleanup = () => {
    if (!restorePage) return;
    restorePage(); restorePage = null;
    startedOnBackdrop = false;
    trigger.focus({preventScroll: true});
  };
  const closeDialog = () => {
    dialog.close();
    cleanup(); // Release the page immediately, before the queued close event.
  };
  const imageFailed = () => { photo.hidden = true; error.hidden = false; };
  photo.addEventListener('error', imageFailed);
  photo.addEventListener('load', () => { photo.hidden = false; error.hidden = true; });

  trigger.addEventListener('click', event => {
    // Preserve open-in-new-tab/window and other ordinary link actions.
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (dialog.open) { event.preventDefault(); return; }
    try {
      // showModal scrolls to focus, so capture/lock the page before opening.
      lockPage();
      dialog.showModal();
      close.focus({preventScroll: true});
      photo.hidden = false; error.hidden = true;
      photo.src = photo.dataset.src;
      if (photo.complete && photo.naturalWidth === 0) imageFailed();
      event.preventDefault();
    } catch (_) {
      if (dialog.open) closeDialog();
      cleanup(); // Leave the link's default navigation as the fallback.
    }
  });
  close.addEventListener('click', closeDialog);
  dialog.addEventListener('cancel', event => { event.preventDefault(); closeDialog(); });
  // An older queued event must not clean up a dialog that has already reopened.
  dialog.addEventListener('close', () => { if (!dialog.open) cleanup(); });
  dialog.addEventListener('pointerdown', event => { startedOnBackdrop = event.target === dialog; });
  dialog.addEventListener('pointercancel', () => { startedOnBackdrop = false; });
  dialog.addEventListener('click', event => {
    if (startedOnBackdrop && event.target === dialog) closeDialog();
    startedOnBackdrop = false;
  });
  dialog.addEventListener('keydown', event => {
    // Close is the only focusable element inside this particular dialog.
    if (event.key === 'Tab') { event.preventDefault(); close.focus({preventScroll: true}); }
  });
})();

// MM-020: progressively enhance the complete server-rendered Explore form.
(() => {
  const form = document.querySelector('#catalogue-search-form');
  const input = document.querySelector('#q');
  const results = document.querySelector('#product-results');
  const grid = document.querySelector('#product-grid');
  const pagination = document.querySelector('#product-pagination');
  const count = document.querySelector('#product-result-count');
  const spinner = document.querySelector('#live-search-spinner');
  const status = document.querySelector('#live-search-status');
  if (!form || !input || !results || !grid || !pagination || !count || !spinner || !status ||
      !form.dataset.liveSearchUrl || typeof fetch !== 'function' || typeof URL !== 'function' ||
      typeof URLSearchParams !== 'function' || typeof FormData !== 'function' ||
      !history || typeof history.replaceState !== 'function') return;

  const LIVE_SEARCH_DELAY = 300;
  let timer = null;
  let requestSequence = 0;
  let currentController = null;
  let isComposing = false;

  const stopTimer = () => {
    if (timer !== null) window.clearTimeout(timer);
    timer = null;
  };
  const loading = active => {
    spinner.hidden = !active;
    results.setAttribute('aria-busy', active ? 'true' : 'false');
    if (active) status.textContent = 'Searching…';
  };
  const validPayload = data => data &&
    typeof data.results_html === 'string' && typeof data.pagination_html === 'string' &&
    Number.isInteger(data.total) && Number.isInteger(data.page) && Number.isInteger(data.pages) &&
    typeof data.count_label === 'string' && typeof data.canonical_query === 'string';

  const runSearch = async () => {
    timer = null;
    const sequence = ++requestSequence;
    if (currentController) currentController.abort();
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    currentController = controller;

    const parameters = new URLSearchParams(new FormData(form));
    parameters.delete('page');
    const endpoint = new URL(form.dataset.liveSearchUrl, window.location.origin);
    endpoint.search = parameters.toString();
    loading(true);

    try {
      const options = {headers: {'Accept': 'application/json'}};
      if (controller) options.signal = controller.signal;
      const response = await fetch(endpoint, options);
      if (sequence !== requestSequence) return;
      if (!response.ok || !(response.headers.get('content-type') || '').includes('application/json'))
        throw new Error('invalid response');
      const data = await response.json();
      if (sequence !== requestSequence) return;
      if (!validPayload(data)) throw new Error('invalid payload');

      grid.innerHTML = data.results_html;
      pagination.innerHTML = data.pagination_html;
      count.textContent = data.count_label;
      const canonical = new URL(form.action, window.location.origin);
      canonical.search = data.canonical_query;
      history.replaceState(history.state, '', canonical.pathname + canonical.search);
      status.textContent = `${data.count_label} found`;
    } catch (error) {
      if (sequence !== requestSequence || (error && error.name === 'AbortError')) return;
      status.textContent = 'Live search is unavailable. Press Find products to search.';
    } finally {
      if (sequence === requestSequence) {
        loading(false);
        if (currentController === controller) currentController = null;
      }
    }
  };

  const schedule = () => {
    stopTimer();
    timer = window.setTimeout(runSearch, LIVE_SEARCH_DELAY);
  };
  input.addEventListener('input', () => { if (!isComposing) schedule(); });
  input.addEventListener('compositionstart', () => { isComposing = true; stopTimer(); });
  input.addEventListener('compositionend', () => { isComposing = false; schedule(); });
  form.addEventListener('submit', () => {
    stopTimer();
    requestSequence += 1;
    if (currentController) currentController.abort();
  });
})();

document.querySelectorAll('[data-view-url]').forEach(node => {
  fetch(node.dataset.viewUrl, {method: 'POST', credentials: 'same-origin',
    headers: {'X-CSRFToken': node.dataset.csrf}}).catch(() => {});
});

// MM-023: optional image analysis. The manual form remains the source of truth.
(() => {
  const listingForm = document.querySelector('#listing-form');
  const imageInput = document.querySelector('#image');
  const enabled = document.querySelector('#vision-ai-enabled');
  const status = document.querySelector('#vision-ai-status');
  const spinner = document.querySelector('#vision-ai-spinner');
  const title = document.querySelector('#title');
  const category = document.querySelector('#category');
  const titleMarker = document.querySelector('#title-ai-marker');
  const categoryMarker = document.querySelector('#category-ai-marker');
  const csrf = listingForm?.querySelector('[name="csrf_token"]');
  if (!listingForm || !imageInput || !enabled || !status || !spinner || !title ||
      !category || !titleMarker || !categoryMarker || !csrf ||
      typeof fetch !== 'function' || typeof FormData !== 'function') return;

  let selectionSequence = 0;
  let analysisSequence = 0;
  let currentFile = null;
  let currentController = null;
  let titleTouched = Boolean(title.value.trim());
  // A select's first option is a browser/form default, not proof the seller
  // deliberately chose it. The change event below records a real choice.
  let categoryTouched = false;
  let applyingAi = false;
  let aiAppliedTitle = null;
  let aiAppliedCategory = null;
  let formLeaving = false;

  const setLoading = active => {
    spinner.hidden = !active;
    spinner.setAttribute('aria-hidden', active ? 'false' : 'true');
  };
  const cancelAnalysis = () => {
    analysisSequence += 1;
    if (currentController) currentController.abort();
    currentController = null;
    setLoading(false);
  };
  const clearAiValues = () => {
    applyingAi = true;
    if (!titleTouched && aiAppliedTitle !== null && title.value === aiAppliedTitle) title.value = '';
    if (!categoryTouched && aiAppliedCategory !== null && category.value === aiAppliedCategory) category.value = '';
    applyingAi = false;
    aiAppliedTitle = null;
    aiAppliedCategory = null;
    titleMarker.hidden = true;
    categoryMarker.hidden = true;
  };
  const markTitleTouched = () => {
    if (applyingAi) return;
    titleTouched = true;
    titleMarker.hidden = true;
  };
  const markCategoryTouched = () => {
    if (applyingAi) return;
    categoryTouched = true;
    categoryMarker.hidden = true;
  };
  title.addEventListener('input', markTitleTouched);
  category.addEventListener('change', markCategoryTouched);

  const analyze = async (file, selectedSequence) => {
    if (!enabled.checked || enabled.disabled || formLeaving || !file) return;
    cancelAnalysis();
    const requestSequence = ++analysisSequence;
    const controller = typeof AbortController === 'function' ? new AbortController() : null;
    currentController = controller;
    setLoading(true);
    status.textContent = 'AI is looking at the product photo…';

    const data = new FormData();
    data.append('image', file, file.name || 'product-photo.jpg');
    data.append('csrf_token', csrf.value);
    try {
      const options = {method: 'POST', body: data, headers: {'Accept': 'application/json'}};
      if (controller) options.signal = controller.signal;
      const response = await fetch('/ai/vision-listing', options);
      if (requestSequence !== analysisSequence || selectedSequence !== selectionSequence || formLeaving) return;
      const result = await response.json();
      if (!response.ok || !result || typeof result.message !== 'string') throw new Error('unavailable');

      applyingAi = true;
      const suggestion = result.suggestion;
      if (suggestion && typeof suggestion.title === 'string' && !titleTouched) {
        title.value = suggestion.title;
        aiAppliedTitle = suggestion.title;
        titleMarker.hidden = false;
      }
      if (suggestion && typeof suggestion.category === 'string' && !categoryTouched) {
        category.value = suggestion.category;
        aiAppliedCategory = suggestion.category;
        categoryMarker.hidden = false;
      }
      applyingAi = false;
      status.textContent = result.message;
    } catch (error) {
      applyingAi = false;
      if (requestSequence !== analysisSequence || selectedSequence !== selectionSequence ||
          formLeaving || (error && error.name === 'AbortError')) return;
      status.textContent = 'AI image suggestions are unavailable. Enter the details yourself.';
    } finally {
      if (requestSequence === analysisSequence) {
        setLoading(false);
        if (currentController === controller) currentController = null;
      }
    }
  };

  listingForm.addEventListener('market-mirror:image-ready', event => {
    selectionSequence += 1;
    const selectedFiles = (event.detail && event.detail.files) || [];
    currentFile = (event.detail && event.detail.file) || selectedFiles[0] || null;
    cancelAnalysis();
    clearAiValues();
    if (currentFile && enabled.checked) analyze(currentFile, selectionSequence);
  });
  listingForm.addEventListener('market-mirror:image-cleared', () => {
    selectionSequence += 1;
    currentFile = null;
    cancelAnalysis();
    clearAiValues();
    status.textContent = '';
  });
  enabled.addEventListener('change', () => {
    cancelAnalysis();
    if (!enabled.checked) {
      clearAiValues();
      status.textContent = 'AI suggestions are off. Enter the details yourself.';
    } else if (currentFile) {
      analyze(currentFile, selectionSequence);
    }
  });
  listingForm.addEventListener('submit', () => {
    formLeaving = true;
    cancelAnalysis();
  });
  window.addEventListener('pagehide', () => {
    formLeaving = true;
    cancelAnalysis();
  }, {once: true});
})();

// MM-022:start — progressively enhance the real new-listing image input.
(() => {
  const form = document.querySelector('#listing-form');
  const zone = document.querySelector('#product-image-dropzone');
  const input = document.querySelector('#image');
  const preview = document.querySelector('#product-image-preview-list');
  const status = document.querySelector('#product-image-upload-status');
  if (!form || !zone || !input || !preview || !status ||
      typeof URL === 'undefined' || typeof URL.createObjectURL !== 'function' ||
      typeof URL.revokeObjectURL !== 'function') return;

  const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
  const MAX_IMAGE_COUNT = 5;
  const MAX_TOTAL_IMAGE_BYTES = 25 * 1024 * 1024;
  const configuredMaximum = Number(zone.dataset.maxBytes);
  const maximumBytes = Number.isSafeInteger(configuredMaximum) && configuredMaximum > 0
    ? configuredMaximum : MAX_IMAGE_BYTES;
  let currentObjectUrls = [];
  let previewSequence = 0;
  let dragDepth = 0;

  const announce = (name, detail = {}) => {
    if (typeof CustomEvent === 'function')
      form.dispatchEvent(new CustomEvent(`market-mirror:${name}`, {detail}));
  };

  const revokeCurrentUrls = () => {
    currentObjectUrls.forEach(objectUrl => URL.revokeObjectURL(objectUrl));
    currentObjectUrls = [];
  };
  const resetDragState = () => {
    dragDepth = 0;
    zone.classList.remove('is-drag-over');
  };
  const clearSelection = (message, clearInput = true) => {
    previewSequence += 1;
    revokeCurrentUrls();
    preview.replaceChildren();
    preview.hidden = true;
    if (clearInput) input.value = '';
    status.textContent = message;
    announce('image-cleared');
  };
  const supportedType = file => {
    if (file.type === 'image/jpeg' || file.type === 'image/png') return true;
    return !file.type && /\.(?:jpe?g|png)$/i.test(file.name || '');
  };
  const attachDroppedFiles = files => {
    if (typeof DataTransfer !== 'function') return false;
    try {
      const transfer = new DataTransfer();
      files.forEach(file => transfer.items.add(file));
      input.files = transfer.files;
      return input.files && input.files.length === files.length;
    } catch (_) {
      return false;
    }
  };
  const useFiles = (files, source) => {
    const selected = Array.from(files || []);
    if (selected.length === 0) {
      clearSelection('Choose at least one product photo.');
      return;
    }
    if (selected.length > MAX_IMAGE_COUNT) {
      clearSelection('Choose no more than five product photos.');
      return;
    }
    if (selected.some(file => !file || file.size === 0)) {
      clearSelection('Choose a nonempty JPEG or PNG.');
      return;
    }
    if (selected.some(file => file.size > maximumBytes)) {
      clearSelection('Each photo must be no larger than 5 MiB.');
      return;
    }
    if (selected.reduce((total, file) => total + file.size, 0) > MAX_TOTAL_IMAGE_BYTES) {
      clearSelection('Product photos must total no more than 25 MiB.');
      return;
    }
    if (selected.some(file => !supportedType(file))) {
      clearSelection('Choose only JPEG or PNG photos.');
      return;
    }
    if (source === 'drop' && !attachDroppedFiles(selected)) {
      clearSelection('This browser could not attach the dropped photos. Use the file chooser instead.');
      return;
    }

    previewSequence += 1;
    const sequence = previewSequence;
    revokeCurrentUrls();
    preview.replaceChildren();
    preview.hidden = true;
    status.textContent = 'Preparing photo previews…';
    let loaded = 0;
    selected.forEach((file, index) => {
      const objectUrl = URL.createObjectURL(file);
      currentObjectUrls.push(objectUrl);
      const item = document.createElement('li');
      item.className = 'image-upload-preview-item';
      const thumbnail = document.createElement('img');
      thumbnail.alt = `Preview of ${file.name || `product photo ${index + 1}`}`;
      const caption = document.createElement('span');
      caption.className = 'image-upload-preview-name';
      caption.textContent = `${index === 0 ? 'Cover photo — ' : `Photo ${index + 1} — `}${file.name || 'product photo'}`;
      item.append(thumbnail, caption);
      preview.append(item);
      thumbnail.onload = () => {
        if (sequence !== previewSequence) return;
        loaded += 1;
        if (loaded === selected.length) {
          preview.hidden = false;
          status.textContent = `${selected.length} photo${selected.length === 1 ? '' : 's'} selected. The first is the cover photo.`;
          announce('image-ready', {file: selected[0], files: selected});
        }
      };
      thumbnail.onerror = () => {
        if (sequence !== previewSequence) return;
        clearSelection('Choose readable JPEG or PNG photos.');
      };
      thumbnail.src = objectUrl;
    });
  };
  const carriesFiles = event => Array.from(event.dataTransfer?.types || []).includes('Files');
  const containsDirectory = transfer => Array.from(transfer?.items || []).some(item => {
    if (item.kind !== 'file' || typeof item.webkitGetAsEntry !== 'function') return false;
    const entry = item.webkitGetAsEntry();
    return Boolean(entry && entry.isDirectory);
  });

  input.addEventListener('change', () => useFiles(input.files, 'picker'));
  zone.addEventListener('dragenter', event => {
    if (!carriesFiles(event)) return;
    event.preventDefault();
    dragDepth += 1;
    zone.classList.add('is-drag-over');
  });
  zone.addEventListener('dragover', event => {
    if (!carriesFiles(event)) return;
    event.preventDefault();
    try { event.dataTransfer.dropEffect = 'copy'; } catch (_) { /* Read-only in some browsers. */ }
  });
  zone.addEventListener('dragleave', event => {
    if (!carriesFiles(event)) return;
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) zone.classList.remove('is-drag-over');
  });
  zone.addEventListener('drop', event => {
    if (!carriesFiles(event)) return;
    event.preventDefault();
    resetDragState();
    if (containsDirectory(event.dataTransfer)) {
      clearSelection('Choose JPEG or PNG files, not a folder.');
      return;
    }
    useFiles(event.dataTransfer.files, 'drop');
  });
  zone.addEventListener('dragend', resetDragState);
  window.addEventListener('pagehide', revokeCurrentUrls, {once: true});
})();
// MM-022:end

// MM-026: switch the main product photo while keeping the lightbox in sync.
(() => {
  const thumbnails = Array.from(document.querySelectorAll('.product-gallery-thumbnail'));
  const trigger = document.querySelector('#product-image-trigger');
  const mainImage = document.querySelector('#product-main-image');
  const lightbox = document.querySelector('#product-lightbox-image');
  const status = document.querySelector('#product-gallery-status');
  if (!thumbnails.length || !trigger || !mainImage || !lightbox || !status) return;

  thumbnails.forEach(thumbnail => thumbnail.addEventListener('click', () => {
    const number = Number(thumbnail.dataset.galleryIndex);
    const photoUrl = thumbnail.dataset.galleryUrl;
    if (!photoUrl || !Number.isSafeInteger(number)) return;
    const description = `photo ${number} of ${thumbnails.length}`;
    thumbnails.forEach(item => item.setAttribute('aria-current', String(item === thumbnail)));
    trigger.href = photoUrl;
    trigger.setAttribute('aria-label', `Enlarge image, ${description}`);
    mainImage.src = photoUrl;
    mainImage.alt = description;
    lightbox.dataset.src = photoUrl;
    lightbox.alt = description;
    lightbox.removeAttribute('src');
    lightbox.hidden = true;
    status.textContent = `Showing photo ${number} of ${thumbnails.length}.`;
  }));
})();

const listingForm = document.querySelector('#listing-form');
let pendingSuggestion = null;
document.querySelectorAll('[data-suggest]').forEach(button => {
  button.addEventListener('click', async () => {
    const output = document.querySelector('#ai-result');
    const apply = document.querySelector('#apply-suggestion');
    apply.hidden = true;
    output.textContent = 'Checking for a suggestion…';
    button.disabled = true;
    try {
      const kind = button.dataset.suggest;
      const data = new FormData(listingForm);
      data.delete('image'); // Suggestions use text and choices, never image bytes.
      const response = await fetch('/ai/' + kind, {method: 'POST', body: data});
      if (!response.ok) throw new Error('unavailable');
      const result = await response.json();
      output.textContent = result.message;
      pendingSuggestion = result.value ? {kind, value: result.value} : null;
      apply.hidden = !pendingSuggestion;
    } catch (_) {
      output.textContent = 'Suggestions are unavailable. You can enter your own values.';
      pendingSuggestion = null;
    } finally { button.disabled = false; }
  });
});
document.querySelector('#apply-suggestion')?.addEventListener('click', event => {
  if (pendingSuggestion) listingForm.elements[pendingSuggestion.kind].value = pendingSuggestion.value;
  event.target.hidden = true;
});

const recommendations = document.querySelector('#recommendations');
if (recommendations) {
  const suffix = recommendations.dataset.productId ? '?product_id=' + recommendations.dataset.productId : '';
  fetch('/recommendations' + suffix).then(response => {
    if (!response.ok) throw new Error('unavailable');
    return response.json();
  }).then(result => {
    const container = document.querySelector('#recommendation-items');
    result.items.forEach(item => {
      const article = document.createElement('article'); article.className = 'panel';
      const link = document.createElement('a'); link.href = '/products/' + item.id; link.textContent = item.title;
      const price = document.createElement('p'); price.className = 'price'; price.textContent = '$' + item.price + ' USD';
      const reason = document.createElement('p'); reason.textContent = item.reason;
      article.append(link, price, reason); container.append(article);
    });
    document.querySelector('#recommendation-note').textContent = result.message;
  }).catch(() => { document.querySelector('#recommendation-note').textContent = 'Explore the marketplace to find more products.'; });
}
