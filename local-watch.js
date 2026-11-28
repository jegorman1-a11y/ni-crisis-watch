(() => {
  const status = document.getElementById('localStatus');
  const notices = document.getElementById('localNotices');
  const planned = document.getElementById('plannedWorks');
  const plannedTitle = document.getElementById('plannedTitle');
  const plannedNotices = document.getElementById('plannedNotices');
  const changes = document.getElementById('localChanges');
  const sources = new Map();
  const storageKey = 'ni-crisis-watch-local-visit-v1';
  const countyDown = /\b(?:county down|co\.? down|downpatrick|newcastle|seaforde|dundrum|ballynahinch|saintfield|crossgar|killyleagh|castlewellan|kilkeel|annalong|rostrevor|warrenpoint|newry|banbridge|dromore|hillsborough|comber|newtownards|donaghadee|groomsport|bangor|holywood|carryduff|ardglass|portaferry|ballywalter|greyabbey|kircubbin|millisle|ballygowan|moira)\b/i;
  const fresh = value => {
    const age = Date.now() - Date.parse(value);
    return age >= -600000 && age <= 5 * 3600000;
  };
  let previous = {};
  try {
    previous = JSON.parse(localStorage.getItem(storageKey)) || {};
  } catch {}
  const latest = {...previous};

  function listItem(item, prefix) {
    const row = document.createElement('li');
    const link = document.createElement('a');
    link.textContent = item.title;
    link.href = item.url;
    row.append(prefix + item.area + ' · ', link);
    return row;
  }

  function render() {
    const available = [...sources].filter(([, items]) => items !== null);
    const roadworks = sources.get('roadworks') || [];
    const incidents = sources.get('incidents') || [];
    const closure = item => /\b(?:closed|closure|impassable)\b/i.test(item.title);
    const active = [...(sources.get('weather') || []),
      ...incidents.slice().sort((a,b) => Number(closure(b)) - Number(closure(a)))];
    planned.hidden = !roadworks.length;
    plannedTitle.textContent = 'Planned roadworks (' + roadworks.length + ')';
    plannedNotices.replaceChildren(...roadworks.map(item => listItem(item, '')));
    const complete = sources.size === 3 && available.length === 3;
    const coverage = complete ? '' : ' · coverage incomplete';
    status.textContent = active.length
      ? active.length + (active.length === 1 ? ' warning or incident' : ' warnings or incidents') + coverage
      : available.some(([key]) => key !== 'roadworks') ? 'No warnings or incidents found in available feeds' + coverage
      : sources.size < 3 ? 'Checking weather warnings and road notices…'
      : 'Weather and road feeds unavailable or stale';
    notices.replaceChildren(...active.map(item => listItem(item, '')));

    const updates = [];
    let comparable = false;
    for (const [key, items] of available) {
      const current = Object.fromEntries(items.map(item => [item.id, item]));
      const before = previous[key];
      if (before && typeof before === 'object') {
        comparable = true;
        for (const item of items) {
          const old = before[item.id];
          if (!old) updates.push(listItem(item, 'New · '));
          else if (old.title !== item.title || old.summary !== item.summary) {
            updates.push(listItem(item, 'Updated · '));
          }
        }
        for (const [id, item] of Object.entries(before)) {
          if (!Object.hasOwn(current, id)) updates.push(listItem(item, 'No longer listed · '));
        }
      }
      latest[key] = current;
    }
    if (!updates.length) {
      const row = document.createElement('li');
      row.textContent = comparable
        ? 'No changes found in the feeds available to compare.'
        : available.length ? 'Changes will appear after you return to this dashboard.'
        : 'Waiting for a successful source check.';
      updates.push(row);
    }
    changes.replaceChildren(...updates);
    if (available.length) {
      try { localStorage.setItem(storageKey, JSON.stringify(latest)); } catch {}
    }
  }

  function normalize(items, area, id) {
    return items.filter(item => typeof item.title === 'string' && /^https:\/\//i.test(item.url))
      .map(item => ({id: id(item), title: item.title, summary: item.summary, area, url: item.url}));
  }

  window.localWatch = {
    weather(feed) {
      const source = feed?.sources?.find(item => item.id === 'met-ni');
      const valid = source?.status === 'ok' && fresh(source.checked_at) && Array.isArray(feed.items);
      const warnings = valid ? feed.items.filter(item => item.source_id === 'met-ni') : [];
      sources.set('weather', valid && (warnings.length || source.item_count === 0)
        ? normalize(warnings, 'NI weather', item => item.url) : null);
      render();
    },
    traffic(feed) {
      for (const kind of ['incidents', 'roadworks']) {
        const source = feed?.traffic?.[kind];
        const valid = source?.status === 'ok' && fresh(feed.generated_at) && Array.isArray(source.items);
        sources.set(kind, valid ? normalize(source.items.filter(item =>
          countyDown.test(item.title + ' ' + item.summary) &&
          !/\b(?:re[ -]?opened|road (?:is )?open again|incident (?:has )?cleared)\b/i.test(item.title)), 'County Down roads', item => item.id) : null);
      }
      render();
    },
  };
})();
