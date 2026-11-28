(() => {
  const tabs = [...document.querySelectorAll('[data-health-region]')];
  const summary = document.getElementById('healthSummary');
  const rows = document.getElementById('healthRows');
  const seasonal = document.getElementById('healthSeasonal');
  const links = document.getElementById('healthLinks');
  const status = document.getElementById('healthStatus');
  let loading = true;
  const publishers = {
    ni: [
      ['PHA alerts and advice','https://www.publichealth.hscni.net/protecting-our-health/alerts-outbreaks-and-emergencies'],
      ['PHA respiratory surveillance','https://www.publichealth.hscni.net/protecting-our-health/health-surveillance-data/respiratory-infections-surveillance'],
      ['NISRA weekly death registrations','https://www.nisra.gov.uk/statistics/death-statistics/weekly-death-registrations-northern-ireland'],
    ],
    gb: [
      ['UKHSA official statistics','https://www.gov.uk/government/organisations/uk-health-security-agency/about/statistics'],
      ['Public Health Scotland','https://publichealthscotland.scot/population-health/health-protection/respiratory-surveillance/respiratory-surveillance-systems/outbreak-surveillance/outputs/'],
      ['Public Health Wales','https://phw.nhs.wales/topics/immunisation-and-vaccines/fluvaccine/weekly-influenza-and-acute-respiratory-infection-report/'],
    ],
    ie: [
      ['HPSC outbreak reports','https://www.hpsc.ie/a-z/outbreaks/surveillancereports/'],
      ['HPSC infectious disease bulletins','https://www.hpsc.ie/p/notifiablediseases/weeklyidreports'],
    ],
    world: [['WHO Disease Outbreak News','https://www.who.int/emergencies/disease-outbreak-news']],
  };
  let region = 'ni';
  let data = null;
  const count = value => Number.isSafeInteger(value) && value >= 0 ? value.toLocaleString('en-GB') : 'Not published';
  const date = value => new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeZone:'UTC'}).format(new Date(value));
  const text = (tag, value) => {
    const node = document.createElement(tag);
    node.textContent = value;
    return node;
  };
  function link(label, url) {
    const node = text('a', label);
    if (/^https:\/\//.test(url)) node.href = url;
    return node;
  }
  function report(item) {
    return link(item.source + (item.published ? ' · ' + (item.dateLabel || 'Published') + ' ' + date(item.published) : ''), item.url);
  }
  function render() {
    const inRegion = item => item.region === region;
    const items = (data?.outbreaks || []).filter(inRegion)
      .sort((a,b) => (b.published || '').localeCompare(a.published || ''));
    for (const tab of tabs) tab.setAttribute('aria-pressed', String(tab.dataset.healthRegion === region));
    links.replaceChildren(...publishers[region].map(([label,url]) => link(label,url)));
    status.textContent = data
      ? items.length ? 'Selected official reports · figures are dated snapshots' : 'No verified reports listed here for this region.'
      : loading ? 'Loading selected reports…' : 'Report data unavailable. Check the official sources.';
    summary.replaceChildren(...items.slice(0,3).map(item => {
      const li = text('li', item.area + ' · ');
      li.append(link(item.title,item.url), text('span', item.period + ' · Reported deaths: ' + count(item.deaths)));
      return li;
    }));
    rows.replaceChildren(...items.map(item => {
      const row = document.createElement('tr');
      const title = text('th',item.title);
      title.scope = 'row';
      if (item.note) title.append(text('small',item.note));
      const source = document.createElement('td');
      source.append(report(item));
      row.append(title,text('td',item.area),text('td',item.period),
        text('td',count(item.cases) + (item.casesLabel ? ' ' + item.casesLabel : '')),
        text('td',count(item.admissions)),text('td',count(item.deaths)),source);
      return row;
    }));
    if (!items.length) {
      const cell = text('td',status.textContent);
      cell.colSpan = 7;
      const row = document.createElement('tr');
      row.append(cell);
      rows.append(row);
    }
    const trends = (data?.seasonal || []).filter(inRegion);
    seasonal.replaceChildren(...trends.map(item => {
      const li = text('li',item.area + ' · ' + item.title + ' · ' + item.period + ' · ' + item.note + ' ');
      li.append(report(item));
      return li;
    }));
    if (!trends.length) seasonal.append(text('li','No seasonal figures listed here. See the official sources for this region.'));
  }
  for (const tab of tabs) tab.addEventListener('click', () => {
    region = tab.dataset.healthRegion;
    render();
  });
  render();
  fetch('data/public-health.json',{cache:'no-cache'}).then(response => {
    if (!response.ok) throw Error('Report data unavailable');
    return response.json();
  }).then(value => {
    if (!Array.isArray(value?.outbreaks) || !Array.isArray(value?.seasonal)) throw Error('Invalid report data');
    loading = false;
    data = value;
    render();
  }).catch(() => {loading = false; render();});
})();
