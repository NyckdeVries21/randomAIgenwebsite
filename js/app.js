document.addEventListener('DOMContentLoaded', ()=>{
  const navToggle = document.getElementById('navToggle');
  const mainNav = document.getElementById('mainNav');
  navToggle.addEventListener('click', ()=>{
    const visible = mainNav.style.display === 'block';
    mainNav.style.display = visible ? '' : 'block';
  });

  // Simple driver search
  const search = document.getElementById('driverSearch');
  const grid = document.getElementById('driversGrid');
  if(search && grid){
    search.addEventListener('input', ()=>{
      const q = search.value.trim().toLowerCase();
      const items = grid.querySelectorAll('.card');
      items.forEach(it=>{
        const name = it.dataset.name.toLowerCase();
        it.style.display = name.includes(q) ? '' : 'none';
      });
    });
  }

  // Load local 2026 calendar JSON and populate table
  const calendarBody = document.getElementById('calendarBody');
  if(calendarBody){
    fetch('data/calendar-2026.json')
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
  fetch('data/entries-2026.json')
    .then(r=>r.ok ? r.json() : Promise.reject('Failed to load entries'))
    .then(data=>{
      // Render teams
      if(teamsGrid){
        teamsGrid.innerHTML = '';
        data.teams.forEach(team=>{
          const slug = team.slug || team.name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'');
          const a = document.createElement('a');
          a.href = `teams/${slug}/index.html`;
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
            art.innerHTML = `<h3><a href="teams/${teamSlug}/drivers/${driverSlug}.html">${driver.name}</a></h3><p>Team: <a href="teams/${teamSlug}/index.html">${team.name}</a></p><p>Land: ${driver.nationality}</p>`;
            driversGrid.appendChild(art);
          });
        });
      }
    }).catch(err=>{
      console.error('Entries load error', err);
      if(teamsGrid) teamsGrid.innerHTML = '<div class="card">Kon teams niet laden.</div>';
      if(driversGrid) driversGrid.innerHTML = '<div class="card">Kon rijders niet laden.</div>';
    });
});
