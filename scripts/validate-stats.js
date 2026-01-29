const fs = require('fs');
const path = require('path');

function slugify(name){
  return (name||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'');
}

function loadJson(rel){
  const p = path.join(__dirname,'..',rel);
  try{ return JSON.parse(fs.readFileSync(p,'utf8')); }catch(e){ console.error('Failed to read',p,e.message); process.exit(2); }
}

const entries = loadJson('data/entries-2026.json');
const stats = loadJson('data/stats.json');

const report = {missingInStats:[], missingInEntries:[], driversWithMissingFields:[], summary:{entriesDrivers:0, statsDrivers:0}};

const entryDrivers = [];
entries.teams.forEach(team=>{ team.drivers.forEach(d=> entryDrivers.push({name:d.name, slug: d.slug || slugify(d.name), team: team.slug || slugify(team.name)})); });
report.summary.entriesDrivers = entryDrivers.length;

const statsDrivers = Object.keys(stats.driverStats||{});
report.summary.statsDrivers = statsDrivers.length;

// find drivers present in entries but missing in stats
entryDrivers.forEach(ed=>{
  if(!stats.driverStats[ed.slug]) report.missingInStats.push({slug:ed.slug, name:ed.name, team:ed.team});
});

// find drivers present in stats but not in entries
statsDrivers.forEach(sd=>{
  const found = entryDrivers.find(e=>e.slug===sd);
  if(!found) report.missingInEntries.push({slug:sd});
});

// check for missing typical fields per driver
const fieldsToCheck = ['allTime','bySeason'];
Object.entries(stats.driverStats||{}).forEach(([slug, d])=>{
  const missing = [];
  fieldsToCheck.forEach(f=>{ if(!(f in d)) missing.push(f); });
  // check bySeason content for each season: ensure points exist and team for F1
  const seasonsMissing = [];
  if(d.bySeason){
    Object.entries(d.bySeason).forEach(([s, sd])=>{
      const seasonMiss = [];
      if(sd.points == null) seasonMiss.push('points');
      if(sd.team == null) seasonMiss.push('team');
      if(seasonMiss.length) seasonsMissing.push({season:s, missing:seasonMiss});
    });
  }
  if(missing.length || seasonsMissing.length){
    report.driversWithMissingFields.push({slug, missing: missing, seasonsMissing});
  }
});

// write report
const outPath = path.join(__dirname,'..','data','stats-validation-report.json');
fs.writeFileSync(outPath, JSON.stringify(report,null,2), 'utf8');
console.log('Validation complete. Report written to', outPath);
