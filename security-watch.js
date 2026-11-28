(() => {
  const status = document.getElementById('securityCheck');
  const local = document.getElementById('securityLocal');
  const localStatus = document.getElementById('securityLocalStatus');
  const meaning = {
    LOW: 'An attack is highly unlikely',
    MODERATE: 'An attack is possible but unlikely',
    SUBSTANTIAL: 'An attack is likely',
    SEVERE: 'An attack is highly likely',
    CRITICAL: 'An attack is highly likely in the near future',
  };
  const baseline = {
    ni: {level:'SUBSTANTIAL',changed_on:'2024-03-06'},
    uk: {level:'SEVERE',changed_on:'2026-04-30'},
  };
  function format(value, withTime = false) {
    const stamp = Date.parse(value);
    if (!Number.isFinite(stamp)) return '';
    const options = {dateStyle:'medium',timeZone:'Europe/London'};
    if (withTime) options.timeStyle = 'short';
    return new Intl.DateTimeFormat('en-GB',options).format(stamp);
  }
  function fresh(value) {
    const age = Date.now() - Date.parse(value);
    return age >= -600000 && age <= 5 * 3600000;
  }
  function render(feed, refreshFailed = false) {
    const threat = feed?.security?.threat;
    const valid = threat?.levels && ['ni','uk'].every(key => Object.hasOwn(meaning,threat.levels[key]?.level));
    const levels = valid ? threat.levels : baseline;
    const check = format(threat?.checked_at, true);
    const verified = valid ? format(threat.verified_at, true) : '28 Nov 2026';
    const current = !refreshFailed && valid && threat.status === 'ok' && fresh(threat.checked_at);
    status.textContent = current
      ? 'MI5 source checked ' + check + ' UK'
      : (refreshFailed ? 'Dashboard refresh failed. ' : check ? (threat.status === 'ok' ? 'MI5 check stale · ' : 'MI5 check unsuccessful · ') + check + ' UK. ' : '') +
        'Showing last verified assessment' + (verified ? ' (' + verified + (valid ? ' UK' : '') + ')' : '') + '.';
    for (const key of ['ni','uk']) {
      const item = levels[key];
      const row = document.querySelector('[data-security-level="' + key + '"]');
      const badge = row.querySelector('strong');
      badge.textContent = item.level;
      badge.dataset.level = item.level;
      row.querySelector('span').textContent = meaning[item.level] +
        (format(item.changed_on) ? ' · Changed ' + format(item.changed_on) : ' · Change date unavailable');
    }
    const police = feed?.security?.police;
    const upToDate = !refreshFailed && police?.status === 'ok' && fresh(police.checked_at) && Array.isArray(police.items);
    local.replaceChildren();
    if (upToDate) {
      for (const item of police.items.slice(0,3)) {
        if (!/^https:\/\/www\.psni\.police\.uk\/latest-news\//.test(item.url)) continue;
        const li = document.createElement('li');
        const link = document.createElement('a');
        link.href = item.url;
        link.textContent = item.title;
        li.append(link);
        local.append(li);
      }
    }
    localStatus.textContent = !upToDate ? 'County Down notice check unavailable. See PSNI updates.'
      : local.childElementCount ? 'County Down and nearby · selected PSNI notices and appeals'
      : 'No local matches in the latest PSNI listing.';
  }
  window.securityWatch = {render};
  render(null);
})();
