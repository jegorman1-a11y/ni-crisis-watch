(() => {
  const controls = document.getElementById('flightControls');
  const status = document.getElementById('flightStatus');
  const areas = controls.querySelectorAll('[data-flight-area]');
  const directions = controls.querySelectorAll('[data-flight-direction]');
  const rows = document.querySelectorAll('[data-airport-group]');
  const links = document.querySelectorAll('[data-flight-link]');
  let area = 'local';
  let direction = 'departures';

  function render() {
    for (const button of areas) {
      button.setAttribute('aria-pressed', String(button.dataset.flightArea === area));
    }
    for (const button of directions) {
      button.setAttribute('aria-pressed', String(button.dataset.flightDirection === direction));
    }
    for (const row of rows) {
      row.hidden = row.dataset.airportGroup !== area;
    }
    for (const link of links) {
      link.hidden = link.dataset.flightLink !== direction;
    }
    document.getElementById('gatwickWeatherPanel').hidden = area !== 'gatwick';
    document.getElementById('localTravel').hidden = area !== 'local';
    const message = 'Live ' + direction + ' unavailable here. Check the official boards.';
    if (status.textContent !== message) status.textContent = message;
  }

  for (const button of areas) {
    button.addEventListener('click', () => {
      area = button.dataset.flightArea;
      render();
    });
  }
  for (const button of directions) {
    button.addEventListener('click', () => {
      direction = button.dataset.flightDirection;
      render();
    });
  }
  render();
  controls.hidden = false;
})();
