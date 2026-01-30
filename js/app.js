document.addEventListener('DOMContentLoaded', ()=>{
  const navToggle = document.getElementById('navToggle');
  if(navToggle){
    const mainNav = document.getElementById('mainNav');
    navToggle.addEventListener('click', ()=>{
      const visible = mainNav && mainNav.style.display === 'block';
      if(mainNav) mainNav.style.display = visible ? '' : 'block';
    });
  }

  // Simple driver search (if driversGrid exists we filter cards, otherwise use entries JSON and navigate)
  const search = document.getElementById('driverSearch');
  const grid = document.getElementById('driversGrid');
  const searchMessage = document.getElementById('searchMessage');
  const slugify = s=>s.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'');
  // compute basePath for GitHub Pages (supports username.github.io and username.github.io/repo)
  const basePath = (()=>{
    const parts = location.pathname.split('/').filter(Boolean);
    if(location.hostname.endsWith('github.io') && parts.length>0) return '/' + parts[0];
    return '';
  })();
  const sitePath = p=>{
    if(!p) return (basePath || '/');
    let out;
    if(p.startsWith('/')) out = (basePath + p).replace(/\\/g,'/');
    else out = (basePath + '/' + p).replace(/\\/g,'/');
    if(location.protocol === 'file:'){
      if(out.startsWith('/')) out = out.slice(1);
    }
    return out;
  };
  if(search){
    if(grid){
      search.addEventListener('input', ()=>{
        const q = search.value.trim().toLowerCase();
        const items = grid.querySelectorAll('.card');
        items.forEach(it=>{
          const name = it.dataset.name.toLowerCase();
          it.style.display = name.includes(q) ? '' : 'none';
        });
      });
    } else {
      // No grid -> compact homepage: perform search on Enter and navigate
      search.addEventListener('keydown', (e)=>{
        if(e.key !== 'Enter') return;
        const q = search.value.trim().toLowerCase();
        if(!q) return;
        fetch(sitePath('/data/entries-2026.json'))
          .then(r=>r.ok? r.json() : Promise.reject('no entries'))
          .then(data=>{
            const matches = [];
            data.teams.forEach(team=>{
              team.drivers.forEach(driver=>{
                if(driver.name.toLowerCase().includes(q)) matches.push({team, driver});
              });
            });
            if(matches.length===0){
              if(searchMessage) searchMessage.textContent = 'Geen rijders gevonden.';
            } else if(matches.length===1){
              const teamSlug = matches[0].team.slug || slugify(matches[0].team.name);
              const driverSlug = slugify(matches[0].driver.name);
              location.href = sitePath(`/teams/${teamSlug}/drivers/${driverSlug}.html`);
            } else {
              if(searchMessage){
                searchMessage.innerHTML = matches.map(m=>{
                  const tslug = m.team.slug || slugify(m.team.name);
                  const dslug = slugify(m.driver.name);
                  const href = sitePath(`/teams/${tslug}/drivers/${dslug}.html`);
                  return `<div><a href="${href}">${m.driver.name} — ${m.team.name}</a></div>`;
                }).join('');
              }
            }
          }).catch(err=>{ if(searchMessage) searchMessage.textContent = 'Zoeken mislukt.'; console.error(err); });
      });
    }
  }

  // Load local 2026 calendar JSON and populate table
  const calendarBody = document.getElementById('calendarBody');
  // sitePath previously defined above to avoid use-before-declaration bugs
  if(calendarBody){
    fetch(sitePath('/data/calendar-2026.json'))
      .then(r=>r.ok ? r.json() : Promise.reject('Failed to load'))
      .then(data=>{
        calendarBody.innerHTML = '';
        data.races.forEach(r=>{
          const tr = document.createElement('tr');
          const date = new Date(r.date);
          const dateStr = date.toLocaleDateString(undefined,{day:'2-digit',month:'short'});
          tr.innerHTML = `<td>${dateStr}</td><td>${r.name}</td><td>${r.city} — ${r.circuit}</td>`;
          calendarBody.appendChild(tr);
        });
      }).catch(err=>{
        calendarBody.innerHTML = '<tr><td colspan="3">Kon kalender niet laden.</td></tr>';
        console.error(err);
      });
  }

  // Load entries (teams + drivers) and render
  const driversGrid = document.getElementById('driversGrid');
  const teamsGrid = document.getElementById('teamsGrid');
  fetch(sitePath('/data/entries-2026.json'))
    .then(r=>r.ok ? r.json() : Promise.reject('Failed to load entries'))
    .then(data=>{
      // Render teams
      if(teamsGrid){
        teamsGrid.innerHTML = '';
        data.teams.forEach(team=>{
          const slug = team.slug || team.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'');
          const a = document.createElement('a');
          a.href = sitePath(`/teams/${slug}/index.html`);
          a.className = 'card';
          a.innerHTML = `<h3>${team.name}</h3><p>${team.country}</p><p>${team.drivers.length} rijders</p>`;
          teamsGrid.appendChild(a);
        });
      }

      // Render drivers inside team mapjes (link naar team drivers pagina)
      if(driversGrid){
        driversGrid.innerHTML = '';
        data.teams.forEach(team=>{
          const teamSlug = team.slug || team.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'');
          team.drivers.forEach(driver=>{
            const driverSlug = driver.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'');
            const art = document.createElement('article');
            art.className = 'card';
            art.dataset.name = driver.name;
            const driverLink = sitePath(`/teams/${teamSlug}/drivers/${driverSlug}.html`);
            const teamLink = sitePath(`/teams/${teamSlug}/index.html`);
            art.innerHTML = `<h3><a href="${driverLink}">${driver.name}</a></h3><p>Team: <a href="${teamLink}">${team.name}</a></p><p>Land: ${driver.nationality}</p>`;
            driversGrid.appendChild(art);
          });
        });
      }
    }).catch(err=>{
      console.error('Entries load error', err);
      if(teamsGrid) teamsGrid.innerHTML = '<div class="card">Kon teams niet laden.</div>';
      if(driversGrid) driversGrid.innerHTML = '<div class="card">Kon rijders niet laden.</div>';
    });

  // Load stats and fill Top-5 and provide helpers for team/driver pages
  fetch(sitePath('/data/stats.json'))
    .then(r=>r.ok ? r.json() : Promise.reject('Failed to load stats'))
    .then(stats=>{
      // Expose full stats to window for pages/tools and add a debug log
      try{
        // expose full stats object for pages and dev tools
        window.APP_STATS = stats;
        // keep a raw JSON copy accessible and persist for debugging (non-sensitive)
        try{ localStorage.setItem('APP_STATS', JSON.stringify(stats)); window.APP_STATS_RAW = JSON.stringify(stats); }catch(e){}

        // small summary: counts for quick verification
        const driverCount = Object.keys(stats.driverStats || {}).length;
        const teamCount = Object.keys(stats.teamStats || {}).length;
        const seasonCount = Array.isArray(stats.seasons) ? stats.seasons.length : 0;
        // total top-level keys
        const topKeys = Object.keys(stats).length;
        console.debug('Loaded stats:', driverCount, 'drivers,', teamCount, 'teams,', seasonCount, 'seasons — top-level keys:', topKeys);
      }catch(e){ console.debug('Could not attach APP_STATS', e); }
      // Top 5 drivers by allTime.points
      const topDriversEl = document.getElementById('topDrivers');
      if(topDriversEl){
        topDriversEl.innerHTML = '';
        const drivers = Object.entries(stats.driverStats).map(([slug, d])=>({slug, name: slug.replace(/-/g,' '), points: d.allTime && d.allTime.points ? d.allTime.points : 0}));
        drivers.sort((a,b)=>b.points-a.points);
        // fetch entries once to map nicer display names and team slugs
        fetch(sitePath('/data/entries-2026.json')).then(r=>r.ok? r.json(): Promise.resolve(null)).then(entries=>{
          const nameMap = {};
          if(entries){
            entries.teams.forEach(t=>{ t.drivers.forEach(dr=>{ const s = dr.name.toLowerCase().replace(/[^a-z0-9]+/g,'-'); nameMap[s] = {display: dr.name, teamSlug: t.slug || t.name.toLowerCase().replace(/[^a-z0-9]+/g,'-')}; }); });
          }
          drivers.slice(0,10).forEach(d=>{
            const li = document.createElement('li');
            const driverSlug = d.slug;
            let display = d.slug.split('-').map(s=>s.charAt(0).toUpperCase()+s.slice(1)).join(' ');
            const map = nameMap[driverSlug];
            if(map){ display = map.display; const teamSlug = map.teamSlug; li.innerHTML = `<a href="${sitePath(`/teams/${teamSlug}/drivers/${driverSlug}.html`)}">${display}</a> — ${d.points} p`; }
            else { li.textContent = `${display} — ${d.points} p`; }
            topDriversEl.appendChild(li);
          });
        }).catch(()=>{
          drivers.slice(0,10).forEach(d=>{ const li=document.createElement('li'); const display = d.slug.split('-').map(s=>s.charAt(0).toUpperCase()+s.slice(1)).join(' '); li.textContent = `${display} — ${d.points} p`; topDriversEl.appendChild(li); });
        });
      }

      const topTeamsEl = document.getElementById('topTeams');
      if(topTeamsEl){
        topTeamsEl.innerHTML = '';
        const teams = Object.entries(stats.teamStats).map(([slug,t])=>({slug,name:slug.replace(/-/g,' '),points: (t && t.allTime && typeof t.allTime.points === 'number') ? t.allTime.points : (t && t.allTime && parseInt(t.allTime.points) || 0)}));
        teams.sort((a,b)=>b.points-a.points);
        teams.slice(0,10).forEach(t=>{
          const li = document.createElement('li');
          li.innerHTML = `<a href="${sitePath(`/teams/${t.slug}/index.html`)}">${t.name}</a> — ${t.points} p`;
          topTeamsEl.appendChild(li);
        });
      }

      // Helper: if on a team page, render season buttons and detailed stats
      const teamSeasonsEl = document.getElementById('teamSeasons');
      const teamStatsEl = document.getElementById('teamStats');
      if(teamSeasonsEl && teamStatsEl){
        const teamSlug = teamSeasonsEl.dataset.team;
        const seasons = stats.seasons;
        teamSeasonsEl.innerHTML = '';
        const normalize = s=> (s||'').toString().toLowerCase().replace(/[^a-z0-9]+/g,'');
        const normTeam = normalize(teamSlug);
        seasons.forEach(s=>{
          const btn = document.createElement('button');
          btn.textContent = `F1 ${s}`;
          btn.addEventListener('click', ()=>{
            const tstats = stats.teamStats[teamSlug] && stats.teamStats[teamSlug].bySeason && stats.teamStats[teamSlug].bySeason[s];
            let html = '';
            if(tstats){
              html += `<h3>${s} — ${tstats.points} punten, ${tstats.wins} overwinningen</h3>`;
            } else {
              html += `<h3>Geen teamdata voor ${s}</h3>`;
            }
            // build list of drivers for this team/season by scanning driverStats
            const drivers = [];
            Object.entries(stats.driverStats).forEach(([dslug, d])=>{
              const sd = d.bySeason && d.bySeason[s];
              if(!sd) return;
              const driverTeam = normalize(sd.team || '');
              // match if normalized strings contain each other (covers 'Red Bull' vs 'oracle-red-bull')
              if(driverTeam && (driverTeam.includes(normTeam) || normTeam.includes(driverTeam))){
                drivers.push({slug: dslug, name: dslug.split('-').map(p=>p.charAt(0).toUpperCase()+p.slice(1)).join(' '), seasonData: sd});
              }
            });
            if(drivers.length>0){
              // try to fetch entries to map nicer display names and links (non-blocking)
              fetch(sitePath('/data/entries-2026.json')).then(r=>r.ok? r.json(): Promise.reject('no entries')).then(entries=>{
                const nameMap = {};
                entries.teams.forEach(t=>{ t.drivers.forEach(dr=>{ const s = dr.name.toLowerCase().replace(/[^a-z0-9]+/g,'-'); nameMap[s]= {display: dr.name, teamSlug: t.slug}; }); });
                // render table
                drivers.sort((a,b)=> (b.seasonData.points||0) - (a.seasonData.points||0));
                html += '<table class="stats-table"><thead><tr><th>Rijder</th><th>Plek</th><th>Punten</th><th>Overwinningen</th><th>Podia</th><th>Poles</th><th>Fastest laps</th></tr></thead><tbody>';
                drivers.forEach(d=>{
                  const map = nameMap[d.slug];
                  let disp = d.name;
                  let link = '';
                  if(map){ disp = map.display; const tslug = map.teamSlug || teamSlug; link = sitePath(`/teams/${tslug}/drivers/${d.slug}.html`); }
                  html += `<tr><td>${ link? `<a href="${link}">${disp}</a>`: disp }</td><td>${d.seasonData.position != null ? d.seasonData.position : '—'}</td><td>${d.seasonData.points||0}</td><td>${d.seasonData.wins||0}</td><td>${d.seasonData.podiums||0}</td><td>${d.seasonData.poles||0}</td><td>${d.seasonData.fastestLaps||0}</td></tr>`;
                });
                html += '</tbody></table>';
                teamStatsEl.innerHTML = html;
              }).catch(()=>{
                // fallback render without nice names/links
                drivers.sort((a,b)=> (b.seasonData.points||0) - (a.seasonData.points||0));
                html += '<table class="stats-table"><thead><tr><th>Rijder</th><th>Plek</th><th>Punten</th><th>Overwinningen</th></thead><tbody>';
                drivers.forEach(d=>{ html += `<tr><td>${d.name}</td><td>${d.seasonData.position != null ? d.seasonData.position : '—'}</td><td>${d.seasonData.points||0}</td><td>${d.seasonData.wins||0}</td></tr>`; });
                html += '</tbody></table>';
                teamStatsEl.innerHTML = html;
              });
            } else {
              // no drivers found for that season
              if(!tstats){ teamStatsEl.innerHTML = html; }
              else { teamStatsEl.innerHTML = html + '<p>Geen rijdersdata gevonden voor dit team in dit seizoen.</p>'; }
            }
          });
          teamSeasonsEl.appendChild(btn);
        });
        // show default season: prefer 2026 if available, otherwise last in seasons array
        let defaultBtn = Array.from(teamSeasonsEl.querySelectorAll('button')).find(b=>b.textContent && b.textContent.includes('2026'));
        if(!defaultBtn) defaultBtn = teamSeasonsEl.querySelector('button:last-child');
        if(defaultBtn) defaultBtn.click();
      }

      // Driver page helper (supports F1 and optional feeder series like F2/F3)
      const driverStatsEl = document.getElementById('driverStats');
      if(driverStatsEl){
        const driverSlug = (driverStatsEl.dataset && driverStatsEl.dataset.driver) || driverStatsEl.getAttribute('data-driver') || '';
        const seasons = stats.seasons;
        const dsourced = stats.driverStats[driverSlug];
        const controls = document.createElement('div');
        controls.className = 'driver-controls';

        function render(series, mode, season){
          // series: 'f1' or feeder key like 'f2'/'f3'
          if(series === 'f1'){
              if(mode === 'all'){
                const dt = dsourced && dsourced.allTime;
                // render career table from bySeason if available
                const bySeason = dsourced && dsourced.bySeason;
                if(bySeason && Object.keys(bySeason).length>0){
                  const seasons = Object.keys(bySeason).sort((a,b)=>b-a);
                  let html = '<h3>F1 Carrière</h3>';
                  html += '<table class="stats-table"><thead><tr><th>Seizoen</th><th>Team</th><th>Plek</th><th>Punten</th><th>Overwinningen</th><th>Podia</th><th>Poles</th><th>Fastest laps</th></tr></thead><tbody>';
                  seasons.forEach(s=>{
                    const sd = bySeason[s];
                    html += `<tr><td>${s}</td><td>${sd.team || '—'}</td><td>${sd.position != null ? sd.position : '—'}</td><td>${sd.points != null ? sd.points : 0}</td><td>${sd.wins||0}</td><td>${sd.podiums||0}</td><td>${sd.poles||0}</td><td>${sd.fastestLaps||0}</td></tr>`;
                  });
                  html += '</tbody></table>';
                  if(dt) html += `<p class="muted">All-time — ${dt.points} p, ${dt.wins} wins, ${dt.podiums || 0} podia</p>`;
                  driverStatsEl.innerHTML = html;
                } else {
                  driverStatsEl.innerHTML = dt ? `<h3>F1 All-time — ${dt.points} p, ${dt.wins} wins, ${dt.podiums || 0} podiums</h3>` : '<h3>Geen F1 all-time data</h3>';
                }
              } else if(mode === 'season'){
                const sdata = dsourced && dsourced.bySeason && dsourced.bySeason[season];
                if(sdata){
                  driverStatsEl.innerHTML = `<h3>F1 ${season} — ${sdata.points || 0} p, ${sdata.wins || 0} wins</h3><p>Team: ${sdata.team || '—'}</p><p>Plek: ${sdata.position != null ? sdata.position : '—'}</p><p>Podia: ${sdata.podiums||0} • Poles: ${sdata.poles||0} • Fastest laps: ${sdata.fastestLaps||0}</p>`;
                } else {
                  driverStatsEl.innerHTML = `<h3>Geen F1 data voor ${season}</h3>`;
                }
              }
              return;
            }
          // feeder series
          const feeder = dsourced && dsourced.feeder && dsourced.feeder[series];
          if(!feeder){ driverStatsEl.innerHTML = `<h3>Geen ${series.toUpperCase()} data beschikbaar</h3>`; return; }
          if(mode === 'all'){
            const f = feeder.allTime;
            driverStatsEl.innerHTML = f ? `<h3>${series.toUpperCase()} Carrière — ${f.points} p, ${f.wins} wins, ${f.podiums || 0} podiums</h3>` : `<h3>Geen ${series.toUpperCase()} carrière data</h3>`;
          } else if(mode === 'season'){
            const s = feeder.bySeason && feeder.bySeason[season];
            driverStatsEl.innerHTML = s ? `<h3>${series.toUpperCase()} ${season} — ${s.points} p, ${s.wins} wins</h3>` : `<h3>Geen ${series.toUpperCase()} data voor ${season}</h3>`;
          }
        }

        // F1 all-time button
        const f1All = document.createElement('button'); f1All.textContent = 'F1 Carrière';
        f1All.addEventListener('click', ()=>render('f1','all'));
        controls.appendChild(f1All);

        // F1 per-season buttons: only for seasons where driver has F1 data
        const f1Seasons = dsourced && dsourced.bySeason ? Object.keys(dsourced.bySeason).sort((a,b)=>b-a) : [];
        f1Seasons.forEach(s=>{ const b=document.createElement('button'); b.textContent = `F1 ${s}`; b.addEventListener('click', ()=>render('f1','season',s)); controls.appendChild(b); });

        // Add feeder series buttons if present in stats
        if(dsourced && dsourced.feeder){
          Object.keys(dsourced.feeder).forEach(fs=>{
            const allBtn = document.createElement('button'); allBtn.textContent = `${fs.toUpperCase()} Carrière`;
            allBtn.addEventListener('click', ()=>render(fs,'all'));
            controls.appendChild(allBtn);
            // if feeder has bySeason entries, add season buttons only for seasons present
            const feederSeasons = dsourced.feeder[fs].bySeason ? Object.keys(dsourced.feeder[fs].bySeason).sort((a,b)=>b-a) : [];
            if(feederSeasons.length>0){
              feederSeasons.forEach(s=>{ const b=document.createElement('button'); b.textContent = `${fs.toUpperCase()} ${s}`; b.addEventListener('click', ()=>render(fs,'season',s)); controls.appendChild(b); });
            }
          });
        }

        driverStatsEl.parentNode.insertBefore(controls, driverStatsEl);
        // trigger default view
        f1All.click();
      }

    }).catch(err=>{
      console.error('Stats load error', err);
      const teamStatsEl = document.getElementById('teamStats');
      const driverStatsEl = document.getElementById('driverStats');
      const msg = 'Kon statistieken niet laden. Open index.html of bekijk de bestanden in de data/ map.';
      if(teamStatsEl) teamStatsEl.innerHTML = `<p class="muted">${msg}</p>`;
      if(driverStatsEl) driverStatsEl.innerHTML = `<p class="muted">${msg}</p>`;
      const topDriversEl = document.getElementById('topDrivers');
      const topTeamsEl = document.getElementById('topTeams');
      if(topDriversEl) topDriversEl.innerHTML = '<li>Kon stats niet laden.</li>';
      if(topTeamsEl) topTeamsEl.innerHTML = '<li>Kon stats niet laden.</li>';
    });
});
