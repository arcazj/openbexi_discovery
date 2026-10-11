'use strict';
// Shared help for static controls and controls created by profiles, dialogs, and results.
(() => {
  const selector = 'button,select,summary,.interpret-organism,.source-chip input';
  const byId = {
    'connection-button': 'Connect an AI model, choose its reasoning level, or update your API key.',
    'nav-help': 'Read help for evidence search, AI connections, saved work, and source terms.',
    'profile-settings': 'Manage learning profiles, open saved research, or browse the local library.',
    'd-theme': 'View the active learning profile and open settings to change its themes, goal, or level.',
    'manage-themes': 'Add or remove research themes for the active profile, with an option to undo saved changes.',
    'add-source': 'Choose an evidence source from the catalogue, restore a removed source, or connect an API or database.',
    'manage-sources': 'Remove sources from this profile’s workspace while preserving saved connections and research.',
    'limit': 'Choose the maximum number of results to retrieve from each selected source.',
    'recommended': 'Restore PubMed, Ensembl, and GWAS Catalog to the workspace and select them for the next search.',
    'search-button': 'Retrieve evidence for your query from the selected sources.',
    'cancel-search': 'Stop the current evidence search.',
    'make-question': 'Start an editable research brief using the current search as context.',
    'export-search': 'Download the search terms, sources, coverage, and retrieved evidence as a JSON audit.',
    'suggest-questions': 'Ask the connected AI to propose research directions from the retrieved evidence.',
    'demo-button': 'Explore an illustrative workspace before running a live evidence search.',
    'guidance-query': 'Run a new evidence search using the suggested refined query.',
    'guidance-save': 'Review and edit the suggested research question before saving a brief.',
    'guidance-add': 'Review the suggested next step and add it to a new or existing brief.',
    'guidance-refresh': 'Request fresh AI guidance for the current evidence and research constraints.',
    'guidance-cancel': 'Stop the current AI guidance request.',
    'new-question': 'Create a research brief with your question, study design, and practical constraints.',
    'saved-new': 'Create another research brief in this workspace.',
    'empty-new': 'Save your first research question, supporting references, and notes in a brief.',
    'dismiss-tip': 'Hide this research tip from the workspace.',
    'compare-button': 'Select two saved briefs to compare their questions, evidence, and feasibility.',
    'compare-ai': 'Ask the connected AI to compare the two selected research briefs.',
    'export-workspace': 'Download a JSON backup of this research workspace, including saved briefs.',
    'import-workspace': 'Choose a previously exported JSON workspace to import saved research.',
    'ai-model': 'Choose the model used for future AI requests. The initial default is GPT-6 Astra.',
    'ai-reasoning': 'Choose how much reasoning effort the model uses. Higher levels may take longer and use more tokens; xHigh is the default.',
    'ai-save-key': 'Save the chosen model, reasoning level, and any new key, then check AI access.',
    'ai-retry-connection': 'Check whether the local backend is available and reload the AI connection settings.',
    'ai-connection-help': 'Open instructions for starting the backend and connecting an AI model.',
    'ai-guidance-preferences': 'Choose whether AI guidance refreshes automatically as you research.',
    'nav-library': 'Find saved documents, datasets, notes, quizzes, and past activities across profiles.',
    'source-pubmed': 'Include publication metadata and available abstracts from PubMed in evidence searches.',
    'source-ensembl': 'Include human gene and genomic region annotations from Ensembl, using GRCh38.',
    'source-gwas': 'Include reported genetic trait associations from GWAS Catalog when relevant to the search.'
  };
  const tabs = {
    evidence: 'Search scientific sources, inspect evidence, and develop research briefs.',
    documents: 'Import and read documents saved in this learning profile.',
    datasets: 'Import data, review sensitive fields, and analyze a separate working copy.',
    connections: 'Connect research APIs or a SQLite database and retrieve data for this profile.',
    quizzes: 'Practice with eight-question AI quizzes, review scores, and manage attempt history.',
    notes: 'Write, revise, and revisit notes saved in this learning profile.'
  };
  const byText = {
    'Add theme': 'Open the research theme catalogue to search or browse themes to add to this profile.',
    'Save themes': 'Save these theme selections in the active profile. Earlier research and quiz attempts remain available.',
    '+ Add source': 'Browse evidence sources, restore a saved connection, or connect another API or database.',
    'Add to workspace': 'Show this source in the active profile again using its saved settings.',
    'Remove from workspace': 'Hide this source from the active workspace. Saved connections and datasets remain available; Add source can restore it.',
    'Undo': 'Restore the profile revision from before the last theme or source visibility change.',
    'Save brief': 'Save this research question, its evidence, and your notes in the current workspace.',
    'Inspect evidence': 'Read this source record, its metadata, and any reported limitations or notices.',
    'Save in a brief': 'Attach this source record to a new research brief.',
    'Explain with AI': 'Send this evidence record to the connected AI for an explanation.',
    'Edit brief': 'Change the question, study details, references, or notes in this saved brief.',
    'Mentor review ↓': 'Download a concise version of this brief for review with your mentor.',
    'Delete brief': 'Confirm removal of this brief from the local workspace.',
    'Keep': 'Cancel deletion and keep this saved brief.',
    'Draft a new brief': 'Review the suggested next step in a new, editable research brief.',
    'Review & save brief': 'Review the AI-proposed question in the brief editor before saving it.',
    'Export AI audit': 'Download the request context, model attribution, and AI response for this result.',
    'Check connection': 'Test the backend address and show whether the local service is reachable.',
    'Change API key': 'Open AI connection settings to replace the saved OpenAI API key.',
    'Enter API key': 'Open AI connection settings to enter an OpenAI API key.',
    'Check AI access': 'Check that the key can access the selected model without generating research text.',
    'Read licensing documents': 'Open the documentation list for licenses and third-party source terms.',
    'All documentation ↗': 'Browse the application guides and licensing documents.',
    'Send this request': 'Send the exact sensitive request you reviewed to the configured AI model.',
    'Open saved research': 'Review saved briefs, compare research questions, or export a workspace backup.',
    'Open local library': 'Browse saved activities across profiles and manage ZIP archives.',
    'Edit': 'Edit this profile’s learning goal, themes, level, and workspace wording.',
    'Use profile': 'Switch to this profile’s learning workspace and saved material.',
    'Reset REI': 'Restore the default REI profile settings while keeping saved work.',
    'Undo last edit': 'Restore the previous saved revision of this learning profile.',
    'Roll back profile': 'Restore the previous saved profile, including its themes, goal, level and interface. Saved research and quiz history remain available.',
    'Create profile': 'Build a learning workspace for a new goal, with its own themes and level.',
    'All branches': 'Return to the top of the research category tree.',
    'Browse ›': 'Explore the more specific categories inside this research theme.',
    'Clear themes': 'Remove all selected themes from this profile draft.',
    'Generate wording draft': 'Ask AI to draft workspace wording for the selected themes, goal, and level.',
    'Preview': 'Review how this profile’s wording will appear before saving it.',
    'Save profile': 'Save the reviewed learning profile and apply its workspace settings.',
    'Start a quiz': 'Ask AI for eight questions matched to your profile’s themes, goal, and learning level.',
    'Create quiz': 'Open the quiz editor to write a quiz or generate an editable AI draft.',
    'Try again': 'Retry generating an eight-question AI quiz for the current profile.',
    'Clear history': 'Remove all quiz attempts for this profile. Saved quizzes remain available.',
    'Review attempt': 'View this attempt’s score, your answers, correct answers, and explanations.',
    'Remove attempt': 'Remove this result from quiz history while keeping the saved quiz.',
    'Grade & save attempt': 'Check your answers, show your score and explanations, and save this attempt in history.',
    'Take quiz again': 'Start a fresh attempt at this saved quiz.',
    'New note': 'Write a note and save it in the current learning profile.',
    'Open': 'Open this saved activity to read its content, provenance, and available actions.',
    'Generate quiz with AI': 'Generate an editable eight-question quiz for your learning goal and level.',
    'Save locally': 'Save this material on this computer in the active profile’s library.',
    'Copy request to search draft': 'Copy this earlier request into the search field so you can edit it before searching.',
    'Previous': 'Show the previous page of data rows.',
    'Next': 'Show the next page of data rows.',
    'Restore as a new profile': 'Create a separate profile from this saved snapshot.',
    'Save a revised copy': 'Edit this saved material and keep the revision as a separate library entry.',
    'Export this activity': 'Prepare a ZIP archive containing this activity for backup or transfer.',
    'Delete local activity': 'Remove this saved activity from the local library after confirmation.',
    'Export current profile': 'Prepare a ZIP archive of the current profile and its saved activities.',
    'Export entire library': 'Prepare a ZIP archive of saved activities across all profiles.',
    'Open ZIP': 'Open a Discovery archive for review before importing its contents.',
    'Download ZIP': 'Download the selected library material, including sensitive items only if you opted in.',
    'Import reviewed archive': 'Add the reviewed archive contents to this computer’s local library.',
    'Connect SQLite database': 'Choose a SQLite file to browse its tables and fields with read-only access.',
    'Browse tables': 'Select a database table, choose fields, and preview data without changing the source.',
    'Connect read-only': 'Save this SQLite connection and read its table structure without modifying the database.',
    'Preview selected fields': 'Retrieve a page of rows using the selected table, fields, and optional filter.',
    'Save this page as offline snapshot': 'Save up to 50 displayed database rows in the local library for offline use.',
    'Remove saved local limits': 'Clear this installation’s token and cost limits. Provider credit limits still apply.',
    'Connect to an API': 'Enter an HTTPS JSON API URL and any required credentials to connect a research source.',
    'Recommend APIs with AI': 'Ask AI to recommend supported public APIs for your profile’s subject and learning goal.',
    'Explore API': 'Search this connected API, review retrieved data for privacy, and analyze an approved copy.',
    'Edit connection': 'Change this API’s URL, authentication, or query options, then test and save the changes.',
    'Reconnect': 'Test whether this API is reachable using its saved settings and credentials.',
    'Test & save connection': 'Test the API URL and authentication, then save this connection for the active profile.',
    'Retrieve data': 'Send your search to this API and open a local privacy review of the returned records.',
    'Review privacy': 'Inspect this imported dataset and choose how to protect sensitive fields before saving a copy.',
    'Save reviewed working copy': 'Save the approved transformed data as a separate working copy in the local library.',
    'Preview working copy': 'Apply the privacy rules locally so you can inspect the transformed data before saving.',
    'Previous preview page': 'Review the previous page of transformed data with the current privacy rules.',
    'Next preview page': 'Review the next page of transformed data with the current privacy rules.',
    'Revise privacy rules': 'Review the privacy rules again and create another protected working copy.',
    'Review privacy and create working copy': 'Review this dataset’s sensitive fields before creating a copy eligible for AI analysis.',
    'Calculate statistics': 'Calculate row counts, missing values, and column summaries locally for this working copy.',
    'Ask AI about this copy': 'After your approval, send the sanitized question, statistics, and a limited sample of this reviewed copy to AI.'
  };
  const selectHelp = {
    'Initial tab': 'Choose which workspace tab opens when this profile is activated.',
    'Profile': 'Limit the library list to one profile, or show material from all profiles.',
    'Content type': 'Filter saved activities by material type, such as document, dataset, or quiz.',
    'Level': 'Filter saved activities by the learning level recorded when they were created.',
    'Table': 'Choose the SQLite table to browse; its available columns appear below.',
    'Filter column (optional)': 'Choose a column to narrow the database preview using a filter value.',
    'Authentication': 'Choose the method this API requires: public access, token, API key, or username and password.'
  };
  const modes = {
    auto: 'Auto-detect recognizes a research topic, gene symbol or ID, or genomic region from your search text.',
    topic: 'Research topic treats your search text as a subject to look up in literature and relevant sources.',
    gene: 'Gene symbol / ID looks up a human gene, such as BRCA1 or an Ensembl gene identifier.',
    region: 'Genomic region looks up human GRCh38 coordinates, such as 17:43044295-43125483 (1-based, inclusive).'
  };
  function captionFor(node) {
    if (node.dataset.caption) return node.dataset.caption;
    if (node.id === 'mode') return modes[node.value] || modes.auto;
    if (byId[node.id]) return byId[node.id];
    if (node.id.startsWith('d-tab-')) return tabs[node.id.slice(6)] || '';
    if (node.matches('.interpret-organism')) return 'Gene and region searches use the human genome (GRCh38). Literature results may include other organisms.';
    if (node.dataset.close || node.matches('.d-close')) return 'Close this panel. Save any changes you want to keep first.';
    if (node.dataset.help) return node.dataset.help === 'sources' ? 'Learn what each evidence source provides and how source selection affects a search.' : 'Read guidance about ' + (node.dataset.help === 'licences' ? 'licenses and source terms.' : 'interpreting evidence.');
    if (node.dataset.view === 'search') return 'Return to evidence search and your current research workspace.';
    if (node.dataset.example || node.closest('.examples')) return 'Run an evidence search for this example topic using the selected sources.';
    if (node.closest('#recent')) return 'Copy this recent query into the search field so you can edit it or search again.';
    if (node.closest('#results-tabs')) return 'Filter the retrieved results to this evidence type; the number shows how many records are available.';
    if (node.closest('.record h3')) return 'Open this source record to inspect its evidence, metadata, and source link.';
    if (node.closest('#help-topics')) return 'Read the instructions and tips in this help topic.';
    const label = node.textContent.trim();
    if (node.closest('#next-step-briefs') && label !== 'Draft a new brief') return 'Review the suggested next step and add it to this saved brief.';
    if (node.closest('.d-chips')) return 'Remove this theme from the profile draft.';
    if (node.closest('.d-theme-breadcrumbs')) return 'Browse this research category and its more specific themes.';
    if (node.tagName === 'SELECT') {
      const name = node.getAttribute('aria-label');
      if (name?.startsWith('Protection for ')) return 'Choose how this field is copied: keep, replace with a label, remove, mask, or generalize. Secret credentials must be removed.';
      return selectHelp[name] || '';
    }
    if (node.tagName === 'SUMMARY') return 'Expand or collapse ' + label.replace(/\?$/, '').toLowerCase() + '.';
    if (label === 'Delete') return node.closest('#profile-dialog') ? 'Delete this learning profile after confirmation. Historical saved activities are retained.' : 'Review removal of this saved brief from the local workspace.';
    if (label === 'Cancel') return node.closest('dialog') ? 'Close this panel without saving this draft.' : 'Stop the current AI request.';
    if (label === 'Refresh') return node.closest('[aria-label="connections"]') ? 'Reload this profile’s saved API and SQLite connections.' : 'Reload the saved material and history shown in this tab.';
    if (label === 'Disconnect') return node.closest('.d-api-connection') ? 'Remove this API connection and its saved credentials. Reviewed datasets remain in the library.' : 'Remove this saved source connection. Library snapshots and reviewed datasets remain available.';
    if (label === 'Import file') return node.closest('[aria-label="datasets"]') ? 'Import CSV or JSON data and review sensitive fields before saving a separate working copy.' : 'Choose a document file to save and read in this profile’s local library.';
    if (/^Use /.test(label) && node.closest('.d-api-catalog')) return 'Start an API connection using this service’s suggested URL and query settings.';
    if (/\.md$/.test(label)) return 'Read this application guide or licensing document in the help panel.';
    return byText[label] || '';
  }

  // Permanent descriptions preserve screen-reader help even when the visual popup is closed.
  const descriptions = document.createElement('div');
  descriptions.hidden = true;
  document.body.append(descriptions);
  const descriptionIds = new Map();
  const tooltip = document.createElement('div');
  tooltip.id = 'control-caption';
  tooltip.className = 'control-caption';
  tooltip.setAttribute('aria-hidden', 'true');
  tooltip.setAttribute('popover', 'manual');
  tooltip.hidden = true;
  document.body.append(tooltip);
  let active = null, hoverTimer, leaveTimer, holdTimer, touchStart = null, held = null, keyboard = false;

  function describe(node) {
    const caption = captionFor(node);
    if (!caption) return;
    if (!descriptionIds.has(caption)) {
      const text = document.createElement('span');
      text.id = 'control-description-' + (descriptionIds.size + 1);
      text.textContent = caption;
      descriptions.append(text);
      descriptionIds.set(caption, text.id);
    }
    const ids = (node.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && !id.startsWith('control-description-'));
    ids.push(descriptionIds.get(caption));
    const value = ids.join(' ');
    if (node.getAttribute('aria-describedby') !== value) node.setAttribute('aria-describedby', value);
    if (node.title !== caption) node.title = caption;
    if (node.matches('.d-close') && !node.hasAttribute('aria-label')) node.setAttribute('aria-label', 'Close panel');
    if (node.id === 'mode') {
      const hint = document.getElementById('search-mode-caption');
      if (hint && hint.textContent !== caption) hint.textContent = caption;
    }
  }
  function scan(root) {
    if (!(root instanceof Element) || root === tooltip || descriptions.contains(root)) return;
    if (root.matches(selector)) describe(root);
    root.querySelectorAll(selector).forEach(describe);
  }
  function control(target) { return target instanceof Element ? target.closest(selector) : null; }
  function hide() {
    clearTimeout(hoverTimer); clearTimeout(leaveTimer);
    if (tooltip.hidePopover && tooltip.matches(':popover-open')) tooltip.hidePopover();
    tooltip.hidden = true;
    active = null;
  }
  function show(node) {
    const caption = captionFor(node);
    if (!node.isConnected || !caption || !node.getClientRects().length) return;
    hide(); describe(node); active = node;
    // Keep the popup within a modal's accessible and interactive subtree.
    (node.closest('dialog') || document.body).append(tooltip);
    tooltip.textContent = caption;
    tooltip.hidden = false;
    if (tooltip.showPopover) tooltip.showPopover();
    const bounds = node.getBoundingClientRect(), box = tooltip.getBoundingClientRect();
    const width = document.documentElement.clientWidth, height = window.innerHeight;
    const left = Math.max(8, Math.min(bounds.left + bounds.width / 2 - box.width / 2, width - box.width - 8));
    const top = bounds.bottom + box.height + 10 <= height ? bounds.bottom + 8 : Math.max(8, bounds.top - box.height - 8);
    tooltip.style.left = left + 'px'; tooltip.style.top = top + 'px';
  }
  scan(document.body);
  new MutationObserver(records => {
    for (const record of records) {
      if (record.target === tooltip || descriptions.contains(record.target)) continue;
      for (const node of record.addedNodes) scan(node);
      const node = control(record.target.parentElement || record.target);
      if (node) describe(node);
      if (record.type === 'attributes') scan(record.target);
    }
    // Profiles and search results can restore the selected mode without a change event.
    describe(document.getElementById('mode'));
    if (active && (!active.isConnected || !active.getClientRects().length || active.closest('dialog:not([open])'))) hide();
  }).observe(document.body, {childList:true, subtree:true, characterData:true, attributes:true, attributeFilter:['title','data-caption']});
  document.addEventListener('change', event => { const node = control(event.target); if (node) { describe(node); if (active === node) show(node); } });
  document.addEventListener('pointerover', event => {
    if (event.pointerType === 'touch') return;
    if (tooltip.contains(event.target)) { clearTimeout(leaveTimer); return; }
    const node = control(event.target);
    if (!node || node.contains(event.relatedTarget)) return;
    clearTimeout(leaveTimer); clearTimeout(hoverTimer);
    hoverTimer = setTimeout(() => show(node), 450);
  });
  document.addEventListener('pointerout', event => {
    if (event.pointerType === 'touch') return;
    const node = control(event.target);
    if (!node && !tooltip.contains(event.target)) return;
    if (node?.contains(event.relatedTarget) || tooltip.contains(event.relatedTarget)) return;
    clearTimeout(hoverTimer); clearTimeout(leaveTimer);
    leaveTimer = setTimeout(hide, 150);
  });
  document.addEventListener('focusin', event => { const node = control(event.target); if (node && keyboard) show(node); });
  document.addEventListener('focusout', () => { if (!held) hide(); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && active) { hide(); event.preventDefault(); event.stopImmediatePropagation(); }
    else if (['Tab','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)) keyboard = true;
    else if (['Enter',' '].includes(event.key)) hide();
  }, true);
  function cancelHold() { clearTimeout(holdTimer); touchStart = null; }
  document.addEventListener('pointerdown', event => {
    keyboard = false; held = null; cancelHold(); hide();
    const node = control(event.target);
    if (event.pointerType !== 'touch' || !node || !captionFor(node)) return;
    touchStart = {x:event.clientX, y:event.clientY};
    holdTimer = setTimeout(() => { held = node; show(node); }, 550);
  }, true);
  document.addEventListener('pointermove', event => {
    if (touchStart && Math.hypot(event.clientX - touchStart.x, event.clientY - touchStart.y) > 10) cancelHold();
  }, {passive:true});
  document.addEventListener('pointerup', event => {
    cancelHold();
    if (held) { event.preventDefault(); event.stopImmediatePropagation(); }
  }, true);
  document.addEventListener('pointercancel', () => { cancelHold(); held = null; hide(); }, true);
  document.addEventListener('click', event => {
    if (held && held === control(event.target)) { held = null; event.preventDefault(); event.stopImmediatePropagation(); return; }
    hide();
  }, true);
  document.addEventListener('contextmenu', event => { if ((touchStart || held) && control(event.target)) event.preventDefault(); });
  document.addEventListener('scroll', hide, true);
  window.addEventListener('resize', () => { cancelHold(); hide(); });
  window.addEventListener('blur', () => { cancelHold(); hide(); });
})();
