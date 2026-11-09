"""Mobile-first single-page dashboard served by app.py.

Pure HTML/CSS/vanilla JS: polls /api/health every 5 s and renders status
cards. Kept as one string so the whole app stays in a single readable file.
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MockNet RTK service health</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: system-ui, sans-serif; background: #10151c;
    color: #e8edf2; padding-bottom: 2rem;
  }
  header {
    position: sticky; top: 0; background: #161d27; padding: 0.8rem 1rem;
    display: flex; justify-content: space-between; align-items: center;
    border-bottom: 1px solid #232d3b; z-index: 1;
  }
  header h1 { font-size: 1.05rem; margin: 0; }
  .pill {
    padding: 0.25rem 0.7rem; border-radius: 999px; font-size: 0.8rem;
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
  }
  .pill.healthy { background: #12351f; color: #5ee08a; }
  .pill.degraded { background: #3a2f10; color: #e6c65c; }
  .pill.down { background: #3b1518; color: #f2777f; }
  .cards {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 0.6rem; padding: 1rem;
  }
  .card {
    background: #161d27; border: 1px solid #232d3b; border-radius: 12px;
    padding: 0.8rem 1rem;
  }
  .card .label { font-size: 0.7rem; text-transform: uppercase;
                 color: #8a97a8; letter-spacing: 0.05em; }
  .card .value { font-size: 1.5rem; font-weight: 700; margin-top: 0.2rem; }
  ul.stations { list-style: none; margin: 0; padding: 0 1rem; }
  li.station {
    background: #161d27; border: 1px solid #232d3b; border-radius: 12px;
    padding: 0.8rem 1rem; margin-bottom: 0.6rem;
    display: flex; justify-content: space-between; align-items: center;
  }
  li.station .name { font-weight: 700; }
  li.station .sub { color: #8a97a8; font-size: 0.78rem; margin-top: 0.15rem; }
  li.station .meta { text-align: right; font-size: 0.78rem; color: #b8c2cf; }
  footer { text-align: center; color: #66717f; font-size: 0.75rem;
           margin-top: 1rem; }
</style>
</head>
<body>
<header>
  <h1>MockNet RTK service</h1>
  <span id="overall" class="pill degraded">loading</span>
</header>
<div class="cards" id="cards"></div>
<ul class="stations" id="stations"></ul>
<footer>mock service &middot; refreshes every 5 s</footer>
<script>
async function poll() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    render(data);
  } catch (e) {
    document.getElementById('overall').textContent = 'offline';
    document.getElementById('overall').className = 'pill down';
  }
}
function pill(status) {
  return `<span class="pill ${status}">${status}</span>`;
}
function render(d) {
  const overall = document.getElementById('overall');
  overall.textContent = d.overall_status;
  overall.className = 'pill ' + d.overall_status;
  const cards = [
    ['Stations up', `${d.stations_healthy}/${d.stations_total}`],
    ['Degraded', d.stations_degraded],
    ['Down', d.stations_down],
    ['Rover sessions', d.rover_sessions],
    ['Median latency',
      d.median_latency_s === null ? '—' : d.median_latency_s + ' s'],
  ];
  document.getElementById('cards').innerHTML = cards.map(
    ([label, value]) =>
      `<div class="card"><div class="label">${label}</div>
       <div class="value">${value}</div></div>`).join('');
  document.getElementById('stations').innerHTML = d.stations.map(s => `
    <li class="station">
      <div>
        <div class="name">${s.name} ${pill(s.status)}</div>
        <div class="sub">${s.identifier} &middot; ${s.format}
          &middot; uptime ${(s.uptime_24h * 100).toFixed(1)}%</div>
      </div>
      <div class="meta">
        ${s.latency_s === null ? 'no data'
          : s.latency_s + ' s latency'}<br>
        ${s.messages_per_minute} msg/min<br>
        ${s.rover_sessions} rovers
      </div>
    </li>`).join('');
}
poll();
setInterval(poll, 5000);
</script>
</body>
</html>
"""
